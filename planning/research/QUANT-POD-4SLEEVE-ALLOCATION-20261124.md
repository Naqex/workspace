# Naqex Quant Pod — Phân Bổ Danh Mục 4-Sleeve & Kiến Trúc Theo Quy Mô Vốn (10k / 50k / 200k+ USD)

- **Generated UTC:** `2026-11-23T16:47:02.667613+00:00`
- **Sealed Overlap Window:** `2020-01-01..2024-12-31 (1305 Mon-Fri business days)` (Holdout `2025+` của Sleeve #1 giữ `100% SEALED`, `holdout_rows_analysed = 0`, `OrderSend = 0`)
- **Causal Split:** Train `2020-01-01..2022-12-30 (783 days)` -> Blind OOS `2023-01-02..2024-12-31 (522 days)` (lợi suất cuối tuần Thứ 7/Chủ nhật của Crypto được cộng gộp chính xác vào ngày Thứ 2)
- **Holdout Lock SHA-256:** `f0a6b43cb205535b...` | Runtime `1.273s`

## 1. Hiệu Suất Độc Lập Của 4 Sleeve Trên Cửa Sổ Chung (`2020–2024` & Blind OOS `2023–2024`)

| Sleeve | Strategy Source | Full CAGR% | Full Vol% | Full Sharpe | Full MaxDD% | Full Calmar | OOS 23-24 CAGR% | OOS Sharpe | OOS MaxDD% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1_PROP_FX_IDX | PORT_7E_INVDD_SYMCAP100_DEV | +6.69% | 5.16% | 1.28 | 5.45% | 1.23 | +3.97% | 0.77 | 5.45% |
| S2_CRYPTO_SPOT | F4_4H_EMA_24_120_BTC | +15.00% | 8.72% | 1.65 | 9.72% | 1.54 | +13.72% | 1.47 | 9.72% |
| S3A_FUND_CARRY | CARRY_BTC_ETH_CONS_2XBUF | +7.12% | 1.03% | 6.68 | 0.95% | 7.52 | +4.64% | 10.41 | 0.35% |
| S3B_MACRO_ETF | M5_VOL_PARITY_TREND_GUARD | +4.85% | 6.33% | 0.78 | 7.64% | 0.63 | +5.07% | 0.80 | 4.53% |

## 2. Ma Trận Tương Quan 4×4 (Toàn Bộ Ngày & Đuôi Xấu Nhất 5%)

### 2A. Tương Quan Toàn Bộ Ngày Giao Dịch (`2020–2024`)

| Sleeve | S1_PROP_FX_IDX | S2_CRYPTO_SPOT | S3A_FUND_CARRY | S3B_MACRO_ETF |
|---|---:|---:|---:|---:|
| S1_PROP_FX_IDX | +1.000 | -0.002 | -0.020 | -0.035 |
| S2_CRYPTO_SPOT | -0.002 | +1.000 | +0.074 | +0.149 |
| S3A_FUND_CARRY | -0.020 | +0.074 | +1.000 | -0.003 |
| S3B_MACRO_ETF | -0.035 | +0.149 | -0.003 | +1.000 |

### 2B. Tương Quan Đuôi Xấu Nhất 5% (Stress Tail Correlation)

| Sleeve | S1_PROP_FX_IDX | S2_CRYPTO_SPOT | S3A_FUND_CARRY | S3B_MACRO_ETF |
|---|---:|---:|---:|---:|
| S1_PROP_FX_IDX | +1.000 | -0.509 | +0.282 | -0.064 |
| S2_CRYPTO_SPOT | -0.509 | +1.000 | -0.508 | -0.510 |
| S3A_FUND_CARRY | +0.282 | -0.508 | +1.000 | +0.192 |
| S3B_MACRO_ETF | -0.064 | -0.510 | +0.192 | +1.000 |

## 3. So Sánh 5 Thuật Toán Phân Bổ Vốn (Equal-Weight, Inv-Vol, Inv-DD, ERC, HRP)

Trọng số được khớp thuần túy trên Train (`2020–2022`) và đánh giá mù trên Blind OOS (`2023–2024`):

| Allocator | OOS CAGR% | OOS Vol% | OOS Sharpe | OOS Sortino | OOS MaxDD% | OOS Calmar | Full CAGR% (Causal W) | Full MaxDD% | Full Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Equal_Weight | +6.92% | 3.26% | 2.07 | 2.36 | 3.06% | 2.26 | +8.49% | 3.06% | 2.78 |
| Inverse_Vol | +5.49% | 1.52% | 3.51 | 4.05 | 1.35% | 4.06 | +7.55% | 1.35% | 5.59 |
| Inverse_DD | +5.41% | 1.39% | 3.81 | 4.50 | 1.25% | 4.31 | +7.60% | 1.25% | 6.07 |
| ERC_RiskParity | +5.42% | 1.53% | 3.47 | 3.97 | 1.39% | 3.91 | +7.50% | 1.39% | 5.41 |
| HRP | +4.79% | 0.54% | 8.59 | 11.61 | 0.42% | 11.49 | +7.18% | 0.66% | 10.89 |
| ERC_Capped35 | +5.95% | 2.58% | 2.25 | 2.50 | 2.45% | 2.43 | +7.76% | 2.45% | 3.17 |
| HRP_Capped35 | +5.52% | 2.51% | 2.15 | 2.34 | 2.48% | 2.23 | +7.43% | 2.48% | 3.00 |

- **Vô địch Blind OOS về Calmar:** `HRP` | **Vô địch Blind OOS về Sharpe:** `HRP`.

### Trọng Số Vốn (Capital %) vs Đóng Góp Rủi Ro (Risk Budget %) — Bộ Trọng Số Đầy Đủ `2020–2024`

| Allocator | S1_PROP_FX_IDX (Cap% / Risk%) | S2_CRYPTO_SPOT (Cap% / Risk%) | S3A_FUND_CARRY (Cap% / Risk%) | S3B_MACRO_ETF (Cap% / Risk%) |
|---|---:|---:|---:|---:|
| Equal_Weight | 25.0% / 15.9% | 25.0% / 53.4% | 25.0% / 1.0% | 25.0% / 29.7% |
| Inverse_Vol | 13.5% / 21.8% | 8.0% / 28.2% | 67.5% / 24.3% | 11.0% / 25.7% |
| Inverse_DD | 12.5% / 22.1% | 7.0% / 25.8% | 71.6% / 32.1% | 8.9% / 20.1% |
| ERC_RiskParity | 14.2% / 25.0% | 7.4% / 25.0% | 67.7% / 25.0% | 10.7% / 25.0% |
| HRP | 3.7% / 3.2% | 1.1% / 1.9% | 93.0% / 93.0% | 2.1% / 1.9% |
| ERC_Capped35 | 28.6% / 33.4% | 14.8% / 31.3% | 35.0% / 2.4% | 21.6% / 32.9% |
| HRP_Capped35 | 34.6% / 51.9% | 10.5% / 17.4% | 35.0% / 2.4% | 19.9% / 28.3% |

## 4. Bản Thiết Kế Triển Khai Theo 3 Bậc Vốn (`10k`, `50k`, `200k+ USD`)

| Capital Tier | Architecture | Allocation Breakdown (USD) | Expected Ann (USD) | Expected ROE % |
|---|---|---|---:|---:|
| 10,000 USD (Prop-Leveraged Starter) | Prop Fee Reserve (15%) + Own 3-Sleeve (85%) | S1_PROP_FEE_RESERVE: 1,500, S1_FUNDED_NOTIONAL_TARGET: 25,000, S2_CRYPTO_SPOT: 3,000, S3A_FUND_CARRY: 3,000, S3B_MACRO_ETF: 2,500 | +2,122.8 | +21.23% |
| 50,000 USD (Hybrid Multi-Prop + ERC Own Pod) | Multi-Prop Reserve (10%) + ERC Own Book (90%) | S1_PROP_FEE_RESERVE: 5,000, S1_FUNDED_NOTIONAL_TARGET: 100,000, S2_CRYPTO_SPOT: 11,181, S3A_FUND_CARRY: 17,500, S3B_MACRO_ETF: 16,319 | +9,066.6 | +18.13% |
| 200,000+ USD (Institutional Own-Book ERC-Capped35 Pod) | Full 4-Sleeve Own-Book ERC (Max 35% Counterparty Cap) | S1_OWN_FX_IDX_BOOK: 57,200, S2_CRYPTO_SPOT: 29,600, S3A_FUND_CARRY: 70,000, S3B_MACRO_ETF: 43,200 | +15,345.9 | +7.67% |

### Ghi Chú Thực Thi Cho Từng Bậc Vốn

- **10,000 USD (Prop-Leveraged Starter):** Tận dụng đòn bẩy phí Prop (~1,500 USD dự phòng vé cho mục tiêu 25k Funded) thay vì chia nhỏ 10k gây trượt min-lot FX; 8,500 USD còn lại nuôi 3 sleeve tự doanh sinh lợi kép & bộ đệm tâm lý.
- **50,000 USD (Hybrid Multi-Prop + ERC Own Pod):** Kết hợp 5,000 USD quỹ dự phòng Multi-Prop (FTMO + The5ers mục tiêu 100k Funded) cùng 45,000 USD tự doanh phân bổ ERC trên S2/S3A/S3B để triệt tiêu rủi ro tập trung một quỹ.
- **200,000+ USD (Institutional Own-Book ERC-Capped35 Pod):** Chuyển S1 sang tài khoản ECN tự doanh (không phụ thuộc quy định Prop), phân bổ chuẩn `ERC_Capped35` (trần tối đa 35% cho mỗi sleeve để chặn rủi ro sàn FTX trên S3A) với tương quan gần 0 và DD danh mục < 3%.

## 5. Rủi Ro Thực Tế & Kỷ Luật Tái Cân Bằng

1. **Tương quan 4 sleeve thực sự gần 0 (`|r| < 0.15` hầu hết các cặp):** giúp `Inverse_Vol`, `ERC_RiskParity` và `HRP` kéo Max Drawdown danh mục xuống chỉ còn khoảng `1.5%–3.5%` mà vẫn giữ Sharpe cao vượt trội từng sleeve đơn lẻ.
2. **Cảnh báo rủi ro tập trung Funding Carry (`S3A`):** Vì `S3A_FUND_CARRY` có độ biến động rất thấp (`< 1.5%/năm`), các thuật toán nghịch đảo biến động/DD (`Inverse_Vol`, `Inverse_DD`, `HRP`) có xu hướng cấp tỷ trọng vốn rất lớn cho `S3A`. Trong vận hành thật, bắt buộc áp trần **Counterparty / Exchange Risk Cap `<= 35%–40%` tổng tài sản** trên các sàn crypto tập trung (bài học FTX 2022) và chỉ chọn `ERC_RiskParity` hoặc `HRP` có ràng buộc trần sàn.
3. **Tái cân bằng hàng tháng (Monthly Rebalance):** Khớp lại ma trận hiệp phương sai trượt 252 ngày vào ngày làm việc cuối tháng, không đảo tỷ trọng theo cảm xúc giữa tháng.
