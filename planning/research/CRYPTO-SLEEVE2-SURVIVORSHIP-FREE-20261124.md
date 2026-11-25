---
doc_type: research_receipt
date: 2026-11-24
lane: quant-rnd
milestone: M3.1_M3.2
status: COMPLETE_VERIFIED_CAUSAL
order_send_count: 0
---

# Sleeve #2 — Crypto Spot Không Thiên Lệch Sống Sót (50 Coin, Rổ Thanh Khoản Trượt 30 Ngày Nhân Quả)

- **Ngày thực hiện:** `2026-11-24` (dữ liệu đóng nến UTC hoàn chỉnh từ `2019-01-01` đến `2026-11-22`, tổng `2.883` ngày).
- **Mã nguồn tái lập:** [crypto_causal_universe.py](../../tooling/ai-engines/quant_factory/crypto_causal_universe.py)
- **Kho dữ liệu Parquet & SHA-256 manifest (offline cache):** `.runtime/crypto-spot-cache/` (`100` tệp Parquet cho `50` đồng × `2` khung `1d` & `4h`, nguồn công khai Binance Spot `/api/v3/klines`, `0` API key, `OrderSend = 0`).
- **Chuỗi lợi suất ngày xuất cho Bộ Phân Bổ Pod (`@risk-auditor`):** `.runtime/quant-pod-returns/sleeve2_crypto_spot.json` (schema `naqex-sleeve-daily-returns-v1`).
- **Quy tắc chống rò rỉ nghiêm ngặt:**
  - Không forward-fill trước ngày niêm yết thực tế; bao gồm cả các coin lịch sử từng nằm top thanh khoản nhưng suy tàn hoặc bị hủy niêm yết (`EOSUSDT`, `MKRUSDT`, `WAVESUSDT` mang trạng thái `BREAK` trên Binance và **cả 3 đều từng lọt rổ Top-15 thực tế**; cùng các đồng suy giảm mạnh như `NEO`, `FIL`, `ICP`, `ALGO`, `VET`, `AXS`, `SAND`, `MANA`, `KSM`, `IOTA`, `XTZ`, `COMP`, `SNX`, `SUSHI`, `THETA`).
  - Bộ chọn rổ Top-N (`Top-15` cho họ xu hướng/breakout, `Top-10` cho họ đảo chiều hoảng loạn) tính trung bình `quote_volume` (USD) trượt `30` ngày (`180` nến `4H`) **chỉ dùng dữ liệu `<= t`**, chuyển sang vị thế tại nến `t+1` (`t -> t+1`).
  - Chỉ Spot Long/Cash (`0 <= w_j`, `sum(w) <= 1.0`, không đòn bẩy, không short); chi phí thực tế `1x = 15 bps` một chiều (`10 bps` phí + `5 bps` trượt giá) và stress `2x = 30 bps` một chiều, cộng phạt thanh khoản hủy niêm yết `100 bps` nếu coin mất nến kế tiếp khi đang nắm giữ.
  - **Phân tách mù nghiêm ngặt:** **Cluster A (`2019-01-01` → `2023-12-31`, `1.826` ngày)** để phát triển & chọn chiến lược; **Cluster B mù (`2024-01-01` → `2026-11-22`, `1.057` ngày)** chỉ dùng để kiểm chứng ngoài mẫu, áp `BH-FDR` trên toàn bộ `m_total = 15` chiến lược đăng ký trước và `Deflated Sharpe Ratio (DSR)` với `n_trials = 15`.

---

## 1. Độ Phủ Rổ 50 Coin & Xác Nhận Không Thiên Lệch Sống Sót

- **Tải thành công:** `50/50` cặp `*USDT` cho cả khung `1d` và `4h` (`0` coin bị bỏ qua).
- **Độ động của rổ Top-15 trượt 30 ngày:** **`48/50` đồng** từng xoay vòng đi vào rổ giao dịch Top-15 thanh khoản trong giai đoạn `2019–2026`.
- **Coin đã hủy niêm yết (`BREAK`) vẫn hiện diện đầy đủ lịch sử & từng lọt Top-15:** `EOSUSDT`, `MKRUSDT`, `WAVESUSDT`.
- **Tác động lên Benchmark thụ động (`BM_CAUSAL_EQW15`):** Rổ mua-giữ đều Top-15 trượt đạt `CAGR +43.97%` trên Cluster A nhưng **rơi xuống `-15.69%/năm` (`-38.99%` tổng lỗ, `MaxDD 69.23%`, `Sharpe 0.070`) trên Cluster B `2024–2026`** — phản ánh đúng thực tế khắc nghiệt của thị trường altcoin giai đoạn `2024–2026` khi loại bỏ thiên lệch sống sót.

