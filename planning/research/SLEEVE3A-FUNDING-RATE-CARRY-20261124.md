---
doc_type: research_receipt
date: 2026-11-24
lane: quant-rnd
milestone: M3.3
status: COMPLETE_VERIFIED_CAUSAL
order_send_count: 0
---

# Sleeve #3A — Crypto Delta-Neutral Funding-Rate Carry (Spot Long + 1x Perp Short)

- **Ngày thực hiện:** `2026-11-24` (dữ liệu 8 giờ liên tục từ `2020-01-01` đến `2026-11-22`, tổng `2.518` ngày lịch).
- **Mã nguồn tái lập:** [funding_rate_carry.py](../../tooling/ai-engines/quant_factory/funding_rate_carry.py)
- **Kho dữ liệu Parquet & đối soát chéo sàn:** `.runtime/crypto-spot-cache/funding/` (`20` cặp Binance USD-M Perpetuals `/fapi/v1/fundingRate` + `/fapi/v1/klines` + đối soát công khai Bybit v5 `/v5/market/funding/history`; `0` API key, `OrderSend = 0`).
- **Chuỗi lợi suất ngày xuất cho Bộ Phân Bổ Pod (`@risk-auditor`):** `.runtime/quant-pod-returns/sleeve3a_funding_carry.json` (schema `naqex-sleeve-daily-returns-v1`).
- **Giả định hạch toán thực tế & bảo thủ:**
  - **Bộ đệm vốn `2x` (`2.0x equity buffer`):** `50%` vốn mua Spot Long + `50%` vốn đặt làm ký quỹ USDT cho `50%` Perp Short (`1x` đòn bẩy Futures -> chống cháy tài khoản ngay cả khi coin tăng đột ngột `+90%`). Cũng kiểm tra so sánh biến thể `1.5x` buffer (`66.7%` danh nghĩa, `2x` đòn bẩy Futures).
  - **Chi phí vào/ra cặp Spot+Perp:** `1x = 23 bps` một chiều trên giá trị danh nghĩa (`15 bps` Spot + `8 bps` Perp = `46 bps` khứ hồi); stress `2x = 46 bps` một chiều (`92 bps` khứ hồi).
  - **Lợi nhuận basis Spot–Perp thực (`r_spot - r_perp`):** Được hạch toán mark-to-market hàng ngày (không giả định basis bằng 0!). Tiền mặt USDT nhàn rỗi tính **0% lãi suất** (không cộng thêm lãi T-bill để làm đẹp alpha).
  - **Nhân quả `t -> t+1`:** Tín hiệu lọc funding trung bình trượt `7` ngày / `14` ngày chỉ dùng dữ liệu `<= t`, áp dụng cho ngày `t+1`.
  - **Phân tách mù:** Cluster A (`2020-01-01` → `2023-12-31`, `1.461` ngày) để chọn cấu hình chịu phí tốt nhất (`2x-cost Calmar`); Cluster B mù (`2024-01-01` → `2026-11-22`, `1.057` ngày) để kiểm chứng ngoài mẫu.

---

## 1. Bảng Hiệu Suất 5 Biến Thể Delta-Neutral Carry (`20` Perpetuals)

*(Tất cả số liệu đã trừ chi phí `1x = 23 bps` một chiều và hạch toán basis Spot–Perp; `2x` là stress phí `46 bps` một chiều.)*

