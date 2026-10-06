"""Publish reviewed pilot evidence and regenerate graphs without model calls."""

import argparse
import csv
import hashlib
import json
import shutil
import statistics
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from evidence_helpers import clean, failure_kind
from inspect_ai.log import EvalLog, read_eval_log, write_eval_log

ROOT = Path(__file__).resolve().parents[1]


def label(log):
    config = log.eval.model_generate_config
    effort = config.reasoning_effort or (
        "on"
        if log.eval.model_args.get("reasoning_enabled") is True
        else "off"
        if log.eval.model_args.get("reasoning_enabled") is False
        else "mandatory"
    )
    return log.eval.model, effort


def export(run_dirs, destination):
    destination.mkdir(parents=True, exist_ok=True)
    traces = destination / "traces"
    traces.mkdir(exist_ok=True)
    sources = destination / "sources"
    sources.mkdir(exist_ok=True)
    samples, requests, files, batches = [], [], [], []
    profiles = json.loads((ROOT / "studies/provider-pilot/profiles.json").read_text())
    by_config = {
        (
            p["model"],
            p.get(
                "effort",
                "on"
                if p.get("thinking") is True
                else "off"
                if p.get("thinking") is False
                else "mandatory",
            ),
        ): p["id"]
        for p in profiles
    }
    for directory in run_dirs:
        manifest = json.loads((directory / "manifest.json").read_text())
        manifest["source_hashes"] = json.loads((directory / "source-hashes.json").read_text())
        manifest["source_hash_capture"] = (
            "Captured before inference."
            if manifest["source_hashes"].get("captured_before_inference")
            else "Captured after inference while the evaluated source files were unchanged."
        )
        source_archive = sources / f"{manifest['run_id']}.zip"
        shutil.copyfile(directory / "source.zip", source_archive)
        manifest["source_archive"] = {
            "path": str(source_archive.relative_to(ROOT)),
            "sha256": hashlib.sha256(source_archive.read_bytes()).hexdigest(),
        }
        catalog = json.loads((directory / "openrouter-catalog.json").read_text())
        selected_ids = {
            profile["model"].removeprefix("free_openrouter/")
            for profile in manifest["profiles"]
            if profile["model"].startswith("free_openrouter/")
        }
        manifest["selected_openrouter_catalog"] = [
            entry for entry in catalog["data"] if entry["id"] in selected_ids
        ]
        batches.append(manifest)
        for source in sorted((directory / "logs").glob("*.eval")):
            original = read_eval_log(source)
            data = clean(original.model_dump(mode="json"))
            # Error text may embed serialized request headers. Keep diagnostic
            # classes publicly; original detailed tracebacks remain private.
            for sample in data.get("samples") or []:
                error = sample.get("error")
                if error:
                    original_sample = next(s for s in original.samples if s.id == sample["id"])
                    error["message"] = failure_kind(original_sample)
                    for key in ("traceback", "traceback_ansi"):
                        if key in error:
                            error[key] = "[private diagnostic traceback omitted]"
                for event in sample.get("events", []):
                    for key in ("traceback", "traceback_ansi"):
                        if event.get(key):
                            event[key] = "[private diagnostic traceback omitted]"
                    if event.get("error") and isinstance(event["error"], str):
                        event["error"] = "[see sample error category]"
            reviewed = EvalLog.model_validate(data)
            target = traces / source.name
            write_eval_log(reviewed, str(target))
            file_record = {
                "path": str(target.relative_to(ROOT)),
                "raw_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "reviewed_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
            files.append(file_record)
            model, effort = label(original)
            profile = by_config[(model, effort)]
            for sample in original.samples or []:
                scores = list((sample.scores or {}).values())
                score = scores[0].value if scores else None
                events = [e for e in sample.events if e.event == "model"]
                samples.append(
                    {
                        "run_id": manifest["run_id"],
                        "profile": profile,
                        "model": model,
                        "thinking": effort,
                        "sample_id": sample.id,
                        "epoch": sample.epoch,
                        "correct": score,
                        "failure": failure_kind(sample),
                        "agent_seconds": sample.store.get("agent_seconds"),
                        "request_events": len(events),
                        "trace": file_record["path"],
                    }
                )
                for index, event in enumerate(events):
                    output = event.output
                    usage = output.usage
                    response = event.call.response if event.call else {}
                    if not isinstance(response, dict):
                        response = {}
                    request = event.call.request if event.call else {}
                    transmitted = request.get("reasoning_effort") or request.get(
                        "extra_body", {}
                    ).get("reasoning")
                    requests.append(
                        {
                            "run_id": manifest["run_id"],
                            "profile": profile,
                            "sample_id": sample.id,
                            "request_index": index,
                            "model": model,
                            "thinking": effort,
                            "transmitted_reasoning": json.dumps(transmitted, sort_keys=True),
                            "returned_model": response.get("model"),
                            "response_id": response.get("id"),
                            "system_fingerprint": response.get("system_fingerprint"),
                            "service_tier": response.get("service_tier"),
                            "provider_usage": json.dumps(response.get("usage", {}), sort_keys=True),
                            "provider": response.get("provider")
                            or ("Groq" if model.startswith("groq/") else None),
                            "request_seconds": output.time,
                            "event_seconds": (
                                (event.completed - event.timestamp).total_seconds()
                                if event.completed
                                else None
                            ),
                            "input_tokens": usage.input_tokens if usage else None,
                            "output_tokens": usage.output_tokens if usage else None,
                            "retries": event.retries,
                            "error": bool(event.error),
                            "stop_reason": output.stop_reason if output.choices else None,
                            "provider_timing": json.dumps(output.metadata or {}, sort_keys=True),
                            "trace": file_record["path"],
                        }
                    )
    evidence = {
        "samples": samples,
        "requests": requests,
        "batches": batches,
        "files": files,
        "publication": {
            "transformations": [
                "transport headers removed",
                "local paths/hostname replaced",
                "opaque signatures removed",
                "diagnostic tracebacks omitted",
                "errors categorized; original diagnostics retained privately",
            ],
            "scope": "all pilot samples, including errors and truncation",
        },
    }
    evidence = clean(evidence)
    (destination / "data.json").write_text(json.dumps(evidence, indent=2) + "\n")
    for name in ("samples", "requests"):
        rows = evidence[name]
        with (destination / f"{name}.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return evidence


def render(evidence, report):
    report.mkdir(parents=True, exist_ok=True)
    samples, requests = evidence["samples"], evidence["requests"]
    profiles = list(dict.fromkeys(row["profile"] for row in samples))
    # Stable alphabetic ordering avoids visually ranking two-point estimates.
    profiles.sort()
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
        }
    )
    for mode, title in [
        ("response", "Complete response latency — compatibility pilot"),
        ("task", "Tool-task elapsed time and outcome — compatibility pilot"),
    ]:
        fig, axis = plt.subplots(figsize=(11, 7.2))
        for y, profile in enumerate(profiles):
            rows = [
                r for r in (requests if mode == "response" else samples) if r["profile"] == profile
            ]
            timed = [
                (r, r["request_seconds"] if mode == "response" else r["agent_seconds"])
                for r in rows
            ]
            timed = [
                (r, t) for r, t in timed if t is not None and (mode != "response" or not r["error"])
            ]
            for index, (row, value) in enumerate(timed):
                success = mode == "response" or row["correct"] == 1
                axis.scatter(
                    value,
                    y + (index - (len(timed) - 1) / 2) * 0.055,
                    color="#1765a0" if success else "#c23b32",
                    marker="o" if success else "x",
                    s=42,
                    alpha=0.85,
                    zorder=3,
                )
            if timed:
                median = statistics.median(t for _, t in timed)
                axis.scatter(median, y, marker="|", s=230, color="#172a3a", zorder=4)
            if mode == "response":
                note = f"{len(timed)}/{len(rows)} requests timed"
            else:
                note = f"{sum(r['correct'] == 1 for r in rows)}/{len(rows)} correct"
            axis.text(1.01, y, note, transform=axis.get_yaxis_transform(), va="center", fontsize=9)
        axis.set_yticks(range(len(profiles)), profiles)
        axis.invert_yaxis()
        axis.set_xlabel("Elapsed seconds (client observed)")
        axis.set_xlim(left=0)
        axis.grid(axis="x", alpha=0.18)
        axis.set_title(title, loc="left", weight="bold", pad=18)
        detail = (
            "Completed responses, including truncation; error coverage at right. Bars mark medians."
            if mode == "response"
            else "Blue: checked correct. Red: error or truncation. Bars mark medians."
        )
        fig.text(
            0.03,
            0.025,
            detail + "\nTwo fictional tool tasks per setting; not a model-speed ranking.",
            fontsize=9,
            color="#445566",
        )
        fig.subplots_adjust(left=0.27, right=0.79, bottom=0.13, top=0.90)
        for extension in ("svg", "png"):
            fig.savefig(report / f"{mode}-latency.{extension}", dpi=160, facecolor="white")
        plt.close(fig)

    failures = Counter(row["failure"] for row in samples if row["failure"])
    correct = sum(row["correct"] == 1 for row in samples)
    lines = [
        "# Provider compatibility and timing pilot — 2026-10-06",
        "",
        (
            f"**{len(samples)} attempted tool tasks across {len(profiles)} configurations; "
            f"{correct} checked correct.** This is a compatibility pilot, not the coding-agent "
            "safety study or a production-performance benchmark."
        ),
        "",
        (
            "Real inference ran through Hawk 3.6.0's local evaluation runner and Inspect "
            "0.3.276. Each sample read a fictional order through a Python tool and returned "
            "a checked calculation and approval decision. No real message was sent."
        ),
        "",
        "![Response latency](response-latency.svg)",
        "",
        "![Task time and outcome](task-latency.svg)",
        "",
        "| Configuration | Correct / attempted | Median task seconds | Observed failures |",
        "| --- | ---: | ---: | --- |",
    ]
    for profile in profiles:
        rows = [r for r in samples if r["profile"] == profile]
        times = [r["agent_seconds"] for r in rows if r["agent_seconds"] is not None]
        failed = ", ".join(sorted({r["failure"] for r in rows if r["failure"]})) or "—"
        lines.append(
            f"| `{profile}` | {sum(r['correct'] == 1 for r in rows)}/{len(rows)} | "
            f"{statistics.median(times):.3f} | {failed} |"
        )
    cost = sum(batch.get("openrouter_usage_delta_usd", 0) for batch in evidence["batches"])
    lines += [
        "",
        "## Interpretation and limits",
        "",
        (
            f"Recorded failure categories: {dict(failures)}. "
            "A completed Hawk evaluation set can still contain sample errors; the table "
            "counts individual samples, not the runner's exit code."
        ),
        "",
        (
            "Rate-limit failures establish an availability problem during these requests; "
            "they do not establish whether account quota or upstream capacity caused it. "
            "Tool-protocol errors and output truncation are separate failure classes. "
            "The 1,024-token completion cap includes reasoning where the provider counts it; "
            "a truncated high-effort response is not evidence that the model cannot solve the task."
        ),
        "",
        (
            "These are two observations per configuration on very small tasks, with no "
            "independent replication, randomized comparison, confidence intervals, or stable "
            "tail-latency estimate. Request counts can differ when a task fails. The response "
            "figure excludes unsuccessful requests explicitly; the task figure includes failures. "
            "Do not read fast error returns as successful model performance."
        ),
        "",
        (
            "Thinking labels are provider controls, not matched compute. Groq Qwen's requested "
            "high maps to native xhigh in the documented interface. Input/output length, "
            "cache behavior, routing, network conditions, and server load affect elapsed times. "
            "No first-token or hidden-thinking duration was measured."
        ),
        "",
        (
            f"OpenRouter key usage changed by **${cost:.6f}** across the recorded batches. "
            "Groq ran on the supplied free-tier account; its request responses are not a "
            "billing ledger. No additional purchase or upgrade was made. The owner's earlier "
            "$10 credit purchase is separate from these inference usage measurements."
        ),
        "",
        "## Evidence and reproduction",
        "",
        "- [Protocol](../../studies/provider-pilot/PROTOCOL.md)",
        "- [Profile definitions](../../studies/provider-pilot/profiles.json)",
        "- [Sample data](../../evidence/provider-pilot/samples.csv)",
        "- [Request data](../../evidence/provider-pilot/requests.csv)",
        (
            "- [Trace manifest, hashes and publication transformations]"
            "(../../evidence/provider-pilot/data.json)"
        ),
        "",
        (
            "The compact reviewed pilot `.eval` logs are kept with this initial evidence set. "
            "Future larger studies will use versioned release bundles. Original diagnostic "
            "tracebacks remain private; publication transformations are recorded in the manifest."
        ),
        "",
        "Regenerate this report and its figures without credentials or new inference:",
        "",
        "```bash",
        "uv sync --frozen",
        "uv run python analysis/provider_pilot.py --render-only",
        "```",
        "",
    ]
    (report / "README.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--run-dir", action="append", type=Path)
    args = parser.parse_args()
    destination = ROOT / "evidence/provider-pilot"
    if args.render_only:
        evidence = json.loads((destination / "data.json").read_text())
    else:
        if not args.run_dir:
            parser.error("Export requires explicit --run-dir values")
        evidence = export(args.run_dir, destination)
    render(evidence, ROOT / "reports/provider-pilot")
    print(
        f"Published {len(evidence['samples'])} sample records and "
        f"{len(evidence['requests'])} model-event records."
    )


if __name__ == "__main__":
    main()