---

## 2. Bảng Kết Quả Đầy Đủ 5 Họ Chiến Lược (`m_total = 15`) + Benchmark

*(Mọi số liệu đã trừ chi phí `1x = 15 bps` một chiều; cột `2x` là stress `30 bps` một chiều. Giữ nguyên cả kết quả âm/bị loại.)*

| Mã Chiến Lược | Họ / Khung | Cl.A `CAGR` (`1x / 2x`) | Cl.A `Sharpe` | Cl.A `MaxDD` | Cl.A `Calmar` | **Cl.B Mù `CAGR` (`1x / 2x`)** | **Cl.B `Sharpe` (`1x / 2x`)** | **Cl.B `MaxDD`** | **Cl.B `Calmar`** | Turnover B (`/năm`) | `BH q_A` / `q_B` / `q_Full` | `DSR_A` / `DSR_B` / `DSR_Full` | Trạng Thái |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `BM_BH_BTC` | Benchmark (`1d`) | `+61.85% / +61.80%` | `1.056` | `76.63%` | `0.807` | `+13.66% / +13.66%` | `0.506 / 0.506` | `52.97%` | `0.258` | `0.0x` | — | — | Benchmark |
| `BM_CAUSAL_EQW15` | Benchmark (`1d`) | `+43.97% / +42.45%` | `0.868` | `85.91%` | `0.512` | `-15.69% / -16.57%` | `0.070 / 0.054` | `69.23%` | `-0.227` | `7.0x` | — | — | Benchmark |
| **`F4_4H_EMA_24_120_BTC`** | `4H_TREND` (`4h`) | **`+16.30% / +15.67%`** | **`1.823`** | **`8.53%`** | **`1.911`** | **`+5.69% / +4.94%`** | **`0.776 / 0.680`** | `9.72%` | `0.586` | `4.76x` | `0.0005 / 0.2934 / 0.0006` | `0.989 / 0.324 / 0.991` | **CHỌN CHÍNH (Cl.A #1)** |
| **`F3_DONCHIAN_4H_120_60`** | `DONCHIAN` (`4h`) | `+12.47% / +12.05%` | `1.488` | `9.71%` | `1.285` | **`+5.58% / +5.07%`** | **`0.857 / 0.784`** | **`6.67%`** | **`0.837`** | **`3.23x`** | `0.0015 / 0.2934 / 0.0011` | `0.939 / 0.375 / 0.966` | **ĐẠT (Bền phí nhất)** |
| `F4_4H_EMA_48_240` | `4H_TREND` (`4h`) | `+15.24% / +14.78%` | `1.482` | `11.48%` | `1.327` | `+6.18% / +5.58%` | `0.751 / 0.684` | `8.99%` | `0.687` | `3.76x` | `0.0014 / 0.2934 / 0.0011` | `0.932 / 0.310 / 0.953` | ĐẠT |
| `F1_TSMOM_D1_L60_VT15` | `TSMOM` (`1d`) | `+9.62% / +8.74%` | `1.290` | `9.84%` | `0.978` | `+5.16% / +4.04%` | `0.782 / 0.623` | **`6.04%`** | **`0.854`** | `7.14x` | `0.0047 / 0.2934 / 0.0032` | `0.870 / 0.328 / 0.915` | ĐẠT (DD thấp nhất) |
| `F1_TSMOM_4H_L360_VT15` | `TSMOM` (`4h`) | `+11.92% / +10.43%` | `1.446` | **`7.81%`** | `1.526` | `+5.44% / +3.34%` | `0.721 / 0.461` | `7.65%` | `0.712` | `13.41x` | `0.0015 / 0.2934 / 0.0018` | `0.928 / 0.291 / 0.942` | ĐẠT |
| `F1_TSMOM_4H_L180_VT15` | `TSMOM` (`4h`) | `+13.80% / +11.65%` | `1.582` | `8.67%` | `1.591` | `+4.01% / +1.10%` | `0.565 / 0.183` | `10.10%` | `0.397` | `18.95x` | `0.0013 / 0.3382 / 0.0017` | `0.962 / 0.205 / 0.957` | Nhạy phí ở 2x |
| `F1_TSMOM_D1_L30_VT20` | `TSMOM` (`1d`) | `+14.62% / +13.00%` | `1.425` | `11.19%` | `1.307` | `+3.71% / +1.65%` | `0.466 / 0.233` | `12.33%` | `0.301` | `13.36x` | `0.0023 / 0.3656 / 0.0036` | `0.924 / 0.161 / 0.911` | Nhạy phí ở 2x |
| `F2_XSEC_TOP3_BTC50` | `XSEC` (`1d`) | `+17.08% / +14.43%` | `1.683` | `11.85%` | `1.441` | `+7.10% / +3.11%` | `0.749 / 0.361` | `11.23%` | `0.632` | `25.29x` | `0.0013 / 0.2934 / 0.0011` | `0.981 / 0.307 / 0.980` | Turnover cao (`25x`) |
| `F2_XSEC_TOP3_BTC100` | `XSEC` (`1d`) | `+12.42% / +10.47%` | `1.238` | `14.32%` | `0.867` | `+5.26% / +2.20%` | `0.535 / 0.257` | `11.72%` | `0.449` | `19.67x` | `0.0063 / 0.3382 / 0.0090` | `0.843 / 0.192 / 0.831` | Turnover cao (`20x`) |
| `F2_XSEC_TOP5_BTC100` | `XSEC` (`1d`) | `+12.27% / +10.35%` | `1.282` | `14.74%` | `0.833` | `+2.58% / -0.30%` | `0.308 / 0.019` | `12.74%` | `0.203` | `19.01x` | `0.0057 / 0.3712 / 0.0112` | `0.866 / 0.106 / 0.787` | Gãy ở stress 2x |
| `F3_DONCHIAN_D1_20_10` | `DONCHIAN` (`1d`) | `+8.49% / +7.98%` | `1.189` | `10.13%` | `0.838` | `+2.13% / +1.51%` | `0.394 / 0.288` | `7.93%` | `0.269` | `4.10x` | `0.0066 / 0.3689 / 0.0096` | `0.812 / 0.135 / 0.800` | Yếu trên Cl.B |
| `F3_DONCHIAN_D1_40_20` | `DONCHIAN` (`1d`) | `+6.13% / +5.73%` | `0.861` | `13.72%` | `0.447` | `+1.60% / +1.12%` | `0.285 / 0.209` | `7.21%` | `0.221` | `3.15x` | `0.0348 / 0.3712 / 0.0411` | `0.561 / 0.099 / 0.542` | Yếu |
| `F5_PANIC_REV_D1_TREND` | `PANIC_REV` (`1d`) | `+0.28% / -0.37%` | `0.079` | `9.07%` | `0.031` | **`-1.92% / -3.05%`** | `-0.306 / -0.508` | `11.46%` | `-0.167` | `7.77x` | `0.4497 / 0.7200 / 0.5810` | `0.058 / 0.011 / 0.025` | **LOẠI (Âm & skew `-7.96`)** |
| `F5_PANIC_REV_D1_UNCOND` | `PANIC_REV` (`1d`) | `+0.51% / +0.01%` | `0.119` | `6.29%` | `0.082` | **`-0.76% / -1.51%`** | `-0.071 / -0.177` | `15.15%` | `-0.050` | `5.07x` | `0.3928 / 0.5903 / 0.4782` | `0.067 / 0.029 / 0.049` | **LOẠI (Bắt dao rơi)** |
| `F5_PANIC_REV_4H_FLUSH` | `PANIC_REV` (`4h`) | `+0.09% / -0.65%` | `0.043` | `7.45%` | `0.012` | `+3.17% / +2.01%` | `1.226 / 0.803` | `2.46%` | `1.289` | `7.54x` | `0.4604 / 0.2048 / 0.1604` | `0.049 / 0.637 / 0.257` | **LOẠI trên Cl.A (`kurt=303`)** |
| **`CRYPTO_SPOT_3FAM_EQW`** | Ensemble 3 họ (chọn từ Cl.A) | `+15.77%` | `1.811` | `8.23%` | `1.917` | `+5.65%` | `0.757` | `9.45%` | `0.598` | — | `p_A=0.00004` | `DSR_B=0.312` (`PSR=90.4%`) | Hợp lệ (đa dạng hóa) |

---

## 3. So Sánh Trung Thực Với Rổ 5 Coin Cũ (`CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.md`)

Đo chính xác **mức độ thổi phồng do thiên lệch sống sót (Survivorship Bias Haircut)** trên cùng cửa sổ ngày `2019–2023` (Cluster A) và `2024–2026` (Cluster B), cùng mức phí `15 bps` một chiều:

| So Sánh Táo-với-Táo (`15 bps` một chiều) | Cl.A `CAGR` | Cl.A `Sharpe` | Cl.A `MaxDD` | Cl.B `CAGR` | Cl.B `Sharpe` | Cl.B `MaxDD` | Toàn Giai Đoạn `Sharpe` |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Cũ 5 coin (`OLD5_C1_TSMOM_VOL20`)** | `+16.23%` | `1.823` | `11.04%` | `+8.15%` | `0.944` | `8.27%` | `1.495` |
| **Mới 50 coin Top-15 nhân quả (`F1_TSMOM_D1_L60_VT15`)** | `+9.62%` | `1.290` | `9.84%` | `+5.16%` | `0.782` | `6.04%` | `1.112` |
| *Chênh lệch thiên lệch sống sót (C1)* | **`-6.61 pp`** | **`-0.533`** | `-1.20 pp` | **`-2.99 pp`** | **`-0.162`** | `-2.23 pp` | **`-0.383`** |
| **Cũ 5 coin (`OLD5_C2_XSEC_TOP2`)** | `+23.63%` | `1.963` | `12.07%` | `+7.80%` | `0.682` | `13.87%` | `1.468` |
| **Mới 50 coin Top-15 nhân quả (`F2_XSEC_TOP3_BTC100`)** | `+12.42%` | `1.238` | `14.32%` | `+5.26%` | `0.535` | `11.72%` | `0.967` |
| *Chênh lệch thiên lệch sống sót (C2)* | **`-11.21 pp`** | **`-0.725`** | `+2.25 pp` | **`-2.54 pp`** | **`-0.147`** | `-2.15 pp` | **`-0.501`** |
| **Ứng viên mới chọn trên Cl.A (`F4_4H_EMA_24_120_BTC`)** | **`+16.30%`** | **`1.823`** | **`8.53%`** | **`+5.69%`** | **`0.776`** | **`9.72%`** | **`1.466`** |

### Kết luận định lượng trung thực (không tô hồng)
1. **Thiên lệch sống sót của bản 5-coin cũ là có thật và rất lớn:** Riêng việc chọn sẵn 5 coin thắng lớn (`BTC, ETH, BNB, ADA, SOL`) đã thổi phồng `CAGR` thêm **`+6.6 đến +11.2 điểm phần trăm/năm`** và `Sharpe` thêm **`+0.53 đến +0.73`** trên Cluster A!
2. **Edge xu hướng vẫn sống sót sau khi khử 100% survivorship bias:** Dù rổ altcoin thụ động `BM_CAUSAL_EQW15` giảm `-38.99%` với `MaxDD 69.23%` trong giai đoạn gấu/đi ngang `2024–2026`, các họ xu hướng chậm-vừa (`F4_4H_EMA_24_120_BTC`, `F3_DONCHIAN_4H_120_60`, `F1_TSMOM_D1_L60_VT15`) vẫn đạt **dương ròng `+5.16%` đến `+6.18%/năm`** ở `1x` phí, giữ **`MaxDD` chỉ `6.04%–9.72%`** (nhỏ hơn `7–11x` so với Buy & Hold), và vẫn dương vững ở stress phí gấp đôi `2x = 30 bps` (`+4.04%` đến `+5.58%/năm`).
3. **Cảnh báo thống kê mù trên Cluster B (`1.057` ngày = `2.9` năm):** Do độ dài Cluster B chỉ `2.9` năm (ngưỡng cắt `DSR` cho `m_total = 15` thử nghiệm là `SR_0 = 1.041`), không có chiến lược đơn lẻ nào vượt qua ngưỡng `BH-FDR q_B < 0.05` hoặc `DSR_B > 0.50` nếu xét riêng `2.9` năm gấu này (`PSR_B(SR>0) = 90.9%–93.2%`). Trên toàn mẫu `7.9` năm (`2.883` ngày), các ứng viên xu hướng đều đạt `BH-FDR q_full <= 0.003` và `DSR_full = 0.915–0.991`.
4. **Họ bị loại hoàn toàn:** `LIQUIDITY_PANIC_REVERSION` (bắt đáy hoảng loạn) thất bại nghiêm trọng trên Cluster A với đuôi âm cực đoan (`skew = -7.96` đến `-12.06`, `kurtosis = 208–307`) và thua lỗ trên Cluster B (D1). Khuyến nghị **loại vĩnh viễn** khỏi Sleeve #2.
5. **Đề xuất thực thi ưu tiên:** Đưa **`F4_4H_EMA_24_120_BTC`** (được chọn mù từ Cluster A, `turnover 4.76x/năm`, `Sharpe full 1.466`, `MaxDD 9.72%`) làm chuỗi chính của Sleeve #2 trong `.runtime/quant-pod-returns/sleeve2_crypto_spot.json`, kèm dự phòng **`F3_DONCHIAN_4H_120_60`** (`turnover 3.23x/năm`, `MaxDD Cl.B 6.67%`) và `F1_TSMOM_D1_L60_VT15` (thuần D1 dễ vận hành tay/cron).
