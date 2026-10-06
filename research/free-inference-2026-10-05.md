# Free inference for a Hawk/Inspect portfolio

**2026-10-06 implementation update:** both supplied accounts authenticated, and
the [real-inference pilot](../reports/provider-pilot/README.md) ran on OpenRouter
and Groq. The supplied OpenRouter key is authorized for **free models only**;
its $1 key limit is not permission for paid inference. This supersedes the paid
confirmation allocation suggested below. The historical research and its access
dates remain intact; actual compatibility and failures are reported in the pilot.

Evidence checked **2026-10-05**; every source link below carries that access date. This is documentation/catalog research, **not successful inference verification**. No accounts, credentials, purchases, installations or inference calls were used. Entitlement, regional eligibility, quota and Inspect adapter behavior still require an account-specific pilot.

## OpenRouter: genuinely free inference, constrained throughput

Free variants have **20 requests/minute** and **50 requests/day** below the purchase threshold; **1,000/day** after nominally **$10 lifetime credits purchased**. The docs describe a one-credit tolerance, effectively $9. These are account-level free-request limits, not a separate allowance for every model. Initial free access needs no credit purchase. Values were verified in the official limits page's embedded constants because its rendered table omitted them: `FREE_MODEL_RATE_LIMIT_RPM=20`, `FREE_MODEL_NO_CREDITS_RPD=50`, `FREE_MODEL_HAS_CREDITS_RPD=1e3`, `FREE_MODEL_CREDITS_THRESHOLD=10`. Inspect the authenticated `GET /api/v1/key` daily counter before scheduling. [Limits](https://openrouter.ai/docs/api_reference/limits), [free plan](https://openrouter.ai/pricing).

Standard credit purchases carry a **5.5% platform fee**. A top-up is therefore a purchase, even when subsequent `:free` inference has zero token charges. Checkout currency conversion/tax totals were not verified. The Free plan's feature table excludes preferred-provider selection and data-policy routing; do not assume those controls are available without upgrading. [Pricing](https://openrouter.ai/pricing).

