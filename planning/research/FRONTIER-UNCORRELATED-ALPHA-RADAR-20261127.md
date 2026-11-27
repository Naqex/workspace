---
doc_type: research-radar
title: "Radar Alpha Lệch Pha Tiền Duyên 2024–2026: 5 Cơ Chế Trực Giao Cho PORT_7E"
date: "2026-11-27"
updated_utc: "2026-11-27T06:47:00Z"
lane: "r3-alpha-hunt"
research_mode: "MODE_2_MULTISOURCE_DEEP_RESEARCH"
untrusted_external_data: true
trust_tier: "MIXED_T1_PRIMARY_AND_T2_COMMUNITY"
holdout_rows_analysed: 0
dev_cutoff_utc: "2024-12-31"
order_send_count: 0
spend_vnd: 0
config_artifact: "tooling/automation/configs/frontier_alpha_candidates.json"
layer: "Layer-1-Public-Sanitized"
---

# Radar Alpha Lệch Pha Tiền Duyên (`2024–2026`): 5 Cơ Chế Trực Giao Ghép Đôi Với `PORT_7E`

**Kết quả cốt lõi:** Đợt săn nghiên cứu đa nguồn Chế độ 2 (`EN / CN / RU / VI` qua `arXiv`, `OpenAlex`, `SSRN`, `NBER`, `GitHub`, `Habr`) đã chốt **5 cơ chế lợi nhuận cấu trúc không nằm trong Danh sách Cấm §3.4**, có kỳ vọng tương quan `|r| < 0,15` với `PORT_7E`, kiểm định được ngay trên kho dữ liệu Dev sẵn có (`<= 2024-12-31`) của `<X13_WORKER>` và lưu trọn bộ đặc tả có cổng bác bỏ đăng ký trước tại [frontier_alpha_candidates.json](../../tooling/automation/configs/frontier_alpha_candidates.json). **Cảnh báo trung thực:** Cả 5 cơ chế hiện ở trạng thái **giả thuyết chưa kiểm chứng cục bộ** — tuyệt đối không tuyên bố có lợi thế giao dịch trước khi vượt qua kiểm định Dev `<= 2024-12-31` (`DSR + PBO <= 0,50 + CPCV + Hansen SPA + stress phí 2x`) và thử nghiệm mù ngoài mẫu.

> **Rào chắn an toàn & chuỗi cung ứng (Fail-Closed):**
> - **Bất biến:** `0 VND` chi tiêu · `OrderSend = 0` · `MT5_PROCS = 0` · **`Holdout 2025+ SEALED`** (`holdout_rows_analysed = 0`, mốc cắt cứng `dev_cutoff_utc = 2024-12-31`).
> - **Dữ liệu ngoài không tin cậy (`untrusted_external_data: true`):** `0` tệp nhị phân tải về, `0` mã nguồn ngoài được thực thi; `100%` đường dẫn DOI/arXiv/GitHub/Habr được xác minh sống trực tiếp qua API trước khi trích dẫn.
> - **Tách bạch tuyệt đối 3 tầng bằng chứng:** (1) *Kết luận trong bài báo gốc đã bình duyệt/xuất bản* (`T1/T2`), (2) *Bằng chứng thực nghiệm cũ của Naqex* (`W`), và (3) *Giả thuyết cục bộ chưa đo* — bài báo đẹp ngoài đời **KHÔNG** tự động có lãi sau phí trên dữ liệu của Naqex.

---

## 1. Bối Cảnh Điểm Nghẽn `PORT_7E` & Lý Do Phải Săn Alpha Lệch Pha (`Luật 15`)

Theo nguồn sự thật duy nhất [TOP1-SOLO-QUANT-MASTER-PLAN.md](../TOP1-SOLO-QUANT-MASTER-PLAN.md) (§2, ứng viên `C10_NEWS_ON` trên `FTMO 2-Step Standard 100K`, ma sát `1,00x`, bằng chứng ở mức Backtest Dev `2018–2024` + `holdout_v1` v1 nền + `28` lệnh Demo — **chưa có tiền thật rút về**):

- **Hiệu suất lõi `PORT_7E` hiện tại:**
  - 🔴/🟡/🟢/🏆 **Winrate / RR / EV mỗi lệnh:** `48,6%` · `1,27x` · `+0,049R` (`2.882` lệnh Dev) -> **`🟡 Đủ dùng`** *(Ngưỡng gãy `<= 0R`; Tốt `+0,07..+0,15R`; Top 1% `> +0,15R` tiền thật)*.
  - 🟡 **Profit Factor:** `1,20` -> **`🟡 Đủ dùng`** *(Xấu `< 1,05`; Đủ dùng `1,10..1,20`; Tốt `1,25..1,50`; Top 1% `1,50..2,00+` tiền thật `>= 12T`)*.
  - 🟡/🟢 **Max DD (`1,0x`) / Calmar / Sharpe:** `8,62%` · `Calmar 0,86` (**`🟡 Đủ dùng`**) · `Sharpe 1,23` (**`🟢 Tốt`** trên quá khứ; Top 1% đòi `Calmar > 2,0..3,0` tiền thật `>= 12T`).
  - **Xác suất 1 vé không thử lại (`Đậu / Rớt / Chờ = 100%`):**
    - `3` tháng: `14,7% / 2,4% / 83,0%` (`100%`)
    - `6` tháng: `32,6% / 3,3% / 64,1%` (`100%`)
    - `12` tháng: `47,4% / 4,4% / 48,2%` (`100%`)
    - `24` tháng: **`62,7% / 6,1% / 31,2%` (`100%`)** · `NPV 24T`: TB `+161,9 triệu VND` (`+12,81x` phí), trung vị `+85,9 triệu VND`, `P(<= 0) = 40,2%` (ở ma sát `1,50x`, trung vị tụt về `-12,6 triệu VND`, `P(<= 0) = 62,2%`; ngưỡng cắt mua vé `> 1,75x`, hòa vốn `2,31x`).
