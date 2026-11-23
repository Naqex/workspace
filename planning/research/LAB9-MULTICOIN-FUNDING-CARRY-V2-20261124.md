---
title: "Lab #9: Multi-Coin Diversified Perpetual Funding Carry v2 (S3A v2) & Tail-Risk Reduction Study"
date: "2026-11-24"
lane: "Lane C (quant-rnd)"
cycle: "Wave-2 Cycle 4F"
status: "COMPLETE — KEEP_S3A_V1 (0/7 Strict Dominators; 1/7 Council-Approved Satellite)"
holdout_rows_analysed: 0
---

# Lab #9 — Nghiên Cứu Multi-Coin Funding Carry v2 (`S3A v2`) & Giảm Rủi Ro Đuôi EVT (`2020–2026`)

> **Tóm tắt điều hành (Executive Decision: `KEEP_S3A_V1`):** Thử nghiệm toàn bộ `M = 8` cấu hình Funding-Rate Carry (`1` chuẩn gốc `S3A v1` + `7` biến thể đa coin `S3A v2`) trên dữ liệu thực `20` hợp đồng perpetual Binance thanh khoản cao nhất (`2020-01-01..2026-11-22`, `2,518` ngày, **zero pre-listing allocation**, `Holdout 2025+ FX/Idx` khóa kín `holdout_rows_analysed = 0`). **Kết quả fail-closed rõ ràng: `2/8` đạt `APPROVE_FOR_INCUBATION` (`F9_V1_BTC_ETH_BASE` và `F9_TOP5_HYST_12_4`), `0/7` biến thể đa coin đánh bại tuyệt đối `S3A v1`.** Do đó, **giữ nguyên `S3A v1` (`CARRY_BTC_ETH_CONS_2XBUF`)** và **không ghi đè** `.runtime/quant-pod-returns/sleeve3a_funding_carry.json` (SHA-256 giữ nguyên `eccaac5ef070f827...`).

---

## 1. Bối Cảnh, Dữ Liệu & Giả Định Chi Phí Thực Tế

