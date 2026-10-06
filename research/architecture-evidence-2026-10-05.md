# Architecture and evidence research — 2026-10-05

Scope: a hiring showcase using Inspect and Hawk, with synthetic demo-company tasks. This is a design recommendation, not an implementation or an execution result. Sources below are current primary documentation; versions must be pinned and compatibility verified during implementation.

## Recommendation

Use one repository containing an installable package of **Inspect extensions**, study protocols/configuration, evidence manifests, analysis code, and readable reports. Keep bulk execution evidence outside Git history. Inspect is the framework; the project's contribution is credible tasks, environments, measurement, and research findings. Do not create another generic task/runner/scorer abstraction. A later newsletter repository can consume the package once concrete reuse exists.

## Verified capabilities

- Inspect's native `@task` returns a `Task` combining dataset, solver, and scorer; tasks can be packaged and their solvers overridden for comparisons. Use those interfaces directly. [Tasks](https://inspect.aisi.org.uk/tasks.html)
- Custom `@scorer` functions consume `TaskState` and `Target` and return `Score`, including explanations and metadata. This accommodates explicit correctness and safety judgements with inspectable evidence. [Custom scorers](https://inspect.aisi.org.uk/custom-scorers.html)
- `eval_set()` already schedules suites, retries failures, preserves completed samples, and resumes unfinished work. Its log directory scopes completion tracking; failure-log cleanup is configurable. [Eval sets](https://inspect.aisi.org.uk/eval-sets.html)
- Hawk's YAML defines a grid of tasks, agents, and models and forwards evaluation parameters to Inspect. `hawk local eval-set CONFIG` runs locally in a fresh temporary environment; local provider calls require credentials. `--direct` instead uses—and installs dependencies into—the current environment. Cluster interfaces can export transcripts and import locally produced `.eval` files. Local use demonstrates Hawk orchestration, not operation of its AWS deployment. [Hawk execution](https://hawk.metr.org/user-guide/running-evaluations/)
- `.eval` is Inspect's default binary log container. Use its Python log API rather than implementing a parser; logs include configuration, sample trajectories, scores, errors, and usage. `inspect log export-config` can recover a run configuration. [Logs](https://inspect.aisi.org.uk/eval-logs.html)
- Inspect's schema includes source revision, package versions, sample events, and the sample store. These are useful provenance fields, not a guarantee that every external dependency or final filesystem state was captured. [Log reference](https://inspect.aisi.org.uk/reference/inspect_ai.log.html)
- `evals_df`, `samples_df`, `messages_df`, and `events_df` expose native analysis tables with identifiers linking records. `inspect view bundle` creates a self-contained viewer directory, including the selected logs. Hosting is a separate choice. [Dataframes](https://inspect.aisi.org.uk/dataframe.html), [viewer](https://inspect.aisi.org.uk/log-viewer.html)

## Proposed layout

These paths and responsibilities are recommendations, not framework requirements.

| Area | Contents and contract |
| --- | --- |
| `src/<package>/` | Native Inspect tasks, tools/solvers, evidence capture, and scorers; no duplicate runtime framework. |
| `environments/` | Synthetic application fixtures and reproducible sandbox definitions; protected checkers outside the evaluated agent's write authority. |
| `studies/<study>/` | Research question, threat model, preregistered comparisons, task selection, seeds, budgets, retry/exclusion rules, and Hawk YAML. |
| `evidence/` | Small public manifests mapping studies and executions to versioned, hashed reviewed artifacts; one tiny synthetic smoke fixture if useful. |
| `analysis/` | Functions/scripts reading evidence through Inspect APIs and regenerating derived tables and figures. |
| `reports/` | Findings, limitations, failure examples, and generated summaries linked to exact evidence. |
| External private storage | Untouched raw logs, captured application state, patches, checker output, and operational diagnostics. |

The dependency direction is definition → execution → captured evidence → scoring/analysis → report. Reports must not silently launch agents. Each new execution gets a unique ID; rescore and analysis outputs also get IDs and reference their input artifact hashes.

## Rerun, rescore, and inspect are different promises

- **Rerun:** execute agents again, with new inference and environment activity. A pinned recipe improves reproducibility but does not promise identical model outputs. Resuming an incomplete eval set may reuse finished samples; use a new run directory for an independent replication.
- **Rescore:** apply a scorer to saved outputs using `inspect score` or `score()`. Inspect bypasses actor generation and can preserve old scores. A model-based grader can still call a model, so rescoring is not inherently offline or free. Write a new artifact rather than overwriting original evidence. [Scoring workflow](https://inspect.aisi.org.uk/scoring-workflow.html)
- **Inspect/analyze:** browse saved trajectories or recompute descriptive statistics and figures. Call this “reproduce analysis”; avoid the ambiguous promise “replay the agent.”

Crucial design consequence: Inspect normally cleans up sandboxes. A saved transcript cannot recreate uncaptured transient state. Capture final application state, generated files/patches, approval decisions, and trusted checker observations before teardown. Offline scorers should consume these captured inputs, with missing evidence reported explicitly. Filesystem-dependent checks require the relevant archived files plus a separately specified execution environment. [Sandbox lifecycle](https://inspect.aisi.org.uk/sandboxing.html#environment-cleanup)

## Publication and provenance policy

Recommended manifest fields: study/execution IDs, source commit and dirty status, lockfile digest, task/fixture/scorer revisions, image digests, model/provider/configuration, timestamps, sample IDs/epochs, retry lineage, run status, artifact hashes, exclusions, and publication transformations. Preserve execution errors separately from behavioral failures and include denominator/coverage information.

Keep raw originals private; synthetic inputs alone do not guarantee clean logs. Review transcripts, attachments, metadata, tool outputs, and diagnostics for credentials, personal information, and host identifiers. Publish reviewed derivative bundles with transformation records and declared omissions. Exemplar transcripts may illustrate findings, but aggregate claims need sufficient reviewed evidence to reproduce their denominators and calculations. If that cannot be published, state the limitation.

Versioned GitHub release assets are a reasonable proposed home for bulk public evidence. Releases are **not automatically immutable**: enable release immutability before publication, or describe only versioning/checksum verification. Immutability applies to future releases and locks assets and tags; checksums alone detect changes rather than prevent them. GitHub documents a limit of 1,000 assets per release, each under 2 GiB. [Enable immutability](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes), [guarantees](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases), [release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

## Latency addendum — 2026-10-05

User constraints: fresh agent executions in a synthetic environment; whole-agent comparisons; OpenRouter and Groq only; initial total cap €50 with $10 OpenRouter credit already purchased. The following is a measurement design, with no inference performed. Pin the inspected versions before implementation: current source behavior may differ from a released package.

### What exists and what needs instrumentation

| Measure | Evidence and interpretation |
| --- | --- |
| Inspect model-event wall time | `completed - timestamp`. Current implementation starts timing before its connection-concurrency gate and completes after generation, so this includes local queueing and retries. |
| Successful request duration | `ModelOutput.time` and `ModelEvent.working_time`. Inspect prefers the underlying `ModelCall.time`; this is distinct from total event wall time and retry/backoff time. |
| Sample timing | Native sample `total_time`, `working_time`, start/end timestamps, and events support diagnostics. Add an explicit monotonic agent-execution span to exclude setup and scoring from the headline agent latency. |
| Client time to first output | Add `on_stream` instrumentation using a monotonic clock and persist first nonempty text, reasoning, and tool-call deltas separately. The stream event types do not themselves provide durable first-token timestamps; streamed progress is not a full token-timing log. Call this time to first observed delta, since a chunk may contain several tokens. |
| Groq server timing | Native Groq adapter retains `queue_time`, `prompt_time`, `completion_time`, and `total_time` in `ModelOutput.metadata` when usage exists. These are provider measurements, not client/network latency. Preserve fields separately; Groq's example `total_time` equals prompt plus completion time, excluding its separately reported queue. |
| OpenRouter server metadata | Collect generation metadata after the timed run, joined by generation ID: provider, streamed status, token counts, cost, `latency`, and `generation_time`. Preserve these as separately named provider fields; the retrieved API page does not define their units/boundaries sufficiently to equate them with client TTFT. |

Sources: [Inspect timing implementation](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_model.py), [event schema](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/event/_model.py), [stream events](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_stream.py), [sample schema](https://inspect.aisi.org.uk/reference/inspect_ai.log.html), [Groq adapter](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_providers/groq.py), [Groq API](https://console.groq.com/docs/api-reference), [OpenRouter generation metadata](https://openrouter.ai/docs/api/api-reference/generations/get-generation).

The inspected Groq adapter normalizes only input/output/total token counts into `ModelUsage`; capture provider usage details separately when reasoning/cache counters are returned. Do not assume every provider field survives normalization. Raw API logging can supply evidence but must cover the measured calls and pass the publication review above.

### Streaming, retries, and reasoning caveats

OpenRouter supports SSE, but its current Inspect adapter declines automatic streaming when reasoning is requested because streamed reasoning-detail reconstruction is unverified. Explicit `stream=true` overrides that safeguard. Groq uses `streaming=true`; automatic streaming declines structured-output requests and Compound models. Recommendation: make complete-request and agent latency mandatory; offer first-delta graphs only after validating tool calls, reasoning continuity, and usage accounting for each exact configuration. Ignore SSE keepalives and empty accounting frames when measuring first output. [OpenRouter adapter](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_providers/openrouter.py), [Inspect provider modes](https://inspect.aisi.org.uk/providers.html), [SSE semantics](https://openrouter.ai/docs/api/reference/streaming).

Inspect retries with exponential backoff and jitter; the Groq SDK also defaults to two retries for selected failures. Explicitly configure both layers and record native retry counts/request IDs plus retry-hook timing; do not assume the outer retry count exposes every provider attempt. Keep user-observed latency including waits alongside successful-request duration. Track sample retries separately. Stream retries can invalidate previously received deltas. [Inspect retries](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_retry.py), [Groq SDK](https://github.com/groq/groq-python#retries), [Inspect hooks](https://inspect.aisi.org.uk/reference/inspect_ai.hooks.html).

Reasoning settings are model-specific: Groq rejects unsupported effort values, and adapter mappings can clamp requested levels. Record both requested and transmitted settings. Hiding reasoning text does not disable reasoning. On OpenRouter, reasoning commonly consumes the same completion-token budget as visible output. Neither total request time nor first visible text isolates hidden thinking time. [Groq reasoning](https://console.groq.com/docs/reasoning), [Groq parameters](https://console.groq.com/docs/api-reference), [OpenRouter reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

### Recommended report and experimental controls

Generate README graphs from reviewed traces: (1) per-task agent elapsed-time distributions by model/effort, with failures and timeouts visible; (2) task success and approval violations against time and actual cost; (3) request latency versus input/output token counts, separated by provider route. Show observations and sample counts before emphasizing percentiles; a small pilot cannot establish a stable p95. Link each graph to data, analysis command, and manifest.

Keep environment, task distribution, scaffold, tool policy, budgets, concurrency, and scoring fixed; interleave/randomize conditions and repeat task seeds. Publish workload/context length, output/reasoning tokens where supplied, date/region, service tier, effective route/fallbacks, streaming mode, cache hits, and retry policy. Disable Inspect response-cache reuse for fresh runs; provider prompt caching is a different mechanism and must be recorded. Groq documents automatic prompt caching. Whole-agent trajectories may diverge, so their timing differences combine model speed, decisions, and tool use—not pure inference throughput. [Groq caching](https://console.groq.com/docs/prompt-caching).

OpenRouter documents extra latency near low credit balances and key limits; the $10 balance makes this a potential recorded confound, not a reason to buy more credit. Start with a small metering/compatibility pilot; account for all trials, retries, graders, and existing purchases within the stated cap, with headroom for in-flight requests and currency conversion. [OpenRouter latency](https://openrouter.ai/docs/guides/best-practices/latency-and-performance).
