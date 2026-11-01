# Paperclip runtime and pilot recovery

Read the current [launcher/owner guide](../../../../tooling/paperclip/README.md)
and relevant section of the
[integration receipt](../../../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md)
before using historical pilot commands. The guide owns paths, ports and setup;
this reference records diagnostic boundaries, not a second runtime registry.

The 01/11 pilot demonstrated one completed offline task with artifact, comment
and issue transition. Historical success does not prove current credential,
quota, model, runtime or tool readiness. Verify those under the current task's
authority; health/picker presence alone proves none of them. Review numerical
artifacts even when the agent run says succeeded.

## Diagnose the failed boundary

- Wakeup skipped after a terminal issue run: inspect run/issue association first.
  A comment did not wake the pilot agent. When dispatch is authorized, use a new
  assigned issue or the supported assignment wakeup with payload.issueId; keep
  the earlier run as evidence. Do not create retry issues without a stopping rule.
- Missing agent API credential: the pilot required instance-local
  PAPERCLIP_AGENT_JWT_SECRET. Inspect presence/status without printing values;
  never copy global credentials or invent a new secret as a diagnostic step.
- HTTP 413: check effective request-size limit and measured body size before
  blaming the provider. Pilot overrides were temporary; current config and its
  owner decide the limit. Do not raise it or start the gateway automatically.
- Windows shell/tool failure: inspect the pinned adapter, effective sandbox and
  minimal child-process environment. Earlier failures involved missing Windows
  sandbox configuration, SystemRoot/WINDIR/ComSpec and skill-link junctions.
  Those pilot patches may have been rolled back or superseded; compare current
  source/revision instead of reapplying them from this checklist.

For recovery, keep the same database/storage and process owner. Use the official
backup/API and scope of the owning task; do not write database rows directly.
Record failed runs and the resolution in the existing receipt. MCP docs or a UI
toggle do not prove an authenticated MCP connection is exposed to this agent.

The [G0–G5 research workflow](../../../../planning/research/AI-RESEARCH-WORKFLOW-20261101.md)
is a proposal. Do not call it enforced, provision a team, open holdout or grant
broker/execution authority from it.
