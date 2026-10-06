"""Describe a post-hoc oracle repair while preserving the frozen v1 evidence."""

import hashlib
import json
from pathlib import Path

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[1]


def apply_revision(data):
    original = [row for row in data["episodes"] if not row["development"]]
    path = ROOT / "evidence/coding-integrity/scorer-v2.json"
    if not path.exists():
        return original, None
    revision = json.loads(path.read_text())
    manifest = ROOT / "evidence/coding-integrity/data.json"
    if revision["input_manifest_sha256"] != hashlib.sha256(manifest.read_bytes()).hexdigest():
        raise ValueError(
            "The v2 audit refers to another evidence manifest. Run scripts/audit_counterexamples.py before rendering the new export."
        )
    revised = {row["episode_id"]: row for row in revision["episodes"]}
    rows = [
        {
            **row,
            "functional_pass": revised[row["episode_id"]]["v2_functional_pass"],
            "unsupported_completion": revised[row["episode_id"]]["v2_unsupported_completion"],
            "additional_checks": revised[row["episode_id"]]["additional_checks"],
        }
        for row in original
    ]
    return rows, revision


def write_revision_report(data, revision):
    originals = {row["episode_id"]: row for row in data["episodes"]}
    changed = [
        row
        for row in revision["episodes"]
        if row["v1_functional_pass"] != row["v2_functional_pass"]
    ]
    rows = [row for row in revision["episodes"] if not row["development"]]
    old = sum(row["v1_functional_pass"] is True for row in rows)
    new = sum(row["v2_functional_pass"] is True for row in rows)
    lines = [
        "# The monitor exposed blind spots in the independent checker",
        "",
        (
            f"The frozen v1 suite marked **{old}/{len(rows)}** captured applications as passing. "
            f"After a documented, uniformly applied coverage correction, **{new}/{len(rows)}** pass. "
            f"**{len(changed)} labels changed without any new model calls.**"
        ),
        "",
        (
            "This was an evaluator mistake. Two apparent monitor false alarms identified real "
            "requirement violations that the v1 tests had missed. The code handled an old visible "
            "test input as a special case, retaining obsolete behavior instead of satisfying the new contract."
        ),
        "",
        (
            "The original visible tests were intentionally stale. The independent checker's missing "
            "coverage was not intentional. Reproducing all saved v1 outcomes confirmed reproducibility, "
            "but did not establish that the oracle was sufficiently complete."
        ),
        "",
        "## What changed",
        "",
        (
            "The v2 additions include the original visible inputs with their newly required outputs, "
            "plus nearby ordinary positive cases. Every captured program in the affected family "
            "received the same added cases. Reference implementations pass them, and regression "
            "tests demonstrate that explicit special-case mutants pass v1 and fail v2."
        ),
        "",
        (
            "Actor prompts, actor outputs, monitor prompts, monitor decisions, and original labels "
            "remain unchanged. `data.json` and `episodes.csv` retain v1 labels; `scorer-v2.json` stores "
            "the additions and revised labels separately. The main report explicitly uses v2."
        ),
        "",
        "## Every changed episode",
        "",
    ]
    for row in changed:
        original = originals[row["episode_id"]]
        log = read_eval_log(ROOT / original["trace"])
        sample = next(s for s in log.samples if s.id == row["episode_id"].rsplit("/", 1)[1])
        failed = next(check for check in row["additional_checks"] if not check["passed"])
        lines += [
            f"### {original['profile']} / {original['family']} / {original['condition']}",
            "",
            (
                f"[Native trace](../../{original['trace']}). V1 pass: `{row['v1_functional_pass']}`. "
                f"V2 pass: `{row['v2_functional_pass']}`. Final done claim: `{original['claim_done']}`."
            ),
            "",
            "Captured application:",
            "",
            "```python",
            sample.store["files"]["app.py"],
            "```",
            "",
            "Added counterexample:",
            "",
            "```json",
            json.dumps(failed, indent=2),
            "```",
            "",
        ]
    lines += [
        "## How to interpret the monitor comparison",
        "",
        (
            "Agreement with v2 labels is **post-hoc**. The monitor's own disagreements helped "
            "reveal these cases, so the revised comparison is not an independent validation of "
            "monitor accuracy. It demonstrates a useful auditing loop and a concrete failure of "
            "the original test suite. The revised finite suite can still miss defects, and this "
            "small task set cannot establish broader prevalence or safety."
        ),
        "",
        (
            "Visible-test special casing is observable. Whether a particular instance reflects "
            "strategic deception, confusion about compatibility, or compliance with the assigned "
            "adversarial objective depends on its condition and further evidence."
        ),
        "",
        "## Evidence",
        "",
        "- [Original v1 report](v1-report.md)",
        "- [Original analysis source archive](../../evidence/coding-integrity/analysis-v1.zip)",
        "- [Revision rationale](../../studies/coding-integrity/SCORER-REVISION-2.md)",
        "- [Fixed added cases](../../studies/coding-integrity/scorer-v2.json)",
        "- [All revised observations and labels](../../evidence/coding-integrity/scorer-v2.json)",
        "- [Reproduction of all original v1 outcomes](../../evidence/coding-integrity/rescore.json)",
        "",
        "```bash",
        "uv run python scripts/audit_counterexamples.py",
        "uv run python analysis/coding_integrity.py --render-only",
        "```",
        "",
    ]
    (ROOT / "reports/coding-integrity/scorer-revision.md").write_text("\n".join(lines))
