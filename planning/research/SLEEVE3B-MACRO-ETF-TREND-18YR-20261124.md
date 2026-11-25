---
doc_type: research_receipt
date: 2026-11-24
lane: quant-rnd
milestone: M4.3
status: COMPLETE_VERIFIED_CAUSAL
order_send_count: 0
---

# Sleeve #3B — Xu Hướng Đa Tài Sản Vĩ Mô ETF & Cân Bằng Rủi Ro 18+ Năm (`2007–2026`)

- **Ngày thực hiện:** `2026-11-24` (dữ liệu giá điều chỉnh cổ tức/chia tách `adjclose` từ `2007-01-03` đến `2026-11-20`, tổng `5.004` phiên giao dịch Mỹ; đánh giá sau cửa sổ warmup `252` phiên từ `2008-01-02` → `2026-11-20`, `4.753` phiên = `18.9` năm).
- **Mã nguồn tái lập:** [macro_etf_trend.py](../../tooling/ai-engines/quant_factory/macro_etf_trend.py)
- **Kho dữ liệu Parquet & SHA-256 manifest:** `.runtime/macro-etf-cache/` (`12/12` ETF vĩ mô thanh khoản toàn cầu: `SPY, QQQ, IWM, TLT, IEF, GLD, SLV, USO, UUP, EFA, EEM, DBC`, nguồn công khai Yahoo Finance v8 Chart API, `0` API key, `OrderSend = 0`).
- **Chuỗi lợi suất ngày xuất cho Bộ Phân Bổ Pod (`@risk-auditor`):** `.runtime/quant-pod-returns/sleeve3b_macro_etf.json` (schema `naqex-sleeve-daily-returns-v1`, `annualization_days = 252.0`).
- **Giả định hạch toán & chống rò rỉ nghiêm ngặt:**
  - Nhân quả tuyệt đối `t -> t+1`: tín hiệu và độ biến động `60` phiên / `SMA200` tính tại đóng cửa ngày `t` áp dụng cho lợi suất ngày `t+1`. Không forward-fill trước ngày niêm yết.
  - Chi phí giao dịch thực tế `1x = 5 bps` một chiều + `50 bps/năm` phí vay cổ phiếu bán khống (`short borrow` trên vị thế short); stress `2x = 10 bps` một chiều + `100 bps/năm` phí short. Tiền mặt nhàn rỗi tính bảo thủ **`0%`** (không cộng thêm lãi T-bill để phóng đại Sharpe!).
  - **Phân tách mù:** Cluster A (`2008-01-02` → `2018-12-31`, `2.769` phiên, bao gồm khủng hoảng GFC 2008) để chọn ứng viên chính; **Cluster B mù (`2019-01-01` → `2026-11-20`, `1.984` phiên = `7.9` năm)** để kiểm chứng ngoài mẫu qua cả đại dịch COVID 2020 lẫn cú sốc lạm phát 2022.

---

## 1. Bảng Hiệu Suất 5 Chiến Lược Vĩ Mô (`m_total = 5`) + Benchmark (`2008–2026`)