The following exact request IDs had zero input/output prices and a listed endpoint. These are a useful shortlist, not an exhaustive catalog. An ID avoids random model selection; it does **not** guarantee immutable weights or a permanent free route. [Live catalog](https://openrouter.ai/api/v1/models).

| Exact request ID | Listed serving endpoint | Context | Advertised capabilities |
| --- | --- | ---: | --- |
| `nvidia/nemotron-3-super-120b-a12b:free` | Nvidia | 262,144 | Tools, reasoning, structured outputs; tool-choice `none` unsupported |
| `google/gemma-4-31b-it:free` | Google AI Studio | 262,144 | Tools, reasoning, `response_format`; no `structured_outputs` flag |
| `liquid/lfm-2.5-2.6b:free` | Liquid (`liquid/fp8`) | 65,536 | Tools, reasoning, structured outputs |

Sources: [NVIDIA endpoint](https://openrouter.ai/api/v1/models/nvidia/nemotron-3-super-120b-a12b:free/endpoints), [Gemma endpoint](https://openrouter.ai/api/v1/models/google/gemma-4-31b-it:free/endpoints), [Liquid endpoint](https://openrouter.ai/api/v1/models/liquid/lfm-2.5-2.6b:free/endpoints). Catalog support is not proof that combinations work in Inspect or that a route has spare capacity.

For controlled comparisons, avoid `openrouter/free`, which chooses among available free models. Where entitled, require supported parameters and explicitly constrain provider/fallback behavior: otherwise unsupported parameters can be ignored. Record the request ID and returned model/provider; the generation metadata endpoint exposes model, provider, token counts and cost. [Router](https://openrouter.ai/openrouter/free), [routing](https://openrouter.ai/docs/guides/routing/provider-selection), [generation metadata](https://openrouter.ai/docs/api/api-reference/generations/get-generation).

OpenRouter normally retains request metadata rather than prompt/completion bodies. Upstream providers have separate policies; paid/free training permissions have separate account toggles. Opting out can remove eligible routes. Confirm the selected endpoint's policy and account settings; “free” does not imply private. Reasoning can arrive as text, summaries or encrypted content, so a supported reasoning parameter does not establish full readable traces. [FAQ](https://openrouter.ai/docs/faq), [provider policies](https://openrouter.ai/docs/guides/privacy/provider-logging), [reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

## Two alternative free tiers

**Groq:** its Free plan currently lists `openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.8-27b` at **30 RPM, 1,000 RPD, 8,000 TPM and 200,000 TPD**, per model at organization scope. These are published defaults; account limits may differ. Payment details are required to upgrade to metered Developer service, not identified as a prerequisite for the documented Free plan. [Limits](https://console.groq.com/docs/rate-limits), [billing](https://console.groq.com/docs/billing-faqs).

All three support tools and strict structured outputs, but Groq currently excludes **tool use and streaming in the same structured-output request**. GPT-OSS exposes a `reasoning` field by default; use `include_reasoning`, not `reasoning_format`. Qwen's default effort returns no reasoning; select an explicit supported effort for trace comparisons. [Tools](https://console.groq.com/docs/tool-use/overview), [structured outputs](https://console.groq.com/docs/structured-outputs), [reasoning](https://console.groq.com/docs/reasoning).

Groq's agreement excludes training on inputs/outputs without explicit permission. Ordinary inference bodies are not retained by default, but reliability/abuse exceptions can retain them for up to 30 days; ZDR is configurable. [Agreement §4.2](https://console.groq.com/docs/legal/services-agreement), [data controls](https://console.groq.com/docs/your-data).

**Gemini Developer API:** `gemini-3.8-flash` currently has free input/output tokens, function calling, structured outputs and thinking. Search/Maps grounding and batch are unavailable on its free tier. [Pricing](https://ai.google.dev/gemini-api/docs/pricing), [model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).

Free qualification is an active project/free trial. **Exact RPM/TPM/RPD cannot be established publicly for this user**: Google now directs users to AI Studio. Limits are per project; RPD resets at midnight Pacific; capacity is not guaranteed. [Limits](https://ai.google.dev/gemini-api/docs/rate-limits). Exposed thoughts are summaries, potentially absent, not full raw reasoning. [Thinking](https://ai.google.dev/gemini-api/docs/thinking).

Unpaid content generally may improve Google products; EEA/UK/Swiss users receive the paid-service data-use treatment even on unpaid quota. Making an API client available to users in those regions requires paid services. Account location and eligibility were not assumed. [Terms](https://ai.google.dev/gemini-api/terms).

**Cerebras is a trial, not a renewing free tier:** $5 credit expires after 30 days and requires a verified payment method. Its trial lists `gpt-oss-120b` and `qwen-3.8-27b` at 5 RPM, 30K uncached/90K total TPM, 1M TPH and 1M TPD. Access stops when credit expires/exhausts. [Official trial/limits](https://inference-docs.cerebras.ai/support/rate-limits).

## Recommendation within €50 total

Start with Groq and two explicitly named OpenRouter models, subject to pilot results. Keep Gemini optional until quota and trace behavior are known. Use **Hawk local**: it runs eval-set configurations without deploying AWS and calls provider APIs directly. [Hawk local](https://hawk.metr.org/user-guide/running-evaluations/#running-locally).

Recommended allocation within the user's €50 ceiling: up to €15 including fees for an optional OpenRouter top-up, €20 for targeted paid confirmation, €15 contingency. Use pilot results to decide whether a purchase adds useful evidence. This is an allocation proposal, not a price estimate; no purchase has been made.

Methodological compromises: one agent episode consumes multiple requests; rate limits constrain completion time and sample size. For example, 100 episodes × 10 generations = 1,000 calls before retries or model-based judging. Preserve failed runs, quota errors, retries, versions, endpoint metadata and raw available traces. Separate exposed reasoning text from summaries. Prefer deterministic outcome checks, matched task/step budgets, held-out cases and uncertainty intervals. A small open-model study can demonstrate careful evaluation engineering; it cannot establish frontier-model risk or general monitoring effectiveness.

## Update: selected providers and thinking/latency comparisons

Checked **2026-10-05**. The user selected **OpenRouter and Groq only** and reports purchasing **$10 OpenRouter credits** toward the **€50 total ceiling**. This supersedes the optional-provider/top-up recommendation above. Account activation, quota and the settled euro debit including fees remain unverified. This update used public documentation/catalogs only; no inference or credential access occurred.

### Exact documented controls

| Provider and exact model ID | Supported request settings | Default / limitation |
| --- | --- | --- |
| OpenRouter `nvidia/nemotron-3-super-120b-a12b:free` | `reasoning.effort`: `low`, `medium`; alternatively `reasoning.max_tokens`; optional reasoning permits an off/on control | Enabled, medium. **No advertised high effort.** Native effort mapping was not established. |
| OpenRouter `google/gemma-4-31b-it:free` | `reasoning.enabled`: `false` / `true` | Disabled. **Binary thinking**, no effort selector or reasoning-token budget advertised. |
| OpenRouter `liquid/lfm-2.5-2.6b:free` | Mandatory reasoning; leave effort/budget unset | **Always on**, no effort selector or reasoning-token budget advertised. |
| Groq `openai/gpt-oss-120b`, `openai/gpt-oss-20b` | Top-level `reasoning_effort`: `low`, `medium`, `high` | Medium; no off setting. |
| Groq `qwen/qwen3.8-27b` | Top-level `reasoning_effort`: `none`, `default`, `low`, `medium`, `high` | API reference says default is none; **high maps to native xhigh**. Use explicit values. |

OpenRouter rows come from its live `reasoning` metadata: omitted `supported_efforts` means no effort selector; omitted `supports_max_tokens` means no reasoning-budget control. Mandatory models reject `effort:"none"`. The guide inconsistently allows effort plus budget in one paragraph but prohibits the combination in its example; select one control per experiment. Do not transfer its generic effort-to-percentage examples to these models. [Catalog](https://openrouter.ai/api/v1/models), [metadata/control definitions](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens). Groq rejects effort values outside each model's supported set with HTTP 400. [Groq API reference](https://console.groq.com/docs/api-reference).

### Visibility, routing and verification

Hiding reasoning is **not disabling it**: OpenRouter `reasoning.exclude:true` suppresses returned text. Groq GPT-OSS uses `include_reasoning:true`, not `reasoning_format`; Qwen can use `reasoning_format:"parsed"` to separate reasoning from answers. Avoid Qwen `raw` with tools/JSON. Do not combine Groq `include_reasoning` and `reasoning_format`. [OpenRouter reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), [Groq reasoning](https://console.groq.com/docs/reasoning).

Where entitled, set OpenRouter `provider.require_parameters:true`, constrain `provider.only` to the exact endpoint slug, and disable `allow_fallbacks`; `order` alone permits fallback. Unrecognized parameters can otherwise be ignored. Do not supply a model fallback list for a fixed-model comparison. [Routing](https://openrouter.ai/docs/guides/routing/provider-selection).

Recommended evidence: retain the serialized request, catalog snapshot, response ID/model and available reasoning/usage. OpenRouter generation metadata supplies provider/model, request/upstream IDs, reasoning-token count, latency and generation time. Groq supplies model, backend `system_fingerprint`, service tier, and queue/prompt/completion timings. These establish reported routing and observed output; **they do not independently attest the model's internal effort**. Record requested settings and documented mappings separately from observed token counts; mark effective effort unverified when not returned. [OpenRouter metadata](https://openrouter.ai/docs/api/api-reference/generations/get-generation), [Groq response schema](https://console.groq.com/docs/api-reference).

### Recommendation for README graphs

Use within-model panels: Groq low/medium/high; Nemotron low/medium; Gemma off/on; Liquid one always-on baseline. Label Qwen high's native mapping. Compare task success alongside client wall-clock duration; distinguish time to first streamed event, first visible answer token, total response and full agent-task time. Use matched prompts/budgets, repeated randomized trials, uncertainty intervals and output/reasoning token counts. Report retries, throttling and failures separately. These are methodological recommendations, not measured findings; provider-specific effort labels are not equal-compute treatments. Preserve the remaining budget until the free-route pilot demonstrates which paid confirmation would add useful evidence.