- **Động lực:** Ở Wave-2 Cycle 3 ([QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md](QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md)), `S3A_FUND_CARRY` (`BTC+ETH`) có chỉ số đuôi trái GARCH(1,1)-EVT kiểu Fréchet (`evt_xi = +0.0718` trên chuỗi Mon–Fri `2020–2024`, tái lập chính xác `4` chữ số thập phân từ file gốc!) và độ tập trung cao vào `2` đồng coin.
- **Nguồn dữ liệu offline (0 gọi mạng, 0 API key, `OrderSend = 0`):** Tái sử dụng trực tiếp chuỗi 8h funding rate thực đã thanh toán (`rates/*.parquet`) và giá D1 Perp/Spot (`perp_1d/*.parquet`, `1d/*.parquet`) của `20` coin (`BTC, ETH, BNB, SOL, XRP, ADA, DOGE, LINK, LTC, BCH, DOT, AVAX, ATOM, TRX, NEAR, FIL, UNI, AAVE, ETC, XLM`) trong `.runtime/crypto-spot-cache/funding/` và `.runtime/crypto-spot-cache/1d/`. Báo cáo JSON tổng hợp lưu riêng tại `.runtime/crypto-statarb-cache/lab9_funding_carry_v2_summary.json`.
- **Phân tách mẫu nghiêm ngặt (khớp Lab #2 / #2B):**
  - **Cluster A (In-Sample):** `2020-01-01` đến `2023-06-30` (`1,277` ngày).
  - **Blind Cluster B (Out-of-Sample):** `2023-07-01` đến `2026-11-22` (`1,241` ngày).
  - **Căn chỉnh Gate 4 vs `S1` (`PORT_7E` Dev):** Khớp 1-đối-1 theo đúng ngày ISO trên đoạn giao `2023-07-01..2024-12-31` (`550` ngày lịch, `Holdout Lock SHA-256 = f0a6b43cb205535b...`, `holdout_rows_analysed = 0`).
- **Mô hình chi phí & ký quỹ CEX (`lab9_multicoin_funding_carry_v2.py`):**
  - **Taker chuẩn (`1x` / `2x`):** `10.0 bps/chân` (`20.0 bps` cặp Spot+Perp) + `3.0 bps` trượt basis khi vào/ra = **`23.0 bps` 1 chiều (`46.0 bps` khứ hồi)** tại `1x`; nhân đôi **`46.0 bps` 1 chiều (`92.0 bps` khứ hồi)** tại `2x` stress.
  - **Phí sốc thoát lệnh (`exit_shock_cost`):** Bất cứ khi nào giảm tỷ trọng trong ngày funding âm hoặc basis Spot-Perp giãn bất lợi (`r_spot - r_perp < 0`), trừ thêm `0.5 * max(0, -(r_spot - r_perp)) + max(0, -funding)` (tối đa `25 bps` tại `1x`, `50 bps` tại `2x`) trên phần notional thoát ra, cộng với Daily Basis Mark-to-Market đầy đủ.
  - **Deadband trọng số nhân quả:** Các chiến lược Inverse-Vol chỉ tái cân bằng khi tập coin nắm giữ thay đổi, khi hệ số regime thay đổi, hoặc khi độ lệch trọng số `>= 5%` notional (loại bỏ nhiễu xoay vòng giả hàng ngày do vol 20d dao động nhỏ).
  - **Đệm ký quỹ (`equity_buffer_mult`):** `2.0x` (tối đa `50%` vốn Spot Long + `50%` USDT ký quỹ 1x Perp Short -> ngưỡng thanh lý Isolated `+95%` nhảy giá Mark trong ngày) và `2.5x` (`40%` notional, `<= 8.0%` vốn mỗi coin -> ngưỡng Isolated `+145%`). Tiền mặt USDT nhàn rỗi tính `0%` lãi suất.
  - **Hội đồng Nghiên cứu (`research_council.py`):** `m_family = 8`, tích lũy `n_trials_cumulative = 13` (`5` thử nghiệm Wave-1 + `8` biến thể Lab #9), ngưỡng `BH-FDR q <= 0.10`, `DSR >= 0.50`, `Cl.B Sharpe >= 0.60`, `Breakeven >= 2.00x`, `|r(S1)| <= 0.25`.

---

## 2. Bảng So Sánh Toàn Diện `M = 8` Biến Thể (Verbatim JSON Parity)

Mã nguồn: [lab9_multicoin_funding_carry_v2.py](../../tooling/ai-engines/quant_factory/lab9_multicoin_funding_carry_v2.py) | Kiểm thử: [test_wave2_lab9_funding_carry_v2.py](../../tooling/ai-engines/tests/test_wave2_lab9_funding_carry_v2.py).

| Spec ID | Buf | Cl.A 1x SR | Cl.B 1x CAGR | Cl.B 1x SR | Cl.B 1x MDD | Cl.B 1x Calmar | Cl.B 1x TO/yr | Cl.B 2x CAGR | Cl.B 2x SR | BE | BH q | DSR | r(S1) Cal/MF | xi MF24 | xi Full | P99 DD MF24 | Liq Iso/Cross | Council Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `F9_V1_BTC_ETH_BASE` | 2.0x | 7.93 | 3.02% | 8.83 | 0.35% | 8.58 | 2.50x | 2.42% | 5.09 | 6.11x | 0.00000 | 1.000 | -0.038 / -0.031 | 0.1075 | 0.3337 | 6.64% | 0 / 0 | `APPROVE_FOR_INCUBATION` |
| `F9_TOP5_HYST_12_4` | 2.0x | 7.16 | 1.37% | 3.89 | 0.24% | 5.84 | 4.44x | 0.32% | 0.66 | 2.31x | 0.00005 | 1.000 | -0.071 / -0.057 | 0.1497 | 0.1375 | 8.28% | 0 / 0 | `APPROVE_FOR_INCUBATION` |
| `F9_TOP8_INVVOL_HYST` | 2.0x | 5.85 | -0.12% | -0.22 | 3.78% | -0.03 | 16.69x | -3.97% | -4.82 | 0.97x | 0.81207 | 0.017 | -0.045 / -0.039 | 0.0876 | 0.0181 | 4.53% | 1 / 0 | `REJECT_KILLED` |
| `F9_TOP10_TIER1_CAP20` | 2.5x | 6.16 | 0.32% | 0.80 | 2.76% | 0.11 | 12.44x | -2.60% | -4.30 | 1.11x | 0.27584 | 0.409 | -0.018 / -0.022 | 0.2894 | 0.0815 | 4.16% | 1 / 0 | `REJECT_KILLED` |
| `F9_ALL20_PERSIST_14D` | 2.0x | 7.07 | 1.80% | 4.46 | 0.75% | 2.41 | 7.69x | -0.04% | -0.06 | 1.98x | 0.00000 | 1.000 | -0.033 / -0.029 | 0.2213 | -0.0437 | 5.51% | 7 / 0 | `REJECT_KILLED` |
| `F9_TOP8_REGIME_BRAKE` | 2.0x | 4.14 | -0.25% | -0.46 | 3.95% | -0.06 | 16.45x | -4.05% | -4.61 | 0.94x | 0.82160 | 0.005 | -0.036 / -0.046 | 0.1478 | 0.0588 | 4.14% | 1 / 0 | `REJECT_KILLED` |
| `F9_TOP6_MAKER_ENTRY` | 2.0x | 7.21 | 1.13% | 2.72 | 0.67% | 1.70 | 14.62x | -1.18% | -1.98 | 1.49x | 0.00126 | 1.000 | -0.027 / -0.032 | 0.2099 | -0.1056 | 4.99% | 0 / 0 | `REJECT_KILLED` |
| `F9_TOP5_BEAR_GUARD` | 2.0x | 5.45 | -0.78% | -1.49 | 3.55% | -0.22 | 17.50x | -4.80% | -5.29 | 0.81x | 0.98412 | 0.000 | 0.025 / 0.033 | -0.0341 | 0.0632 | 8.96% | 0 / 0 | `REJECT_KILLED` |

### Độ Nhạy Thực Thi Maker vs Taker Trên `F9_TOP6_MAKER_ENTRY` (Blind Cl.B, `TO = 14.62x/yr`)

| Chế Độ Khớp Lệnh (`F9_TOP6_MAKER_ENTRY`) | Phí 1 Chiều (+3bps Basis) | Cl.B 1x CAGR | Cl.B 1x SR | Cl.B 1x MDD | Cl.B 2x CAGR | Cl.B 2x SR | Nhận Xét |
|---|---:|---:|---:|---:|---:|---:|---|
| **Maker Limit (70% fill, `6.15 bps/chân`)** | 15.30 bps | 1.13% | 2.72 | 0.67% | -1.18% | -1.98 | Sống ở 1x, gãy Gate 3 ở 2x (`BE = 1.49x`) |
| **Taker Chuẩn (`10.0 bps/chân`)** | 23.00 bps | -0.00% | 0.00 | 2.36% | -3.38% | -4.16 | Hòa vốn 1x, âm nặng ở 2x |
| **Taker Khắt Khe (`15.0 bps/chân`)** | 33.00 bps | -1.45% | -2.34 | 5.48% | -6.17% | -5.54 | Âm ngay tại 1x do turnover `14.62x/yr` |

---

## 3. Stress Khủng Hoảng Lịch Sử & Kiểm Toán Đuôi GARCH(1,1)-EVT

| Spec ID | May 2021 Crash (Ret / MDD) | FTX Nov 2022 (Ret / MDD) | Full Bear 2022 (Ret / MDD) | Aug 2024 Yen Shock (Ret / MDD) | Worst Day MF24 | Max Mark Jump | Max Cross-Margin Draw |
|---|---:|---:|---:|---:|---:|---:|---:|
| `F9_V1_BTC_ETH_BASE` | +1.11% / 0.15% | -0.11% / 0.36% | -0.04% / 0.56% | -0.13% / 0.20% | -0.682% | 30.90% | 27.94% |
| `F9_TOP5_HYST_12_4` | +0.93% / 0.35% | +0.00% / 0.00% | +0.10% / 0.08% | +0.00% / 0.03% | -0.512% | 82.77% | 26.30% |
| `F9_TOP8_INVVOL_HYST` | +0.52% / 0.63% | -0.39% / 0.43% | -2.17% / 2.44% | -0.26% / 0.28% | -0.651% | 147.72% | 27.65% |
| `F9_TOP10_TIER1_CAP20` | +0.56% / 0.38% | -0.25% / 0.38% | -2.06% / 2.20% | -0.25% / 0.28% | -0.410% | 147.72% | 18.52% |
| `F9_ALL20_PERSIST_14D` | +0.73% / 0.50% | -0.23% / 0.36% | -1.24% / 1.43% | -0.18% / 0.22% | -0.537% | 405.46% | 41.50% |
| `F9_TOP8_REGIME_BRAKE` | +0.49% / 0.62% | -0.97% / 1.01% | -4.12% / 4.40% | -0.38% / 0.38% | -0.651% | 147.72% | 27.65% |
| `F9_TOP6_MAKER_ENTRY` | +1.01% / 0.29% | +0.13% / 0.17% | +0.41% / 0.33% | +0.05% / 0.03% | -0.518% | 88.20% | 28.71% |
| `F9_TOP5_BEAR_GUARD` | +0.03% / 0.95% | +0.01% / 0.07% | -0.57% / 0.63% | +0.01% / 0.06% | -0.357% | 88.20% | 27.75% |

---

## 4. 4 Phát Hiện Định Lượng Cốt Lõi (Vì Sao `S3A v1` Vẫn Thắng)

1. **Bẫy Turnover Trong Chế Độ Funding Bị Nén (`2023–2026`):** Trong Cluster A (`2020–2023`), funding altcoin thường vượt `+20%..+50%/năm`, nên cả `7/7` biến thể đa coin đều đạt Cl.A Sharpe `4.14–7.21`. Nhưng ở Blind Cluster B (`2023-07..2026-11`), dòng vốn arbitrage tổ chức (ETF + Ethena `USDe`) nén funding trung bình về vùng `+5%..+10%/năm` (`+2.5%..+5.0%` trên tổng vốn ở đệm `2.0x`). Khi các hệ thống xoay vòng Top-5..Top-10 altcoin tạo turnover **`7.69x–17.50x/năm`**, chi phí giao dịch thực (`23 bps` 1 chiều + phí sốc thoát lệnh) ăn mòn **`1.8%–4.0%/năm`** — triệt tiêu sạch lợi suất. Ngược lại, `F9_V1_BTC_ETH_BASE` chỉ xoay vòng **`2.50x/năm`** (`34` ngày tái cân bằng trong `3.4` năm), giữ lại `> 85%` gross carry (`+3.02%` CAGR, Sharpe `8.83`, `BE = 6.11x`).
2. **Nghịch Lý Chỉ Số Đuôi EVT `xi` vs Thiệt Hại Tuyệt Đối:** Trên chuỗi đầy đủ 24/7 (`2,518` ngày), đa dạng hóa đa coin thực sự cắt mạnh đuôi Fréchet `xi` từ **`+0.3337`** (`S3A v1`, `P99 252d DD = 7.78%`) xuống **`-0.1056`** (`F9_TOP6_MAKER_ENTRY`), **`-0.0437`** (`F9_ALL20_PERSIST_14D`), **`+0.0815`** (`F9_TOP10_TIER1_CAP20`, `P99 DD = 1.62%`), và **`+0.1375`** (`F9_TOP5_HYST_12_4`, `P99 DD = 4.00%`). Tuy nhiên, lý do `S3A v1` có `xi > 0` (`+0.0718` file gốc / `+0.1075` có exit-shock trên MF24) là vì **độ biến động nền của nó quá nhỏ (`0.34%/năm` ở Cl.B!)**: chỉ vài ngày lệch basis `-0.17%..-0.68%` đã trở thành outlier `5–10 sigma` trong mắt GARCH-EVT, dù **mức lỗ tiền thật tối đa chỉ là `0.35%` trong `3.4` năm** (chưa tới `0.09%` tổng Pod v2 dưới trần `NCO_CexCap25`!). Đánh đổi `-1.65%..-3.80%/năm` CAGR chỉ để làm phẳng kurtosis chuẩn hóa của một sleeve có MaxDD `0.35%` là tối ưu hóa ngược.
3. **Cảnh Báo Thanh Lý Isolated Margin Từ Short-Squeeze Altcoin:** Dữ liệu Mark Price thực ghi nhận các cú nhảy 1 ngày cực đoan: **`DOGEUSDT +405.5%` (`2021-01-28`)**, **`DOGEUSDT +147.7%` (`2021-04-16`)**, **`XLMUSDT +105.7%` (`2023-07-13`)**, **`TRXUSDT +103.1%` (`2024-12-03`)**, và **`FILUSDT +110.1%` (`2025-11-07`)**. Do đó, ngay cả ở đệm bảo thủ `2.5x` (`+145%` ngưỡng thanh lý), `F9_TOP10_TIER1_CAP20` vẫn dính `1` sự kiện thanh lý Isolated (`F9_ALL20_PERSIST_14D`: `7` sự kiện!). Ngược lại, **Cross-Margin ghi nhận `0` sự kiện thanh lý trên cả `8/8` biến thể** (tỷ lệ rút quỹ ký quỹ tối đa `18.52%–41.50%`), còn `BTC+ETH` (`S3A v1`) chỉ nhảy giá Mark tối đa **`30.90%`** (`0` cảnh báo, `0/0` thanh lý).
4. **Phanh Regime Cứng Bị Whipsaw Trong Bear 2022:** `F9_TOP8_REGIME_BRAKE` (`-4.12%` Bear 2022) thua nặng `F9_TOP8_INVVOL_HYST` (`-2.17%`) vì cắt `0%` ngay đáy căng thẳng basis/funding rồi mua lại chỉ vài ngày sau (`TO = 19.95x/năm`). Ngược lại, bộ lọc ngưỡng rộng tự nhiên `F9_TOP5_HYST_12_4` (`>+12%` vào / `<+4%` thoát) tự động đứng ngoài `100%` tiền mặt qua FTX 2022 (`+0.00% / 0.00% MDD`) và đạt `APPROVE_FOR_INCUBATION` — nhưng vì đứng ngoài `61.1%` thời gian ở Cl.B (`avg exposure = 12.9%`), nó chỉ tạo `+1.37%` CAGR (`SR = 3.89`) so với `+3.02%` (`SR = 8.83`) của `S3A v1`.

---

## 5. Quyết Định Vận Hành & Điều Kiện Thăng Hạng (`Promotion Gate`)

- **Quyết định hiện hành (`KEEP_S3A_V1`):** Giữ nguyên **`S3A v1` (`CARRY_BTC_ETH_CONS_2XBUF`)** làm Sleeve #3A chính thức (`sleeve3a_funding_carry.json` giữ nguyên 100%, không làm xáo trộn regression test của Pod v2). Kiểm soát rủi ro sàn tập trung và đuôi trái của `S3A v1` ở **tầng phân bổ danh mục** thông qua trần cứng **`NCO_CexCap25` (`S2 + S3A <= 25%` tổng vốn Own-Book)**.
- **Tiêu chuẩn Promotion cho ứng viên vệ tinh `F9_TOP5_HYST_12_4` (Chưa kích hoạt live):** Chỉ được phép xem xét nâng cấp làm vệ tinh bổ trợ (`<= 30%` ngân sách Sleeve #3A, `r vs S3A v1 = +0.488`) khi đồng thời thỏa 4 điều kiện cứng:
  1. **Cross-Margin / Portfolio Margin bắt buộc:** Tuyệt đối cấm chạy altcoin short-perp trên Isolated Margin (đã chứng minh rủi ro `+100%..+405%` 1-day mark jump).
  2. **Thực thi Maker-Only xác thực live (`<= 5.0 bps/chân`):** Dữ liệu live từ `crypto_maker_shadow_probe.py` phải xác nhận tỷ lệ khớp passive `>= 75%` và chi phí thực hiệu dụng `<= 5.0 bps/chân` (đưa Breakeven `F9_TOP5_HYST_12_4` vượt `3.5x`).
  3. **Chế độ Bull Funding thực tế:** Chỉ kích hoạt phân bổ vệ tinh khi trung vị funding 7 ngày của Top-12 Tier-1 vượt `+12%/năm` trong thực chiến (tự động về `0%` ở thị trường trầm lắng để không lãng phí vốn).
  4. **Giữ nguyên trần tổng CEX `<= 25%`:** Bất kỳ vốn nào cấp cho `F9_TOP5_HYST_12_4` phải trích từ bên trong ngân sách CEX hiện hữu, không mở rộng tổng phơi nhiễm sàn tập trung.
