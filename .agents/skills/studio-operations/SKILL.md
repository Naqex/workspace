---
name: studio-operations
description: Operate registered Trader Studio research workflows and reconcile native task, run, report or cancellation state. Use for workflow setup review and interrupted attempts; not strategy selection or engine upgrades.
---

# Studio operations

Read the [operating guide](../../../tooling/ai-engines/OPERATIONS.md), then only
the relevant section of its linked plan, receipt and runtime/engine guide.
The existing receipt owns results; native Paperclip owns tasks and runs.

1. Identify the company/project, graph/attempt, current native state and authority
   for the requested action. A cancelled fixture is history; inspect it without
   assigning or restarting it. Do not dispatch a model to diagnose a settings field.
2. Use Paperclip's native UI/MCP/API and fixed graph CLI helpers. The outer
   Workflows dialog/HTTP bridge was retired by the owner; do not recreate it from
   old receipts. Verify an unmet native capability before adding management UI.
   Preview and draft are distinct from start. Check the declared system fixture and dependency
   evidence; do not tune the strategy or select a new dataset incidentally.
3. Handle an interrupted create with its existing idempotency token. For uncertain
   start/cancel or publication, reconcile native run and local receipt before any
   mutation. A running local receipt after a native hard kill is not success.
   Repair delivery independently from inference; keep previous attempts intact.
4. Distinguish child-task review/human handoff from native executionPolicy
   Reviewer/Approver stages. Repo skills, worker contracts, Hermes prompts and
   native agent instructions have different loaders and capabilities.
5. Verify the affected behavior proportionally. Use native reads for setup claims;
   a model call needs a consumer and authorized budget. Record source, runtime,
   workflow/provider and strategy acceptance separately in the existing receipt.

For engine adoption or upgrades, use `upstream-integrations`. For changing Codex
instructions/skills/configuration, use `ai-environment-maintainer`. This skill
does not add scheduler, spending, account, holdout or broker authority.

Strategy selection belongs to `strategy-research`, result review to
`strategy-qualification`; use [strategy workflow](../../../tooling/ai-engines/STRATEGY-WORKFLOW.md)
for artifacts/tools. Do not redispatch a fixed fixture for an unregistered study.

Use [observability](../../../tooling/ai-engines/OBSERVABILITY.md) for job status/logs.
Native run/receipt is the state owner; event logs explain transitions. Read stale
or unknown state before retry, and publish projections in the existing native
task instead of another dashboard.
