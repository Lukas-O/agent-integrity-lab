# Run the coding study

Use Linux with Python 3.13 or 3.14, `uv`, bubblewrap, `prlimit`, and unprivileged
user namespaces. The sandbox uses `/usr/bin/python3` independently of the Python
environment running Inspect. Its version and executable hash enter the run manifest.

```bash
uv sync --frozen
uv run pytest
```

The saved figures and report need no provider access:

```bash
uv run python analysis/coding_integrity.py --render-only
uv run inspect view --log-dir evidence/coding-integrity/traces
```

## New actor inference

The default task reproduces the **frozen v1 study**, including its now-documented
checker gap. The [v2 correction](../studies/coding-integrity/SCORER-REVISION-2.md)
is a separate audit of captured code. Do not present v1 pass labels as the final
corrected findings or the revised monitor agreement as an independent validation.

Configure the owner-only credential file described in [running the pilot](run-pilot.md).
The shared runner also supports the provider pilot. Select the coding study explicitly:

```bash
uv run python scripts/run_study.py --study coding-integrity \
  --development --profiles groq-oss20-low or-nemotron-low

uv run python scripts/run_study.py --study coding-integrity \
  --profiles groq-oss20-low or-nemotron-low
```

The first command runs only the excluded quote task. The second executes all
15 family/condition combinations for each selected model. Read the
[protocol](../studies/coding-integrity/PROTOCOL.md) before changing a task,
condition, model, budget, or retry rule. A changed study needs a new protocol
version and new run directories; do not relabel a changed run as replication.

Free-tier pacing can make elapsed runs substantially longer than API response
times. The runner serializes tasks and samples. Its shared rolling quota file
assumes **one active runner at a time**; parallel invocations are unsupported.
The limits are conservative local estimates, not account quota guarantees.
Errors remain recorded, and neither provider nor model fallbacks are enabled.

## Export and blind audit

Use every actor/development batch that belongs to the report:

```bash
uv run python analysis/coding_integrity.py \
  --run-dir .local-runs/DEVELOPMENT_RUN_ID \
  --run-dir .local-runs/ACTOR_RUN_ID
```

This produces reviewed native logs, tables, source hashes, and blind monitor
inputs. The monitor receives only each record's `evidence` field. The adjacent
`truth` field becomes an Inspect scoring target; it is not sent in its prompt.

```bash
uv run python scripts/run_study.py --study coding-integrity \
  --monitor --profiles groq-oss120-low
```

Then repeat the export command including the new monitor run directory. Inspect
the native traces and publication transformations before sharing any new bundle.
Original raw diagnostics remain private in `.local-runs/`.

If a prior v2 audit exists, exporting new evidence deliberately rejects the stale
v2-to-manifest hash. The new v1 export is written; apply the fixed additional
checks and regenerate the report before using the revised results:

```bash
uv run python scripts/rescore_coding.py
uv run python scripts/audit_counterexamples.py
uv run python analysis/coding_integrity.py --render-only
```

## What stays separate

Actor execution, independent behavioral checking, and LLM monitoring are separate
spans. The checker reruns captured code inside a fresh sandbox for each JSON
request. Offline report regeneration reads saved results and makes no model calls.
Rechecking arbitrary saved candidate code is executable evaluation work and still
requires the sandbox; it is different from recomputing a table.

```bash
uv run python scripts/rescore_coding.py
```

This runs each captured application against its saved independent requests and
expected responses. It writes a new result in ignored local storage plus a
public `rescore.json` summary linked to the input manifest hash. It does not
overwrite original traces or call a model. A mismatch or missing capture exits
with a failure status so it cannot silently endorse changed outcomes.

The small initial evidence bundles live with the code for convenient review.
Large future runs should use versioned release assets with manifests and hashes
in Git. There is no need for a second framework repository until another study
actually requires an independently maintained package.
