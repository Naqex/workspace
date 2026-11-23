# Current context — Naqex Workspace

`23/11/2026` · `WORK: ACTIVE/QUANT-FACTORY-UPGRADED | REVIEW: VERIFIED | DOC: COMPACTED-RESUMABLE`

`RESEARCH: FROZEN_PRE_HOLDOUT_PORT7E_CALMAR_121_PORT9E_CALMAR_139 · QUANT_FACTORY_4LAYER_ACTIVE · 8/8 MQ5 + SHARED PROPGUARD · HOLDOUT >= 01/01/2025 LOCKED · PROP: PRE_HOLDOUT_BLINDSPOT_VERIFIED`

## 1. Mục tiêu & Ràng buộc bất biến

- **North Star:** Hệ thống giao dịch tự động white-box đa động cơ (`zero-grid`, `zero-martingale`, `swap = 0`, kiểm chứng M1 Bid/Ask thực tế) vận hành trên dây chuyền **Quant Factory 4 lớp linh hoạt** (cắm-và-chạy theo JSON config) đủ bằng chứng vượt **FTMO 2-Step (Swing/Standard)** và **The5ers (High Stakes / Hyper Growth)** bền vững ([Lộ trình prop](research/PROP-SYSTEM-ROADMAP.md)).
- **Ràng buộc an toàn bất biến:** Khóa cứng Holdout từ `01/01/2025` (`holdout_rows = 0`, [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json)), `OrderSend = 0`, không tự sửa global config, không đụng pin `projects/trader` hay WIP `projects/vi-dubber`. Kho săn ý tưởng `D:\ANNAM\strategy-intel` giữ **Air-Gap tuyệt đối**.

## 2. Trạng thái danh mục đóng băng (Single Source of Truth: [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Danh mục đóng băng (`2018–2024` M1 Floating Equity, Prague Reset) | Lãi/năm (`A / B`) | `DailyDD` | `FloatDD` | `Calmar` | Giữ lãi dưới khóa tin đỏ `±5m` (US / US+UK) |
|---|---:|---:|---:|---:|---:|
| **`PORT_7E_P28_CORE`** (`E1..E7`, `swap=0`, 100% FTMO Demo Spec Bound) | `+7.73%` (`+8.22 / +7.36%`) | `1.95%` | `6.36%` | **`1.21`** | `91.7%` (`Cal 0.87`) / `88.6%` (`Cal 0.92`) |
| **`PORT_9E_P28_TURBO`** (`E1..E7 + FX_USD_BASKET + XAU_EXP_120`) | **`+8.83%`** (`+9.96 / +7.97%`) | `2.24%` | `6.37%` | **`1.39`** | **`93.3%` (`Cal 1.02`) / `90.4%` (`Cal 1.08`)** |

- **Khám phá mới nhất (Pass 24–28 & Pre-Holdout Audit):** Thêm 5 động cơ/vệ tinh trực giao ngoài lõi 3E cũ (`US100 SESS_CONT_BRK_40`, `US100 RS_1130`, `EURJPY VOLCOMP_EXP75`, `USDJPY NY_RISK_FLOW_10ET`, `FX_USD_BASKET_12U_Z35`); đo xong spec FTMO-Demo thật cho `US100.cash`/`GER40.cash`/`BTCUSD` (`sha256 220b916e60a7`, `OrderSend = 0`); kiểm chứng `Cluster-A Inverse-DD + Downside Vol Brake [0.55, 1.00]` (`PeakDD 4.89%`, `UW` Cụm B `5.4m`, cháy P1 `0.4%`, `Pass 24m = 78.2%`) và trần `1.00%`/mã (`SYMCAP_100`) giữ `PORT_7E` Funded `+7.79%/năm` (`Cal 1.23`).
- **Biên giới tốc độ thi quỹ (`N = 2,000`):** 2-Step `PORT_9E @ 2.5×–3.0×` đạt trung vị **`6.8–7.6` tháng** (`Br1 0.8%–1.7%`, `CF12 +172..+185 USD`, `CF24 +736..+756 USD` FTMO / `+372..+379 USD` The5ers); 1-Step Hyper Growth `2.0×` (`1tr <= 1%`) đạt **`4.8` tháng** (`51.6%` trong 6m, phí `$260` không hoàn lại).
- **Lịch sử chi tiết Pass 1 → Pass 28:** Xem [research/README.md](research/README.md) và [research/ARCHIVE-INDEX-202611.md](research/ARCHIVE-INDEX-202611.md).

## 3. Hạ tầng Quant Factory, Dữ liệu & Công cụ vận hành

- **Runtime đã tối ưu (`.runtime/quant-audit-v24`, Python 3.12):** `numpy`, `pyarrow`, `scipy`, **`numba`** (JIT 100× cho lifecycle/MC), **`pytest` + `pytest-xdist`** (chạy song song 6 nhân).
- **D: SSD Hot M1 Parquet Cache (`.runtime/hot-m1-cache/`, `597.7 MB` / `31.02M` phút / 12 tài sản 100% Native Bid/Ask, đọc lạnh `1.64s`)** + Derived Cache `.npz` (`< 0.3s`). E: Cold Archive (`510 GB` trống) giữ raw CSV, kết quả Pass và raw JSON `> 1 MiB` (đã fix `check_anti_bloat.py` = `passed: true`).
- **Dây chuyền 4 lớp không gắn cứng:**
  - Cấu hình JSON: `tooling/ai-engines/configs/` (`firms/`, `profiles/`, `calendars/`).
  - Core Factory: `tooling/ai-engines/quant_factory/` (`data_store.py`, `eval_pipeline.py`, `prop_engine.py`, `report_gen.py`).
  - Thư viện MQL5 dùng chung: `tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh` (DST, `TICK_VALUE_LOSS`, Daily Breaker, Per-Symbol Risk Cap, Red-News `±5m` CSV, Spread Guard, Holiday Early-Close, Restart Recovery, `InpDryRunLogOnly = true`) + `8/8` EA `.mq5` sạch.
  - Bác sĩ hệ thống 1 lệnh: `tooling/ai-engines/system_doctor.py --mode fast|full` (và skill `.agents/skills/quant-factory-ops/SKILL.md`).

## 4. Cổng duy nhất trước khi mở Holdout `2025–2026` & vào tiền

1. Rà soát đầy đủ [PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md](research/PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md) (DSR tích lũy, tương quan đuôi 5%, giới hạn rủi ro theo mã `US100`/`USDJPY`, kiểm parity MT5 Demo).
2. Chỉ mở khóa **1 lần duy nhất Holdout `2025–2026`** khi owner xác nhận rõ — sau khi mở không sửa tham số.
3. Trước khi thi thật trên The5ers: mở Free Monthly Competition (`0 USD`) đo MT5 `SymbolInfo` + gửi email Support xác nhận EA tự code theo Terms §11 ([Hồ sơ The5ers & MCP](research/THE5ERS-PARALLEL-PROFILE-AND-SPEC-PLAN-20261123.md)).
