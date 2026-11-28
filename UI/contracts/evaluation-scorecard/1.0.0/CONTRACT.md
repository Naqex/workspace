# Evaluation scorecard contract 1.0.0

- **Status:** `candidate`
- **Version:** `1.0.0`
- **Layer:** `UI/` (shared trading-domain contract; does not mutate `UI-Systems/` or consumer `sharedUiPins`)
- **Authoritative references:**
  - [Trading UI contract (line 19 — candidate domain families)](../../../docs/TRADING-UI-CONTRACT.md#L19)
  - [TradingWorkspace shared UI rules (line 26 — promotion after reuse)](../../../AGENTS.md#L26)
  - [ANNAM presentation-state 1.0.0 contract](../../../../UI-Systems/core/contracts/presentation-state/1.0.0/CONTRACT.md)
  - [Evaluation taxonomy SSOT](../../../../tooling/ai-engines/configs/ssot/evaluation_taxonomy.json)
  - [JSON Schema 2020-12 (Pydantic v2 export)](./schema.json)

This document defines the shared trading-domain contract for rendering strategy, portfolio, and prop-evaluation scorecards consistently across reports, interactive explorers, and trading product panels. It is strictly read-only presentation semantics: it grants zero broker, provider, Holdout-unlock, or order-execution authority (`execution_capability: false`, `order_send_count: 0`, `holdout_rows_analysed: 0`).

## Scope and safety invariants

Consumers rendering an `EvaluationScorecard` payload MUST preserve these distinctions and never allow theme styling to erase them:

1. **Four-tier inside-out grading (`domain_tier`):**
   - `T1_CFD_PROP` (single CFD prop bot / fleet), `T2_CME_FUTURES` (CME intraday futures prop), `T3_MULTI_ASSET_OWNBOOK` (multi-asset portfolio / own-book), and `T4_LIVE_OPS` (live reconciliation & forensics) are graded independently against their own tier thresholds. Never display one tier's ceiling as a grade for another tier.
2. **Continuous half-open metric intervals (zero dead zones):**
   - Every finite numeric metric (`profit_factor`, `calmar`, `sharpe`, `ev_per_fee`, `funded_12m_blowup`, `ruin_36m`, `p_le_zero_24m`, `payout_1_cal_days`, `slippage_breakeven`) maps deterministically to exactly one numeric band (`BAD`, `ADEQUATE`, `GOOD`, `TOP_1_PCT`).
3. **Mandatory `presentation-state@1.0.0` binding (`availability`, `freshness`, `certainty`):**
   - Every scorecard root and every phase entry (`p1`, `p2`, `pass_eval`, `funded_12m`) carries a valid `PresentationState` object.
   - Missing or uninstrumented phases (such as legacy Wave 4 Monte Carlo cases without separate P1/P2 splits) MUST use grade `UNKNOWN_LEGACY_UNINSTRUMENTED` with `availability: "ready"`, `freshness: "partial"`, `certainty: "unknown"`, and a non-empty plain-language `label` (canonical Wave 4 label: `"Chưa tách riêng P1/P2 ở dữ liệu Đợt 4"`).
   - `UNKNOWN_LEGACY_UNINSTRUMENTED` MUST NEVER render as numeric zero (`0`, `0%`) or as a green pass badge.
4. **Visible scope, pricing, resolution, and evidence badges:**
   - Every rendered scorecard MUST surface `evidence_stage` (`DEV_IS`, `DEV_BLIND_OOS`, `DEV_CONSUMED_OOS`, `HOLDOUT_SEALED_ONCE`, `SHADOW_DEMO`, `LIVE_REAL`), `data_resolution` (with plain-Vietnamese label, e.g., `XẤP XỈ CẤP NGÀY` for `APPROX_DAILY`), `pricing_regime` (`ALL_REGULAR_SSOT` vs `BLACK_FRIDAY_PROMO` model assumption), `eval_scope` (`SINGLE_TICKET` vs `MULTI_ACCOUNT_FLEET`), and `execution_status` (`MEASURED_DEMO_EXECUTION` vs `TERMS_VERIFIED_EXECUTION_UNMEASURED`).
5. **Legacy and unified grade transparency:**
   - When historical records carry `legacy_grade_code` (for example Wave 4 `TOT` or `DU_DUNG`), consumers preserve `legacy_grade_code` alongside `unified_grade_code` so taxonomy upgrades remain auditable instead of silently rewriting history.
6. **Exact `100%` Pass / Fail / Pending partition:**
   - Whenever `monthly_pass_fail_pending` is displayed, each horizon bar (`3m`, `6m`, `12m`, `24m`, `36m`) must sum to `100.0%` (`tolerance <= 0.0001`) with visible numeric text for all three segments.
7. **Ordered actionable bottlenecks (`exact_bottlenecks[]`):**
   - Bottlenecks render in `severity_rank` order (worst deficit first) displaying machine `code`, current value, target threshold, and plain-Vietnamese `label_vi`.

## Semantic role mapping (theme-independent)

Domain views request semantic roles rather than hard-coded hex colors. Color alone is never the only signal; every badge and gauge pin requires visible text and `ariaLabel`.

| Grade band | Semantic role | Visible text requirement |
| --- | --- | --- |
| `BAD` | `danger` | Band text (`Xấu` / `Bad`) + metric value |
| `ADEQUATE` | `warning` | Band text (`Đủ dùng` / `Adequate`) + metric value |
| `GOOD` | `success` | Band text (`Tốt` / `Good`) + metric value |
| `TOP_1_PCT` | `info` | Band text (`Top 1% thực tế` / `Top 1%`) + evidence stage tag |
| `UNKNOWN_LEGACY_UNINSTRUMENTED` | `stale` | Mandatory `presentation_state.label` (never `0` or green) |

## Schema parity and validation

- Backend validation uses Pydantic v2 (`tooling/ai-engines/quant_factory/wave5/evaluation_catalog.py::EvaluationScorecard`) with zero `jsonschema` runtime dependency.
- `./schema.json` MUST match `export_scorecard_json_schema()` exactly and is verified automatically in unit tests (`tooling/ai-engines/tests/wave5/test_evaluation_scorecard_contract.py`).
- All payloads reject `NaN`, `Inf`, booleans disguised as numbers, invalid partition sums, missing `presentation-state@1.0.0` labels, `holdout_rows_analysed != 0`, and `order_send_count != 0`.

## Promotion criteria

Per `UI/docs/TRADING-UI-CONTRACT.md` (line 19) and `UI/AGENTS.md` (line 26), this contract stays `status: candidate` until:

1. Two real trading consumers (for example Naqex Trader web workspace and Wave 5 standalone evaluation explorer) demonstrate reuse against `./schema.json`.
2. Focused state (`ready`, `partial`, `unknown`, `error`), keyboard/focus, and light/dark QA receipts pass without altering `UI-Systems/` foundations or existing consumer `sharedUiPins`.
3. A versioned promotion receipt records stability review and backward-compatibility guarantees.
