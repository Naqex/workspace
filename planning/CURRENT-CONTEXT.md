# Current context — Naqex Workspace

`27/11/2026 05:25 ICT` · `WORK: WORLD-WAR-V2.1-SSOT-RENOVATION-VERIFIED | 0-VND | LIVE-NODE1: UNTOUCHED | HOLDOUT 2025+ SEALED`

`GOAL-NOW: HOÀN TẤT TOÀN BỘ 12/12 LÀN CẢI TỔ AGENT-FIRST SSOT (WORLD-WAR V2.1) + 12/12 PHẢN BIỆN ĐỐI ĐẦU PASS | TÁI DỰNG BĂNG NHÂN QUẢ C10_NEWS_ON (HOLDOUT=0, 0 VND) | CHỜ ĐỒNG BỘ NTP QUYỀN ADMIN (< 1.000 MS) TRƯỚC CỬA SỔ QUOTE_ONLY NFP 04/12 & CPI 10/12`

## 0. Trạng Thái Sau Đợt Cải Tổ Agent-First SSOT (`World-War v2.1`, `27/11/2026`)

- **Kết quả tổng quan (`12/12` làn tác giả + `12/12` làn phản biện độc lập đều `PASS` · `0 VND` · `OrderSend = 0`):**
  - **Hạ tầng, CI & Cổng Kiến trúc (`L1`, `L2`, `L6`):** Chuẩn hóa LF `.gitattributes`, `pyproject.toml` (5 `testpaths` + `ruff`/`ty`/`pytest-xdist`), `.pre-commit-config.yaml`, `tooling/naqex_cli.py`, `tooling/worktree_ctl.py`, `tooling/check_architecture.py` (`ARCH-01..07`, siết `ARCH-03` còn đúng `233` tệp gốc), tách thẻ `@pytest.mark.local_cache` (`40` bài) để CI chạy sạch ngoại tuyến (`-m "not local_cache"`).
  - **Lõi Quant SSOT & Lịch Tin Đỏ (`L3`, `L4`):** Ban hành `quant_core/` SSOT (`schemas`, `metrics` DSR/PBO/CPCV/Hansen SPA, `prop_sim`, `decimal_oracle`, `mql_contract_drift`, `red_news`) cùng hợp đồng `configs/ssot/{firms_catalog,risk_profiles,fx_rates}.json`. [Đính chính tin đỏ 6-CCY](research/RED-NEWS-2025-ERRATA-AND-6CCY-SOURCES-20261127.md) ghi nhận `9` mốc BLS `2025` bị hủy/dời, dựng lịch Dev `2018–2024` `6-CCY` (`523` mốc T1), giữ bất biến `naqex_red_news_utc.csv` (`492` dòng).
  - **Hiệu Năng, Bộ Não & Điều Phối 3 Máy (`L5`):** Gỡ `scipy` khỏi đường nóng (cold import giảm xuống `< 200 ms`), nâng `brain_cli.py` sang SQLite WAL + `vec_blob` (`< 30 ms` cập nhật 1 tệp), hoàn tất `compute_router.py` + `x13_probe.py` chạy thực tế sang `<X13_WORKER>` (`AC=1`, `0` tệp cấm).
  - **Gỡ Lookahead, Sổ Thí Nghiệm & Tách Monolith (`L7`, `L8`):** Khóa `holdout_guard.py` chịu `python -O`, dựng sổ thí nghiệm băm chuỗi `experiment_ledger.py` (`SQLite + DuckDB`), vá `6` điểm lookahead + `2` lỗi mô phỏng (`raw DD` kiểm trước `ea_cut`, `0` Infinite Mulligan), tách `3` tệp lớn (`prop_capital_promo_optimizer`, `cockpit/server`, `ftmo_demo_calibration_probe`) qua façade đồng bộ + `io_utils.py`.
  - **Cấu Trúc, Hệ Sinh Thái & Đối Soát TCA (`L9`, `L10`, `L11`):** Hợp nhất lộ trình về nguồn duy nhất [TOP1-SOLO-QUANT-MASTER-PLAN.md](TOP1-SOLO-QUANT-MASTER-PLAN.md), dọn `156` script cũ vào `legacy/` & `345` báo cáo cũ vào `archive/` (`README.md < 10 KB`, `AGENTS.md` `+0 B`). [Kiểm toán hệ sinh thái & Gitleaks](research/ECOSYSTEM-SECURITY-LICENSE-AUDIT-20261127.md) xác nhận `0` bí mật lộ trên `5` kho Git và `0` copyleft mạnh trong lõi (gắn cờ P0 `diffq-fixed` `CC-BY-NC-4.0` trước thương mại hóa `projects/vi-dubber`). Nâng `quant_core/tca.py` + `daily_statement_reconciler.py` (Markout `+1s..+5m`, chặn `swap != 0` / `FILL_UNRESOLVED`).
