---
doc_type: research-report
title: "Lab #4: Nghiên cứu 40-ETF Multi-Factor, RSI(2), Credit-Spread & VRP cho Own-Book (2005–2026)"
date: 2026-11-24
scope: wave2-cycle2b-lab4-etf40-own-book
status: completed
owner: domain-research
code_module: tooling/ai-engines/quant_factory/etf40_multifactor_vrp_lab.py
evidence_json: .runtime/etf40-cache/etf40_study_summary.json
sleeve_export: .runtime/quant-pod-returns/sleeve4_etf40_multifactor.json
order_send_count: 0
holdout_rows_analysed: 0
---

# Lab #4: Nghiên cứu 40-ETF Multi-Factor, RSI(2), Credit-Spread & VRP (Own-Book 2005–2026)

> **Tóm tắt điều hành (Executive Summary):** Mở rộng vũ trụ Own-Book từ 15 ETF (Sleeve #3B) lên **40 mã thanh khoản cao (`38` ETF giao dịch + `2` chỉ số biến động chỉ dùng làm tín hiệu `^VIX`, `^VIX3M`)** giai đoạn `2005-01-03..2026-11-20` (`5,255` phiên NYSE đánh giá sau warmup, loại sạch ngày lễ CBOE không khớp NYSE). Cả **`4 / 4` chiến lược** đều vượt qua toàn bộ 6 cổng kiểm định của `SkepticalRedTeamCritic` (`APPROVE_FOR_INCUBATION`, `0` cổng trượt). Chiến lược chọn trước hoàn toàn trên **Cluster A (`2006–2018`)** theo Sharpe #1 là **`E40_VRP_VOL_CARRY`** (`Cl.A Sharpe 0.791` -> **mù Cluster B `2019–2026`: `CAGR +6.85%`, `Sharpe 0.915`, `MaxDD 20.81%`, `BH q = 0.01247`, `DSR = 0.9332`, `2x cost +4.60%`, `r(S1_7E) = -0.0155`**). Khi ghép đều 4 chiến lược đã duyệt thành **`E40_APPROVED_EQW_ENSEMBLE`**, hiệu năng mù **Cluster B (`2019–2026`)** đạt **`CAGR +7.72%`, `Vol 7.81%`, `Sharpe 0.992`, `Sortino 1.308`, `MaxDD 15.66%`, `Calmar 0.493`** — vượt `SPY` về tỷ số rủi ro/lợi nhuận (`SPY Sharpe 0.841`, `MaxDD 33.72%`, `Calmar 0.457`) và cắt lỗ khủng hoảng cực sâu (`GFC 2008: -2.81%` vs `SPY -52.30%`; `COVID 2020: -3.22%` vs `SPY -33.40%`). Toàn bộ đường lợi suất ngày đã xuất chuẩn sang `.runtime/quant-pod-returns/sleeve4_etf40_multifactor.json` để tích hợp vào NCO Pod v2 (`OrderSend = 0`, không API key, `Holdout 2025+` của FX/FTMO hoàn toàn niêm phong).

---

## 1. Bối cảnh, Bất biến Chống Rò rỉ & Vũ trụ 40 Mã

### 1.1 Quy ước dữ liệu & Anti-Bias
- **Nguồn dữ liệu:** Public Yahoo Finance v8 Chart API (`adjclose` bao gồm cổ tức & chia tách, cache Zstd Parquet + `manifest.sha256.json` tại `.runtime/etf40-cache/`). Đã tải đủ **`40 / 40` mã (`0` mã lỗi/bỏ qua)**; lịch giao dịch neo cứng theo các ETF NYSE giao dịch thực (`SIGNAL_ONLY_TICKERS` không chèn ngày nghỉ lễ Mỹ vào lịch).
- **Cửa sổ đánh giá & chia tập nghiêm ngặt:**
  - Warmup (`2005-01-03..2005-12-30`): đủ `200` phiên cho `SMA(200)` mà không dùng dữ liệu tương lai.
  - **Cluster A (Khám phá & Chọn lọc):** `2006-01-03..2018-12-31` (`3,271` ngày giao dịch — bao gồm khủng hoảng tài chính `2008 GFC`, khủng hoảng nợ châu Âu `2011`, cú sốc thanh khoản `Q4 2018`).
  - **Cluster B (Kiểm định mù OOS):** `2019-01-01..2026-11-20` (`1,984` ngày giao dịch — bao gồm `2020 COVID`, thị trường gấu lạm phát `2022` khi cả cổ phiếu lẫn trái phiếu cùng giảm, và chu kỳ lãi suất cao `2023–2026`).
- **Bất biến nhân quả & thực thi (`Causal t -> t+1`):**
  - Mọi chỉ báo (`RSI(2)`, `SMA(5/50/126/200)`, `Vol(60)`, tỷ lệ `HYG/IEF`, cấu trúc kỳ hạn `^VIX / ^VIX3M`) chỉ dùng dữ liệu đến đóng cửa ngày `t` (`<= t`) để quyết định tỷ trọng ngày `t+1`.
  - **Không điền ngược pre-listing (`Zero Backfill`):** Các ETF niêm yết sau `2005` (`HYG` `2007-04`, `^VIX3M` `2007-12`, `USMV` `2011-10`, `MTUM/QUAL` `2013`, `XLRE` `2015-10`) giữ nguyên `NaN` trước ngày niêm yết và có tỷ trọng bắt buộc bằng `0.0`.
  - **Chỉ số tín hiệu thuần (`^VIX`, `^VIX3M`):** Cứng hóa tỷ trọng giao dịch `= 0.0` mọi ngày; chỉ dùng làm công tắc trạng thái.
  - **Chi phí giao dịch & tiền mặt nhàn rỗi:** `1x = 5 bps` mỗi chiều (`10 bps` round-trip trên tỷ trọng quay vòng); stress `2x = 10 bps` mỗi chiều (`20 bps` RT). Tiền mặt nhàn rỗi giả định lợi suất **`0%`** (bảo thủ, chưa cộng lãi T-Bill `BIL`/`SGOV` ~4–5%/năm giai đoạn `2022–2026`).
  - **Kiểm định qua Hội đồng Nghiên cứu:** Toàn bộ 4 chiến lược đi trực tiếp qua `quant_factory/research_council.py` (`propose_hypothesis` -> `critique_proposal`, `m = 4` phép thử gia đình cho `BH-FDR` và `DSR`).

### 1.2 Cấu trúc Vũ trụ 40 Mã

| Nhóm tài sản | Số mã | Danh sách mã (`adjclose` 2005–2026) | Vai trò kinh tế |
| :--- | :---: | :--- | :--- |
| **US Sectors (10)** | 10 | `XLK, XLF, XLE, XLV, XLI, XLP, XLU, XLY, XLB, XLRE` | Xoay vòng động lượng ngành (`E40_XSEC_SECTOR_MOM_TOP4`) & đảo chiều `RSI(2)` |
| **Broad & Smart-Beta Factors (7)** | 7 | `SPY, QQQ, IWM, MTUM, QUAL, USMV, VTV` | Lõi tăng trưởng Risk-On & bộ lọc chất lượng/biến động thấp (`VRP`, `Credit`) |
| **Fixed Income & Credit (7)** | 7 | `SHY, IEF, TLT, TIP, LQD, HYG, EMB` | Tín hiệu chênh lệch tín dụng (`HYG/IEF`, fallback `LQD/IEF` trước `2007-04`) & hầm trú ẩn |
| **International Equities (6)** | 6 | `EFA, EEM, EWJ, EWG, FXI, EWZ` | Đa dạng hóa rủi ro vùng trong rổ Risk-On (`Credit`) |
| **Commodities (6)** | 6 | `GLD, SLV, USO, UNG, DBA, DBC` | Phòng hộ lạm phát & cú sốc biến động (`GLD` khi `> SMA200`) |
| **FX, Cash & Vol Signals (4)** | 4 | `UUP, BIL, ^VIX` *(signal-only)*, `^VIX3M` *(signal-only)* | Cấu trúc kỳ hạn biến động (`Contango` vs `Backwardation`) |

---

## 2. Cơ chế Kinh tế & Logic 4 Chiến lược

1. **`E40_RSI2_CONNORS` (Đảo chiều ngắn hạn 2–5 ngày trên xu hướng tăng):**
   - *Đối tác trả tiền (Economic Counterparty):* Các lệnh cắt lỗ ngắn hạn của nhà đầu tư cá nhân/CTA và nhu cầu thanh khoản tái cân bằng trong các nhịp rũ bỏ ngắn trên xu hướng tăng dài hạn.
   - *Quy tắc nhân quả:* Trên `12` ETF cổ phiếu/ngành Mỹ, vào lệnh khi `Close > SMA(200)` và `Wilder RSI(2) < 10`; thoát khi `Close > SMA(5)` hoặc nắm giữ đủ `7` ngày giao dịch. Phân bổ nghịch đảo biến động `Vol(60)`, trần tối đa `25%` mỗi ETF, tổng tỷ trọng `<= 1.0`.
2. **`E40_CREDIT_HYG_IEF_REGIME` (Xoay vòng theo Chênh lệch Tín dụng `HYG/IEF`):**
   - *Đối tác trả tiền:* Dòng vốn trái phiếu rác (High-Yield) thường định giá lại rủi ro vỡ nợ sớm hơn thị trường cổ phiếu do các quỹ hưu trí/tổ chức cổ phiếu phản ứng chậm theo quý.
   - *Quy tắc nhân quả:* Tái cân bằng định kỳ mỗi 5 phiên hoặc cuối tháng. Nếu `HYG/IEF > SMA50(HYG/IEF)` (trước `2007-04` dùng `LQD/IEF` nhân quả) -> Risk-On: chọn Top-4 ETF động lượng điều chỉnh rủi ro dương (`0.5 * Ret63 + 0.5 * Ret126`) / `Vol60`, phân bổ nghịch đảo biến động. Ngược lại -> Phòng thủ trên `IEF/TLT/GLD/SHY`, cắt tỷ trọng xuống `0.25x` nếu tài sản phòng thủ dưới `SMA(200)` để tránh bẫy trái phiếu `2022`.
3. **`E40_XSEC_SECTOR_MOM_TOP4` (Động lượng Chéo Ngành Mỹ — Quay vòng thấp):**
   - *Đối tác trả tiền:* Sự dịch chuyển dòng tiền định chế chậm chạp giữa các ngành kinh tế Mỹ (ngành dẫn dắt thu hút dòng vốn thụ động/ETF theo quý).
   - *Quy tắc nhân quả:* Tái cân bằng đúng **1 lần cuối tháng**. Chọn tối đa Top-4 trong 10 ngành Mỹ có động lượng `3m+6m` dương và `Close > SMA(200)`, phân bổ nghịch đảo biến động. Mỗi suất trống (`4 - active_slots`) xoay sang `IEF` nếu `IEF > SMA(126)`, ngược lại giữ `0%` Tiền mặt.
4. **`E40_VRP_VOL_CARRY` (Cấu trúc Kỳ hạn VIX & Chế độ Biến động — Chiến lược Chọn Chính):**
   - *Đối tác trả tiền:* Phần bù rủi ro biến động (Variance Risk Premium — VRP): nhà đầu tư tổ chức trả phí bảo hiểm định kỳ cho quyền chọn phòng vệ (tạo trạng thái `VIX < VIX3M` Contango); khi cấu trúc đảo ngược (`Backwardation`) hoặc `VIX > SMA60(VIX)`, xác suất sụp đổ đuôi tăng vọt.
   - *Quy tắc nhân quả:* Trạng thái `Calm VRP` khi `^VIX < SMA60(^VIX)` VÀ `^VIX < ^VIX3M` (trước `2007-12` dùng ngưỡng nhân quả `^VIX < 22.0`). Khi `Calm`: giữ `60%` cổ phiếu chất lượng/ít biến động (`SPY, QQQ, USMV, QUAL`) + `40%` trái phiếu hạng đầu tư (`IEF, LQD, TIP`), trọng số nghịch đảo `Vol(60)`. Khi `Stress/Backwardation`: cắt rủi ro cứng sang `20% GLD` (nếu `> SMA200`) + `25% TLT` (nếu `> SMA126`) + `25% SHY`, phần còn lại giữ tiền mặt. Chỉ tái cân bằng khi cuối tháng hoặc độ lệch tỷ trọng `L1 > 0.20` để giảm nhiễu whipsaw.

---

## 3. Bảng Kết quả Chính thức: Cluster A (`2006–2018`) vs Mù Cluster B (`2019–2026`)

Mọi số liệu dưới đây đối khớp chính xác `100%` với `.runtime/etf40-cache/etf40_study_summary.json` (`3,271` ngày Cluster A; `1,984` ngày Cluster B; `5,255` ngày toàn chu kỳ 21 năm).

| Chiến lược / Tổ hợp | Cl.A CAGR (`1x`/`2x`) | Cl.A Sh | Cl.A MaxDD | Cl.B CAGR `1x` | Cl.B CAGR `2x` | Cl.B Sharpe | Cl.B Sortino | Cl.B MaxDD | Cl.B Calmar | Turn/yr (B) | `BH q` (B) | `DSR` (B / Full) | `BE` Cost | `r(S1_7E)` | `r(S3B)` | Hội đồng (`Critic`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`E40_VRP_VOL_CARRY`** *(Chọn #1 Cl.A)* | `+5.20%` / `+2.89%` | `0.791` | `12.57%` | **`+6.85%`** | `+4.60%` | **`0.915`** | `1.196` | `20.81%` | `0.329` | `42.56x` | `0.01247` | `0.9332` / `0.9971` | `4.25x` | `-0.0155` | `+0.4570` | **`APPROVE_FOR_INCUBATION`** |
| **`E40_CREDIT_HYG_IEF_REGIME`** | `+4.94%` / `+3.55%` | `0.486` | `13.29%` | **`+10.04%`** | **`+8.43%`** | **`0.890`** | `1.130` | `25.56%` | `0.393` | `29.31x` | `0.01247` | `0.9217` / `0.9679` | `7.98x` | `+0.0135` | `+0.4907` | **`APPROVE_FOR_INCUBATION`** |
| **`E40_XSEC_SECTOR_MOM_TOP4`** | `+9.57%` / `+9.17%` | `0.764` | `20.21%` | `+8.89%` | **`+8.46%`** | `0.713` | `0.939` | `24.31%` | `0.366` | **`8.01x`** | `0.03032` | `0.8251` / `0.9898` | **`24.44x`** | `-0.0064` | `+0.5132` | **`APPROVE_FOR_INCUBATION`** |
| **`E40_RSI2_CONNORS`** | `+2.47%` / `+0.39%` | `0.352` | `15.87%` | `+4.21%` | `+1.87%` | `0.544` | `0.496` | **`11.86%`** | `0.355` | `45.44x` | `0.06339` | `0.6803` / `0.8120` | `2.96x` | `-0.0270` | **`+0.3350`** | **`APPROVE_FOR_INCUBATION`** |
| **`E40_APPROVED_EQW_ENSEMBLE`** *(4 chiến lược)* | `+5.76%` *(1x)* | `0.795` | **`9.56%`** | **`+7.72%`** | — | **`0.992`** | **`1.308`** | **`15.66%`** | **`0.493`** | — | — | `p_NW = 0.00193` | — | — | — | **Tổ hợp Own-Book Đề xuất** |
| *Chuẩn so sánh: `BM_SPY` (Buy & Hold)* | `+7.69%` | `0.482` | `55.19%` | `+15.42%` | — | `0.841` | `1.031` | `33.72%` | `0.457` | `0.00x` | — | `p_NW = 0.00458` | — | — | — | *Benchmark Cổ phiếu Mỹ* |

### 3.1 Tổng lợi nhuận toàn chu kỳ 21 năm (`2006–2026`, `5,255` ngày, `1x` phí, `0%` lãi tiền mặt)
- **`E40_XSEC_SECTOR_MOM_TOP4`:** `CAGR +9.31%` (`+540.61%`), `Sharpe 0.745`, `MaxDD 24.31%`, `p_NW = 0.00020`, `BH q_full = 0.00067`.
- **`E40_CREDIT_HYG_IEF_REGIME`:** `CAGR +6.84%` (`+297.05%`), `Sharpe 0.641`, `MaxDD 25.56%`, `p_NW = 0.00105`, `BH q_full = 0.00227`.
- **`E40_VRP_VOL_CARRY`:** `CAGR +5.82%` (`+225.23%`), `Sharpe 0.840`, `MaxDD 20.81%`, `p_NW = 0.00005`, `BH q_full = 0.00025`.
- **`E40_RSI2_CONNORS`:** `CAGR +3.12%` (`+89.94%`), `Sharpe 0.427`, `MaxDD 20.24%`, `p_NW = 0.01419`, `BH q_full = 0.02564`.
- **`E40_APPROVED_EQW_ENSEMBLE`:** `CAGR +6.50%` (`+271.58%`), `Vol 7.55%`, **`Sharpe 0.872`**, `Sortino 1.101`, **`MaxDD 15.66%`**, **`Calmar 0.415`**, `p_NW = 0.00001` (vs `BM_SPY` 21 năm: `CAGR +10.54%`, `Vol 19.21%`, `Sharpe 0.618`, `MaxDD 55.19%`, `Calmar 0.191`).

---

## 4. Kiểm toán 3 Cú Sốc Lịch Sử (`2008 GFC`, `2020 COVID`, `2022 Inflation`)

| Chiến lược / Tổ hợp | `2008 GFC` (`2008-01-02..2009-03-09`) | `2020 COVID` (`2020-02-19..2020-03-23`) | `2022 Inflation` (`2022-01-03..2022-10-14`) | Nhận xét phòng thủ đuôi |
| :--- | :---: | :---: | :---: | :--- |
| **`E40_VRP_VOL_CARRY`** | `-5.01%` | **`+3.53%`** | `-17.02%` | VIX backwardation cứu sạch 2008 & 2020; năm 2022 chịu đòn kép cổ phiếu + trái phiếu |
| **`E40_CREDIT_HYG_IEF_REGIME`** | **`+5.82%`** | **`+4.72%`** | `-20.45%` | Dương cả 2008 lẫn 2020 nhờ xoay sang Treasury/Vàng; nhạy hơn khi tín dụng whipsaw 2022 |
| **`E40_XSEC_SECTOR_MOM_TOP4`** | `-9.71%` | `-13.58%` | `-12.42%` | Lỗ giới hạn ~1/4 đến 1/5 so với `SPY` nhờ xoay sang `IEF`/tiền mặt cuối tháng |
| **`E40_RSI2_CONNORS`** | `-2.93%` | `-6.82%` | **`-4.53%`** | Tắt hoàn toàn dưới `SMA(200)` nên gần như miễn nhiễm cú sập kéo dài 2008 & 2022 |
| **`E40_APPROVED_EQW_ENSEMBLE`** | **`-2.81%`** | **`-3.22%`** | **`-13.59%`** | Cắt >90% thiệt hại 2008/2020 và giảm 43% thiệt hại 2022 so với `SPY` |
| *`BM_SPY` (Buy & Hold)* | `-52.30%` | `-33.40%` | `-23.83%` | Rủi ro đuôi quá lớn cho nhà đầu tư cá nhân sợ trả lại lợi nhuận |

---

## 5. Phản biện Trung thực (Red-Team Disclosure) & Khuyến nghị Triển khai Own-Book

1. **Rủi ro vòng quay (`Turnover`) cao ở 2 nhánh tín hiệu ngày:**
   - `E40_RSI2_CONNORS` (`45.44x/năm`, `BE = 2.96x`) và `E40_VRP_VOL_CARRY` (`42.56x/năm`, `BE = 4.25x`) có chi phí ma sát đáng kể nếu đặt lệnh qua môi giới phí cao hoặc chênh lệch spread rộng. Ở mức stress `2x` (`10 bps` mỗi chiều), `RSI(2)` chỉ còn `+1.87%` CAGR ở Cluster B (`+0.39%` ở Cluster A).
   - **Giải pháp thực thi:** Chỉ chạy trên tài khoản tiền mặt **Interactive Brokers (`IBKR Pro` / `Tiered`)** dùng lệnh giới hạn (`Limit / MidPrice`) trên các ETF siêu thanh khoản (`SPY, QQQ, XL*`, spread thực tế `0.5–2 bps` — thấp hơn giả định `5 bps` bảo thủ của lab). Nếu muốn phiên bản siêu nhàn (tái cân bằng 1 lần/tháng), **`E40_XSEC_SECTOR_MOM_TOP4` (`8.01x/năm`, `BE = 24.44x`, `2x CAGR +8.46%`)** là lựa chọn bền bỉ nhất trước ma sát.
2. **Độ tương quan với các Sleeve hiện có trong Naqex Quant Pod:**
   - Với **Sleeve #1 (`FTMO 7E Intraday`)**: Gần như **trực giao hoàn hảo** trên đúng lịch NYSE (`2019–2024`: `r = -0.0270` đến `+0.0135`, tương quan đuôi ngày xấu `tail_r = +0.0302..+0.0939`). Đây là mảnh ghép tăng Sharpe cấp Pod tốt nhất cho vốn tự có sau khi rút payout từ Prop Firm.
   - Với **Sleeve #3B (`Macro ETF Trend`)**: Có tương quan dương mức trung bình (`r = +0.3350` cho `RSI2`, `+0.4570` cho `VRP`, `+0.4907` cho `Credit`, `+0.5132` cho `Sector Mom`) do cùng hưởng phần bù tăng trưởng dài hạn Mỹ. Do đó **không nên phân bổ toàn bộ Own-Book vào cả `S3B` và `S4` cùng lúc như 2 nguồn độc lập 100%**; hãy để bộ tối ưu **NCO (`portfolio_allocator.py`)** tự chia tỷ trọng cụm Equity/Macro theo ma trận hiệp phương sai thực tế.
3. **Điểm mù 2022 (`-13.59%` trên Ensemble):** Khi lãi suất tăng sốc từ `0%` lên `5%`, cả cổ phiếu lẫn trái phiếu (`TLT/IEF`) đồng loạt giảm, khiến `VRP` (`-17.02%`) và `Credit` (`-20.45%`) chịu drawdown lớn nhất lịch sử. Cần kết hợp với **Sleeve #1 (FX/Gold Intraday)**, **Sleeve #3B (Hàng hóa/Năng lượng Trend)** và giữ tiền mặt nhàn rỗi trong **`SGOV`/`BIL`** (bù thêm `+3%..+4.5%/năm` trong môi trường lãi suất cao, vốn đang được đặt bảo thủ ở `0%` trong backtest này).

---

## 6. Tài sản & Tích hợp Hệ thống

- **Mã nguồn chuẩn hóa:** [etf40_multifactor_vrp_lab.py](../../tooling/ai-engines/quant_factory/etf40_multifactor_vrp_lab.py)
- **Kiểm thử chống nhìn trộm tương lai (Anti-Lookahead):** [test_wave2_etf40_and_cme_labs.py](../../tooling/ai-engines/tests/test_wave2_etf40_and_cme_labs.py)
- **Đường lợi suất Sleeve #4 cho NCO Pod v2 & Cockpit:** `.runtime/quant-pod-returns/sleeve4_etf40_multifactor.json` (đã gửi thông báo sang `@risk-auditor`).
- **Liên kết giáo trình & phân bổ vốn liên quan:** [capital-scaling-prop-to-own-book.md](../../knowledge/topics/capital-scaling-prop-to-own-book.md)
