"""Recheck captured candidate code against the saved behavioral cases, without inference."""

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from inspect_ai.log import read_eval_log

from showcase_evals.sandbox import TMP, invoke

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest_path = ROOT / "evidence/coding-integrity/data.json"
    manifest = json.loads(manifest_path.read_text())
    logs = {entry["path"]: read_eval_log(ROOT / entry["path"]) for entry in manifest["files"]}
    results = []
    TMP.mkdir(exist_ok=True)
    for episode in manifest["episodes"]:
        identifier = episode["episode_id"].rsplit("/", 1)[1]
        sample = next(s for s in logs[episode["trace"]].samples if s.id == identifier)
        captured = sample.store.get("files")
        checks = sample.store.get("independent_checks", {}).get("checks")
        if not captured or not checks:
            results.append({"episode_id": episode["episode_id"], "recheckable": False})
            continue
        with tempfile.TemporaryDirectory(dir=TMP, prefix="rescore-") as directory:
            workspace = Path(directory)
            for name in ("app.py", "test_visible.py"):
                (workspace / name).write_text(captured[name])
            cases = []
            for check in checks:
                observed = invoke(workspace, check["request"])
                passed = observed["returncode"] == 0 and json.dumps(
                    observed["response"], sort_keys=True
                ) == json.dumps(check["expected"], sort_keys=True)
                cases.append(
                    {"case": check["case"], "original": check["passed"], "rescored": passed}
                )
        results.append(
            {
                "episode_id": episode["episode_id"],
                "recheckable": True,
                "same_outcomes": all(c["original"] == c["rescored"] for c in cases),
                "cases": cases,
            }
        )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = {
        "rescore_id": stamp,
        "model_calls": 0,
        "input_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "rescore_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sandbox_source_sha256": hashlib.sha256(
            (ROOT / "src/showcase_evals/sandbox.py").read_bytes()
        ).hexdigest(),
        "episodes": results,
    }
    private = ROOT / ".local-runs" / f"rescore-{stamp}"
    private.mkdir(parents=True)
    text = json.dumps(evidence, indent=2) + "\n"
    (private / "result.json").write_text(text)
    (ROOT / "evidence/coding-integrity/rescore.json").write_text(text)
    comparable = [r for r in results if r["recheckable"]]
    matched = sum(r["same_outcomes"] for r in comparable)
    print(
        f"Rechecked {len(comparable)}/{len(results)} captured episodes; {matched} reproduced every recorded case outcome. No model calls."
    )
    if matched != len(comparable) or len(comparable) != len(results):
        raise SystemExit("Recheck coverage or outcome mismatch; inspect the new rescore artifact")


if __name__ == "__main__":
    main()
