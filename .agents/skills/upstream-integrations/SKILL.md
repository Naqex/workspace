---
name: upstream-integrations
description: Adopt, fork, relocate or upgrade external apps and engines in Naqex Workspace while preserving pins, local runtimes and upstream ownership. Use for integration source/runtime changes; not for ordinary product edits or strategy research.
---

# Upstream integrations

Read [integration guide](../../../tooling/integrations/README.md), its catalog
and the owner plan linked there. The guide owns paths/commands; do not copy a
second port or revision registry into this skill.

For Paperclip dispatch failures or pilot/runtime recovery, read
[Paperclip diagnostics](references/paperclip.md). Ordinary source adoption does
not need that branch.

1. Classify the actual change: source adoption, dependency installation, UI
   embedding, worker job connection or active-runtime cutover. Report those
   states separately. A clone or import is not a successful engine job.
2. Inspect root/submodule Git status, exact pin, origin/upstream, repo AGENTS/
   rules and applicable license/install scripts. Preserve upstream layout,
   attribution and unrelated WIP. Use an existing adapter before inventing one.
3. For fork/adoption, keep the accepted pin even when the remote default branch
   is newer. Stage only intended gitlinks and config; use a candidate checkout
   for upgrades. LangGraph-like libraries remain consumer dependencies.
4. For relocation/cutover, verify process owner, ports and active work; back up
   through the owning app and keep data/secret paths independent of source.
   Check Windows junctions and Python editable paths; repair/reinstall then
   verify the loaded paths. Never kill listeners merely because their port
   matches, or assume stopping a launcher also stopped its database.
5. Validate the real affected consumer, error/retry and preserved state. Run
   doctor from the guide; inspect its scope before calling source-ready an
   execution result. Record failed attempts and their resolution in the owner
   receipt, then update the pin/handoff and commit coherent changes.

Installing source does not authorize new services, provider credentials, paid
runs or broker access. For a worker connection, choose one owner for dispatch,
retry, cancellation and approval; preserve run/artifact provenance outside the
engine. Extract a research workflow skill only after a real flow has been run.