- **Thực Tại Dev Hậu-L7 Của `C10_NEWS_ON` (`L12` · `holdout_rows_analysed = 0` · `DEV_BACKTEST_2018_2024`, KHÔNG phải Holdout mù/tiền thật):**
  - Chi tiết tại [C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md](research/C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md): băng nhân quả mới `frozen_9e_tapes_v2` (`1.564` phiên `< 2025-01-01`, `warm hit < 0,30s`) xác nhận biên lõi giữ nguyên (`PORT_7E` `10K` `1x`: `5.408,09 USD`, lệch `-0,098%`; `Core7` `100K` `1x`: `WR 48,61%` · `RR 1,272x` · `EV +0,0486R` · `PF 1,203` · `Max DD 8,62%` · `Calmar 0,861` · `Sharpe 1,234` · hòa vốn trượt giá **`2,31x`**).
  - `FTMO Standard 10K` (`1` vé BF thẻ `70,42 USD` ~ `1,81 tr VND`, ma sát `1,00x`, `10.000` đường MC): `24T` **`61,89% Đậu / 5,60% Rớt / 32,51% Chờ`** (`100%`), `NPV 24T` TB **`+14,97 tr`** / trung vị **`+7,55 tr VND`**, **`EV/Phí +8,25x`**, `P(<=0) = 42,05%`, cháy Funded `12T` `0,01%`, tháng Funded đói payout `66,45%`.
  - **Cảnh báo đỏ hậu-L7:** Bỏ kẹp `< 5%` trong ma trận sốc Flash-Crash cho thấy `Funded 4,06% (SAFE)` nhưng `P2 7,19%`, `P1 Bal 15,00%`, `P1 Spr 16,88% (BREACH)` nếu trượt gap đồng thời `1,25x` -> bắt buộc giữ khiên tin đỏ `±5p` + khóa cụm hướng `USD/JPY/US100`. Đã fuzz **`15.000`** mẫu Hypothesis trên `<X13_WORKER>` + **`20/20`** đột biến âm (`python -O` PASS).

## 1. Khóa An Toàn Bất Biến & Trạng Thái Hạ Tầng

| Thành phần | Trạng thái xác minh | Ghi chú |
|---|---|---|
| **Ứng viên duy nhất & tài chính** | **`C10_NEWS_ON` (`7E`) · `0 VND`** | `Naqex_Master_Prop7E.mq5` bất biến (`6b7ea2ee...`); `OrderSend = 0`; `MT5_PROCS = 0`. |
| **Holdout `2025+` & tệp khóa** | **NIÊM PHONG (`0` dòng / bất biến)** | Lock `f0a6b43c...`; `step3` `a3b65380...`; CSV tin đỏ `235722ed...`; `AGENTS.md` `10.901 B`. |
| **Home-VPS `naqex-node1`** | **UNTOUCHED / CÔ LẬP 24/5** | Không động chạm suốt toàn bộ chiến dịch cải tổ. |
| **Worker `<X13_WORKER>`** | **VERIFIED (`AC=1`, `0` tệp cấm)** | Đã chạy thực tế `15.000` mẫu Hypothesis (`manifest VERIFIED_PASS`). |
| **Đồng hồ NTP (`<DEV_PC>` / `<X13>`)** | **Trôi `-1.615 ms` / `-4.690 ms`** | Chặn fail-closed mặc định; cần Admin `w32tm /resync` về `< 1.000 ms` trước `04/12`. |
| **Kho con `projects/` & Vault** | **Sạch / không bị sửa** | `trader`, `quant-trading`, `vi-dubber`, `private_vault/` giữ nguyên. |

## 2. Việc Kế Tiếp (`0 VND`)

1. **Đồng bộ đồng hồ NTP quyền Admin (`w32tm /resync`)** trên `<DEV_PC>` và `<X13_WORKER>` về `< 1.000 ms` trước cửa sổ `QUOTE_ONLY` quanh **NFP `04/12/2026`** & **CPI `10/12/2026` (`20:25 ICT`)**.
2. **Đóng các điểm drift cấu hình trước mọi lần nạp thực địa mới:** rà soát `mql_contract_drift.py` (bật `InpGuardEnableRedNews=true` trên 2 preset `C10` P1/P2; chốt thư xác nhận EA bằng văn bản từ FTMO / The5ers).
3. **Giữ khóa cổng `G6` (`0 VND`) & đẩy song song nhánh lệch pha:** chuẩn hóa nhánh Alpha #2 trên Dev (`projects/quant-trading`, `|r| < 0,15`, `PBO <= 0,50`) và gỡ phụ thuộc `diffq-fixed` trước khi thương mại hóa `projects/vi-dubber`.