- **Điểm nghẽn cấu trúc số 1:** **`60%–66%` số tháng ở pha Funded không có tiền rút** (`P50 = 8` tháng đói, chờ lần rút đầu trung vị `265` ngày) vì cả `7` động cơ đều thuộc chung 1 họ CFD trong ngày `swap = 0` trên `4` mã vĩ mô liên đới (`USDJPY`, `US100`, `GBPUSD`, `EURJPY`). Khi biên độ phá vỡ trong ngày cạn kiệt (như năm `2023`), cả 7 động cơ chậm lại cùng lúc.
- **Mục tiêu toán học của Lane R3:** Tìm nguồn lợi nhuận có bản chất kinh tế hoàn toàn khác (`|r| < 0,15` với `PORT_7E`) để khi ghép ở cấp danh mục đa nhánh (*Quant Pod*), nâng Sharpe tổ hợp từ `~1,2` lên vùng `1,7–2,0+` và kéo tỷ lệ tháng không có dòng tiền từ **`60%–66%` xuống dưới `35%`**.
- **Ranh giới vốn trung thực (§3.2):** Các nhánh ETF/Crypto dưới đây **KHÔNG** chạy đè lên tài khoản Prop MT5 và **KHÔNG** tốn tiền ở Mốc 0–1 (`0 VND`). Trong lúc chờ thu bằng chứng thực địa Demo/Prop, `<X13_WORKER>` kiểm định toàn bộ giả thuyết trên dữ liệu Dev (`<= 2024-12-31`) ở mức chi phí **`0 VND`** để xây sẵn hàng ghế dự bị sạch overfit trước khi vốn riêng chạm mốc triển khai (`>= 10.000 USD` cho ETF gọn; `>= 25.000 USD` cho Crypto với trần cứng `CEX <= 25%`).

---

## 2. Bộ Lọc Loại Trừ Tuyệt Đối Theo Danh Sách Cấm (§3.4) & Bài Học Nội Bộ

Mọi ứng viên lọt vào [frontier_alpha_candidates.json](../../tooling/automation/configs/frontier_alpha_candidates.json) đều phải vượt qua kiểm toán `PASS_ZERO_VIOLATIONS` trước toàn bộ 4 điều cấm của [TOP1-SOLO-QUANT-MASTER-PLAN.md](../TOP1-SOLO-QUANT-MASTER-PLAN.md) (§3.4) và các bài học đã bị khai tử trong các phòng thí nghiệm trước:

| Quy tắc cấm / Bài học thất bại cũ (`W`) | Đã bị loại khỏi Radar này như thế nào? |
|---|---|
| **1. Cấm Crypto Spot `< 4H` chịu phí Taker** (`Lab #1: 0/12`) | `FRONTIER_03` chỉ tái cân bằng khung `D1` / hàng tuần trên dữ liệu `1D` và `4H`, đặt trần vòng quay cứng `<= 6,0x/năm`. |
| **2. Cấm CFD Vàng/Dầu/Chỉ số qua đêm chịu Swap âm** (`Labs #3A/#3B: 0/21`) | `0` chiến lược CFD giữ qua đêm; các nhánh vĩ mô/lịch/phân tán đều dùng ETF tiền mặt (`swap = 0`) cho Own-Book. |
| **3. Cấm cày thêm biến thể CFD intraday `swap = 0`** (`Labs #11–#12: 0/36`, `Pass 29–31: 0/66`) | Tuyệt đối không đề xuất thêm biến thể phá vỡ intraday FX/US100/Vàng nào trong `.runtime/hot-m1-cache/`. |
| **4. Cấm Grid, Martingale & bộ lọc ML `Brier Skill <= 0`** (`Lab #6`) | `100%` chiến lược hộp trắng (*white-box*), định cỡ nghịch đảo biến động/rủi ro có cắt lỗ hoặc trần vốn; mọi mô-đun dự báo phụ phải vượt `Brier Skill > 0` hoặc bị loại bỏ. |
| **5. Bài học Lab #7 (Overnight MOC-MOO hàng ngày `0/4` bị giết)** | Không lặp lại kiểu mua đóng / bán mở mỗi ngày (`300x/năm` bị phí `5–10 bps` ăn sạch). Nghiên cứu `2025–2026` về lợi suất qua đêm (`arXiv:2507.04481`, `arXiv:2607.03669`) chỉ dùng làm bộ lọc rủi ro đuôi vòng quay thấp cho `FRONTIER_05`. |

---

## 3. Tổng Quan 5 Cơ Chế Alpha Lệch Pha Được Chọn (`x13_ready: true`)

