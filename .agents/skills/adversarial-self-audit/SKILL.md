---
name: adversarial-self-audit
description: Run falsification-first internal red-team self-audits on Naqex quant scripts, MQL5/Python parity, prop pricing/optimizer math, and ops collectors before reporting done. Use before major quant/ops/financial handoffs; not for trivial Q&A, copy-only edits, or Holdout unlock.
---

# Adversarial Self-Audit (Internal Red-Team Verifier)

Replace external audit rounds by actively trying to **break your own implementation and claims** before presenting results to the owner. Passing happy-path unit tests is necessary but never sufficient.

## Hard Boundaries (Fail-Closed)

- **Holdout lock (`>= 2025-01-01`):** Never unlock, read, or mutate `NATIVE_FTMO_HOLDOUT_LOCK.json` (`holdout_rows = 0`).
- **Zero live execution:** Never send orders (`OrderSend = 0`), connect live broker trading, or disable `InpDryRunLogOnly` / `trade_allowed == False` guards.
- **2-Layer OPSEC:** Never place real LAN/Tailscale IPs, hostnames, usernames, account logins, or secrets inside Layer-1 tracked reports, scripts, or skills.
- **Independent evidence only:** Never cite a metric, SHA-256, or test count from memory or a worker summary without verifying the raw file or command output directly.

## Mandatory 7-Vector Falsification Checklist

Run every vector applicable to the task before declaring `PASS`:

1. **Boundary & Poisoned-Input Rejection (Fail-Closed):**
   - Feed `NaN`, `+Inf`, `-Inf`, `0`, negative prices/lots, empty files, malformed JSON, and future dates (`2099-01-01`) — including when relaxed flags like `allow_stale=True` are passed. Every poisoned input MUST raise or exit non-zero, never silently fall back.
2. **API `None` vs Empty `()` & Disconnect Safety:**
   - Verify broker/OS calls returning `None` (transport failure/disconnect) NEVER coerce into `0` open positions, `0` deals, or `flat/safe` state. Separate hard read failure from verified zero.
3. **Read-Only & Identity Locks (Ops / Collectors / Probes):**
   - Live/demo read-only scripts MUST require explicit `--expected-login` and `--expected-server`, abort fail-closed if `trade_allowed == True`, abort if `abs(ntp_offset_ms) >= 1000`, and reject partial/1-tick coverage spoofs (require full phase/window coverage + explicit flagging of same-millisecond ordering ambiguity).
4. **State-Machine & Phase-Transition Integrity:**
   - Verify phase-pass/payout checks require `open_positions == 0` (never pass mid-trade on floating/closed balance alone), check floating DD vs balance DD explicitly (disclose inter-sample gaps honestly), and verify scope filters (e.g., Core7 vs Shadow magics) match the headline verdict.
5. **Non-Monotonic Math & Optimizer Assumptions:**
   - Never assume monotonicity (e.g., binary search over shifting-horizon wait days or promo sweeps) without proving it; prefer dense integer sweeps over small domains (`0..180`) and report continuous-positive ceiling, first dip, and last positive day.
   - Stamp per-tier freshness (`verified_utc`) so updating one tier never silently refreshes untouched tiers. Tag unmeasured firm execution mechanics explicitly (`TERMS_VERIFIED_EXECUTION_UNMEASURED`, `DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`).
6. **Raw-Artifact & SHA-256 Reconciliation:**
   - Recalculate headline counts, sums, win/tie/loss counts, and exact SHA-256 hashes from raw `.htm`/`.csv`/`.json` files; confirm every report table matches raw receipts with `0` unexplained deltas.
7. **Negative-Mutation Proof (`>= 1` Deliberate Break):**
   - Before closing a gate/comparator/validator, prove via unit test that injecting at least 1 realistic defect (flipped SELL slippage sign, 1-sec spoof, future date, missing position close, swapped config field) flips the gate from `PASS` to `FAIL`.

## Execution Pattern (Single-Agent vs Swarm)

- **Multi-lane / `/swarm` / major milestone:** Assign a dedicated **independent verifier** role (read-only/audit mindset) that did NOT author the implementation to re-run tests, inspect raw diffs/SHAs, and try to falsify all 7 vectors before retiring workers.
- **Single-agent high-impact edit:** Run a separate explicit audit pass after editing: re-read `git diff`, run focused negative-mutation tests + `system_doctor.py --mode fast`, and record unresolved real-world caveats honestly instead of smoothing them over.

## Output Contract

Every completed self-audit reports concisely:
1. Exact verified commands, test counts, and SHA-256 hashes of touched critical files.
2. Which of the 7 vectors were attacked and proven fail-closed.
3. Any remaining unverified real-world caveats (e.g., inter-sample tick gap, NTP clock drift, unmeasured firm execution) stated plainly without hand-waving.

## Negative Triggers

- Do NOT trigger for simple factual Q&A, wording/translation tweaks, UI color adjustments, or routine read-only status checks.
- Do NOT use to bypass Holdout locks, weaken tests, or manufacture busywork refactors after all vectors pass.
