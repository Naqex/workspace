# Current context — Naqex Workspace

`23/11/2026` · `WORK: ACTIVE/FULL-STACK-QUANT-READY | REVIEW: HOLDOUT-VERIFIED-GO | DOC: COMPACTED-RESUMABLE`

`RESEARCH: HOLDOUT_2025_2026_VERIFIED_9OF9_POS_PORT7E_GO_CALMAR_175_194 · QUANT_POD_SHARPE_191_199 · 8/8 MQ5+PROPGUARD+ORCHESTRATOR · TCA+CUSUM+OPS_READY · ORDERSEND=0`

## 1. Mục tiêu & Ràng buộc bất biến

- **North Star:** Hệ thống giao dịch định lượng full-stack 2 nhánh trực giao — **Nhánh #1 Intraday FX/Index Prop** (`zero-grid`, `zero-martingale`, `swap = 0`, đã qua Holdout mù `2025–2026`) + **Nhánh #2 Crypto Spot Quant** (`t → t+1`, không đòn bẩy, `r = 0.02` với Nhánh #1) — vận hành trên dây chuyền **Quant Factory 4 lớp** ([Lộ trình prop](research/PROP-SYSTEM-ROADMAP.md)).
- **Ràng buộc an toàn bất biến:** Kho Development `.runtime/hot-m1-cache/` (`2018–2024`) và [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) giữ nguyên vẹn (`0` dòng Holdout); dữ liệu Holdout tách riêng tại `.runtime/holdout-m1-cache/`; `OrderSend = 0` (`InpDryRunLogOnly = true` trên mọi EA); không tự sửa global config hay WIP `projects/vi-dubber`.

## 2. Trạng thái danh mục đã kiểm chứng Holdout `2025–2026` (Single Source: [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Danh mục đóng băng (M1 Floating Equity, Prague Reset) | Dev `2018–2024` (`Ann / DD / Cal`) | **Holdout mù `2025–2026` (`Ann / DD / Cal`)** | Phán quyết G0 (`521926f`) |
|---|---|---|---|
| **`PORT_7E_P28_CORE`** (`E1..E7`, `swap=0`) | `+7.73% / 6.36% / 1.21` | **`+12.10% / 6.92% / 1.75`** (`+22.76%` tổng) | **GO** (`7/7` động cơ dương) |
| **`PORT_7E + SYMCAP_100 + Red-News ±5m`** | `+7.11% / 8.19% / 0.87` | **`+12.70% / 6.55% / 1.94`** (`+23.88%` tổng) | **GO** (bản sản xuất Funded) |
| **`PORT_9E_INVDD_SYMCAP_100`** (`InvDD Cụm A`) | `+7.32% / 5.09% / 1.44` | **`+12.28% / 7.46% / 1.65`** (`Daily 1.18%`) | **GO** (`9/9` động cơ dương) |
| **`PORT_9E_UNCAPPED`** (thô chưa phanh) | `+8.83% / 6.37% / 1.39` | `+12.42% / 8.34% / 1.49` | *CONDITIONAL* (`DD > 7.5%`) |

- **Holdout Verdict & Alpha Decay:** Toàn bộ `9/9` động cơ đều dương trên `2025–2026` (`491` ngày, `SPRT = CONFIRM_EDGE_INTACT`, `CUSUM = 0.00σ`, bách phân vị `66.5%–74.5%`). Xem [HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md](research/HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md).
- **Nhánh Alpha #2 Crypto Spot (`projects/quant-trading`):** `C1_TSMOM_VOL20` / `C2_XSEC_TOP2_TREND` dương `+5.98% / +8.98%/năm` (`MaxDD 6.46% / 8.21%`) ngay trong thị trường gấu `2025–2026` (`BTC -53%`). Tương quan với `PORT_7E` chỉ `r = +0.016..+0.021`; ghép thành **One-Person Quant Pod** đạt **`Sharpe 1.91–1.99`, `Calmar 2.09–2.36`** ([CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.md](research/CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.md)).
- **Lịch sử chi tiết Pass 1 → Pass 28:** Xem [research/README.md](research/README.md) và [research/ARCHIVE-INDEX-202611.md](research/ARCHIVE-INDEX-202611.md).

## 3. Hạ tầng Full-Stack Quant Factory & Công cụ vận hành

- **Runtime (`.runtime/quant-audit-v24`, Python 3.12):** `numpy`, `pyarrow`, `scipy`, `numba`, `pytest`, `pytest-xdist`.
- **Dữ liệu & Cache:** `.runtime/hot-m1-cache/` (Dev `2018–2024`, `597.7 MB`) + `_derived/` (`.npz` `< 0.3s`), `.runtime/holdout-m1-cache/` (Holdout `2025–2026`, `124.6 MB`), `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\` (Cold Archive).
- **Lớp vận hành sống đầy đủ (Full-Stack Layer):**
  - MQL5 Production Suite: `tooling/ai-engines/exports/` gồm `Include/Naqex_PropGuard.mqh` v2.0, `Naqex_AccountOrchestrator.mq5` (AMBER/RED + Global Kill-Switch + Orphan detector + `naqex_heartbeat.json`), **`8/8` EA `.mq5` đã nối `PropGuard` với `8` Magic Number duy nhất (`20261122..20261129`)**, và `Files/naqex_red_news_utc.csv` (`2018–2026`).
  - Python Ops & Verification: `quant_factory/` (`data_store`, `eval_pipeline`, `prop_engine`, `report_gen`, **`tca_reconcile`**, **`live_decay_monitor`** tái dùng `CUSUM` của `projects/quant-trading`, **`ops_monitor`**, `holdout_eval_2025_2026`, `crypto_sleeve_study`) + `system_doctor.py --mode fast|full` + skill `quant-factory-ops`.
  - Personal Knowledge Vault & Research Stack: [knowledge/README.md](../knowledge/README.md) (`owner/{PROFILE,CURIOSITY-LOG,DECISIONS-JOURNAL}.md`, `topics/*.md`, gitignored `inbox/`) + `tooling/knowledge/{brain_cli,research_cli}.py` (`.runtime/research-tools`, SQLite FTS5 tiếng Việt không dấu + Vector RRF `< 40 ms`) + CLI `rg`/`fd`/`jq` + skill `research-and-memory-ops`.

## 4. Bước thực thi tiếp theo (chuyển giao Demo / Live có kiểm soát)

1. Biên dịch `8` EA `.mq5` + `Naqex_AccountOrchestrator.mq5` trong MetaEditor (chép `Files/naqex_red_news_utc.csv` vào `MQL5/Files/`), chạy MT5 Strategy Tester **"Every tick based on real ticks"** (`150–250 ms` latency).
2. Treo **FTMO Free Trial `14` ngày** (`OrderSend` chỉ mở trên tài khoản Demo Free Trial khi owner kích hoạt `InpDryRunLogOnly = false`), rồi đối soát `naqex_exec_audit.csv` bằng `quant_factory.tca_reconcile` và `ops_monitor`.
3. Mở **The5ers Free Monthly Competition (`0 USD`)** đo spec MT5 thật + gửi email Support xác nhận EA tự viết theo Terms §11 ([Hồ sơ The5ers](research/THE5ERS-PARALLEL-PROFILE-AND-SPEC-PLAN-20261123.md)).