| Mã Chiến Lược | Họ / Đòn Bẩy Tối Đa | Cl.A `CAGR` (`1x / 2x`) | Cl.A `Sharpe` | Cl.A `MaxDD` | **Cl.B Mù `CAGR` (`1x / 2x`)** | **Cl.B `Sharpe`** | **Cl.B `MaxDD`** | **Cl.B `Calmar`** | Turnover B | `r(SPY)` Cl.B | `BH q_B` / `DSR_B` | Toàn Mẫu `Sharpe` (`DSR_Full`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `BM_SPY` | Benchmark (`1.0x`) | `+7.20%` | `0.447` | `52.30%` | `+15.42%` | `0.841` | `33.72%` | `0.457` | `0.0x` | `1.000` | — | `0.607` |
| `BM_60_40` | Benchmark (`1.0x`) | `+6.71%` | `0.638` | `30.79%` | `+9.95%` | `0.871` | `21.02%` | `0.473` | `0.0x` | — | — | `0.738` |
| **`M5_VOL_PARITY_TREND_GUARD`** | `RISK_PARITY` (`1.0x` Long) | **`+3.64% / +3.56%`** | **`0.605`** | **`10.45%`** | **`+7.58% / +7.47%`** | **`1.063`** | **`7.77%`** | **`0.975`** | **`1.90x`** | `+0.468` | **`0.0062 / 0.958`** | **`0.809` (`0.989`)** |
| `M2_AHL_TSMOM_LO_VOL10` | `TSMOM` (`1.0x` Long) | `+3.08% / +2.47%` | `0.529` | `10.61%` | `+5.49% / +4.84%` | `0.887` | **`5.75%`** | `0.956` | `12.41x` | `+0.334` | `0.0062 / 0.897` | `0.681` (`0.958`) |
| `M3_DUAL_MOMENTUM_TOP3` | `DUAL_MOM` (`1.0x` Long) | `+7.63% / +7.39%` | `0.554` | `26.85%` | `+12.98% / +12.73%` | `0.889` | `22.67%` | `0.573` | `4.49x` | `+0.747` | `0.0062 / 0.898` | `0.691` (`0.963`) |
| `M4_ALL_WEATHER_VOL_PARITY` | `RISK_PARITY` (`1.0x` Long) | `+3.61% / +3.58%` | `0.434` | `23.40%` | `+9.30% / +9.26%` | `0.997` | `15.59%` | `0.596` | **`0.58x`** | `+0.651` | `0.0062 / 0.941` | `0.672` (`0.956`) |
| `M1_AHL_TSMOM_LS_VOL10` | `TSMOM` (`1.5x` L/S) | `+2.51% / +1.33%` | `0.325` | `12.72%` | `+2.79% / +1.64%` | `0.361` | `19.26%` | `0.145` | `19.97x` | **`-0.138`** | `0.1374 / 0.429` | `0.340` (`0.611`) |
| **`MACRO_50TSMOM_LS_50ALLWEATHER_TG`** | Blend `50% M1 + 50% M5` | `+3.18%` | `0.532` | **`8.53%`** | `+5.25%` | `0.799` | `8.85%` | `0.594` | — | — | `p_B=0.0096` / `DSR=0.847` | `0.647` |

---

## 2. Kiểm Định "Crisis Alpha" Qua 3 Đại Khủng Hoảng Kinh Tế (`2008`, `2020`, `2022`)

| Chiến Lược | **GFC `2008–2009`** (`2008-01-02..2009-03-09`) | **Sập COVID `2020`** (`2020-02-19..2020-03-23`) | **Cả Năm `2020`** | **Sốc Lạm Phát `2022`** (`2022-01-03..2022-10-14`) | **Cả Năm `2022`** |
|---|---:|---:|---:|---:|---:|
| `BM_SPY` (Cổ phiếu Mỹ) | `-52.30%` (`DD 52.3%`) | `-33.40%` (`DD 33.7%`) | `+18.33%` | `-23.83%` (`DD 24.5%`) | `-18.18%` |
| `BM_60_40` (60% SPY / 40% IEF) | `-30.39%` (`DD 30.8%`) | `-18.91%` (`DD 19.1%`) | `+16.91%` | `-20.69%` (`DD 20.7%`) | `-16.39%` |
| **`M1_AHL_TSMOM_LS_VOL10`** *(Crisis Alpha thuần)* | **`+15.90%`** (`DD 7.4%`) | **`+4.75%`** (`DD 4.6%`) | `+10.87%` | **`+12.22%`** (`DD 5.0%`) | **`+3.74%`** |
| **`M2_AHL_TSMOM_LO_VOL10`** *(Long-Only Cash)* | **`+3.24%`** (`DD 4.5%`) | `-3.86%` (`DD 5.8%`) | `+6.63%` | **`+3.64%`** (`DD 3.8%`) | **`+1.83%`** |
| **`M5_VOL_PARITY_TREND_GUARD`** *(Chọn chính Cl.A)* | **`-0.02%`** (`DD 10.5%`) | `-4.52%` (`DD 7.6%`) | `+13.13%` | **`-2.67%`** (`DD 5.8%`) | `-2.22%` |
| `M4_ALL_WEATHER_VOL_PARITY` *(Không lọc SMA200)* | `-13.01%` (`DD 23.4%`) | `-12.28%` (`DD 15.6%`) | `+13.64%` | `-11.99%` (`DD 14.0%`) | `-6.97%` |
| `M3_DUAL_MOMENTUM_TOP3` | `-4.59%` (`DD 26.9%`) | `-21.65%` (`DD 22.7%`) | `+21.50%` | `-4.11%` (`DD 10.9%`) | `-4.50%` |
| **`MACRO_50TSMOM_LS_50ALLWEATHER_TG`** | **`+7.98%`** (`DD 7.0%`) | **`+0.13%`** (`DD 4.0%`) | — | **`+4.67%`** (`DD 4.0%`) | **`+0.90%`** |

---

## 3. Phân Tích Định Lượng & Khuyến Nghị Cho Quant Pod

1. **Ứng viên chọn mù trên Cluster A (`M5_VOL_PARITY_TREND_GUARD`) vượt trội ngoài mẫu Cluster B (`2019–2026`):**
   - Cân bằng rủi ro `4` nhóm tài sản vĩ mô (`Cổ phiếu / Trái phiếu / Kim loại quý / Hàng hóa & USD`) kết hợp bộ lọc xu hướng `SMA200` (cắt tỷ trọng tài sản xuống `25%` khi rơi dưới `SMA200`) đạt **`Sharpe 1.063`, `Calmar 0.975`, `MaxDD 7.77%`, `BH-FDR q_B = 0.0062`, `DSR_B = 0.958`** trên `7.9` năm mù — vượt `BM_60_40` về cả `Sharpe` (`1.063` vs `0.871`) lẫn `Calmar` (`0.975` vs `0.473`, gấp đôi!) với `turnover` cực thấp chỉ **`1.90x/năm`** (hầu như miễn nhiễm chi phí: `2x` phí chỉ giảm CAGR từ `+7.58% -> +7.47%`!).
   - Bảo thủ tuyệt đối: trung bình chỉ giải ngân `75.7%` vốn (`24.3%` nằm tiền mặt tính lãi `0%`). Nếu thực tế tiền mặt nhàn rỗi hưởng lãi T-bill ngắn hạn `SGOV/BIL`, CAGR thực tế còn cao hơn khoảng `+0.8%` đến `+1.2%/năm`.
2. **Đánh đổi trung thực của Man AHL Long/Short TSMOM (`M1`):**
   - `M1` tạo **Crisis Alpha đích thực không ai thay thế được** (`+15.90%` GFC 2008, `+4.75%` cú sập COVID 24 phiên, `+12.22%` đỉnh-đáy lạm phát 2022, tương quan âm `r = -0.138` với SPY), nhưng khi đứng đơn lẻ chịu chi phí whipsaw và short-borrow (`turnover 20x/năm`, `Sharpe 0.361`, không vượt `BH-FDR` riêng lẻ `q_B = 0.137`).
   - Vai trò đúng của `M1` trong danh mục thực tế không phải chạy độc lập mà là **lớp bảo hiểm đuôi** (như tổ hợp `50% M1 + 50% M5` giữ dương ròng qua cả 3 đại khủng hoảng `2008 / 2020 / 2022` với `DSR_B = 0.847`), hoặc dùng **`M2_AHL_TSMOM_LO_VOL10`** trên tài khoản cash-only (`MaxDD Cl.B 5.75%`, `+3.64%` trong cú sốc 2022, `DSR_B = 0.897`).
3. **Phù hợp hành vi người vận hành:** `M5_VOL_PARITY_TREND_GUARD` chỉ tái cân bằng **1 lần/tháng** (12 lần/năm, tài khoản ETF phổ thông không margin/short), hoàn toàn khớp với hồ sơ ưu tiên workflow bảo trì thấp và ít gây áp lực tâm lý trả lại lãi của owner.
