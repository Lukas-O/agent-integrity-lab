# Run and inspect the provider pilot

The checked-in evidence is enough to regenerate the report without credentials:

```bash
uv sync --frozen
uv run python analysis/provider_pilot.py --render-only
```

Open the reviewed native logs in Inspect's local viewer:

```bash
uv run inspect view --log-dir evidence/provider-pilot/traces
```

Keep the viewer local. Starting it does not publish a website or configure remote access.

## Fresh inference

Store credentials in an owner-only JSON file outside the checkout. Its two keys
are `OPENROUTER_API_KEY` and `GROQ_API_KEY`; values are your provider secrets.
The default location is `~/.config/hawk-inspect-showcase/providers.json`.
The directory should have mode `700`, and the file must have mode `600`.
Never put secret values in command arguments, source files, or a commit.

Run two explicit profiles:

```bash
uv run python scripts/run_study.py \
  --profiles groq-oss20-low or-nemotron-low
```

Use `--credentials /path/to/private/providers.json` for another location. Other
profile IDs are listed in [profiles.json](../studies/provider-pilot/profiles.json).
This makes new provider calls and consumes free-tier quotas. The OpenRouter
adapter rejects paid models and routing overrides; the runner checks key usage
before and after the batch. A free route can still be unavailable or rate limited.

Each invocation writes a new `.local-runs/<run-id>/` directory containing the
Hawk configuration, untouched logs, catalog snapshot, source archive, and
manifest. It uses Hawk's local runner directly to set sample/task concurrency
to one, without deploying cloud infrastructure. Both the provider SDK and Inspect
have automatic retries disabled for this compatibility protocol.

Inspect sample outcomes even when Hawk exits successfully: its runner is
configured to retain and continue past individual sample failures.

## Review and export

Export all batches belonging to a report together, substituting their actual
directories. This replaces the derived pilot report; it does not erase raw logs.

```bash
uv run python analysis/provider_pilot.py \
  --run-dir .local-runs/RUN_ID_A \
  --run-dir .local-runs/RUN_ID_B
```

The export strips transport headers, local paths/hostname, opaque reasoning
signatures, and diagnostic tracebacks. It preserves all attempted samples,
including errors, and records hashes for raw and reviewed logs. Read the reviewed
traces before publishing; automatic filtering is not proof that arbitrary future
task content contains no personal information.

For the initial pilot, source hashes were recorded after inference while the
source files were unchanged; archived files were checked against those hashes.
The current runner automatically captures sources before inference. Archives
preserve the actual measured runner version separately from this improvement.

The source snapshots contain the task, scorer, provider guard, runner, protocol,
profile matrix, and lockfile. They are provenance records, not standalone source
distributions: use the checkout for installation and the normal analysis command.