| Biến Thể Carry | Đệm Vốn | Cl.A `CAGR` (`1x / 2x`) | Cl.A `Sharpe` | Cl.A `MaxDD` | Cl.A `Calmar` (`1x / 2x`) | **Cl.B Mù `CAGR` (`1x / 2x`)** | **Cl.B `Sharpe`** | **Cl.B `MaxDD`** | Turnover B (`/năm`) | `BH q_B` / `DSR_B` | Đỉnh Nhảy Mark / Cross-DD | Trạng Thái |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`CARRY_BTC_ETH_CONS_2XBUF`** | `2.0x` | **`+7.69% / +6.73%`** | **`7.825`** | **`0.95%`** | `8.11 /` **`3.40`** | **`+2.99% / +2.46%`** | **`9.061`** | **`0.29%`** | **`2.24x`** | `0.0000 / 1.000` | `+30.9% / 27.9%` (`0` liq) | **CHỌN CHÍNH (Cl.A #1 bền phí)** |
| `CARRY_STATIC_CORE5_2XBUF` | `2.0x` | `+5.31% / +5.23%` | `2.432` | `5.69%` | `0.93 / 0.92` | `+2.38% / +2.38%` | `7.384` | `0.35%` | `0.00x` | `0.0000 / 1.000` | `+99.3% / 27.9%` (`1` iso-liq) | Baseline (chết FTX `-4.7%`) |
| `CARRY_NEG_EXIT_ALL20_2XBUF` | `2.0x` | `+7.57% / +4.94%` | `6.408` | `1.79%` | `4.24 / 0.71` | `+1.72% / -0.07%` | `4.015` | `0.91%` | `7.70x` | `0.0000 / 1.000` | `+405.5% / 32.7%` (`7` iso-liq) | Gãy ở stress phí `2x` Cl.B |
| `CARRY_TOP5_HYST_2XBUF` | `2.0x` | `+8.91% / +6.03%` | `6.515` | `0.91%` | `9.82 / 2.10` | `+0.94% / -1.35%` | `2.069` | `1.01%` | `10.01x` | `0.0124 / 0.991` | `+88.2% / 29.7%` (`0` liq) | Turnover cao ăn mòn Cl.B |
| `CARRY_TOP5_HYST_1P5XBUF` | `1.5x` | `+12.05% / +8.11%` | `6.515` | `1.21%` | `9.97 / 2.13` | `+1.26% / -1.80%` | `2.069` | `1.34%` | `13.34x` | `0.0124 / 0.991` | `+88.2% / 59.4%` (`8` iso-liq) | Quá rủi ro đòn bẩy + phí |

---

## 2. Stress Test Khủng Hoảng (`2021`, `2022 FTX`, `2024 Yen Shock`) & Thanh Lý Ký Quỹ

| Giai Đoạn Cú Sốc | `CARRY_STATIC_CORE5` *(không cắt funding âm)* | **`CARRY_BTC_ETH_CONS_2XBUF`** *(chọn chính)* | `CARRY_TOP5_HYST_2XBUF` | Nhận Xét Cơ Chế |
|---|---:|---:|---:|---|
| **Sập Tháng 5/2021** (`2021-05-01..06-30`) | `+1.41%` (`MaxDD 0.14%`) | **`+1.12%` (`MaxDD 0.15%`)** | `+0.72%` (`MaxDD 0.55%`) | Funding giảm nhanh nhưng vẫn dương ròng sau khi thoát kịp |
| **Sập FTX Tháng 11/2022** (`2022-11-01..12-31`) | **`-4.70%` (`MaxDD 5.23%`, ngày tệ `-3.38%`)** | **`-0.07%` (`MaxDD 0.31%`, ngày tệ `-0.13%`)** | `-0.03%` (`MaxDD 0.21%`) | **Quy tắc cắt funding âm 7 ngày đã chặn gần như 100% cú sập FTX (`-4.70% -> -0.07%`)!** |
| **Cả Năm Gấu 2022** (`2022-01-01..12-31`) | `-5.03%` (`MaxDD 5.30%`) | **`+0.03%` (`MaxDD 0.51%`)** | `+0.24%` (`MaxDD 0.69%`) | Giữ vốn gần như nguyên vẹn suốt mùa đông crypto 2022 |
| **Sốc Yên Nhật Tháng 8/2024** (`2024-08-01..31`) | `+0.07%` (`MaxDD 0.01%`) | **`-0.13%` (`MaxDD 0.20%`)** | `-0.12%` (`MaxDD 0.13%`) | Hầu như không tương quan cú sốc FX/cổ phiếu |

### Phát hiện trọng yếu về thanh lý ký quỹ & đối soát chéo sàn Bybit
1. **Rủi ro short-squeeze trên altcoin ngay cả ở đòn bẩy `1x`:** Dữ liệu thực lịch sử cho thấy `DOGEUSDT` (`2021-01-28`: `+405.5%` Mark / `+412.4%` Perp High trong 1 ngày), `XRPUSDT` (`2023-07-13`: `+105%`), `TRXUSDT` (`2024-12-03`: `+103%`), `FILUSDT` (`2025-11-07`: `+110%`) sẽ **thanh lý hoàn toàn vị thế Perp Short `1x` nếu chạy Isolated Margin**. Ngược lại, `CARRY_BTC_ETH_CONS_2XBUF` chỉ giao dịch `BTC + ETH` có đỉnh nhảy Mark Price lớn nhất 7 năm chỉ `+30.90%` (`0` cảnh báo ký quỹ, `0` sự kiện thanh lý; râu giá last-trade `2020-03-13` trên ETH là `+202.7%` nhưng Binance thanh lý theo Mark Price gắn Spot Index chỉ `+29.5%`).
2. **Đối soát công khai chéo sàn Binance vs Bybit (`533` ngày gần nhất, giữa 2025 → 11/2026):**
   - `BTCUSDT`: Binance `+4.20%/năm` vs Bybit `+3.87%/năm` (tương quan ngày `r = 0.664`).
   - `ETHUSDT`: Binance `+3.29%/năm` vs Bybit `+3.29%/năm` (`r = 0.647`).
   - `SOLUSDT`: Binance `+0.20%/năm` vs Bybit `+0.61%/năm` (`r = 0.937`).
   - `XRPUSDT`: Binance `+2.10%/năm` vs Bybit `+2.37%/năm`; `DOGEUSDT`: Binance `+3.95%/năm` vs Bybit `+3.24%/năm`.
   - **Kết luận kinh tế trung thực:** Mức carry đã **nén mạnh trong giai đoạn `2024–2026`** (từ `~15%/năm` danh nghĩa xuống `~3–6%/năm` danh nghĩa, tức `~2.5–3.0%/năm` trên tổng equity có đệm `2x`) do dòng vốn arbitrage cơ sở quy mô tỷ USD (như Ethena USDe và các quỹ market-neutral) cộng với pha gấu `2025–2026`. Vì vậy, các chiến lược xoay vòng altcoin có turnover `8–13x/năm` bị phí ăn mòn nặng trên Cluster B (`-0.07%` đến `-1.80%` ở `2x` phí), trong khi **`CARRY_BTC_ETH_CONS_2XBUF`** có turnover chỉ `2.24x/năm` vẫn giữ vững **`+2.99%/năm` (`+2.46%` ở `2x` phí) với `MaxDD 0.29%`**.
3. **Cảnh báo rủi ro đối tác sàn (CEX Tail Risk — Bài học FTX):** Dù độ biến động hàng ngày rất thấp (`0.33%–0.95%/năm`, tạo ra `Sharpe 7–9` trên giấy), **Sharpe danh nghĩa này KHÔNG đo lường rủi ro đuôi mất khả năng thanh toán của sàn tập trung (CEX insolvency)**. Khi triển khai thực tế:
   - Bắt buộc giới hạn tỷ trọng Sleeve #3A tối đa **`<= 15%–20%`** tổng vốn Quant Pod;
   - Ưu tiên tài khoản Portfolio Margin / Unified Margin (hoặc chia tối thiểu 2 sàn Tier-1 như Binance + OKX/Bybit) và chỉ kích hoạt khi trailing 7d funding vượt rõ ngưỡng chi phí (`> +3%` năm cho BTC/ETH, hoặc `> +8%` năm nếu mở rộng sang coin khác);
   - Nếu lãi suất T-bill / tiền gửi an toàn (ví dụ `4–5%/năm` USD hoặc lãi suất tiền gửi VND quy đổi) cao hơn mức carry ròng `~3%/năm` của chế độ nén hiện tại, **không ép chạy Sleeve #3A** — coi nó là nhánh cơ hội *regime-dependent* bật mạnh khi thị trường crypto nóng trở lại (carry > `10–15%/năm`).
