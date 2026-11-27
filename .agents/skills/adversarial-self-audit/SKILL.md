---
name: adversarial-self-audit
description: Run falsification-first internal red-team self-audits on Naqex quant scripts, MQL5/Python parity, prop pricing/optimizer math, and ops collectors before reporting done. Use before major quant/ops/financial handoffs; not for trivial Q&A, copy-only edits, or Holdout unlock.
---

# Adversarial Self-Audit (Internal Red-Team Verifier)

Actively try to **break your own code and claims** before reporting done. Passing happy-path tests is never sufficient.

## Hard Boundaries (Fail-Closed)

- **Holdout lock (`>= 2025-01-01`):** Never unlock, read, or mutate `NATIVE_FTMO_HOLDOUT_LOCK.json` (`holdout_rows_analysed = 0`).
- **Zero live execution:** Never send orders (`OrderSend = 0`), connect live broker trading, or disable `InpDryRunLogOnly` / `trade_allowed == False` guards.
- **2-Layer OPSEC:** Never place real LAN/Tailscale IPs, hostnames, usernames, account logins, or secrets inside Layer-1 tracked reports, scripts, or skills.
- **Independent evidence only:** Never cite a metric, SHA-256, or test count from memory or a worker summary without verifying the raw file or command output directly.

## Mandatory 7-Vector Falsification Checklist

Run every vector applicable to the task before declaring `PASS`:

1. **Boundary & Poisoned-Input Rejection (Fail-Closed):**
   - Feed `NaN`, `+Inf`, `-Inf`, `0`, negative prices/lots, `bool` disguised as numeric, empty files, malformed JSON, and future dates (`2099-01-01`) — including when relaxed flags like `allow_stale=True` are passed. Every poisoned input MUST raise or exit non-zero.
2. **API `None` vs Empty `()` & Disconnect Safety:**
   - Verify broker/OS calls returning `None` (transport failure/disconnect) NEVER coerce into `0` open positions, `0` deals, or `flat/safe` state. Separate hard read failure from verified zero.
3. **Read-Only & Identity Locks (Ops / Collectors / Probes):**
   - Live/demo read-only scripts MUST require explicit `--expected-login` and `--expected-server`, abort fail-closed if `trade_allowed == True`, abort if `abs(ntp_offset_ms) >= 1000`, and reject partial/1-tick coverage spoofs.
4. **State-Machine & Phase-Transition Integrity:**
   - Verify phase-pass/payout checks require `open_positions == 0`, check floating DD vs balance DD explicitly (disclose inter-sample gaps honestly), and verify scope filters (Core7 vs Shadow magics) match the headline verdict.
5. **Non-Monotonic Math & Optimizer Assumptions:**
   - Never assume monotonicity without proof; prefer dense integer sweeps over small domains (`0..180`) and report continuous-positive ceiling, first dip, and last positive day.
   - Stamp per-tier freshness (`verified_utc`) and tag unmeasured firm execution mechanics explicitly (`TERMS_VERIFIED_EXECUTION_UNMEASURED`, `DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`).
6. **Raw-Artifact & SHA-256 Reconciliation:**
   - Recalculate headline counts, sums, win/tie/loss counts, and exact SHA-256 hashes from raw `.htm`/`.csv`/`.json` files; confirm every report table matches raw receipts with `0` unexplained deltas.
7. **Negative-Mutation Proof (`>= 1` Deliberate Break):**
   - Before closing a gate/comparator/validator, prove via unit test that injecting at least 1 realistic defect (flipped SELL slippage sign, 1-sec spoof, future date, missing position close, swapped config field) flips the gate from `PASS` to `FAIL`.
- **Bug catalog (on demand):** Read [references/offensive3-bug-patterns.md](references/offensive3-bug-patterns.md) for zero-gap, PowerShell, `tzdata`, lot-floor & LLM traps.

## Execution Pattern & 9-Stage Workflow Handoffs

- **Multi-lane / `/swarm` / major milestone:** Assign a dedicated read-only **independent verifier** (see [parallel-agent-workflow](../parallel-agent-workflow/SKILL.md)) that did NOT author the implementation to attack all 7 vectors before retiring workers.
- **Upstream stages handing off here:** [strategy-research](../strategy-research/SKILL.md), [whitebox-prop-discovery](../whitebox-prop-discovery/SKILL.md), [quant-factory-ops](../quant-factory-ops/SKILL.md), and [naqex-node-ops](../naqex-node-ops/SKILL.md).
- **Downstream handoffs after `PASS`:**
  - Strategy / economic gate review -> [strategy-qualification](../strategy-qualification/SKILL.md)
  - Durable receipt & delta recording -> [evidence-continuity](../evidence-continuity/SKILL.md)
  - Post-batch systemic lessons -> [engineering-retrospective](../engineering-retrospective/SKILL.md)

## Typed Output Contract (`quant_core/schemas.py`)

Emit a structured receipt matching `AdversarialAuditReceipt` (and stage handoff `HandoffEnvelope`) in [schemas.py](../../../tooling/ai-engines/quant_core/schemas.py):

```json
{
  "schema_version": "naqex-adversarial-audit-receipt-v1",
  "audit_id": "audit-<lane>-YYYYMMDD",
  "target_path": "tooling/ai-engines/...",
  "target_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "audited_utc": "2026-11-26T20:00:00Z",
  "auditor_role": "independent-verifier",
  "vectors_checked": ["V1_BOUNDARY", "V6_SHA256", "V7_MUTATION"],
  "negative_mutations": [
    {
      "mutation_id": "mut-01",
      "description": "Inject NaN / future date / flipped SELL sign",
      "expected_outcome": "FAIL_CLOSED",
      "observed_failed": true,
      "evidence_ref": "tests/test_...::test_negative_mutation"
    }
  ],
  "caveats": ["State unverified real-world caveats plainly"],
  "passed": true,
  "holdout_rows_analysed": 0,
  "order_send_count": 0
}
```

`passed: true` fails validation unless `negative_mutations` has `>= 1` entry with `observed_failed: true`, `holdout_rows_analysed == 0`, and `order_send_count == 0`.

## Negative Triggers

- Do NOT trigger for simple factual Q&A, wording/translation tweaks, UI color adjustments, or routine read-only status checks.
- Do NOT use to bypass Holdout locks, weaken tests, or manufacture busywork refactors after all vectors pass.
