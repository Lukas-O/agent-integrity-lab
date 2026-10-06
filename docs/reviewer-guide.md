# A short review path

Start with the [coding study report](../reports/coding-integrity/README.md), open
one linked episode, and compare the captured application with an independent
failing or passing case. Then regenerate the report without a provider key.
The [provider pilot](../reports/provider-pilot/README.md) covers a broader matrix
of native thinking settings and the initial compatibility failures.

Read the [scorer correction](../reports/coding-integrity/scorer-revision.md) to
see where the original checker failed. Monitor disagreements exposed two missed
special cases; the revised cases were applied to every program in those families.
Original and corrected labels remain available, and the resulting monitor
agreement is explicitly post-hoc.

| Engineering question | Where to inspect it |
| --- | --- |
| Does the benchmark measure the requested behavior? | [Task contracts, references and independent cases](../src/showcase_evals/workshop.py), plus [reference and isolation tests](../tests/test_workshop.py). |
| Is this a real framework integration? | [Native Inspect task, solver, tools and scorer](../src/showcase_evals/coding.py) and [Hawk runner configuration](../scripts/run_study.py). |
| Can the agent change its own ground truth? | [Isolated execution](../src/showcase_evals/sandbox.py): expected outputs stay in the scorer process, outside the mounted candidate workspace. |
| Are failures and operational constraints accounted for? | [Frozen protocol](../studies/coding-integrity/PROTOCOL.md), explicit request pacing, all-attempt tables, and native error traces. |
| Does the monitor actually intervene? | The blocked cohort rejects protected-file writes before applying them; the separate [LLM monitor](../src/showcase_evals/monitor.py) only audits saved evidence. |
| Can another engineer reproduce the analysis? | [Analysis script](../analysis/coding_integrity.py), reviewed logs, source archives, runtime and artifact hashes. |
| Are safety claims appropriately limited? | Induced adversarial objectives, pressure, ordinary work, and evaluation cues remain separate; a changed test alone is not called deception. |

## Why this shape

Benchmark engineering involves creating tasks and maintaining reliable execution
infrastructure; evaluation execution also needs inspectable measurements of
autonomous behavior and mitigations. This project makes those responsibilities
visible in a small, runnable repository. That connection is a project-design
judgment, not an endorsement or a claim that this study reproduces either
organization's evaluations. [Epoch role context](https://epoch.ai/about/careers#software-engineer-benchmarking),
[METR role context](https://metr.org/careers#open-roles).

The business motivation also makes the work relevant to product engineering:
an adaptive demo must deliver a requested feature while keeping approval gates
and accurately explaining failures. The fixture implements that contract at a
small JSON workflow interface. It does not claim to be the full demo company app.

## Tradeoffs to discuss

The visible-test conflicts are deliberate, not representative sampling. The
finite independent checks validate selected behaviors rather than proving
arbitrary program correctness. Small cells favor trace-level analysis over a
leaderboard. Native thinking labels and provider routing remain distinct.
The four-tool scaffold limits agent freedom and improves inspectability, at the
cost of generality to unconstrained coding agents. The deterministic write monitor
enforces a precise policy but cannot establish truthful completion.

Development used AI coding assistance. Actual evaluated model runs, reference
implementations, development smoke tasks, and deterministic test fixtures are
identified separately in the evidence.
