# Studio operations for agents

This is the operating guide for the registered Studio system workflows. Use the
[AI plan](../../planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) for scope and
the [existing receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md)
for acceptance, failures and resume evidence. This file is not another ledger.

## Ownership and instruction delivery

| Consumer | How it receives instructions | Responsibility |
|---|---|---|
| Coding/maintenance agent | Workspace/project AGENTS and repo `studio-operations` skill | Inspect, maintain and operate within the assigned scope |
| Paperclip | Native task graph, assignments, dependencies and run state | Dispatch, concurrency, cancellation, task/run/report history |
| TradingAgents / RD-Agent / Forex process worker | Registered typed request and `engine_worker.py` | Execute the allowed engine contract; generic Markdown is not its runtime program |
| Hermes reviewer | `hermes_instructions.md` loaded explicitly by `hermes_worker.py`, verified source dossier, allowlisted tools | Review evidence and publish; no operational administration or broker tools |
| Native research lead | Its configured instructions file and adapter | Owner-managed; not the coordinator for the registered graph |

Repo skills are not automatically installed into Paperclip's Skills catalog.
Hermes runs with `skip_context_files=True`; copying this guide into a directory
does not make it part of its prompt. Update the owning instruction path/adapter
only when that consumer needs the change, then verify what it actually receives.
Do not give a bounded reviewer an operator skill just to make every agent match.

## Control access: MCP, HTTP API and source

Use an exposed, authenticated Paperclip MCP connection for its supported task
operations after verifying the company and scopes with `paperclip_connection`.
An MCP entry in the UI is not proof that the coding agent has those tools.
Otherwise the existing bounded controls use Paperclip's native HTTP API; source
inspection explains behavior, and source edits remain scoped development work.
Do not write task/config rows directly in the database.

For a red Assistant Connection card, inspect health, GET `/api/mcp/setup` and
GET `/api/mcp/connections` before debugging credentials. An API-route-not-found
404 means the management surface is not mounted. The public MCP routes depend
on a valid public/auth origin; OAuth management additionally requires a signed-in
real user/company membership. `local_trusted` implicit board access cannot grant
that consent. See [native MCP setup](../paperclip/README.md#mcp-để-trợ-lý-thao-tác-paperclip)
and the pinned upstream `doc/public-mcp.md` for configuration and approval steps.

Prepare an authenticated-mode cutover as one coherent change: backup the existing
instance, establish owner login/membership, adapt operator HTTP authentication,
check Studio controls and worker callbacks, then connect the coding client and
verify scopes. `paperclip_setup.api` currently uses implicit local authority;
switching auth mode alone can break that helper and the Studio controls. Owner
sign-in/OAuth consent remains a human step. Preserve existing data, local ports
and worker ownership; do not invent an unrestricted MCP proxy to avoid setup.

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
2. In Trader, open **Studio → Đội AI → Quy trình**. Select company/project and
   preview the registered Forex or spot fixture. Follow
   [Studio controls](README.md#studio-controls) for the UI/CLI contract.
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
