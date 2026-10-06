# Fictional workshop engine

This small Python application models the business operations behind an adaptive
demo: preparing an order card, grouping production work, and placing a reviewed
message into a simulated outbox. It has a JSON request/response interface and no
network or real sending integration. It is an executable evaluation fixture, not
the full demo company's product or a finished customer interface.

The task files are intentionally incomplete. The coding agent receives one file
as `app.py`, a requirement, and existing `test_visible.py` checks. It can read and
replace these files, run the visible checks, and probe the app with its own JSON
requests. Task-specific independent cases
and valid reference implementations live in
[`workshop.py`](../../src/showcase_evals/workshop.py), outside the candidate's
mounted workspace. The development-only `quote.py` is excluded from study counts.

The requested behavior, rather than the existing visible checks, defines success.
Two families contain stale checks. See the
[frozen protocol](../../studies/coding-integrity/PROTOCOL.md) for why and how these
conflicts are scored.

## Execution isolation

[`sandbox.py`](../../src/showcase_evals/sandbox.py) constructs a bubblewrap
sandbox using read-only `/usr` and candidate-file mounts; a separate network,
PID, IPC, and user namespace; a cleared environment; disabled nested user
namespaces; no capabilities; and private temporary storage. Candidate code gets
hard 256 MiB address-space, three-second CPU, 64 KiB output-file, 64-descriptor,
and zero-new-process limits. The parent also enforces a six-second wall timeout.
Test output is bounded before it reaches a model prompt. Credentials and
independent checker code are not mounted.

This requires Linux, `/usr/bin/python3`, `prlimit`, and bubblewrap with user
namespaces enabled. The system Python runtime is recorded separately from the
evaluator's lockfile; `/usr` is read-only but is not an immutable image. Bubblewrap
is a sandbox construction tool: protection depends on the chosen configuration.
This project is not an audited public hostile-code execution service.
[Bubblewrap's security model](https://github.com/containers/bubblewrap#sandbox-security)

Run reference-solution and isolation checks without provider access:

```bash
uv run pytest tests/test_workshop.py
```

## GitHub runner compatibility

CI uses Ubuntu 24.04 explicitly. Its default AppArmor policy can deny Bubblewrap's
unprivileged namespace setup with `Failed RTM_NEWADDR: Operation not permitted`.
The [CI setup script](../../.github/ci/prepare-sandbox.sh) first runs a trusted
namespace probe, then applies Ubuntu's documented per-executable `userns`
allowance to `/usr/bin/bwrap` if the restriction is enabled and the probe fails.
It repeats the probe before running tests. The script requires a disposable
GitHub-hosted runner and does not change this project's development host.

The system-wide restriction remains enabled. Filesystem, network, process, and
resource boundaries still come from the explicit Bubblewrap and `prlimit`
configuration, verified by the existing isolation tests.
[Ubuntu's explanation of the per-application policy](https://documentation.ubuntu.com/release-notes/24.04/).
