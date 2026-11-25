---
name: parallel-agent-workflow
description: Coordinate authorized parallel agents sharing a workspace, Git index or runtime. Use for independent implementation lanes and interrupted handoffs; not for single-agent work or permission to start workers.
---

# Parallel agents in a shared workspace

Use only when delegation is authorized by the user or applicable instructions.
Keep the owning PLAN/ledger and active workers authoritative.

## Assign ownership before dispatch

Split by files/subsystems with useful independent outcomes. Give each lane its
owned files, exclusions, acceptance, output receipt and runtime/port allocation.
Shared registries/copy files need one writer; other agents send that owner their
required changes. Separate files still share a Git index in one checkout.

Choose isolation using [Git branch/worktree decisions](../../../tooling/github-workflow/BRANCHES.md#agent-chọn-sửa-tại-chỗ-branch-hay-worktree):
actual concurrent writers or a preserved checkout need separate worktrees;
read-only lanes or one serialized integrator do not need one branch per agent.
Worktrees still share external runtime/data resources unless explicitly isolated.

Put long specifications in a durable brief file and pass its path. Include the
entrypoint and required references in that brief; do not assume the whole spawn
message survived. Ask the agent to report missing inputs before editing.

## Preserve work across interruptions

On agent failure or rate limits, inspect current diff, checkpoint and process
ownership before replacing it. Tell the replacement to continue from that diff.
Record what was completed, what remains and its validation; do not rerun an
external job merely because the chat worker stopped. Retry transient failures
with backoff and a bounded checkpoint, without changing provider or permissions.

## Serialize shared mutations

Choose one integrator for staging and commits when agents share a checkout.
If agents are explicitly assigned their own commits, serialize Git mutations,
stage only owned paths and inspect the complete cached diff before committing.
An index.lock is evidence of another operation: inspect/allow it to finish; do
not delete the lock blindly. If staged content belongs to another lane, hand
back to its owner instead of resetting it. Separate worktrees have separate
indexes, but merging their outputs still needs review.

For previews, use the assigned free port with strictPort; record PID/log/output
paths and stop only the process the lane started. Recheck ownership on resume.
Port registries and active worker state override historical port examples.

## Keep parallel capacity busy during long passive lanes

Separate passive wall-clock lanes (>= 20 min I/O or market wait: live spread/fill
captures, broker telemetry probes, slow downloads, long renders) from active worker
capacity. Never park the coordinator and idle workers on `swarm_wait` for hours
while genuine non-conflicting workspace backlog remains.

When a passive lane still has >= 20 min left and active lanes finish:
1. Pull the next real item from the 3-tier non-interfering backlog queue (do NOT
   invent fake busywork or endlessly re-polish already-verified files):
   - Tier 1 (Same plan / repo): remaining deliverables, parity/red-team audits,
     updated counterfactual simulations, tests, deployment checklists.
   - Tier 2 (Adjacent workspace value): primary-source ops/legal/quant research,
     offline R&D into Layer-2 `private_vault/`, `knowledge/` ledger updates,
     read-only hygiene/status audits.
   - Tier 3 (Cross-repo or approval-gated boundary, e.g. `projects/*` edits or
     broker/deploy actions): if Tiers 1–2 are genuinely exhausted and >= 30 min
     remain, do NOT silently idle — report passive progress and propose 2–3
     concrete ready-to-run options for the owner to pick.
2. Enforce strict non-interference: active parallel lanes must never launch a
   second `terminal64.exe`, write to the passive lane's active files, touch live
   VPS execution, or open Holdout `2025+`.
3. Pair multi-hour passive lanes with brief periodic checkpoints (or live progress
   reads) so completion handoff happens cleanly with zero stall.
4. Keep the Swarm roster clean and briefs substantive:
   - Retire (`swarm kill`) completed one-off specialists immediately after their
     deliverables are verified so the Swarm UI never shows a wall of stale
     `standing-by` cards; keep only workers needed for active/upcoming waves.
   - Size parallel assignments as cohesive 20–45 min missions (implement -> test
     -> verify/CI) rather than 3-minute micro-tasks that bounce workers back to
     `waiting`.
   - When active lanes finish early with >= 25 min left on a passive capture,
     launch a read-only multi-angle `run_workflow` deep audit (security/OPSEC,
     correctness/edge-cases, latency/perf, reliability) to surface real P0 bugs
     and feed concrete fixes back to `/swarm` (never fake busywork).
   - Within the final `< 15 min` before an imminent blocking handoff (e.g., last
     2–3 live probe fills before Wave 3 compile), do not start disruptive new
     edits that delay the handoff; report exact live progress, note that workers
     parked on background commands (`run_command` / `gh run watch`) display as
     `waiting` in Swarm UI, and state the exact ETA.

## Integrate evidence

Review each lane's diff and focused validation, then check the interfaces where
lanes meet. A passed lane does not establish whole-product/runtime acceptance.
Leave one receipt with reviewed revision/diff, checks, unresolved gates and the
next safe action. Do not let a worker create a competing status ledger.

For tracked issues, use [GitHub workflow](../github-issue-workflow/SKILL.md).
Paperclip runtime work also uses
[integration workflow](../upstream-integrations/SKILL.md) and its Paperclip branch.
