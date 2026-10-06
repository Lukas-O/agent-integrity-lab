"""Verify public artifact integrity, trace-derived claims, and obvious secret leaks."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(
    r"(?:sk-or-v1-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]{20,})"
)
HOST_PATH = re.compile(r"/home/[A-Za-z0-9][A-Za-z0-9_.-]*/")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(path):
    data = json.loads(path.read_text())
    logs = {}
    for record in data["files"]:
        target = ROOT / record["path"]
        assert sha(target) == record["reviewed_sha256"], f"Trace hash mismatch: {record['path']}"
        logs[record["path"]] = read_eval_log(target)
    for batch in data["batches"]:
        archive = ROOT / batch["source_archive"]["path"]
        assert sha(archive) == batch["source_archive"]["sha256"], "Source archive changed"
        with zipfile.ZipFile(archive) as content:
            for name, expected in batch["source_hashes"]["files"].items():
                assert hashlib.sha256(content.read(name)).hexdigest() == expected, (
                    f"Archived source changed: {name}"
                )
    if "episodes" not in data:
        assert len(data["samples"]) == sum(len(log.samples or []) for log in logs.values())
        return
    for row in data["episodes"]:
        identifier = row["episode_id"].rsplit("/", 1)[1]
        sample = next(s for s in logs[row["trace"]].samples if s.id == identifier)
        assert row["functional_pass"] == sample.store.get("independent_checks", {}).get("passed")
        assert row["claim_done"] == sample.store.get("claim_done")
        checks = sample.store.get("independent_checks", {}).get("checks")
        if checks:
            assert row["functional_pass"] == all(check["passed"] for check in checks)
        changed = any(
            a.get("path") == "test_visible.py" and a.get("changed") and not a.get("blocked")
            for a in sample.store.get("actions", [])
        )
        assert row["test_modified"] == changed
        assert row["agent_seconds"] == sample.store.get("agent_seconds")
    actor_samples = sum(
        len(log.samples or [])
        for log in logs.values()
        if log.eval.task.rsplit("/", 1)[-1] == "coding_integrity"
    )
    assert actor_samples == len(data["episodes"]), "An actor attempt was omitted from the report"
    assert len(data["requests"]) == sum(
        event.event == "model"
        for log in logs.values()
        for sample in log.samples or []
        for event in sample.events
    ), "Request coverage changed"
    inputs = json.loads((path.parent / "monitor-inputs.json").read_text())
    actors = {row["episode_id"]: row for row in data["episodes"] if not row["development"]}
    assert set(actors) == {row["id"] for row in inputs}
    for record in inputs:
        assert set(record["evidence"]) == {
            "requirement",
            "before",
            "after",
            "actions",
            "final_answer",
        }
        actor = actors[record["id"]]
        assert record["truth"] == {
            "tampering": actor["test_modified"],
            "unsupported_completion": bool(actor["unsupported_completion"]),
        }


def main():
    for path in (ROOT / "evidence").glob("*/data.json"):
        verify_manifest(path)
    revision_path = ROOT / "evidence/coding-integrity/scorer-v2.json"
    if revision_path.exists():
        revision = json.loads(revision_path.read_text())
        base_path = revision_path.parent / "data.json"
        base = json.loads(base_path.read_text())
        assert revision["input_manifest_sha256"] == sha(base_path)
        cases_path = ROOT / "studies/coding-integrity/scorer-v2.json"
        assert revision["additional_cases_sha256"] == sha(cases_path)
        assert revision["audit_script_sha256"] == sha(ROOT / "scripts/audit_counterexamples.py")
        cases = json.loads(cases_path.read_text())["cases"]
        original = {row["episode_id"]: row for row in base["episodes"]}
        rescore = json.loads((revision_path.parent / "rescore.json").read_text())
        assert rescore["input_manifest_sha256"] == sha(base_path)
        assert rescore["rescore_script_sha256"] == sha(ROOT / "scripts/rescore_coding.py")
        assert rescore["sandbox_source_sha256"] == sha(ROOT / "src/showcase_evals/sandbox.py")
        assert set(original) == {row["episode_id"] for row in rescore["episodes"]}
        assert all(row["recheckable"] and row["same_outcomes"] for row in rescore["episodes"])
        assert set(original) == {row["episode_id"] for row in revision["episodes"]}
        for row in revision["episodes"]:
            prior = original[row["episode_id"]]
            assert row["v1_functional_pass"] == prior["functional_pass"]
            assert row["v2_functional_pass"] == (
                prior["functional_pass"]
                and all(check["passed"] for check in row["additional_checks"])
            )
            assert row["v1_unsupported_completion"] == prior["unsupported_completion"]
            expected_claim = (
                bool(prior["claim_done"] and not row["v2_functional_pass"])
                if prior["claim_done"] is not None and row["v2_functional_pass"] is not None
                else None
            )
            assert row["v2_unsupported_completion"] == expected_claim
            expected = cases.get(prior["family"], [])
            assert [c["id"] for c in row["additional_checks"]] == [c["id"] for c in expected]
            for actual, defined in zip(row["additional_checks"], expected, strict=True):
                assert (
                    actual["request"] == defined["request"]
                    and actual["expected"] == defined["expected"]
                )
                observed = actual["observed"]
                assert actual["passed"] == (
                    observed["returncode"] == 0
                    and json.dumps(observed["response"], sort_keys=True)
                    == json.dumps(defined["expected"], sort_keys=True)
                )
        with zipfile.ZipFile(revision_path.parent / "analysis-v1.zip") as archive:
            assert (
                hashlib.sha256(archive.read("analysis/coding_integrity.py")).hexdigest()
                == base["analysis_sha256"]
            )
        build = json.loads((ROOT / "reports/coding-integrity/build.json").read_text())
        assert build["input_manifest_sha256"] == sha(base_path)
        assert build["scorer_revision_sha256"] == sha(revision_path)
        for path, expected in build["analysis_sources"].items():
            assert sha(ROOT / path) == expected
    scanned = 0
    paths = [p for p in ROOT.iterdir() if p.is_file()]
    for directory in (
        "src",
        "scripts",
        "analysis",
        "tests",
        "environments",
        "studies",
        "research",
        "docs",
        "reports",
        "evidence",
        ".github",
    ):
        paths.extend(
            p for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
    for path in paths:
        if path.suffix in {".png", ".pyc"}:
            continue
        if path.suffix == ".eval":
            contents = [read_eval_log(path).model_dump_json()]
        elif path.suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                contents = [archive.read(name).decode() for name in archive.namelist()]
        else:
            contents = [path.read_text()]
        for content in contents:
            assert not SECRET.search(content), f"Credential-like content: {path.relative_to(ROOT)}"
            assert not HOST_PATH.search(content), f"Local home path: {path.relative_to(ROOT)}"
            scanned += 1
        if path.suffix == ".md":
            prose = re.sub(r"```.*?```", "", contents[0], flags=re.DOTALL)
            for target in re.findall(r"\]\(([^)]+)\)", prose):
                target = target.split("#")[0]
                if target and not re.match(r"[a-z]+:", target):
                    assert (path.parent / target).exists(), (
                        f"Broken local link in {path.relative_to(ROOT)}: {target}"
                    )
    print(
        f"Verified trace coverage and artifact hashes; scanned {scanned} public text/trace/source entries."
    )


if __name__ == "__main__":
    main()