| Mã Cơ Chế | Lớp Tài Sản | Ai Trả Tiền Cho Ta? (Cơ Chế Kinh Tế) | Kho Dữ Liệu Dev (`<= 2024-12-31`) | Kỳ Vọng `\|r\|` vs `PORT_7E` | Trạng Thái Bằng Chứng Cục Bộ |
|---|---|---|---|---|---|
| **`FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY`** | ETF Vĩ Mô Đa Tài Sản | Quỹ `60/40` & Risk Parity tĩnh chậm xoay trục khi tương quan cổ–trái phiếu đảo dương (kiểu 2022) | `.runtime/etf40-cache/` & `.runtime/macro-etf-cache/` | `< 0,10` *(giả định)* | Chưa kiểm chứng Dev |
| **`FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR`** | ETF Yếu Tố + Cấu Trúc VIX | Tổ chức mua bảo hiểm sập giá định kỳ (`VIX < VIX3M`) nhưng phản ứng chậm khi biến động bùng nổ | `.runtime/etf40-cache/` (`IDX_VIX`, `IDX_VIX3M`, 12 ETF) | `< 0,10` *(giả định)* | Chưa kiểm chứng Dev |
| **`FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM`** | Crypto Spot + Perp (`>= 4H/D1`) | Nhà đầu cơ đòn bẩy trả phí funding 8 giờ cao kéo dài và bị xả vị thế khi thanh khoản arb co hẹp | `.runtime/crypto-spot-cache/` (`funding`, `1d`, `4h`) | `< 0,12` *(giả định)* | Chưa kiểm chứng Dev |
| **`FRONTIER_04_MONTH_END_PENSION_REBAL_AND_DURATION_FLOW`** | Lịch Tái Cân Bằng Cổ–Trái Phiếu | Quỹ hưu trí & quỹ chỉ số trái phiếu bắt buộc bán/mua máy móc quanh ngày cuối tháng và đầu tháng | `.runtime/etf40-cache/` & `.runtime/macro-etf-cache/` | `< 0,08` *(giả định)* | Chưa kiểm chứng Dev |
| **`FRONTIER_05_SECTOR_CORR_DISPERSION_NEUTRAL_SPREAD`** | Phân Tán 10 Ngành Mỹ Trung Lập | Dòng tiền ETF thụ động gây bầy đàn khi tương quan cao, bỏ ngỏ xoay vòng ngành khi tương quan thấp | `.runtime/etf40-cache/` (`10` mã `XL*`, `SPY`, `VIX`) | `< 0,10` *(giả định)* | Chưa kiểm chứng Dev |

---

## 4. Phân Tích Chuyên Sâu Từng Cơ Chế (Tách Bạch Bài Báo Gốc vs Giả Thuyết Cục Bộ)

### 4.1. `FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY` — Cân Bằng Rủi Ro Phân Cụm Lồng Nhau (`NCO`) Theo Chế Độ Bước Nhảy (`SJM`)

- **Giải thích dễ hiểu (bản chất kinh tế):** Mô hình cân bằng rủi ro truyền thống hay `S3B` (`SMA200`) gặp 2 lỗi kinh điển: hoặc chịu đòn kép khi cổ phiếu và trái phiếu cùng giảm (năm `2022`), hoặc bật/tắt quá nhạy gây tốn phí (*whipsaw*) như mô hình Markov ẩn (HMM) cũ. **Mô hình Bước Nhảy Thống Kê (*Statistical Jump Model — SJM*)** gán thêm một "hình phạt đổi trạng thái" (`lambda`), buộc hệ thống chỉ chuyển trạng thái (Êm dịu <-> Căng thẳng) cho **từng tài sản riêng lẻ** khi xu hướng rủi ro đổi thật sự bền vững, rồi mới chia tỷ trọng bằng **Tối Ưu Cụm Lồng Nhau (*Nested Clustered Optimization — NCO*)** để tránh sai số ma trận hiệp phương sai.
- **Điểm mới so với Lab cũ của Naqex:** Khác với `S3B` dùng `SMA200` cứng và `Lab #4` dùng công tắc chung `VIX`/`HYG`, `SJM` nhận diện chế độ **riêng cho từng nhóm tài sản** (ví dụ nhận biết trái phiếu `TLT` vào chế độ gấu năm `2022` mà không làm tê liệt hàng hóa `DBC` hay đồng `UUP`).
- **Nguồn chính thức đã xác minh (`untrusted_external_data: true`):**
  1. (`T1`, EN, 2024, `37` trích dẫn) Yizhan Shu, Chenyu Yu, John M. Mulvey — *Downside risk reduction using regime-switching signals: a statistical jump model approach*, *Journal of Asset Management*: `https://doi.org/10.1057/s41260-024-00376-x`
  2. (`T1`, EN, 2024, `10` trích dẫn) Yizhan Shu, Chenyu Yu, John M. Mulvey — *Dynamic Asset Allocation with Asset-Specific Regime Forecasts*, *arXiv*: `https://doi.org/10.48550/arxiv.2406.09578`
  3. (`T1`, CN-authors/EN, 2025, `6` trích dẫn) Xianglong Li, Jianjun Chen, Xiangxing Tao, Yanting Ji — *Regime-Switching Asset Allocation Using a Framework Combing a Jump Model and Model Predictive Control*, *Mathematics*: `https://doi.org/10.3390/math13172837`
  4. (`T1`, EN, 2026) Supriadi Supriadi, Bambang Siswoyo — *Market Regime-Based Multi-Asset Portfolio Optimization Using Nested Clustered Optimization for Tactical Asset Allocation*, *arXiv*: `https://doi.org/10.48550/arxiv.2610.27751`
  5. (`T1`, Open-Source) `Yizhan-Oliver-Shu/jump-models` (`Apache-2.0`, `173` sao): `https://github.com/Yizhan-Oliver-Shu/jump-models` · `skfolio/skfolio` (`BSD-3-Clause`, `2.678` sao): `https://github.com/skfolio/skfolio` · `dcajasn/Riskfolio-Lib` (`BSD-3-Clause`, `4.626` sao): `https://github.com/dcajasn/Riskfolio-Lib`
