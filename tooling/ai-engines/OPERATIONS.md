# Studio operations for agents

This is the operating guide for the registered Studio system workflows. Use the
[AI plan](../../planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) for scope and
the [existing receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md)
for acceptance, failures and resume evidence. This file is not another ledger.

## Bounded Demo execution handoff

Research/review completion does not start broker execution. For a separately
approved Demo session, use Trader's native immutable Automation grant and
[`mt5_demo_session.py`](../../projects/trader/foundation_v2/scripts/mt5_demo_session.py)
with the [capability/session contract](../../projects/trader/foundation_v2/docs/LOCAL-CAPABILITIES.md).
The Owner controller creates authority; the runner receives only that bounded
credential and frozen artifact/commands, without Owner/DB/provider credentials.
Do not use the manual endpoint, MCP order tools or an engine SDK as a fallback.

The session file owns client intents only; native PostgreSQL owns broker
receipts, attempt counters and risk reservations. `resume` can finish an unsent
approved close, while `reconcile` never sends. Expiry, revocation, a STOP file,
partial fill or an unknown result must remain visible; none means the position
was closed. Never create another session/grant to erase an attempted command.
Report outcome and remaining exposure through the existing native task/report;
do not add a Trader workflow dialog or another approval/state store.

The maintained client is a bounded open/close system check, not a strategy
scheduler. Observed chart SSE is sampled latest state and has no complete-tick
cursor. Historical QDM replay, a short live feed check, broker fill acceptance
and long-duration unattended operation remain different evidence scopes.

## Ownership and instruction delivery

| Consumer | How it receives instructions | Responsibility |
|---|---|---|
| Coding/maintenance agent | Workspace/project AGENTS and repo `studio-operations` skill | Inspect, maintain and operate within the assigned scope |
| Paperclip | Native task graph, assignments, dependencies and run state | Dispatch, concurrency, cancellation, task/run/report history |
| TradingAgents / RD-Agent / Forex process worker | Registered typed request and `engine_worker.py` | Execute the allowed engine contract; generic Markdown is not its runtime program |
| Hermes reviewer | `hermes_instructions.md` loaded explicitly by `hermes_worker.py`, verified source dossier, allowlisted tools | Review evidence and publish; no operational administration or broker tools |
| Native research lead | Its configured instructions file, selected native catalog skills and assigned `naqex-research-lead` company skill | Owner-managed; not a second coordinator for the registered graph |

Repo skills are not automatically installed into Paperclip's Skills catalog.
Hermes runs with `skip_context_files=True`; copying this guide into a directory
does not make it part of its prompt. Update the owning instruction path/adapter
only when that consumer needs the change, then verify what it actually receives.
Do not give a bounded reviewer an operator skill just to make every agent match.

The native lead's Naqex skill source is
[`paperclip-skills/naqex-research-lead/SKILL.md`](paperclip-skills/naqex-research-lead/SKILL.md).
This is a Paperclip consumer package, not another Codex discovery skill. Publish
its reviewed content through the native company skill API, then attach it using
`POST /agents/:id/skills/sync` with `mode: add`, preserving existing selections.
The installed native version is a runtime snapshot; maintain the source in this
repo and compare content/version before updates. Avoid independent UI-only edits.

The current non-Beta assignment follows the skill's current version. Explicit
version pins require Paperclip's Beta skills setting; do not enable that setting
incidentally. The `codex_local` adapter materializes/mounts assigned versions on
the next run, so a catalog entry, attachment count or `configured`/`missing`
snapshot alone does not prove an agent has read it. Inspect the published file
and runtime package separately; a real task remains its own execution check.

### Selected native catalog skills

The owner approved `task-planning`, `qa-acceptance` and `doc-maintenance` for
the native research lead. Install from the app catalog with
`POST /companies/:id/skills/install-catalog`, then assign the returned keys with
native sync `mode: add`. Keep upstream content and provenance; do not create
company copies of those procedures or replace the agent's other selections.

Use planning for a scoped task outcome and verification, QA for observable
system acceptance, and doc maintenance for authorized behavior changes. Link
the existing PLAN/receipt instead of mirroring their scope or status into a new
ledger. Apply the user's proportional-verification policy; a generic checklist
does not require unrelated checks or rerunning unchanged tests. Skills do not
grant repository write access or authorize dispatch, strategy tuning or trading.
The Naqex skill keeps project-specific worker contracts and recovery boundaries.
Process workers do not load this catalog; do not assign it to them as a substitute
for their registered instructions. No separate maintenance agent is required.

### Owner-facing reports

