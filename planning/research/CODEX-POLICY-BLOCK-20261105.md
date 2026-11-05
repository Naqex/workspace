# Codex Windows: opaque pre-execution policy rejection

Investigated05/11/2026. Scope: legitimate local maintenance in TradingWorkspace;
no application launch retry, safeguard removal, alternate execution route or
global permission expansion was performed during this investigation.

## What is established locally

| Evidence | Observation |
|---|---|
| Rejection boundary | `CreateProcess ... Rejected ... blocked by policy`, before the requested command runs |
| Affected operation | Existing Paperclip launcher, hidden window, localhost embedding origin; the shell command included an HTTP URL and process-launch syntax |
| Additional observed rejection | A read-only source-inspection command containing HTTP and launch words as search strings was also refused before execution |
| Global config | `sandbox_mode = "danger-full-access"`, `approval_policy = "never"`; no reviewer override |
| Active thread metadata | Permission profile disabled, approval mode never, CLI version0.166.0-alpha.6 |
| Desktop package | OpenAI.Codex26.1029.7803.0 |
| Separate CLI on PATH | codex-cli0.164.0; changing this installation would not establish that the active bundled runtime changed |
| Project config before repair | Only MCP configuration; project marked trusted in user config |
| Local rules | No rule files found in the inspected global rules directory or project `.codex` tree |
| Managed files checked | No requirements.toml/managed_config.toml at the inspected user/OpenAI ProgramData locations; other policy delivery channels are not ruled out |
| Diagnostics | Current thread had0guardian feedback records and no matching denial rows in the bounded local logs query. The current rollout slice did not retain the original raw failure. This does not establish absence of every other log or reviewer |

The successful file/Git/test operations and the pre-execution rejection do not
support treating this as an ordinary NTFS error or a broken Paperclip process.
The specific enforcing component/rule ID is **not confirmed** by a runtime
decision trace. Static Windows command classification is the leading hypothesis.

Earlier reports called this an "automatic approval reviewer rejection". That
attribution was more specific than the retained evidence supports: the verified
fact is a tool-level policy refusal. Do not assume a reviewer agent ran.

## Research findings

- [Official approval documentation](https://learn.chatgpt.com/docs/agent-approvals-security)
  distinguishes filesystem access from approval behavior. `on-request` provides
  an interactive review path; `never` cannot ask. Eligible requests can instead
  use `approvals_reviewer = "auto_review"`, with additional model usage.
- [Official config precedence](https://learn.chatgpt.com/docs/config-file/config-basic)
  places invocation overrides above trusted project config, which is above user
  defaults. Editing a file cannot guarantee replacement of an explicit app/task
  invocation policy.
- [Official config reference](https://learn.chatgpt.com/docs/config-file/config-reference)
  documents on-request/never/granular policies and the separate reviewer setting.
- [Upstream issue41779](https://github.com/openai/codex/issues/41779) includes a
  community source analysis of Windows URL/launch heuristics and the generic
  diagnostic. Its proposed diagnostic patch is not an installed/vendor-supported
  fix on this PC. The issue was open when inspected.
- [Upstream core source, main](https://github.com/openai/codex/blob/main/codex-rs/core/src/exec_policy.rs)
  maps some dangerous-command matches to the generic rejection. Main was read;
  exact source execution equivalence with the installed binary was not proven.
- [Issue41068](https://github.com/openai/codex/issues/41068) reports a distinct,
  explicit prompt-rule/never conflict that recovered with on-request in one
  environment. We found no such local prompt rule, so it is supporting evidence
  for the review route, not proof of the same root cause.
- [Issue45403](https://github.com/openai/codex/issues/45403) contains reports that
  the desktop continued to pass never despite an on-request file setting. Do not
  claim that a saved TOML change has changed the current session.
- [Reddit discussion](https://www.reddit.com/r/codex/comments/1x39vnw/windows_codex_blocked_by_policyhow_do_i_identify/)
  includes a reported rule exception/new-session remedy, with uncertainty about
  the trigger; this is anecdotal and was not adopted as a broad allow rule.
- [OpenAI Developer Community discussion](https://community.openai.com/t/windows-codex-rejected-blocked-by-policy-how-can-i-identify-what-blocked-it/1404871)
  reports the same opaque refusal class without a confirmed remedy.

No confirmed universal fix or exact fixed release was established. Do not
install community-patched binaries, change shell/encoding to evade rejection,
or add blanket PowerShell/Node allow rules as a remedy.

## Scoped remediation prepared

Added only `approval_policy = "on-request"` at the root of the project's existing
`.codex/config.toml`. All parsed MCP settings were compared before/after and
preserved; global config, sandbox and reviewer were not changed. This restores a
review-capable project default, not an exemption from command safety policy.

Backup: `.runtime/diagnostics/codex-policy-20261105/project-config.before.toml`.
Original SHA256:
`bf2257687d71f6223aea26fc7aa38a034de2a13e7a1884c78a198b15cc8ae2b6`.
Rollback restores that exact file; do not overwrite unrelated future MCP edits.

Maintainer audit before and after: statusok,0errors/0warnings; global12279B,
project9269/65536B, reserve56267B, combined21548B. TOML parse and full comparison
confirmed that only the project approval key changed. No credentials were
printed, uploaded or changed. This does not verify that a blocked launch works.

## Required activation and acceptance

The current task still has the app-supplied `never` permission instruction. The
agent cannot replace that active policy through a configuration edit or perform
an escalation while it remains in effect.

1. Owner selects an approval-capable mode in the desktop task controls, such as
   Ask for approval/on-request. If automatic review is preferred, use the app's
   supported review mode when available; do not silently enable it from research.
2. Inspect the next turn's effective permission/approval context. If it still
   says never, open a new task with the intended mode and resume from the existing
   AI plan/receipt. App restart may refresh a stale session but is not a proven
   fix by itself; this investigation did not restart the owner's app.
3. Once effective policy permits review, submit the original, already-authorized
   bounded Paperclip launch for review. Verify launcher ownership, health and
   publication afterward. Do not treat an unrelated harmless command as proof.
4. If refused again, retain exact time, runtime version and sanitized tool error;
   stop equivalent retries and prepare support feedback. Any support submission
   requires the owner's authorization; no report was sent externally here.

Current acceptance: configuration prepared and audited; **active-mode change,
original-operation review and end-to-end recovery remain unverified**.