- **Tuyên bố bài báo vs Thực tế Naqex:** Các bài báo gốc ghi nhận `SJM` giảm sụt giảm đuôi và giảm tần suất xoay vòng so với HMM chuẩn; **tuy nhiên chưa có bằng chứng cục bộ trên bộ dữ liệu `.runtime/etf40-cache/` cắt tại `<= 2024-12-31`** xem `SJM + NCO` có thắng nổi `M5_VOL_PARITY_TREND_GUARD` hay `L7_C3_MM17_VAR_MACRO_CORE` hay không.
- **Cổng bác bỏ đăng ký trước (`<X13_WORKER>`):** Tập khám phá `2006–2018` -> kiểm mù Dev `2019–2024` (`0` dòng `2025+`), tối đa `M = 8` biến thể; **GIẾT NGAY** nếu `PBO > 0,50`, `DSR < 0,50`, `Sharpe Cl.B < 0,75`, `Hansen SPA p > 0,10`, vòng quay `> 10x/năm`, lỗ ròng ở phí `2x` (`10 bps/chiều`), `|r(PORT_7E)| >= 0,15`, hoặc sụt giảm năm `2022` tệ hơn `-13,59%`.

---

### 4.2. `FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR` — Phần Bù Biến Động `VIX/VIX3M` Kết Hợp Quản Trị Biến Động Đa Yếu Tố Có Vùng Đệm

- **Giải thích dễ hiểu (bản chất kinh tế):** Các quỹ lớn thường xuyên mua quyền chọn phòng vệ sập thị trường nên biến động hàm ý (`VIX`) đa số thời gian cao hơn biến động thực tế và thấp hơn kỳ hạn 3 tháng (`VIX < VIX3M`, gọi là *Contango*). Kết hợp thước đo **hướng về tương lai** từ độ dốc `VIX/VIX3M` với thước đo **biến động thực tế trễ** trên rổ yếu tố cổ phiếu (`MTUM`, `QUAL`, `USMV`, `VTV`, `SPY`, `QQQ`) giúp giảm rủi ro sớm hơn khi thị trường sắp gãy, thay vì đợi biến động thực tế tăng vọt mới rút vốn.
- **Điểm mới so với Lab #4 & Lab #7:** `Lab #4` (`E40_VRP_VOL_CARRY`) bị vòng quay quá cao (`42,56x/năm`) và sập `-17,02%` năm `2022` do chuyển mù sang trái phiếu dài hạn `TLT` lúc lãi suất tăng sốc; `Lab #7` (`L7_C3`) chỉ dùng phương sai thực tế nhìn lại quá khứ. Cơ chế mới bổ sung **vùng đệm chết (*L1 deadband*)** để cắt vòng quay xuống `<= 15x/năm` và đổi hầm trú ẩn khi căng thẳng sang **tiền mặt/T-Bill ngắn hạn (`BIL`/`SHY`) + Vàng (`GLD > SMA200`)** thay vì ôm trái phiếu dài hạn `TLT` khi xu hướng trái phiếu gãy.
- **Nguồn chính thức đã xác minh (`untrusted_external_data: true`):**
  1. (`T1`, EN, 2024, `82` trích dẫn) Victor DeMiguel, Alberto Martín-Utrera, Raman Uppal — *A Multifactor Perspective on Volatility-Managed Portfolios*, *The Journal of Finance*: `https://doi.org/10.1111/jofi.13395`
  2. (`T1`, EN, 2024/2025) Christoph Reschenhofer, Josef Zechner — *Volatility Managed Multi-Factor Portfolios*, *SSRN / Journal of Investment Management (2025)*: `https://doi.org/10.2139/ssrn.4005163`
  3. (`T1`, EN, 2026) Chun Hin Liu — *Adaptive Portfolio Positioning under Market Volatility: A Forward-Looking Regime-Switching Approach Using the VIX Term Structure*, *SSRN*: `https://doi.org/10.2139/ssrn.7249698`
  4. (`T1`, EN, 2017 nền tảng, `726` trích dẫn) Alan Moreira, Tyler Muir — *Volatility-Managed Portfolios*, *The Journal of Finance*: `https://doi.org/10.1111/jofi.12513`
  5. (`T1`, EN, 2026 — **Bằng chứng phản biện**) Nishath Akula — *One Premium in Four Disguises: Volatility Arbitrage, Implied Correlation and the (Apparent) Decay of the Dispersion Premium, 2006–2026*, *Zenodo*: `https://doi.org/10.5281/zenodo.23355138`
