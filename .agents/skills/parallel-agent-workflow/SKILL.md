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

## Integrate evidence

Review each lane's diff and focused validation, then check the interfaces where
lanes meet. A passed lane does not establish whole-product/runtime acceptance.
Leave one receipt with reviewed revision/diff, checks, unresolved gates and the
next safe action. Do not let a worker create a competing status ledger.

For tracked issues, use [GitHub workflow](../github-issue-workflow/SKILL.md).
Paperclip runtime work also uses
[integration workflow](../upstream-integrations/SKILL.md) and its Paperclip branch.
