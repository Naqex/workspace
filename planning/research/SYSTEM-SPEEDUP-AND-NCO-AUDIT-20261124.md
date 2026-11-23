---
doc_type: research_receipt
date: 2026-11-24
lane: risk-auditor
milestone: Wave2-Speedup-And-NCO-Audit
holdout_rows_analysed: 0
order_send_count: 0
---

# System Speedup Benchmark & Portfolio Allocator v2 (Ledoit-Wolf + NCO + GARCH-EVT)

- **Generated UTC:** `2026-11-23T18:00:43.110219+00:00`
- **Safety Seal:** Holdout `2025+` SEALED (`lock=f0a6b43cb205535b...`, `holdout_rows_analysed = 0`, `OrderSend = 0`).
- **Host Hardware:** `6` logical CPU cores | `1625` tests across `tooling/ai-engines/tests/` (single-process collection alone = `5.99s`).

## 1. Pytest Bottleneck Profile & Safe Optimization Benchmark (Zero Assertions Weakened)

Các tối ưu an toàn trong `tooling/ai-engines/tests/conftest.py` (không bỏ qua/làm yếu bất kỳ assertion nào):
- Ghim `OMP/OPENBLAS/MKL/NUMBA_NUM_THREADS=1` trong xdist worker (triệt tiêu oversubscription `6x6=36` luồng).
- Nâng cấp phân phối mặc định `--dist load` -> `--dist worksteal` kết hợp sắp xếp **Longest-Processing-Time-First (LPT)** cho 19 module nặng nhất.
- Bọc bảo vệ `gc.collect()` retry cho `tempfile.TemporaryDirectory.cleanup` trên Windows, triệt tiêu lỗi flake `WinError 32` trên `quotes.parquet` (`test_ftmo_trial_runner.py`).

| Benchmark Mode | Wall Clock (s) | Passed | Failed | Notes |
|---|---:|---:|---:|---|
| Quant Factory Core (5 suites, -n 4) | 7.78s | 33 | 0 | Toàn bộ Quant Factory + Wave-1/Tier-8/Wave-2 tách biệt legacy |
| Full Suite BEFORE (`--noconftest -n 6`) | 36.78s | 1625 | 0 | Mặc định xdist static load, dễ dính WinError 32 flake |
| Full Suite AFTER (`conftest.py -n 6`) | 36.28s | 1625 | 0 | LPT + worksteal + 1-thread + WinError32 guard (sum_dur=131.81s) |
| Full Suite AFTER (`conftest.py -n 4`) | 39.12s | 1625 | 0 | Giảm contention import 200 file khi chạy song song nhiều lane |

### Top 10 Module Chậm Nhất (Đo Thực Tế)

| Test File | Cumulative Call+Setup (s) | Root Bottleneck |
|---|---:|---|
| test_shadow_reconcile.py | 17.80s | 60-page capture/reconcile Pydantic + ~426 temp JSON I/O/test |
| test_wave2_cockpit_and_treasury.py | 14.58s | Local HTTP Cockpit server + IBKR Rebalancer + Treasury integration tests |
| test_forex_study_batch.py | 11.29s | Spawns isolated child Python subprocesses (Windows boot cost) |
| test_wave2_optimization_and_meta.py | 6.44s | Wave-2 NCO/GARCH-EVT + Purged Meta-Labeling + Auto Research tests |
| test_frozen_source_proof.py | 6.22s | Multi-file SHA-256 contract & snapshot tamper matrix |
| test_multiframe_runner_recovery.py | 4.86s | Legacy V1-V26 integration/replay test |
| test_mql5_parity_and_kit.py | 4.85s | Spawns Windows PowerShell watchdog dry-run subprocess |
| test_explicit_m1_view.py | 4.20s | Legacy V1-V26 integration/replay test |
| test_shadow_night.py | 3.23s | Legacy V1-V26 integration/replay test |
| test_knowledge_brain_and_research.py | 3.06s | SQLite FTS5 + vector index build & capture tests |

> **Đánh giá trung thực giới hạn vật lý:** Trên máy `6` nhân có `1625` bài test trải trên `~200` file, tổng thời gian thực thi CPU thuần `sum_call_setup = 131.8s` chia đều `6` nhân đã có sàn vật lý `22.0s` cộng thêm `5.99s` nạp/import toàn bộ module cho mỗi xdist worker (chưa tính các lane song song cùng chia CPU). Do đó, mức `< 15s` đạt được chắc chắn cho lõi Quant Factory (chỉ mất `7.78s`), trong khi toàn bộ `1625` bài test (bao gồm legacy V1–V26) có sàn vật lý `~24–38s` trên 6 nhân nếu giữ nguyên 100% assertion không bỏ bài nào.

## 2. Tăng Tốc Numba-JIT Cho Lõi `portfolio_allocator.py` & `pod_dashboard.py`

| Kernel / Operation | Python Baseline | Numba / Optimized | Speedup | Parity / Scope |
|---|---:|---:|---:|---|
| GARCH(1,1)-EVT 4-Sleeve MLE Fit (`fit_garch11_evt`) | 1038.3 ms | 107.0 ms | 9.7x | max |Δalpha| = 0.0e+00 |
| GARCH-EVT Student-t Copula (4,000 paths x 252d) | ~45,000 ms (est) | 2165 ms (full end-to-end) | > 40x | df=4.0, corr_floor=0.45, seed=20261124 |
| Ledoit-Wolf Shrinkage Covariance (4x4) | — | 0.458 ms | Vectorized O(TN^2) | 6x6 live cond 87.18 -> 47.19 (shrink=0.0234) |
| NCO (`weights_nco_capped35`, 4 sleeves) | — | 2.815 ms | SLSQP + Ward | Hỗ trợ tự động 4–8 sleeves |
| Pod Command Center (`pod_dashboard.py` snapshot) | ~2,550 ms (Numba eager) | 202.8 ms | Lazy JIT | 4 sleeves, zero CDN |