- **Tuyên bố bài báo vs Thực tế Naqex:** Các bài báo *JF 2024* và *JOIM 2025* cho thấy quản trị biến động đa yếu tố có lợi ích kinh tế sau phí cao hơn đơn yếu tố; ngược lại, nghiên cứu phản biện `Akula (2026)` cảnh báo nhiều biến thể lịch VIX thực chất chỉ là "VRP đội lốt". Do đó **chưa có bằng chứng cục bộ** cho tới khi `<X13_WORKER>` kiểm định đối đầu trực tiếp với chuẩn `SPY` quản trị biến động đơn giản bằng `Hansen SPA`.
- **Cổng bác bỏ đăng ký trước (`<X13_WORKER>`):** Tập `2008–2018` -> mù Dev `2019–2024`, tối đa `M = 8`, khóa cứng tỷ trọng `IDX_VIX = IDX_VIX3M = 0,0` và cấm điền ngược trước ngày niêm yết (`USMV` 2011, `MTUM/QUAL` 2013); **GIẾT NGAY** nếu vòng quay `> 15x/năm`, sụt giảm `2022 > 10%`, `Sharpe Cl.B < 0,85`, `PBO > 0,50`, `DSR < 0,50`, `BE < 3,0x`, hoặc `|r(PORT_7E)| >= 0,15`.

---

### 4.3. `FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM` — Chênh Lệch Phí Funding & Basis Hợp Đồng Vĩnh Viễn Crypto Kết Hợp Động Lượng Chậm (`>= 4H/D1`)

- **Giải thích dễ hiểu (bản chất kinh tế):** Hợp đồng vĩnh viễn Crypto (*Perpetual Futures*) không có ngày đáo hạn nên dùng **phí funding 8 giờ** để kéo giá về gần giá giao ngay (*Spot*). Khi đám đông dùng đòn bẩy mua quá mức, bên mua phải trả phí funding liên tục cho bên bán, nhưng khi thanh khoản nhà tạo lập co hẹp, hiện tượng lệch basis và nén funding xảy ra theo từng đồng tiền riêng biệt. Thay vì chỉ chạy một kiểu thuần ôm funding (như `Lab #9`) hay thuần đuổi giá Spot (như `S2`), cơ chế mới kết hợp **xếp hạng độ đông đúc của funding + độ lệch basis Spot–Perp + động lượng chậm khung ngày/tuần** trên rổ `20` hợp đồng thanh khoản nhất.
- **Điểm mới so với `S2` & `Lab #9`:** `Lab #9` đã chứng minh cứng rằng xoay vòng altcoin kiểu Taker tần suất cao (`7–17x/năm`) bị phí `23 bps/chiều` và funding bị nén giai đoạn `2023–2024` tiêu diệt sạch, đồng thời phát hiện bẫy thanh lý *Isolated Margin* khi altcoin bật `+100%..+405%` trong 1 ngày (`DOGE`, `XLM`, `TRX`). Vì vậy, cơ chế tiền duyên này khóa chặt: **tái cân bằng tối đa `<= 6x/năm` (`>= D1`), chỉ dùng *Cross-Margin* đệm `2,0x–2,5x`, tuyệt đối `0` giao dịch `< 4H` Taker**, và áp nguyên trần rủi ro sàn tập trung **`CEX <= 25%`**.
- **Nguồn chính thức đã xác minh (`untrusted_external_data: true`):**
  1. (`T1`, EN, 2025, `12` trích dẫn) Jae Hyun Kim, Hyungbin Park — *Designing funding rates for perpetual futures in cryptocurrency markets*, *arXiv*: `https://doi.org/10.48550/arxiv.2506.08573`
  2. (`T1`, EN, 2026) Oleg Arefev — *Cross-Sectional Momentum in Cryptocurrency: A Net-of-Costs Replication on Tradable Binance Perpetuals (2020–2026)*, *SSRN*: `https://doi.org/10.2139/ssrn.7404139`
  3. (`T1`, EN, 2026) Helvin Shek — *Conditional Arbitrage Capacity: Evidence from Crypto Perpetual Funding Rates*, *SSRN*: `https://doi.org/10.2139/ssrn.7520320`
  4. (`T1`, EN, 2022/sửa đổi 2024–2026, `66` trích dẫn) Songrun He, Asaf Manela, Omri Ross, Victor von Wachter — *Fundamentals of Perpetual Futures*, *SSRN / arXiv*: `https://doi.org/10.2139/ssrn.4301150`
  5. (`T1`, EN, 2026) Tony Lau — *Replication package for "The Funding Carry and a Cross-Venue Spread on Perpetual Futures"*, *Zenodo*: `https://doi.org/10.5281/zenodo.20938722`
  6. (`T1`, Open-Source EN/CN) `PietroC21/Crypto-PerpetualFutures` (`MIT`): `https://github.com/PietroC21/Crypto-PerpetualFutures` · `NovaQuantHub/Nova_funding_hub` (CN): `https://github.com/NovaQuantHub/Nova_funding_hub`
  7. (`T2`, RU, 2026) Habr RU — *Что такое фандинг арбитраж и как сделать автоматический поиск спредов* (cảnh báo thực chiến về trượt phí, đảo dấu funding và bẫy thanh lý): `https://habr.com/ru/articles/983154/`
- **Tuyên bố bài báo vs Thực tế Naqex:** Tài liệu `2025–2026` chỉ ra cả cơ hội từ giới hạn vốn arb lẫn sự nén mạnh của lợi suất funding. **Chưa có bằng chứng cục bộ** xem việc ghép tín hiệu funding–basis vào động lượng chậm có vượt được cặp hiện hữu (`S2` + `S3A v1 BTC+ETH`) sau phí `2x` trên đoạn Dev `<= 2024-12-31` hay không.
- **Cổng bác bỏ đăng ký trước (`<X13_WORKER>`):** Tập `2020–2022` -> mù Dev `2023–2024` (`0` dữ liệu `2025+`), phí mô phỏng chặt `1x = 23 bps/chiều` + phạt sốc thoát lệnh basis, stress `2x = 46 bps/chiều`, tối đa `M = 8`; **GIẾT NGAY** nếu vòng quay `> 6,0x/năm`, có bất kỳ `>= 1` sự kiện thanh lý *Cross-Margin*, âm ròng ở phí `2x`, `Sharpe Cl.B < 0,80`, `PBO > 0,50`, `DSR < 0,50`, hoặc `|r(PORT_7E)| >= 0,15`.

