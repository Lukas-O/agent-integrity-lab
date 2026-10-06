# Provider compatibility and timing pilot

Frozen before the first inference attempt on 2026-10-06. This pilot qualifies
provider configurations for later coding-agent studies; it is not evidence of
production performance, coding ability, or scheming propensity.

Each configuration performs the same two short fictional-order tasks. It must
call a real Python fixture tool, compute a total, interpret approval state, and
return exactly checked JSON. No message is sent and no arbitrary code is run.

The matrix is in `profiles.json`. Every model uses the same Inspect solver and
tools, 1,024 maximum completion tokens per call, at most eight messages, at most
120 seconds per sample, and no automatic request/sample retries. Hawk runs with
one active task and sample. Provider-internal behavior remains outside our
control. Nonstreaming full responses are the common timing measurement.

Stage 1 validates Groq GPT-OSS 20B low and OpenRouter Nemotron low. Stage 2 runs
the remaining configurations once stage 1 establishes the execution path.
Technical fixes and reruns receive new run IDs and remain part of the evidence.
The single stage-1 run is reused as pilot evidence, not mislabeled as an
independent replication. New cohorts must use new log directories.

Measures: independently checked tool/result correctness, full agent elapsed
time, Inspect successful model-call time and model-event wall time, input/output
tokens, stop reason, and available provider timing/usage. Record errors and
truncation as outcomes. Requested reasoning controls are not attested internal
compute. Qwen high's documented native mapping is xhigh.

Show every measured point and sample counts. Do not infer p95, a general ranking,
statistical significance, or a pure model-speed comparison from two samples per
configuration. Different outputs and reasoning lengths affect response times.
Setup/catalog validation and independent scoring are outside the agent timer.

OpenRouter requests must use the guarded provider: explicit `:free` routes,
current zero-price catalog validation, zero upstream input/output price ceilings,
and no model/provider fallbacks or extra request bodies. Check key usage before
and after each batch. Groq uses the user's existing free-tier account. No new
purchase or provider upgrade is part of this pilot.

Raw logs stay outside version control. Reviewed public records must preserve all
attempted profiles, errors, and exclusions, with hashes linking to the source
logs. Credentials, authorization headers, host/user identifiers, and opaque
reasoning signatures must not enter public bundles. Ordinary reasoning text,
when a provider exposes it, is labeled as such rather than as verified internal
reasoning.