The existing Naqex lead skill routes to
[`references/owner-reporting.md`](paperclip-skills/naqex-research-lead/references/owner-reporting.md).
Publish both files in the same native company skill package. Hermes's wrapper
explicitly appends this same reference to its reviewer prompt and records the
combined instruction hash; it does not discover catalog skills or repo AGENTS.
Changes apply on the next run, not to past reports or an in-flight worker.
Retain engine-native numerical reports and evidence; the shared guidance governs
the lead/reviewer's human narrative, not scientific output schemas or authority.

Native `summarize-status` writes scope summary slots and `status-card-query`
manages status cards. They are separate workflows, not universal task-report
formatters. Keep their upstream procedures intact; the existing Naqex skill
holds this company's reporting convention without installing another skill.

## Control access: MCP, HTTP API and source

Use an exposed, authenticated Paperclip MCP connection for its supported task
operations after verifying the company and scopes with `paperclip_connection`.
An MCP entry in the UI is not proof that the coding agent has those tools.
Otherwise the registered CLI helpers use Paperclip's native HTTP API; source
inspection explains behavior, and source edits remain scoped development work.
Do not write task/config rows directly in the database.

For a red Assistant Connection card, inspect health, GET `/api/mcp/setup` and
GET `/api/mcp/connections` before debugging credentials. An API-route-not-found
404 means the management surface is not mounted. The public MCP routes depend
on a valid public/auth origin; OAuth management additionally requires a signed-in
real user/company membership. `local_trusted` implicit board access cannot grant
that consent. See [native MCP setup](../paperclip/README.md#mcp-để-trợ-lý-thao-tác-paperclip)
and the pinned upstream `doc/public-mcp.md` for configuration and approval steps.

The local instance now uses authenticated mode with the existing database and
ports. The owner claimed the previous local board through Paperclip's native
flow. `paperclip_setup.api` reads only the exact-origin board credential in
`.runtime/paperclip/auth.json`, created by the project-isolated native CLI login.
It does not retry anonymously if a credential is rejected. The operator helpers
accept only registered workflow operations; Trader has no outer workflow HTTP bridge. Worker callbacks
retain their separate per-run JWTs; the auth cutover did not change their signing
secret or dispatch a worker to test it.

Codex's project MCP connection is `naqex_paperclip`, with read/write task access
and refresh authorization, without `paperclip:configure`. The project allowlist
exposes task, document and directory tools. Owner sign-in and OAuth consent remain
human steps. After reconnecting, verify `paperclip_connection` and the company
before using task tools; OAuth login or CLI discovery does not prove this chat
has loaded them. See the launcher guide for renewal and rollback. Preserve data,
ports and worker ownership; do not invent a proxy or write the database to bypass
authorization.

## Read the task fields correctly

| UI field | Meaning in the registered graph |
|---|---|
| Project / parent / child / blocked by | Native graph relationships; verify IDs and company/project scope |
| Assignee | Actual worker for a child task; the summary starts unassigned and is handed to the human after review |
| Reviewers / Approvers | Separate native `executionPolicy` stages; a Hermes child task does not populate these fields |
| Monitor / Watchdog | Separate native monitoring controls; configured process deadlines and whole-graph Stop are not these features |
| Cancelled | Preserved history, not a missing setup to repair by assigning/restarting it |

The existing human handoff is `in_review` plus a human assignee and summary
document. It is not a configured native approval policy. It cannot authorize
paper/demo/live trading. Do not add a second Hermes review through executionPolicy
without revising the graph's ownership/acceptance and testing the native stages.

## Operate a registered workflow

1. Read the current plan/receipt and native task/run state. Determine whether
   this is a fresh draft, an existing attempt or an unknown outcome. Historical
   model success and an idle/error worker status do not prove provider readiness.
2. In Trader, open **Studio → Đội AI** and use Paperclip's native interface.
   For a registered Forex or spot fixture, use the bounded CLI helper, then
   inspect its graph in Paperclip. Follow [Studio controls](README.md#studio-controls).
3. Create a draft without dispatch. Start only within current task authorization
   and its quota/cost scope; confirmation is a separate action. Do not change
   strategy parameters, datasets, providers or model routes as an incidental fix.
4. Follow the native child task and its run/documents. Numeric evidence must
   pass dependency/run/hash checks before Hermes; human review follows publication.
   Keep the paper placeholder blocked and NOT_RUN.
5. Stop through the whole-graph control or documented CLI when the graph needs
   cancellation. Cancelling only the parent in native UI does not prove all child
   processes/provider computation have stopped. Preserve completed outputs.
6. Reconcile unknown outcomes before retry: native task/run, local receipt,
   attempt ID and document hashes. Reuse a pending create token. A fresh attempt
   gets a new key only after the previous outcome is understood. Repair failed
   report delivery without repeating inference. See [failed workflows](README.md#failed-workflows)
   and [Hermes limits](hermes.md).
7. Record changed behavior, affected source/runtime, verification and next step
   in the existing receipt. System acceptance and strategy qualification remain
   separate. Use the [launcher guide](../paperclip/README.md) for owned-runtime
   recovery; use `upstream-integrations` for source adoption/upgrades.

The outer Workflows dialog/HTTP bridge was retired by the owner on02/11. Keep
operator UI in Paperclip; add application code only for domain contracts,
integration or a demonstrated native capability gap. Human `in_review` handoff
still does not establish a native Reviewer/Approver policy. Process timeouts,
iteration limits and concurrency do not establish a money cap. Scheduling stays
off until attempt/spend bounds, unknown accounting and restart/stop recovery have
been verified; this read-only reconciliation does not satisfy those gates alone.

## Pilot run limits and provider throttling

On 03 November 2026 the owner removed the experimental 10-runs/day cap from all
five agents to prioritize workflow reliability before cost optimization. Omit
`maxDailyRuns` and its legacy aliases; do not replace it with a large arbitrary
number. Setup helpers use the same uncapped daily default for new workers and
preserve existing agents. Native API changes must retain other runtime fields,
especially `aiConnection`.

Keep `maxConcurrentRuns: 1` per agent, timers off and on-demand work enabled.
Different agents can run concurrently; a run can make several model requests.
Retain duplicate protection, process deadlines, bounded retries and permission
checks. Daily cost tuning is deferred; unknown billing is still unknown, and
provider quotas still apply. This does not enable unattended scheduling or
establish a token or money cap.

Avoid multiplying retries across layers:

| Layer | Pilot behavior |
|---|---|
| Project CLIProxyAPI v8 | `routing.retry`: `request-retry: 0`, `max-retry-credentials: 1`, `max-retry-interval: 0`; no extra credential round/failover for a failed request |
| TradingAgents | `llm_max_retries: 0`; the wrapper does not replay a failed run |
| RD-Agent generation | One request, output limit 4096 tokens, no retry |
| Hermes SDK | Profile `agent.api_max_retries: 1` means one attempt, `auto_recovery_cycles: 0`, empty `fallback_providers`, auxiliary `transient_retries: 0`; OpenAI transport retries are disabled upstream |

At the audited pin these settings stop a 429 rather than sleeping/retrying in
multiple layers. Recheck per-credential overrides when gateway routes change;
`max-retry-interval: 0` alone does **not** disable retries. Native metadata/model
discovery requests are separate from inference. Hermes still allows up to six
conversation iterations and a 180s agent budget; those are not token budgets.

Provider 429 errors in the analysis/RD wrapper and Hermes's structured
`rate_limit`/`upstream_rate_limit` results become `model_rate_limited`. Reports,
receipts and any already attached output remain available. Wait for the provider's
cooldown/reset, reconcile native run and artifacts, then explicitly retry only
when needed. Do not rotate accounts/models or rerun completed inference to repair
publication. This policy controls Studio workers, not the host's Codex quota or
an owner's separate CLIProxyAPI instance.

Configuration readback and an isolated local 429 smoke are separate from real
provider readiness. See the current receipt for exactly which checks ran.

## Research to implementation without copying context

Use the current native task as the durable dossier: research in a revisioned
document, a concise `plan` document when needed, and links to source evidence.
The lead's [company skill](paperclip-skills/naqex-research-lead/SKILL.md) describes
the handoff. An already-authorized, cohesive task stays with its existing owner.

When a new owner decision is genuinely required, use native `request_confirmation`
bound to the exact `plan` revision, with `resolverPolicy: human_only` and the
actual owner as addressee when known. Read back the effective resolver policy;
the native default can allow agents to resolve an interaction. Acceptance can
wake the assigned lead through
`continuationPolicy: wake_assignee`. The owner reviews the saved proposal rather
than copying research into another task. A revised plan requires a current
confirmation; a comment or completed research task is not approval.

For real delegation after plan acceptance, use native
`/issues/:id/accepted-plan-decompositions`, retaining its revision binding and
idempotency. Otherwise use ordinary native tasks under existing authorization.
Verify `blockedByIssueIds`; nesting alone does not impose execution order. Check
the assignee's actual adapter/model and contract before dispatch. The fixed
process workers are not general coding agents. These mechanics are provided by
the pinned Paperclip source; published instructions and API checks do not by
themselves prove a fresh model-driven end-to-end handoff.

## GitHub repositories and coding work

Reuse the existing Naqex repositories; a Paperclip project is not a new GitHub
repository. Keep the research pilot's bounded worker contracts separate from
coding jobs. A repository connection alone does not give the Hermes reviewer
code, shell or GitHub tools, and it does not synchronize the two issue trackers.

| Work | Repository / Paperclip project |
|---|---|
| Trader implementation | `Naqex/trader` / a coding project such as **Phát triển Trader** |
| Shared plans and tooling | `Naqex/workspace` / a separate project only when that work needs an agent |
| Registered offline research | Existing research pilot; no writable product checkout required |

Keep engineering issue intake in `Naqex/workspace`, with PRs in the owning repo
as specified by [GitHub conventions](../github-workflow/README.md). Link a
Paperclip execution task to that issue and its PR; do not mirror the entire
backlog or create another progress ledger.
Versioned worker contracts/instructions stay in the existing `tooling/ai-engines/`
owner. A separate configuration repo is only justified by an independent release
or reuse need; native database, runtime profiles and credentials are not code to
push alongside those contracts.

There are two separate setup steps: the project workspace supplies `cwd`,
`repoUrl` and `repoRef`; the native GitHub connector supplies authorized actions.
For coding, explicitly enable isolated execution with `git_worktree`, using
`origin/main` as the reviewed base and the `codex/` branch convention. Merely
entering a repo URL does not enable isolation. Verify the supported project
policy at the pinned source and test it before dispatching a coding agent;
do not let it share the owner's active checkout or infer submodule authority.

Start the native connector with selected repositories and agents, read-only
Contents/Metadata/Issues/Pull requests and an expiring fine-grained PAT. Owner
consent and credential entry are separate steps; do not copy the host's `gh`
token into Paperclip. The managed GitHub App path is available only with eligible
Paperclip Cloud enrollment; do not add Cloud solely for this local pilot.
PAT-based repository tools and a managed shell identity are different paths.
The experimental Code Review Bot is also separate and is not needed to read code.

Verify a known file read and its native connector trace before granting writes.
For a later coding worker, review shell credentials separately: gateway
Ask-first switches do not constrain shell `git`/`gh`. Unmanaged standard-trust
local execution may inherit host authentication. Selected repos, GitHub-side
permissions, branch protection and PR review provide the relevant write limits;
a read-only connector is not a sandbox for a local coding process.

Primary references: [GitHub connector setup](https://docs.paperclip.ing/connectors/github-setup/),
[GitHub access boundaries](https://docs.paperclip.ing/connectors/github/),
[coding workspace setup](https://docs.paperclip.ing/how-to/connect-agent-to-github/).
At a future setup/upgrade, compare these live docs with the pinned
`projects/integrations/paperclip/doc/execution-github-identity.md` and project
validator; do not copy credential examples blindly. Current setup evidence and
any owner authorization belong in the existing integration receipt.

## Decision models: when to connect one

At the audited Paperclip pin, the shared provider choices are OpenAI and
OpenRouter/Jev 1.13. Eligible connections require a supported native API-key route;
an OpenAI-compatible chat gateway is not automatically a Decision API connection.
The server currently registers `settings.test`; the Studio wrappers do not call
this service. Enabling its settings does not route workers or enforce their review.

Keep known permissions, hashes, numeric limits and state transitions in code.
Consider a decision model when a concrete consumer needs semantic classification,
such as categorizing a free-text failure for operator triage. Evaluate labeled
normal/ambiguous/failure cases, latency and actual usage/cost before promotion.
Start with advisory output; preserve unknown/escalation and deterministic authority.
Confidence and typed output do not establish correctness or permission.

Use a supported native Decision connection when such a consumer exists. A new
key/account or paid probe keeps its own authorization gate. Pin the tested model;
do not silently follow a latest alias or edit upstream merely to replace the picker.
Model/API details must be rechecked before implementation:
[TypeSafe concepts](https://docs.typesafe.ai/concepts/system-one),
[confidence](https://docs.typesafe.ai/confidence),
[OpenRouter Jev guide](https://openrouter.ai/docs/guides/community/jev).

Implementation references for the current pin:
`projects/integrations/paperclip/server/src/services/decision-models.ts`,
`server/src/routes/decision-models.ts`, `packages/shared/src/decision-models.ts`.
Current connection state and usage are runtime evidence, not permanent facts in
this guide; inspect the native GET settings/availability/history before reporting.