---

### 4.4. `FRONTIER_04_MONTH_END_PENSION_REBAL_AND_DURATION_FLOW` — Dòng Tiền Tái Cân Bằng Cuối Tháng Của Quỹ Hưu Trí & Chỉ Số Trái Phiếu

- **Giải thích dễ hiểu (bản chất kinh tế):** Hàng nghìn tỷ USD tài sản của quỹ hưu trí, quỹ mục tiêu (`60/40`) và quỹ chỉ số trái phiếu chính phủ buộc phải tái cân bằng đúng theo lịch cố định cuối tháng để giữ đúng tỷ lệ cổ phiếu/trái phiếu và kỳ hạn trái phiếu, đồng thời giải ngân lương hưu/tiền đóng góp đầu tháng mới. Khi cổ phiếu tăng mạnh hơn trái phiếu trong tháng, các quỹ này buộc phải **bán cổ phiếu và mua trái phiếu** quanh những ngày cuối tháng bất kể tin tức cơ bản — sau đó áp lực bán tan biến ở cửa sổ giao tháng (`T-1..T+3`).
- **Điểm mới so với mọi Lab cũ của Naqex:** Naqex **chưa từng chạy** bất kỳ kiểm định thực nghiệm nào cho dòng chảy tái cân bằng cổ phiếu–trái phiếu cuối tháng (`SPY/QQQ` vs `TLT/IEF`) trên `.runtime/etf40-cache/`. Ưu điểm lớn nhất là chiến lược chỉ giữ vị thế rủi ro khoảng **`25%–30%` số ngày giao dịch trong năm** (phần thời gian còn lại nằm tiền mặt `BIL/SHY`), nên cực kỳ sạch rủi ro đuôi và có kỳ vọng tương quan sát `0` với cả `PORT_7E` lẫn các nhánh ETF xu hướng liên tục (`S3B`/`S4`).
- **Nguồn chính thức đã xác minh (`untrusted_external_data: true`):**
  1. (`T1`, EN, 2025, `36` trích dẫn) Campbell R. Harvey, Michele Mazzoleni, Alessandro Melone — *The Unintended Consequences of Rebalancing*, *NBER Working Paper w33554*: `https://doi.org/10.3386/w33554` *(Tóm tắt gốc ghi nhận khi cổ phiếu vượt tỷ trọng mục tiêu, áp lực bán cổ phiếu/mua trái phiếu của quỹ đi kèm mức giảm trung bình khoảng `17 bps` của cổ phiếu vào ngày kế tiếp).*
  2. (`T1`, EN, 2026) Aleksandar Andonov, Kristy Jansen, Joshua Rauh — *When Cash Flows Turn Negative: Liquidity-Driven Selling by Pension Funds*, *NBER Working Paper w35896*: `https://doi.org/10.3386/w35896`
  3. (`T1`, EN, 2026) Amar Soebhag, Patrick Verwijmeren, Fabio Martinetti — *Buying Duration: Index Rebalancing and Price Pressure in Government Bond Markets*, *SSRN*: `https://doi.org/10.2139/ssrn.7601879`
  4. (`T1`, EN, 2019/2020 nền tảng, `75` trích dẫn) Erkko M. Etula, Kalle Rinne, Matti Suominen, Lauri Vaittinen — *Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs*, *Review of Financial Studies*: `https://doi.org/10.1093/rfs/hhz054`
- **Tuyên bố bài báo vs Thực tế Naqex:** Các công trình NBER `2025–2026` và *RFS* xác nhận cơ chế áp lực giá mang tính cơ học rất mạnh; nhưng chính các bài báo này cũng cảnh báo nguy cơ các quỹ lớn bắt đầu **ngẫu nhiên hóa ngày tái cân bằng** để né bị đón đầu (*front-running*). Do đó cần kiểm định mù nghiêm ngặt trên đoạn `2019–2024` để xem hiệu ứng còn sống sót sau phí `2x` (`10 bps/chiều`) và giả định `0%` lãi tiền mặt hay không.
- **Cổng bác bỏ đăng ký trước (`<X13_WORKER>`):** Tập `2006–2018` -> mù Dev `2019–2024`, tối đa `M = 6`, so chuẩn trực tiếp với cửa sổ ngày ngẫu nhiên cùng thời lượng bằng `Hansen SPA`; **GIẾT NGAY** nếu `Sharpe Cl.B < 0,65`, `PBO > 0,50`, `DSR < 0,50`, `Hansen SPA p > 0,10`, vòng quay `> 24x/năm`, âm ở phí `2x` (khi lãi tiền mặt = `0%`), `|r(PORT_7E)| >= 0,15`, hoặc `|r(S4_ETF40)| >= 0,45`.

---

### 4.5. `FRONTIER_05_SECTOR_CORR_DISPERSION_NEUTRAL_SPREAD` — Phân Tán 10 Ngành Mỹ Trung Lập Thị Trường (Lọc Theo Tương Quan Đa Tỷ Lệ & Đuôi Phiên Đêm/Ngày)

