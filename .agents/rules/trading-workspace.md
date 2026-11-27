---
trigger: always_on
---

- **Workspace & Plan Authority:** Read `@../../AGENTS.md` first. For Trading Workspace tasks, read relevant sections of `planning/trader/PLAN.md` (especially `12B` for execution/review). Reuse before building new.
- **CLI Delegation & Hard Permissions:** For explicitly requested CLI delegation, read `tooling/agent-workflow/README.md` and `POLICY.md` (`roles.json` picks model/effort). Never auto-start agents on folder open. Rules never grant broker, deploy, merge, or global provider-config permissions, and never change the Antigravity model picker to Codex Web GPT.
- **Plain Vietnamese Default:** Report and explain in simple, plain Vietnamese (avoid heavy jargon/acronyms unless the owner explicitly asks for deep technical analysis; keep exact file paths/code identifiers only where needed for links/verification).
- **Balanced Strategy & Prop Reporting** *(skip on trivial status checks/code-only Q&A)*: Always present the full balanced set — Winrate, RR, EV/trade & EV/fee, PF, Max DD, Calmar/Sharpe, and monthly `Đậu/Rớt/Chờ` summing to `100%` — in plain terms with VND/USD amounts, evidence stage (backtest vs blind holdout vs demo vs live), break-even/failure threshold, explicit numeric scale (`Xấu -> Đủ dùng -> Tốt -> Top 1% thực tế`, `.agents/skills/strategy-qualification/references/validation-gates.md` Law 15), current position, and concrete gap to Top 1%.
- **Low-Cognitive-Load Formatting:**
  - Lead line 1 with the result or next action (zero preamble or closing pleasantries).
  - Restate `Bước X/Y` on multi-step work; number multi-step actions; keep visible lists `<= 5` grouped items (full detail in files).
  - Give concrete time estimates (minutes/hours); make completed wins explicit; separate secondary tangents at the end.
  - Report errors matter-of-factly without guessing unverified root causes (state `chưa xác định nguyên nhân` + 1 diagnostic step when uncertain).
  - End open threads with ONE concrete `< 2 min` next action (exempt when the owner asks for a full deep walkthrough).
- **Scorecard Visuals:** For `Xấu -> Top 1%` scorecards and `Đậu/Rớt/Chờ` rates, render a compact inline `generative_ui` 4-color gauge widget (`<= 450px` tall, pin marker + 4 range labels + hover tooltips) in chat and vertical color-dot lists (`🔴/🟡/🟢/🏆`) in repo `.md` reports; keep wide multi-column matrices in `.md` files or side-pane artifacts.
- **Zero Idle Waiting:** Never treat waiting periods — multi-week calendar gates (`14d` trial) OR `>= 20 min` passive captures/probes/downloads/renders inside `/goal` or `/swarm` — as dead time. Keep gated actions strictly locked, NEVER park idle agents while non-conflicting backlog exists, and continuously advance high-leverage parallel workstreams (same-plan backlog, audits, counterfactual math, research, knowledge hygiene) without disturbing active captures or the Holdout lock. If only cross-repo or approval-gated work remains with `>= 30 min` left, proactively surface 2–3 concrete options instead of silently idling.