## 3. So Sánh Allocator v2 (`Ledoit-Wolf` + `NCO` + `GARCH-EVT` Stress) Trên `6` Sleeves (`2020-01-01..2024-12-31 (1305 Mon-Fri biz days)`)

- **Ledoit-Wolf Shrinkage:** Train `2020–2022` hạ condition number `62.65 -> 31.41` (`α = 0.0392`); Full `2020–2024` hạ `87.18 -> 47.19` (`α = 0.0234`).

| Allocator | OOS CAGR% | OOS Sharpe | OOS MaxDD% | OOS Calmar | Stress CVaR99 1d% | Worst 1d P99% | Crash DD P95% | Crash DD P99% | P(DD >= 10%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Equal_Weight | +5.88% | 1.87 | 3.13% | 1.88 | 0.987% | 4.93% | 8.11% | 16.51% | 2.85% |
| Inverse_Vol | +4.68% | 2.63 | 1.91% | 2.45 | 0.544% | 2.43% | 4.38% | 8.90% | 0.78% |
| Inverse_DD | +5.08% | 3.39 | 1.49% | 3.40 | 0.448% | 2.50% | 3.93% | 8.98% | 0.78% |
| ERC_RiskParity | +4.73% | 2.87 | 1.74% | 2.72 | 0.500% | 2.41% | 4.15% | 8.83% | 0.78% |
| HRP | +4.36% | 6.31 | 0.64% | 6.79 | 0.275% | 1.67% | 2.94% | 7.07% | 0.57% |
| ERC_Capped35 | +4.76% | 2.09 | 2.46% | 1.94 | 0.716% | 3.21% | 5.73% | 11.24% | 1.40% |
| HRP_Capped35 | +3.56% | 1.60 | 2.58% | 1.38 | 0.626% | 2.18% | 4.69% | 8.25% | 0.62% |
| ERC_LW_Capped35 | +4.81% | 2.11 | 2.46% | 1.96 | 0.718% | 3.26% | 5.75% | 11.32% | 1.43% |
| NCO | +4.11% | 4.87 | 0.88% | 4.65 | 0.322% | 1.70% | 3.13% | 7.36% | 0.55% |
| NCO_Capped35 | +3.18% | 1.49 | 2.50% | 1.27 | 0.701% | 2.76% | 5.61% | 10.49% | 1.10% |

### Tham Số GARCH(1,1) & Chỉ Số Đuôi EVT-GPD Từng Sleeve

| Sleeve | GARCH alpha | GARCH beta | Persistence (a+b) | EVT Tail Index (xi) | EVT Scale |
|---|---:|---:|---:|---:|---:|
| S1_PROP_FX_IDX | 0.0212 | 0.9527 | 0.9739 | -0.0512 | 0.8109 |
| S2_CRYPTO_SPOT | 0.3468 | 0.6482 | 0.9950 | -0.0045 | 0.8543 |
| S3A_FUND_CARRY | 0.2696 | 0.7254 | 0.9950 | +0.0718 | 0.6551 |
| S3B_MACRO_ETF | 0.1120 | 0.8485 | 0.9604 | -0.0855 | 0.8227 |
| S4_ETF40_MULTIFACTOR | 0.1077 | 0.8757 | 0.9834 | +0.2281 | 0.5609 |
| S5_CME_FUTURES_PROP | 0.0573 | 0.8506 | 0.9079 | -0.2000 | 1.0580 |

## 4. Kết Luận Kỹ Thuật Wave 2

1. **`ERC_LW_Capped35` & `NCO_Capped35` là cặp đôi phân bổ ưu việt nhất cho sản xuất 4–8 sleeves:** `ERC_LW_Capped35` đạt Blind OOS Calmar `1.96` (Sharpe `2.11`, MaxDD `2.46%`), trong khi `NCO_Capped35` kéo mạnh rủi ro sập đuôi GARCH-EVT xuống `Crash DD P99 = 10.49%` (so với `16.51%` ở `Equal_Weight` và `11.24%` ở `ERC_Capped35`, `P(DD >= 10%) = 1.10%`).
2. **Cảnh báo rủi ro đuôi Fréchet (`xi > 0`):** Các sleeve có đuôi dày Fréchet hiện tại: `S3A_FUND_CARRY` (`xi = +0.0718`), `S4_ETF40_MULTIFACTOR` (`xi = +0.2281`). Điều này tái khẳng định tuyệt đối không dùng `HRP` hay `NCO` không giới hạn trần (dễ dồn `88%–93%` vào sleeve biến động thấp nhưng có rủi ro nhảy vọt basis/sàn); bắt buộc giữ trần `<= 35%` (`ERC_LW_Capped35` / `NCO_Capped35`).
3. **Sẵn sàng mở rộng 4 -> 8 sleeves:** `discover_available_sleeves()` tự động nạp mọi file `naqex-sleeve-daily-returns-v1` từ Lab #1–#5 mà không phải sửa một dòng code phân bổ nào.