- **Giải thích dễ hiểu (bản chất kinh tế):** Khi thị trường hoảng loạn, cả 10 ngành kinh tế Mỹ (`XLB..XLY, XLRE`) cùng giảm đồng loạt (tương quan cặp vọt lên sát `1,0`) khiến chọn ngành mạnh/yếu mất tác dụng. Ngược lại, khi **tương quan trung bình giữa 10 ngành thấp và độ phân tán lợi suất cao**, dòng vốn luân chuyển rõ rệt giữa ngành dẫn dắt và ngành tụt hậu. Chiến lược mở vị thế **trung lập đồng USD (Mua Top-3 ngành mạnh nhất, Bán khống Bottom-3 ngành yếu nhất)** chỉ tái cân bằng `2–4` tuần/lần, tự động **tắt về tiền mặt** khi tương quan cặp vượt phân vị thứ `75` hoặc khi bộ lọc bất đối xứng đuôi phiên đêm/ngày báo căng thẳng.
- **Điểm mới so với Lab #4 & Lab #7:** Khác với `E40_XSEC_SECTOR_MOM_TOP4` (mua thuần nên có tương quan `+0,51` với `S3B` và dính beta cổ phiếu) và tránh hoàn toàn bẫy phí của `Lab #7` (`L7_A1` mua đóng/bán mở mỗi ngày `300x/năm` bị khai tử), cơ chế **trung lập thị trường có cổng tương quan** nhắm trực tiếp vào độ tương quan sát `0` với **cả `PORT_7E` lẫn `S3B/S4`**.
- **Nguồn chính thức đã xác minh (`untrusted_external_data: true`):**
  1. (`T1`, EN, 2024) Marina Dolfin, George Kapetanios, Leone Leonida, Jose De Leon Miranda — *Investor behavior and multiscale cross-correlations: Unveiling regime shifts in global financial markets*, *arXiv*: `https://doi.org/10.48550/arxiv.2408.17200`
  2. (`T1`, EN, 2020/2023, `35` trích dẫn) Oleg Bondarenko, Carole Bernard — *Option-Implied Dependence and Correlation Risk Premium*, *Journal of Financial and Quantitative Analysis*: `https://doi.org/10.1017/s0022109023000960`
  3. (`T1`, EN, 2026 — **Bằng chứng phản biện**) Nishath Akula — *One Premium in Four Disguises: Volatility Arbitrage, Implied Correlation and the (Apparent) Decay of the Dispersion Premium, 2006–2026*, *Zenodo*: `https://doi.org/10.5281/zenodo.23355138`
  4. (`T1`, EN, 2025) Paul Glasserman, Kriste Krstovski, Paul Laliberte, Harry Mamaysky — *Does Overnight News Explain Overnight Returns?*, *arXiv / SSRN*: `https://doi.org/10.48550/arxiv.2507.04481`
  5. (`T1`, EN, 2026) Xinxian Chen, Peter Reinhard Hansen, Chen Tong — *Split-Session Cluster GARCH for Overnight and Intraday Returns: The Role of Tail Heterogeneity*, *arXiv*: `https://doi.org/10.48550/arxiv.2607.03669`
- **Tuyên bố bài báo vs Thực tế Naqex:** Nghiên cứu `2024–2026` chỉ ra cấu trúc khối tương quan ngành và dị biệt đuôi đêm/ngày là tín hiệu chế độ rõ nét, nhưng `Akula (2026)` cảnh báo phần bù phân tán thuần có thể suy giảm sau phí. Đặc biệt, chân bán khống ETF chịu thêm **phí mượn cổ phiếu (`50 bps/năm`, stress `2x = 100 bps/năm`)**, nên chỉ được giữ nếu sống sót trọn vẹn sau mọi chi phí thực tế.
- **Cổng bác bỏ đăng ký trước (`<X13_WORKER>`):** Tập `2006–2018` -> mù Dev `2019–2024`, tối đa `M = 8`, cấm gán tỷ trọng cho `XLRE` trước tháng `10/2015`; **GIẾT NGAY** nếu `Sharpe Cl.B < 0,60`, `PBO > 0,50`, `DSR < 0,50`, `Hansen SPA p > 0,10`, lỗ ở phí `2x` (`10 bps/chiều + 100 bps/năm` phí mượn short), `|beta(SPY)| > 0,20`, `|r(S4_ETF40)| >= 0,30`, hoặc `|r(PORT_7E)| >= 0,15`.

---

## 5. Tổng Hợp Quét Đa Ngôn Ngữ (`EN / CN / RU / VI`) & Kiểm Toán Giấy Phép Mã Nguồn Mở

