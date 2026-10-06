"""Execute a recorded study through Hawk's local runner; no credentials in argv."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from showcase_evals.free_openrouter import fetch_catalog, validate_free_model

ROOT = Path(__file__).resolve().parents[1]


def snapshot_sources(output, study="provider-pilot"):
    paths = [ROOT / "pyproject.toml", ROOT / "uv.lock"]
    paths += sorted((ROOT / "src").rglob("*.py"))
    paths += sorted((ROOT / "scripts").glob("*.py"))
    paths += sorted((ROOT / "studies" / study).glob("*"))
    paths += sorted((ROOT / "environments").rglob("*.py"))
    hashes = {}
    with zipfile.ZipFile(output / "source.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            if not path.is_file():
                continue
            relative = str(path.relative_to(ROOT))
            content = path.read_bytes()
            hashes[relative] = hashlib.sha256(content).hexdigest()
            archive.writestr(relative, content)
    (output / "source-hashes.json").write_text(
        json.dumps({"captured_before_inference": True, "files": hashes}, indent=2)
    )


def key_status(key):
    response = httpx.get(
        "https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"}, timeout=20
    )
    response.raise_for_status()
    data = response.json()["data"]
    return {
        k: data.get(k) for k in ("usage", "usage_daily", "limit", "limit_remaining", "is_free_tier")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--study", choices=["provider-pilot", "coding-integrity"], default="provider-pilot"
    )
    parser.add_argument(
        "--development",
        action="store_true",
        help="Coding infrastructure smoke task; excluded from study results",
    )
    parser.add_argument(
        "--monitor", action="store_true", help="Audit the exported coding-study evidence"
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        required=True,
        help="Explicit profile IDs from the committed pilot matrix",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path.home() / ".config/hawk-inspect-showcase/providers.json",
    )
    args = parser.parse_args()
    (ROOT / ".tmp").mkdir(exist_ok=True)
    if args.monitor and (args.study != "coding-integrity" or args.development):
        parser.error("--monitor requires --study coding-integrity and excludes --development")
    profiles = json.loads((ROOT / "studies/provider-pilot/profiles.json").read_text())
    indexed = {profile["id"]: profile for profile in profiles}
    if len(set(args.profiles)) != len(args.profiles):
        parser.error("Duplicate profile IDs are not independent replications")
    try:
        selected = [indexed[name] for name in args.profiles]
    except KeyError as error:
        parser.error(f"Unknown profile: {error.args[0]}")
    if args.credentials.stat().st_mode & 0o077:
        parser.error("Credential file must not be accessible to group or other users")
    keys = json.loads(args.credentials.read_text())
    env = os.environ.copy()
    for name in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        if not keys.get(name):
            parser.error(f"Missing {name}")
        env[name] = keys[name]
    env.update(
        {
            "AWS_EC2_METADATA_DISABLED": "true",
            "INSPECT_DISABLE_TELEMETRY": "1",
            "TMPDIR": str(ROOT / ".tmp"),
            "PYTHONUNBUFFERED": "1",
        }
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / ".local-runs" / stamp
    output.mkdir(parents=True)
    snapshot_sources(output, args.study)
    env["SHOWCASE_RATE_STATE"] = str(ROOT / ".local-runs" / "request-pacing.json")
    catalog = fetch_catalog()
    before = key_status(keys["OPENROUTER_API_KEY"])
    (output / "openrouter-catalog.json").write_text(json.dumps(catalog, indent=2))
    (output / "key-status-before.json").write_text(json.dumps(before, indent=2))
    models = []
    for profile in selected:
        model = profile["model"]
        if model.startswith("free_openrouter/"):
            validate_free_model(model.removeprefix("free_openrouter/"), catalog)
        elif not model.startswith("groq/"):
            raise ValueError("Pilot permits only Groq and guarded free OpenRouter models")
        config = {
            "max_tokens": 1024 if args.study == "provider-pilot" or args.monitor else 2048,
            "max_retries": 0,
            "timeout": 70,
            "max_connections": 1,
            "cache": False,
        }
        if "effort" in profile:
            config["reasoning_effort"] = profile["effort"]
        model_args = {"config": config, "max_retries": 0}
        model_args["streaming" if model.startswith("groq/") else "stream"] = False
        if "thinking" in profile:
            model_args["reasoning_enabled"] = profile["thinking"]
        models.append({"name": model, "args": model_args})
    task_item = (
        {"name": "provider_probe"}
        if args.study == "provider-pilot"
        else {"name": "coding_integrity", "args": {"development": args.development}}
    )
    monitor_input = ROOT / "evidence/coding-integrity/monitor-inputs.json"
    if args.monitor:
        task_item = {"name": "coding_monitor", "args": {"input_manifest": str(monitor_input)}}
    study = {
        "name": args.study + ("-development" if args.development else ""),
        "tasks": [{"package": str(ROOT), "name": "showcase_evals", "items": [task_item]}],
        "models": [{"package": "inspect-ai", "items": models}],
        "epochs": 1,
        "limit": 2 if args.study == "provider-pilot" else None,
        "time_limit": 120 if args.study == "provider-pilot" else 900,
        "message_limit": 8 if args.study == "provider-pilot" else 40,
        "max_retries": 0,
        "retry_attempts": 1,
        "log_model_api": True,
        "metadata": {
            "study": args.study,
            "development": args.development,
            "profile_ids": args.profiles,
            "free_only": True,
            "protocol": f"studies/{args.study}/PROTOCOL.md",
        },
    }
    infra = {
        "job_id": "pilot-" + stamp.lower(),
        "created_by": "local",
        "email": "local",
        "model_groups": ["local"],
        "log_dir": str(output / "logs"),
        "max_samples": 1,
        "max_tasks": 1,
        "max_subprocesses": 1,
        "display": "plain",
        "retry_attempts": 1,
        "retry_cleanup": False,
        "continue_on_fail": True,
        "fail_on_error": False,
    }
    (output / "hawk.yaml").write_text(yaml.safe_dump(study, sort_keys=False))
    (output / "infra.yaml").write_text(yaml.safe_dump(infra, sort_keys=False))
    manifest = {
        "run_id": stamp,
        "study": args.study,
        "development": args.development,
        "role": "monitor" if args.monitor else "actor",
        "profiles": selected,
        "started_at": stamp,
        "runtime": {
            "evaluator_python": platform.python_version(),
            "machine": platform.machine(),
            "kernel": platform.release(),
            "sandbox_python": subprocess.check_output(
                ["/usr/bin/python3", "--version"], text=True
            ).strip(),
            "bubblewrap": subprocess.check_output(
                ["/usr/bin/bwrap", "--version"], text=True
            ).strip(),
            "sandbox_python_sha256": hashlib.sha256(
                Path("/usr/bin/python3").read_bytes()
            ).hexdigest(),
            "bubblewrap_sha256": hashlib.sha256(Path("/usr/bin/bwrap").read_bytes()).hexdigest(),
        },
        "protocol_sha256": hashlib.sha256(
            (ROOT / f"studies/{args.study}/PROTOCOL.md").read_bytes()
        ).hexdigest(),
        "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"RUN_DIRECTORY={output}", flush=True)
    command = [
        sys.executable,
        "-m",
        "hawk.runner.run_eval_set",
        str(output / "hawk.yaml"),
        str(output / "infra.yaml"),
    ]
    # Raw console output is private. Callers get progress and return code only.
    try:
        with (output / "runner.log").open("w") as log:
            result = subprocess.run(
                command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
            )
        manifest["runner_exit_code"] = result.returncode
    finally:
        after = key_status(keys["OPENROUTER_API_KEY"])
        (output / "key-status-after.json").write_text(json.dumps(after, indent=2))
        manifest["openrouter_usage_delta_usd"] = after["usage"] - before["usage"]
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        f"Hawk exit code: {result.returncode}; "
        f"OpenRouter usage delta: {manifest['openrouter_usage_delta_usd']}"
    )
    if manifest["openrouter_usage_delta_usd"] != 0:
        raise RuntimeError("Nonzero OpenRouter usage observed; stop all further runs")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