| Kênh / Ngôn Ngữ | Điểm Đóng Góp Thực Chất Cho Đợt Săn R3 | Ghi Chú Kiểm Chứng & Độ Tin Cậy |
|---|---|---|
| **Tiếng Anh (`EN`)** — `arXiv`, `OpenAlex`, `NBER`, `JF`, `RFS`, `JFQA`, `SSRN`, `Zenodo` | Cung cấp toàn bộ trục học thuật `2024–2026`: SJM (`JAM 2024`), Multifactor Vol-Managed (`JF 2024`), Rebalancing Impact (`NBER 2025/2026`), Perp Funding BSDE & Capacity (`arXiv 2025 / SSRN 2026`), Split-Session Tail Heterogeneity (`arXiv 2025/2026`). | `T1_PRIMARY_OFFICIAL`; `100%` DOI và danh sách tác giả xác minh trực tiếp qua OpenAlex API. |
| **Tiếng Trung (`CN`)** — Tác giả/tài liệu `Mathematics 2025`, `GitHub` | Nghiên cứu kết hợp `Jump Model + Model Predictive Control` (`doi:10.3390/math13172837`), kinh nghiệm kết hợp Risk Parity + Trend để vượt bẫy cổ–trái phiếu cùng giảm, và kiến trúc giám sát funding đa sàn (`NovaQuantHub/Nova_funding_hub`). | `T1` (bài báo bình duyệt) & `T1/T2` (mã nguồn mở); giữ nguyên quy tắc không thực thi mã bên ngoài. |
| **Tiếng Nga (`RU`)** — `Habr` Engineering | Góc nhìn kỹ sư thực chiến về bẫy độ trễ, phí hoa hồng, trượt basis và đảo dấu đột ngột khi săn chênh lệch funding (`https://habr.com/ru/articles/983154/`, `https://habr.com/ru/articles/972036/`). | `T2_TECHNICAL_COMMUNITY`; dùng để bổ sung quy tắc cắt lỗ/phí vào cổng bác bỏ chứ không lấy làm bằng chứng lợi nhuận. |
| **Tiếng Việt (`VI`)** — OpenAlex & Web VN | Tài liệu công khai tiếng Việt `2024–2026` chủ yếu dừng ở giáo trình Markowitz/MPT, phân bổ đa tài sản tổng quát và quản trị rủi ro doanh nghiệp, chưa có công trình alpha định lượng thực nghiệm chuyên sâu. | `T2/T3`; xác nhận chiến lược đúng của Naqex là săn ý tưởng gốc từ nguồn `EN/CN/RU` hạng `T1` rồi Việt hóa hoàn toàn quy trình vận hành. |
| **Kiểm toán giấy phép thư viện tham khảo** | `jump-models` (`Apache-2.0`), `skfolio` (`BSD-3-Clause`), `Riskfolio-Lib` (`BSD-3-Clause`), `Crypto-PerpetualFutures` (`MIT`) -> **`0` mã GPL/AGPL/CC-BY-NC**, an toàn tuyệt đối để tham khảo thuật toán (nhưng **chưa cài mới** vào `.runtime` khi chưa được duyệt). | Khớp chuẩn kiểm toán giấy phép [ECOSYSTEM-SECURITY-LICENSE-AUDIT-20261127.md](ECOSYSTEM-SECURITY-LICENSE-AUDIT-20261127.md). |

---

## 6. Thứ Tự Ưu Tiên Kiểm Định Trên `<X13_WORKER>` (`0 VND`, Chỉ Dev `<= 2024-12-31`)

Tất cả 5 ứng viên đều có `x13_ready: true` (dùng hoàn toàn kho `.parquet` cục bộ, `0` bí mật, `0` dòng `2025+`, bắt buộc chạy `quant_core.holdout_guard.enforce_pre_holdout_dates` an toàn dưới `python -O`, và cắm sạc AC `ACLineStatus == 1` trên `<X13_WORKER>`):

1. **Ưu tiên 1 (`~4` phút chạy):** `FRONTIER_04_MONTH_END_PENSION_REBAL_AND_DURATION_FLOW` — Cơ chế mới hoàn toàn chưa từng kiểm thử tại Naqex, kỳ vọng tương quan sát `0` với cả `PORT_7E` lẫn `S3B/S4`, dễ lập trình trắng sạch trong `< 120` dòng Python.
2. **Ưu tiên 2 (`~6` phút chạy):** `FRONTIER_05_SECTOR_CORR_DISPERSION_NEUTRAL_SPREAD` — Trung lập thị trường (`beta ~ 0`), kiểm chứng thẳng khả năng tạo nguồn lợi nhuận lệch pha ngay cả trong năm thị trường đi ngang hoặc lạm phát `2022`.
3. **Ưu tiên 3 (`~5` phút chạy):** `FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR` — Nâng cấp trực diện 2 điểm yếu đã biết của `Lab #4` (giảm vòng quay `42,5x -> <= 15x` và cắt lỗ `2022` bằng `BIL/SHY`).
4. **Ưu tiên 4 (`~8` phút chạy):** `FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY` — Thử nghiệm thay `SMA200` thô bằng `SJM + NCO` theo từng tài sản để đối chứng trực tiếp với `S3B`/`L7_C3`.
5. **Ưu tiên 5 (`~6` phút chạy):** `FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM` — Chỉ ưu tiên triển khai thực địa khi vốn riêng `>= 25.000 USD` (`CEX <= 25%`), nhưng vẫn kiểm định sớm trên Dev `2020–2024` để đối chứng với `S2` và `S3A v1`.

---

**Hành động kế tiếp (`< 2` phút):** Đưa tệp hợp đồng [frontier_alpha_candidates.json](../../tooling/automation/configs/frontier_alpha_candidates.json) vào hàng đợi kiểm định offline Dev (`<= 2024-12-31`) của `<X13_WORKER>`, bắt đầu bằng **Ưu tiên 1 (`FRONTIER_04`)** để đo `DSR + PBO + CPCV + Hansen SPA + |r(PORT_7E)|` và chỉ nâng hạng bất kỳ ứng viên nào vượt sạch `100%` cổng bác bỏ đăng ký trước.
