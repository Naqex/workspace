---
doc_type: plan
domain: strategy-and-operations
status: active
updated_utc: 2026-11-24
order_send_count: 0
holdout_rows_analysed: 0
owner: "knowledge/owner/PROFILE.md"
---

# Kế Hoạch Tổng Thể Chạm Chuẩn "Chuyên Gia Độc Lập Bậc Nhất (Top 1%)"

> **Mục đích tài liệu:** Đây là bản kế hoạch hành động duy nhất của Naqex để đưa hệ thống từ mức hiện tại (đang chạy thử 1 nhánh FX/Chỉ số trên `naqex-node1`, chưa có lịch sử rút lãi thật) tiến sát cảnh giới **chuyên gia giao dịch tự động độc lập bậc nhất (Top 1% Solo Quant)** — hoàn toàn **thực tế, đo bằng tiền lời ròng sau mọi chi phí, và lấy tiền lời tự nuôi hạ tầng**.
>
> **Chế độ an toàn bất biến:** Không tự động gửi lệnh tiền thật (`OrderSend = 0` trên mọi công cụ nghiên cứu), giữ niêm phong tuyệt đối tập dữ liệu kiểm tra mật `Holdout 2025+` ([NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json)) cho thế hệ chiến lược v2, và luôn quy đổi rủi ro song song theo `%`, `USD` và `triệu VND` (`25.500 VND/USD`).

---

## Phần 1 — Đích Đến Lượng Hóa (Đo Bằng Tiền Lời Ròng, Không Ảo Tưởng)

### 1.1. Bảng Đối Chiếu: Hiện Tại -> Đích Đến Top 1% Độc Lập

Mục tiêu được đặt ở mức **Top 1% trader độc lập dùng hệ thống tự động + AI** — đủ cao để đứng nhóm dẫn đầu thế giới thực, nhưng tuyệt đối không chạy theo bánh vẽ X5/X10 tài khoản hay chi phí hàng triệu USD như quỹ tỷ đô.

| Chỉ số cốt lõi | Vị trí hiện tại của Naqex *(đã kiểm chứng)* | **Mục tiêu Top 1% Độc Lập** *(Đích đến thực tế)* | Ghi chú cách đo trung thực |
|---|---|---|---|
| **Độ đều lợi nhuận thực chiến** *(lãi ròng chia cho độ rung lắc — càng cao càng êm)* | `~1,1 – 1,5` *(riêng bộ 8 bot FX)* · **`~2,25`** *(bản vẽ ghép 4 nhánh trên giấy)* | **`2,0 – 3,0`** *(chạy tiền thật sau đủ mọi loại phí và trượt giá)* | Đo trên lịch sử tiền thật tối thiểu `12` tháng, không cộng gộp dữ liệu mô phỏng |
| **Lãi năm / Sụt giảm sâu nhất** *(khi đánh mức an toàn `1×`)* | `+8,3% .. +12,7%/năm` · sụt sâu nhất `~6,5% – 9,1%` | **`+18% .. +30%/năm`** · sụt sâu nhất **`6% – 8%`** | Mức tăng trưởng phải đến từ **ghép thêm nguồn tiền độc lập**, không phải vặn đòn bẩy liều |
| **Tốc độ đậu quỹ 2 vòng (an toàn)** | Trung vị **`4,6 – 5,9 tháng`** *(3 tháng: `18%–30%`, 6 tháng: `49%–62%`)* | Trung vị **`1,5 – 3,0 tháng`** *(3 tháng: `50%–70%`, 6 tháng: `85%–95%`)* | Rút ngắn bằng cách thêm chiến lược khác kiểu phá vỡ + chạy song song nhiều gói quỹ |
| **Vùng rớt vé thi & Hiệu quả đồng phí** | Đã ở đúng vùng đỉnh: rớt `22%–33%`, lời **`+3,25× .. +7,17×`** tiền vé | Giữ vùng rớt vòng thi **`22% – 35%`**, lời **`>= +2,5×`** tiền vé; **cháy tài khoản thật (Funded) `< 1%`** | Không chạy theo rớt ít nhất (`2%–5%`), cũng không đánh liều rớt `> 40%` |
| **Số nguồn kiếm tiền không dính nhau** | `1` nhánh đang chạy thử thật + `3` nhánh sẵn sàng trên giấy | **`4 – 6` nhánh độc lập thật sự** *(nhiều thị trường, cả thuận xu hướng lẫn đảo chiều)* | Tương quan giữa các nhánh mục tiêu **`r < 0,25`** |
| **Chi phí hạ tầng & dữ liệu** | Gần như **`0 USD/tháng`** *(máy nhà `naqex-node1` + gói Heroku Student)* | **`30 – 150 USD/tháng`** *(VPS sát sàn + dữ liệu sạch — trích `<= 10%` lãi ròng)* | **Nguyên tắc sắt:** Chỉ nâng cấp khi đã có tiền lời thật tự trả |

---

### 1.2. Nguyên Tắc Toán Học Cốt Lõi: Tối Ưu "Tiền Lời Ròng Kỳ Vọng (EV)"

Mọi thông số tỷ lệ đậu, tỷ lệ rớt hay mức rủi ro trong dự án này **không bao giờ đánh giá cảm tính** kiểu "càng ít rớt càng tốt" hay "càng nhanh càng tốt". Mọi quyết định phải căn theo **2 thước đo**:
1. **Tổng tiền lời ròng sau 2 năm** *(đã trừ sạch tiền mua mọi vé thi lại)*.
2. **Mỗi `1 USD` phí mua vé đẻ được bao nhiêu `USD` lãi ròng** *(hiệu quả đồng vốn)*.

Kết quả thực đo trên `10.000` kịch bản của chính bộ 8 bot nhà mình ([PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md](research/PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md)) xác nhận 4 vùng rõ ràng:

| Vùng rủi ro ở Vòng Thi | Tỷ lệ rớt vé đầu | Tốc độ đậu 2 vòng | Lãi ròng 2 năm (FTMO 10k) | Lãi ròng 2 năm (The5ers 5k) | Phán quyết cho Naqex |
|---|---|---|---:|---:|---|
| **Quá nhát** *(2,5× – 3,25×)* | `2% – 9%` | Rất chậm (`7,0 – 8,2 tháng`) | `+577 – +642 USD` | `+284 – +312 USD` | **BỎ** — ít rớt nhất nhưng mất oan 3–4 tháng tiền thưởng |
| **Cân bằng đẹp (`P1_Balanced`)** *(4,0×)* | **`22% – 24%`** | Vừa (`5,5 – 5,9 tháng`) | **`+712 USD`** *(3,25× phí)* | **`+348 USD`** *(7,17× phí)* | **CHỌN LÀM MẶC ĐỊNH** cho vé đầu và vốn mỏng |
| **Đỉnh lời toán học (`ProfitLock / Sprint`)** *(4,5× – 5,0×)* | **`28% – 35%`** | Nhanh (`4,0 – 5,0 tháng`) | **`+738 – +749 USD`** *(đỉnh)* | **`+368 – +377 USD`** *(đỉnh)* | **CHỌN KHI ĐỦ QUỸ DỰ PHÒNG `3–5` VÉ** |
| **Quá liều** *(>= 5,75×)* | `> 40%` | Rất nhanh (`3,6 – 4,0 tháng`) | Tụt còn `+717 USD` | Đi ngang `+374 USD` | **CẤM** — mua lại quá nhiều vé, ăn ngược vào lãi |

> **Quy tắc 2 số ga bắt buộc:** Ở **Vòng Thi**, đánh đúng vùng tối ưu **`22% – 35%`** rớt vé đầu (vì thua tối đa chỉ mất tiền mua vé). Nhưng **ngay giây phút nhận tài khoản thật (Funded)**, hệ thống tự động hạ ga cứng về **`1,0×` (`Funded_Safe`)** để khóa nguy cơ cháy tài khoản thật xuống **`< 1%`** (`~0,0% – 0,3%` trên mô phỏng) và rút thưởng bền vững qua nhiều kỳ.

---

## Phần 2 — Kế Hoạch Hành Động Toàn Diện Theo 6 Khía Cạnh

Để tiệm cận Top 1% độc lập mà không vấp phải sai lầm phổ biến (cố vắt kiệt bot cũ, cháy tài khoản vì lỗi vận hành, hay đốt tiền mua máy chủ quá sớm), kế hoạch được chia thành **6 khía cạnh song song**, mỗi khía cạnh có mục tiêu và hàng rào bảo vệ riêng.

### Khía Cạnh 1 — Chiến Lược Giao Dịch & Đa Dạng Hóa Nguồn Kiếm Tiền *(Nút thắt lớn nhất)*

Bộ 8 bot FX hiện tại đã gần chạm trần của riêng kiểu **"đánh phá vỡ trong ngày trên tiền tệ"**. Chìa khóa duy nhất để tăng tốc độ đậu từ `~5 tháng` xuống `2–3 tháng` và nâng độ đều lên `2,0–3,0` là **ghép thêm các nguồn tiền hoạt động theo cơ chế khác hẳn**.

1. **Giữ nguyên nòng cốt #1 trên tài khoản quỹ (`A1_V1_LIVE8`) & Chốt ranh giới khoa học CFD trong ngày:**
   - Nghiên cứu [v1 vs v2](research/PORTFOLIO-V1-VS-V2-ARCHITECTURE-STUDY-20261124.md) đã chứng minh cắt bớt bot yếu đi (`A3_PRUNE_6E`) làm tụt cả lãi lẫn độ an toàn. Đồng thời hai đợt kiểm định quy mô lớn [Lab #11](research/LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.md) (`20` giả thuyết đảo chiều / Vàng / `GER40` / `BTCUSD`) và [Lab #12](research/LAB12-ORTHOGONAL-MOMENTUM-V2-DISCOVERY-20261124.md) (`16` giả thuyết động lượng / nén biến động trên `7` tài sản M1 mới) đều đạt **`0/36` vượt đủ 6 cổng** (phí chênh mua/bán CFD ăn mòn gần hết biên lợi nhuận giao dịch trong ngày — riêng `BTCUSD` CFD ăn tới `12%` khoảng cắt lỗ).
   - **Quyết định chiến lược đã khóa cứng:** **`A1_V1_LIVE8` chính là giới hạn tối ưu (Pareto frontier) đã được chứng minh của nhóm bot CFD `swap = 0` trong ngày.** Do đó **KHÓA DỨT ĐIỂM việc săn thêm bot CFD trong ngày** (tránh lãng phí thời gian và phình số phép thử `M`), giữ nguyên đội hình 8 bot `A1_V1_LIVE8`, giữ dự phòng `A5_V2_ROBUST_TIER_9E_EUR` cho tình huống trượt giá `>= 1,5×`, và **dồn toàn lực tăng tốc sang thang đa quỹ lệch pha (`Khía cạnh 2`) kết hợp các nhánh Sổ Vốn Riêng (`4H–D1` / Maker / ETF IBKR) nơi phí sàn thấp hơn rất nhiều!**
2. **Hướng nghiên cứu v2 duy nhất còn mở (đa ngày `0`-swap / sàn gốc):**
   - Mọi nghiên cứu chiến lược mới về sau chỉ nhắm tới tài sản **sàn giao dịch gốc hoặc giữ nhiều ngày không bị phí Swap âm CFD** (ETF IBKR, Crypto khung `4H–D1`, Crypto Maker `M2B` chờ đủ 30 ngày đo thực địa, và CME Micros khi vốn riêng `>= 100.000 USD`). Vẫn giữ nghiêm tiêu chuẩn `r < 0,25`, đủ `6` cổng phản biện trên `2018–2024`, và **tuyệt đối không chạm tập mật `2025+`** trong lúc tìm kiếm.
3. **Kích hoạt lần lượt 4 nhánh Sổ Vốn Riêng (Own-Book) để đẩy độ đều thực chiến lên `2,0–3,0`:**
   - **Nhánh 2 — Crypto Spot (`S2`, khung `4H+`, không vay đòn bẩy):** Dùng phiên bản đã loại sạch thiên kiến chọn coin trên nhánh `projects/quant-trading:feat/causal-top15-sleeve2` (`264/264` kiểm thử đạt).
   - **Nhánh 3A — Crypto Ăn phí Funding (`S3A`):** Giữ nguyên bản gọn sạch **`BTC + ETH` đệm `2×`** (`KEEP_S3A_V1`), chỉ mở khi mức phí nhận được ròng cao hơn lãi suất tiền gửi phi rủi ro.
   - **Nhánh 3B & 4 — Quỹ chỉ số ETF toàn cầu trên IBKR (`S3B + S4`, `0` phí qua đêm):**
     - Khi vốn riêng **`< 25.000 USD`**: dùng rổ gọn ít lệnh (`L7_TOP2` / `S3B` hoặc cổ phiếu lẻ) để né bẫy phí tối thiểu `0,35 USD/lệnh` của IBKR.
     - Khi vốn riêng **`>= 50.000 USD`**: nâng lên bộ đầy đủ 6 động cơ lô nguyên (`SUPER_ETF_6ENG`).
     - Tiền mặt chưa vào lệnh gửi quỹ trái phiếu ngắn hạn (`SGOV`/`BIL`) ăn lãi đều.
   - **Nhánh điều kiện A — Crypto Làm giá Maker (`M2B`):** **CHỈ MỞ** sau khi máy `naqex-node1` thu thập đủ `30` ngày dữ liệu thật đạt tỷ lệ khớp lệnh **`>= 70%`** và chi phí thực tế **`<= 6,15 bps`** (đang gom mỗi 5 phút).
   - **Nhánh điều kiện B — Hợp đồng tương lai CME (`MES/MNQ`):** Chỉ xét khi sổ vốn riêng đạt **`>= 100.000 USD`** (vì kích thước 1 hợp đồng micro quá lớn so với vốn nhỏ).
4. **Danh sách CẤM TUYỆT ĐỐI *(đã chứng minh thất bại, không lãng phí thời gian làm lại)*:**
   - Không đánh Crypto Spot khung `< 4H` chịu phí mua/bán chủ động (Taker).
   - Không giữ lệnh CFD Vàng/Dầu/Chỉ số qua đêm chịu phí Swap âm trên tài khoản quỹ.
   - Không dùng lưới gồng lỗ (`grid`) hay gấp thếp (`martingale`).
   - Không gắn bộ lọc máy học (ML) chèn lên chiến lược gốc khi độ chính xác dự báo không thắng nổi bản gốc trắng.

---

### Khía Cạnh 2 — Chiến Lược Thi Quỹ Tối Ưu Toán Học & Cỗ Máy Vòng Quay Vốn *(Đã rà soát sâu `2026-11-24`)*

Thay vì ép 1 tài khoản chạy liều để mong đậu trong 1 tháng, ta dùng toán học để **tăng xác suất đậu nhanh mà vẫn giữ rủi ro cháy quỹ phí gần như bằng `0%`**, đồng thời tránh mọi bẫy luật ngầm và thuế phí của từng hạng vé.

1. **Chạy song song nhiều gói lệch pha (`DUAL_2FIRM_STAGGER_42D`) — Đúng quỹ, đúng loại tài khoản:**
   - **Tuyệt đối không mở 2 quỹ cùng 1 ngày bằng chế độ liều (`Sprint`)** vì khi thị trường xấu sẽ kéo rủi ro rớt đồng thời cả 2 tài khoản lên tới `24,1%`.
   - **Trình tự khởi động tối ưu:**
     1. Mở **`The5ers High Stakes 5K` (`~39–52 USD` tùy đợt khuyến mãi; kiểm tra kỹ trên dashboard trước khi mua xem là bản `8%+5%` hay `10%+5%`)** trước ở chế độ `P1_Balanced` (hiệu quả đồng phí cao nhất, vốn thử nhỏ để kiểm chứng khớp lệnh tiền thật).
     2. Chờ lệch pha **`~42` phiên giao dịch (~2 tháng)** rồi mới mở tiếp tài khoản thứ 2 tại **FTMO**.
   - **Chọn `FTMO Swing` làm ưu tiên #1 thay vì `FTMO Standard`:**
     - Trên **FTMO Standard (sau khi Funded)**, nếu giá giật tin đỏ quét trúng **cắt lỗ (SL) hoặc chốt lời (TP) ngay trong khung `±2 phút`**, FTMO vẫn có quyền **xử vi phạm luật tin đỏ và khóa tài khoản**.
     - Trong khi **FTMO Swing (2-Step)** **miễn hoàn toàn luật cấm tin đỏ** cả lúc thi lẫn khi cầm quỹ, và đòn bẩy `1:30` hoàn toàn dư sức cho bộ 8 bot của mình (đang chạy thực tế rất mượt trên `FTMO-Demo 1515343166`). Chỉ chọn `FTMO Standard` khi có khuyến mãi sâu *và* đã hoàn tất đủ 4 bản vá kỹ thuật bên dưới.
   - **Chiến lược nhảy bậc quy mô vé (`Smart-Tier Ladder`) để gấp `2,5×–3,2×` hiệu quả tiền phí *(đã kiểm định 10.000 nhánh)*:**
     - Theo [PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md](research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md) và [TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md](research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md): vé `FTMO 10K` tốn `~168–192 USD` (`~1,7%–1,9%` vốn danh nghĩa, `EV/Phí 3,61×`), trong khi nhảy lên `25K` (`5,83×`), `50K` (`8,93×`), và `100K` (`11,60×`) giúp **nhân hiệu quả đồng phí tới `3,21×`**.
     - Mô phỏng nối thông `60` tháng (`5.000` kịch bản) chứng minh cùng ngân sách phí `1.500 USD` (vốn riêng khởi điểm `0 USD`), thang nhảy bậc **Smart-Tier (`The5ers 5K -> FTMO 25K -> The5ers 20K -> FTMO 50K -> The5ers 60K 4%/8% -> FTMO 100K`)** đẩy Sổ Vốn Riêng trung vị sau 5 năm tăng **`2,52×`** (**`11.085 -> 27.956 USD`**), cắt cháy kép từ `39,0%` xuống **`11,1%`** (`0,00%` cháy quỹ phí); nếu kết hợp vốn mồi lai `25.000 USD` + ngân sách phí `3.000 USD`, Sổ Vốn Riêng trung vị 5 năm đạt **`78.326 USD` (`~1,997 tỷ VND`)**.
     - **Cảnh báo đỏ bậc `The5ers 50K/60K/100K` (`4% ngày / 8% tổng`):** Chạy nhầm preset `5K` sang bậc này làm tỷ lệ cháy ngày lượt đầu vọt lên **`34,7%`** (`OOP95 = 1.316 USD`); bộ cấu hình hiệu chỉnh `4%/8%` (`SYMCAP 1,15%`, `2,75× -> 1,50×`, chặn lỗi tự động trong `verify_deployment_kit.py`) kéo cháy ngày xuống **`6,1%`** và giữ `EV/Phí 8,25×–10,02×`.
   - **Chỉ tập trung 2 quỹ uy tín hàng đầu (`FTMO` + `The5ers`):** Không chạy sang các quỹ nhỏ/mới nổi chỉ vì giá vé rẻ để tránh rủi ro bị từ chối trả thưởng (`R4`).
2. **4 bản vá kỹ thuật bắt buộc — ĐÃ HOÀN TẤT & BIÊN DỊCH SẠCH `9/9 .ex5` (`0` lỗi/cảnh báo), sẵn sàng đồng bộ lên `naqex-node1` khi tài khoản phẳng (`open_positions == 0`):**
   - **[XONG] Vá #1 — Khớp tên mã `NAS100` & bí danh sàn (`Naqex_PropGuard.mqh` + preset The5ers):** Đã bổ sung nhận diện không phân biệt hoa thường cho `US100/NAS100/NDX/USTEC/US500/SPX/US30/XAU/BTC` (`USD`), `GER40/DE40/DAX` (`EUR`), `UK100/FTSE` (`GBP`), và tự gắn đúng biểu đồ `NAS100` trên mọi hồ sơ The5ers.
   - **[XONG] Vá #2 — Lịch tin đỏ `418` dòng đủ 4 đồng tiền `USD/GBP/EUR/JPY` đến hết `2027` & tách vùng đóng trước tin:** Đã dựng bộ lịch xác định (`build_red_news_calendar.py`, khớp 100% nguồn chính thức) phủ đủ FOMC/Press Conf, NFP, CPI, PPI, Retail Sales, Core PCE/GDP, BoE, UK CPI, ECB/Press Conf, BoJ; đồng thời tách cứng vùng đóng trước tin (`-5p` đến `-2p15s`) khỏi khung cấm cứng `±2p15s` (`InpGuardNewsHardBanSec = 135`) trên cả `8` EA.
   - **[XONG] Vá #3 — Siết trần rủi ro 1 mã `SYMCAP` Vòng 1/2 + Bộ bảo vệ `4%/8%` fail-closed:** Đã hạ `SYMCAP` xuống `1,75%` (`P1_Balanced`), `2,00%` (`P1_Sprint`), `1,50%` (`P2_Verify`), `1,00%` (`FreeTrial/Funded`) — kiểm định thực nghiệm chứng minh **cắt cháy ngày lượt đầu FTMO từ `25,5%` xuống còn `4,7%`** (mà `EV/Phí` vẫn tăng nhẹ `3,59× -> 3,61×`), kèm hàm `build_scaled_tier_config()` tự từ chối áp nhầm cấu hình `5%/10%` lên The5ers `>= 50K`.
   - **[XONG] Vá #4 — Đồng bộ `Dyn_ProfitLock`, giờ reset ngày & Control Room `3` ngày lãi + `R4 -> R1`:** Đã lập trình xong `Dyn_ProfitLock` (`+5% -> 2,01×` hiệu dụng), chọn múi giờ reset ngày (`1 = Europe/Prague` cho FTMO, `0 = Server Midnight` cho The5ers) trong `Naqex_AccountOrchestrator.mq5`, và nâng cấp Control Room (`127.0.0.1:8787`) + `prop_challenge_tracker.py` đếm đúng `3` ngày lãi `>= +0,50%` kèm dải chẩn đoán `R4 -> R3 -> R2 -> R1`. *(Chỉ chờ lệnh đang mở trên `naqex-node1` đóng phẳng là đồng bộ `9/9 .ex5` + `naqex_red_news_utc.csv` qua `sync_updated_ex5_when_flat.ps1`.)*
3. **Luật chia tiền tự động 3 Ngăn (`3-Bucket`) ghi sổ bằng `treasury_ledger.py`:**
   - Mọi đồng lãi rút về từ tài khoản quỹ phải chia cứng theo đúng 3 ngăn, không tiêu cảm tính:
     - **Ngăn 1 — `30%` Quỹ Dự Phòng Vé Thi:** Dùng để mở rộng lên bậc vé lớn hơn (`25K -> 50K -> 100K`) hoặc thi lại khi chẳng may dính vùng rớt `22%–35%`. Khóa trần đúng **`5×` giá vé mục tiêu**; khi đã đầy ngăn này, **`100%` phần thừa tự động chảy thẳng sang Ngăn 2** (đưa tỷ lệ đổ vào vốn riêng lên **`80%`** mỗi kỳ rút!).
     - **Ngăn 2 — `50%` Sổ Vốn Tự Có (`Own-Book`):** Nuôi 4 nhánh độc lập (Crypto Spot, Funding, ETF IBKR) để tích lũy tài sản thật không phụ thuộc quỹ.
     - **Ngăn 3 — `20%` Quỹ Vận Hành & Thuế:** Dùng riêng cho máy chủ VPS sát sàn, dữ liệu sạch và dự phòng nghĩa vụ thuế.

---

### Khía Cạnh 3 — Hệ Thống Phân Loại & Gắn Nhãn Rủi Ro 4 Tầng (`R4 -> R3 -> R2 -> R1`)

Sai lầm chết người của 90% người làm bot là thấy tài khoản lỗ liền vội sửa thuật toán, trong khi nguyên nhân lại đến từ luật sàn, trượt giá hay tâm lý con người. Toàn bộ dự án áp dụng **bộ 4 nhãn rủi ro chuẩn** và quy tắc **chẩn đoán ngược bắt buộc từ `R4 -> R1`**:

| Thứ tự kiểm tra | Mã nhãn | Tên dễ hiểu | Bản chất vấn đề | Cách đo & Hàng rào xử lý |
|---|---|---|---|---|
| **1 (Kiểm đầu tiên)** | **`R4`** | **Luật quỹ, Sàn & Con người** *(tác động từ ngoài)* | Dính cấm tin đỏ `±2p`, dùng chung IP VPN bị nghi copy-trade, quỹ tự đổi điều khoản, hoặc chủ tài khoản tự bấm tắt/đóng lệnh vì xót lãi. | **Không đụng code bot.** Trị bằng: giấy xác nhận văn bản từ quỹ, IP sạch cố định trên `naqex-node1`, khóa tin đỏ rộng hơn luật quỹ (`±5p`), kỷ luật không can thiệp tay. |
| **2** | **`R3`** | **Khớp lệnh, Trượt giá & Máy móc** *(tác động từ kỹ thuật)* | Chênh giá mua/bán giãn bất thường, trượt giá thực cao hơn `1,5×` giả định, rớt mạng, MT5 treo, hoặc đồng hồ máy chạy lệch giờ. | **Không sửa logic vào lệnh.** Trị bằng: đối chiếu `naqex_exec_audit.csv` với MetriX, đồng bộ đồng hồ NTP `< 1s`, cảnh báo Telegram `@naqex_guard_bot`, chuyển sang cấu hình `A5` hoặc nâng cấp VPS sát sàn khi có lãi. |
| **3** | **`R2`** | **Trùng lặp Danh mục & Dồn trứng 1 giỏ** *(tác động từ phân bổ)* | Nhiều bot cùng mở lệnh vào chung 1 đồng tiền, hoặc để quá nhiều tài sản trên 1 sàn Crypto dễ mất trắng khi sàn gặp sự cố. | **Không sửa từng bot lẻ.** Trị bằng khóa cứng toàn cục: tổng rủi ro đồng thời trên 1 mã **`<= 1,0%`** (`SYMCAP`), tổng tài sản trên các sàn Crypto tập trung **`<= 25%`** (`NCO_CexCap25` — kể cả sàn sập mất 50%, tổng tài sản chỉ giảm tối đa `-12,89%`). |
| **4 (Kiểm cuối cùng)** | **`R1`** | **Rủi ro THẬT của chiến lược** *(mất lợi thế thị trường)* | Đã kiểm sạch `R4`, `R3`, `R2` đều bình thường nhưng chiến lược vẫn thua dài bất thường, vượt ra ngoài biên độ mô phỏng. | **Lúc này mới xử lý chiến lược:** Để bộ giám sát thống kê (`CUSUM/SPRT`) và `AccountOrchestrator` tự động hạ ga rủi ro, tạm dừng nhánh hỏng và đưa vào xưởng nghiên cứu tìm nguồn thay thế. |

**Quy tắc quy đổi nỗi đau bằng tiền Việt (`VND`):** Trước mọi quyết định tăng vốn thật, luôn tính sẵn mức lỗ xấu nhất theo cả `%`, `USD` và `triệu VND` (ví dụ: ở mốc `50.000 USD` ~ `1,275 tỷ VND`, cú sốc sập sàn CEX `-50%` trong cấu hình `NCO_CexCap25` bị khóa cứng ở mức `-6.445 USD` ~ `-164,3 triệu VND`, không bao giờ để rơi vào cảnh mất `41,6%` như cách chia không có trần).

---

### Khía Cạnh 4 — Hạ Tầng, Bảo Mật & Ngân Sách Tự Nuôi (`0 USD` -> Tự Trích Từ Lãi Thật)

Chi phí hạ tầng **không bao giờ được phép vượt quá mức lợi nhuận thực tế** mà hệ thống kiếm ra.

| Cấp độ hạ tầng | Điều kiện mở khóa | Cấu hình cụ thể | Trần chi phí / tháng | Mục tiêu vận hành |
|---|---|---|---|---|
| **Cấp 1 — Hiện tại** *(Đang chạy 24/7)* | Đã sẵn sàng ngay hôm nay | Máy nhà `naqex-node1` (`Windows 10 LTSC`, 3 ổ tách riêng, sao lưu ngày `05:30`, đồng bộ giờ NTP `< 1s`) + Trạm giám sát mây Heroku EU + Cảnh báo Telegram `@naqex_guard_bot` | **`~0 USD` tiền túi** *(Heroku `12 USD <= 13 USD` gói Student miễn phí đến `2028-09-30`)* | Tách sạch 100% tải nền khỏi máy dev; sống sót ổn định suốt vòng Free Trial & các vé thi đầu tiên |
| **Cấp 2 — Sát sàn chuyên nghiệp** | Khi rút lãi ròng ổn định **`>= 300 USD/tháng`** từ Prop *(trung vị **Tháng `20`** theo quỹ đạo Smart-Tier)* | Thuê 1 VPS Windows đặt sát trung tâm dữ liệu sàn (London `LD4` hoặc New York `NY4`) để chạy riêng MT5 tiền thật; giữ `naqex-node1` làm máy thu thập dữ liệu Crypto 24/7 & máy dự phòng nóng | **`25 – 40 USD/tháng`** *(trích từ Ngăn 3 — Quỹ Vận Hành)* | Kéo độ trễ gửi lệnh xuống **`< 5ms`**, bảo vệ khỏi trượt giá `1,5×` (**tránh thất thoát `> 25.000 USD` sau 5 năm** theo [Quỹ đạo 60 tháng](research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md)) |
| **Cấp 3 — Dữ liệu sạch Top 1%** | Khi tổng vốn quản lý (Prop + Vốn riêng) đạt **`>= 50.000 USD`** *(trung vị **Tháng `30`**)* | Đăng ký nguồn dữ liệu lịch sử tick chuẩn & dữ liệu ETF/vĩ mô sạch (phục vụ nghiên cứu chiến lược v2/v3 không nhiễu) | **`30 – 100 USD/tháng`** *(tổng hạ tầng + dữ liệu `<= 150 USD/tháng` và `<= 10%` lãi ròng)* | Chống ảo giác dữ liệu bẩn, rút ngắn chu kỳ kiểm định chiến lược mới |

**Danh sách khóa an toàn bắt buộc trên `naqex-node1` trước khi nạp đồng tiền thật đầu tiên *(cập nhật từ [Kiểm toán sống 2026-11-24](research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md))*:**
1. **[ĐÃ BẬT SẴN]** **Windows Defender bảo vệ thời gian thực** trên `naqex-node1` đã được bật lại sạch sẽ (`RealTimeProtectionEnabled = True`, ngoại lệ duy nhất `C:\Naqex`, tường lửa `3/3` hồ sơ BẬT).
2. **[ĐẠT]** **`0` mật khẩu lưu trần trên ổ cứng**, đồng hồ NTP chuẩn `< 0,1s` (`time.google.com`), ổ `C:` trống `103,88 GB`, bản sao lưu `D:\NaqexBackup\daily\20261124` sẵn sàng.
3. **[CHỜ DIỄN TẬP KHI PHẲNG]** **Diễn tập sự cố 1 lần** khi `open_positions == 0`: tạm tắt heartbeat `3` phút để xác nhận trực tiếp điện thoại nhận đúng tin nhắn đỏ `🔴 MẤT KẾT NỐI` từ `@naqex_guard_bot` (xem 5 bước hướng dẫn trong [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md)).
4. **Đặt lịch nhắc ngày `2028-09-25`** kiểm tra gia hạn hoặc chuyển trạm giám sát Heroku trước khi gói Student hết hạn (`2028-09-30`).
5. Mọi thao tác bảo trì máy `naqex-node1` tuân thủ đúng quy trình trong kỹ năng nội bộ [naqex-node-ops](../.agents/skills/naqex-node-ops/SKILL.md).

---

### Khía Cạnh 5 — Kiểm Chứng Thực Chiến, Pháp Lý Quỹ & Kỷ Luật Con Người

Đây là khía cạnh chiếm tới **70% nguyên nhân thành bại** ngoài đời thật — kể cả khi toán học và code đã chuẩn 100%.

1. **Chốt sạch pháp lý trước khi mua vé thật (`0` rủi ro bị khóa tài khoản oan `R4`):**
   - Gửi email chính thức xin xác nhận bằng văn bản cho phép chạy bộ EA tự viết độc quyền (không copy-trade, không spam lệnh tốc độ cao, tuân thủ khóa tin đỏ `±5p`) tới **FTMO (`support@ftmo.com`)** và **The5ers (`help@the5ers.com`, mục Terms §11)** theo mẫu đã soạn sẵn tại [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](../tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md).
   - Lưu nguyên bản email phản hồi kèm ảnh chụp vào kho hồ sơ trước khi thanh toán bất kỳ vé thi nào.
2. **Hoàn thành đủ vòng kiểm chứng Free Trial `14` ngày (`FTMO-Demo 1515343166`):**
   - Thu tối thiểu **`10 – 15` lệnh đóng trọn vẹn** xuyên qua đủ phiên Á/Âu/Mỹ và đổi ngày (rollover).
   - Đối chiếu từng lệnh giữa trang **FTMO Account MetriX** và file kiểm toán `naqex_exec_audit.csv`: xác nhận `0` lệnh thiếu cắt lỗ, `0 USD` phí qua đêm, và độ lệch giá khớp thực tế nằm trong ngưỡng cho phép (`<= 1,5×` stress).
3. **Hàng rào kỷ luật bảo vệ tâm lý chủ sở hữu:**
   - Theo [PROFILE.md](../knowledge/owner/PROFILE.md), rủi ro hành vi lớn nhất cần phòng ngừa là *cảm giác xót khi lãi đang có bị kéo lùi (profit giveback) dẫn tới muốn bấm tay can thiệp giữa lệnh*.
   - **Quy tắc vận hành cố định:**
     - Chỉ mở xem tổng quan tài khoản tối đa `1–2` lần/ngày (sáng/tối qua Control Room), không ngồi canh từng cây nến.
     - **Tuyệt đối không bấm đóng lệnh hoặc sửa cắt lỗ bằng tay** trong giờ bot đang chạy, trừ khi xảy ra sự cố kỹ thuật `R3/R4` đã được xác minh (ví dụ mất cắt lỗ, kẹt lệnh quá giờ đóng cửa).
     - Mọi ý tưởng chỉnh sửa chiến lược đều ghi vào sổ nghiên cứu và chỉ thảo luận vào buổi rà soát cuối tuần / hàng tháng.
4. **Kỷ luật niêm phong dữ liệu kiểm tra mật (`Holdout 2025+`):**
   - Tập dữ liệu `2025+` khóa cứng (`holdout_rows_analysed = 0`) cho toàn bộ quá trình phát triển thế hệ chiến lược v2.
   - Chỉ được mở **đúng 1 lần duy nhất không thể đảo ngược** khi bộ chiến lược v1 đã chạy thực chiến đủ `90` ngày, toàn bộ mã nguồn v2 đã đóng băng có mã kiểm tra SHA-256 và tiêu chí Đạt/Trượt ghi sẵn trước khi mở, dưới lệnh xác nhận trực tiếp của chủ sở hữu.

---

### Khía Cạnh 6 — Buồng Lái Công Cụ, Dữ Liệu & Tận Dụng Lợi Thế AI Agents

Lợi thế cạnh tranh mạnh nhất của chủ sở hữu là **năng lực điều phối đội AI Agents và ngân sách AI dồi dào**. Ta tận dụng đúng điểm mạnh này nhưng tránh bẫy "xây công cụ màu mè mà quên kiếm tiền".

1. **Một Buồng Lái Duy Nhất — Local Control Room (`127.0.0.1:8787`):**
   - Dùng trực tiếp màn hình **Prop Account MetriX** (kéo số sống từ `NAQEX_NODE1` qua Heroku, hiển thị đủ 3 khoảng đệm lỗ, 5 quy tắc quỹ, `MAE/MFE` từng lệnh, lịch PnL ngày và lịch tin đỏ giờ Việt Nam `ICT`) kết hợp lệnh kiểm tra nhanh buổi sáng `daily_ops_briefing.py` và sổ tiền `treasury_ledger.py`.
   - **Nâng cấp thiết thực duy nhất sắp làm:** Khi đã có đủ `10–15` lệnh thực chiến đầu tiên, bổ sung cột **gắn nhãn sự cố `R1 / R2 / R3 / R4`** vào báo cáo đối soát thực thi để mỗi lần lệch số đều quy về đúng nguyên nhân gốc.
2. **Dùng đội AI Agents như "Phòng Nghiên Cứu Phản Biện Tự Động":**
   - Tận dụng các phiên chạy AI độc lập để quét ý tưởng chiến lược mới (nhánh không trùng kiểu phá vỡ cho Khía cạnh 1), tự động lọc dữ liệu sạch, chạy kiểm thử chống ăn gian thời gian và chạy đội phản biện đỏ (`Red-Team`) trước khi trình chủ sở hữu duyệt.
   - Mọi phát hiện thành công **hay thất bại** đều ghi thẳng vào kho tri thức `knowledge/` và `planning/research/` để không bao giờ lặp lại vết xe đổ.
3. **Nguyên tắc chống phình to (Anti-Bloat):**
   - Không vẽ thêm dashboard, app hay tính năng mới trên `projects/trader` hoặc Control Room nếu tính năng đó không trực tiếp giúp **ra quyết định rủi ro nhanh hơn, giữ kỷ luật tốt hơn, hoặc kiếm thêm tiền lời ròng**.

---

## Phần 3 — Lộ Trình Thực Thi 5 Mốc Có Cổng Khóa (`Mốc 0 -> Mốc 4`)

Không đi theo lịch cứng nhắc bắt ngồi chờ vô ích — chuyển mốc dựa trên **bằng chứng thực tế đã đạt được**, và luôn chạy song song các nhánh độc lập trong lúc chờ dữ liệu thực địa tích lũy.

| Mốc | Thời gian dự kiến | Việc trọng tâm cần hoàn thành | Trần chi phí | **Điều kiện qua cửa (Exit Gate)** | **Điểm dừng / Bỏ (Kill Criteria)** |
|---|---|---|---|---|---|
| **Mốc 0** *(Hiện tại)* | **Tuần `1 – 2`** | 1. Chạy đủ `14` ngày Free Trial `FTMO-Demo 1515343166` trên `naqex-node1` *(đang mở lệnh `E1_USDJPY_TOKYO`, `orphan = 0`)*.<br>2. Tiếp tục gom đủ `30` ngày dữ liệu Crypto Shadow (`208` chu kỳ) & Maker (`197` chu kỳ, còn `~29,3` ngày).<br>3. Gửi & lưu email xác nhận từ **FTMO** và **The5ers (Terms §11)** theo mẫu [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md).<br>4. **[ĐÃ XONG]** Windows Defender (`RealTime=True, excl C:\Naqex`) đã bật sẵn; chỉ còn diễn tập cảnh báo Telegram `3` phút khi tài khoản phẳng.<br>5. **[ĐÃ XONG TRÊN DEV — CHỜ ĐỒNG BỘ KHI PHẲNG]** Đủ 4 bản vá kỹ thuật (`9/9 .ex5` sạch + lịch tin đỏ `418` dòng 4 đồng tiền) sẵn sàng đẩy qua `sync_updated_ex5_when_flat.ps1` ngay khi `open_positions == 0`. | **`0 USD`** | - Đủ `10–15` lệnh đóng khớp sát MetriX.<br>- `0` lệnh thiếu cắt lỗ, `0 USD` phí qua đêm.<br>- Trượt giá thực `<= 1,5×` mức kiểm thử.<br>- Có thư xác nhận bằng văn bản từ quỹ.<br>- Đã đồng bộ sạch `9/9 .ex5` + CSV `418` dòng lên `naqex-node1` & hoàn tất diễn tập Telegram. | Nếu phát hiện trượt giá thực `> 2,0×`, lỗi kỹ thuật `R3` gây mất cắt lỗ, hoặc chưa đồng bộ xong 4 bản vá -> **chặn tuyệt đối không mua vé thật**, sửa dứt điểm rồi mới đi tiếp. |
| **Mốc 1** | **Tháng `1 – 4`** | 1. Mua vé **`The5ers High Stakes 5K` (`~39–52 USD`)** chạy chế độ `P1_Balanced` (vùng rớt tối ưu `~23%`, đã siết trần 1 mã `<= 1,5%–2,0%`).<br>2. Sau `+42` phiên giao dịch, mở tiếp **`FTMO Swing`** (ưu tiên săn khuyến mãi hoặc nhảy thẳng bậc `25K` khi quỹ dự phòng đã dày để tránh phí đắt của vé `10K`).<br>3. Vừa lên Funded lập tức hạ cứng **`1,0×` (`Funded_Safe`)**.<br>4. Áp dụng sổ chia tiền **3 Ngăn (`3-Bucket`)**. | Ngân sách vé **`500 – 1.500 USD`** *(12,8 – 38,2 tr VND)* | - Đậu tối thiểu `1` tài khoản Funded.<br>- Rút thành công **`>= 2` kỳ lãi ròng** về ví.<br>- Quỹ dự phòng vé lấp đủ **`5×` vé mục tiêu**.<br>- `0` lần tự tay can thiệp phá kỷ luật. | Nếu dính chuỗi `3` vé rớt liên tiếp trên cùng 1 quỹ -> **dừng mua vé mới**, chạy kiểm toán ngược `R4 -> R3 -> R2 -> R1` toàn diện trước khi tiếp tục. |
| **Mốc 2** *(Chạy song song)* | **Tháng `3 – 9`** | 1. **Nghiên cứu Nhánh Prop v2 không trùng kiểu phá vỡ** (đảo chiều / tài sản khác, `r < 0,25` với `A1_V1_LIVE8`).<br>2. **Mở Sổ Vốn Riêng giai đoạn đầu (`5k -> 25k USD`):** kích hoạt Crypto Spot (`S2`), Funding Carry (`S3A` `BTC+ETH`), và ETF IBKR ít lệnh (`S3B / L7_TOP2`).<br>3. Chấm điểm nhánh Maker (`M2B`) bằng dữ liệu thật 30 ngày từ `naqex-node1`. | Nghiên cứu **`0 USD`**; vốn riêng trích từ lãi Prop (+ vốn mồi nếu chủ động) | - Ít nhất `1` nhóm chiến lược Prop v2 vượt đủ 6 cổng phản biện Dev (`2018–2024`), hạ thời gian đậu dự kiến về **`2,5 – 3,5 tháng`**.<br>- Sổ Vốn Riêng vận hành tái cân bằng đúng ngày 1 hàng tháng trong `>= 6` tháng, giữ tổng CEX `<= 25%`. | Với Maker (`M2B`): nếu sau 30 ngày tỷ lệ khớp `< 70%` hoặc chi phí thực `> 6,15 bps` -> **loại thẳng, không mở tiền thật**. Với ý tưởng v2: nếu tương quan `r >= 0,35` với v1 -> **không gộp**. |
| **Mốc 3** | **Tháng `9 – 18`** | 1. Khi lãi rút đều `>= 300 USD/tháng`, thuê **VPS sát sàn LD4/NY4 (`25–40 USD/tháng`)** từ Ngăn 3 cho MT5 tiền thật.<br>2. Nhân thang đa quỹ lệch pha lên tổng danh nghĩa **`100k – 250k USD`**.<br>3. Mở rộng Sổ Vốn Riêng lên **`25k -> 100k USD`** (`NCO_CexCap25`, nâng ETF IBKR lên bản đầy đủ từ mốc `50k`).<br>4. Khi đủ `90` ngày live v1, thực hiện **lượt mở khóa Holdout `2025+` 1 lần duy nhất** cho đội hình v2. | **`25 – 40 USD/tháng`** *(100% trích từ lãi thật)* | - Nhánh v2 vượt ngưỡng Đạt/Trượt đã đăng ký trước trên Holdout `2025+`.<br>- `3–4` nhánh chạy tiền thật song song ổn định, sụt giảm thực tế nằm gọn trong biên mô phỏng (`<= 8%`). | Nếu đội hình v2 trượt Holdout `2025+` -> **khai tử ngay ứng viên đó**, tuyệt đối không chỉnh tham số để chạy lại; tiếp tục dùng `A1_V1_LIVE8` và chuyển sang chu kỳ nghiên cứu mới. |
| **Mốc 4** | **Tháng `18 – 36+`** | 1. Chạm điểm **Giao cắt (`Crossover`)**: lãi ròng hàng tháng từ Sổ Vốn Riêng vượt thu nhập sau chia tỷ lệ từ Prop.<br>2. Bổ sung nguồn dữ liệu sạch (`30–100 USD/tháng` từ lãi) và cân nhắc CME Micros nếu vốn riêng `>= 100k USD`.<br>3. Duy trì **kiểm toán tháng (GIPS-Lite)** và **rà soát quản trị quý** cố định 4 lần/năm. | **`30 – 150 USD/tháng`** *(<= 10% lãi ròng)* | - Đạt hoặc tiệm cận sát chuẩn **Top 1% Độc lập**: `4–6` nhánh độc lập chạy tiền thật, **Độ đều `2,0–3,0`**, **Lãi/Sụt giảm `+18%..+30% / 6%–8%`**, kiểm soát rủi ro tuyệt đối theo VND. | Bất kỳ nhánh nào vi phạm trần lỗ tuyệt đối VND hoặc suy giảm lợi thế `R1` liên tục `2` quý -> tự động cắt giảm tỷ trọng về `0%` theo quy trình quản trị quý. |

---

## Phần 4 — Việc Cần Làm Ngay Tuần Này (Không Chờ Đợi)

1. **Giữ nguyên `naqex-node1` chạy yên 24/7** — không bấm tay đóng lệnh `E1_USDJPY_TOKYO` đang mở (`open_positions = 1`, `orphan_no_sl = 0`) trên `FTMO-Demo 1515343166`, theo dõi qua Control Room (`http://127.0.0.1:8787`, đã có dải `R4 -> R1` & đếm `3` ngày lãi `>= +0,5%`) và `@naqex_guard_bot`.
2. **Đồng bộ 1 lần khi tài khoản phẳng (`open_positions == 0`, tối nay sau `16:00–21:00 UTC`):** Chạy `sync_updated_ex5_when_flat.ps1` để đẩy bộ `9/9 .ex5` đã đóng đủ 4 bản vá kỹ thuật + tệp lịch tin đỏ `418` dòng 4 đồng tiền sang `naqex-node1` trước tin `US GDP + Core PCE` ngày `2026-11-25 13:30 UTC`.
3. **Gửi ngay 2 email xin xác nhận chạy EA độc quyền** tới FTMO (`support@ftmo.com`) và The5ers (`help@the5ers.com`) bằng bộ thư copy-paste sẵn tại [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md).
4. **Diễn tập cảnh báo mất kết nối `3` phút `@naqex_guard_bot`** ngay sau khi tài khoản phẳng *(Windows Defender `excl C:\Naqex` đã được bật sẵn — kiểm chứng tại [Kiểm toán sống `naqex-node1`](research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md))*.
5. **Không mở thêm bài săn bot CFD `swap = 0` trong ngày** *(Lab #11 + #12 đã chốt `0/36` -> `A1_V1_LIVE8` là biên tối ưu)*; dồn tập trung tích lũy đủ `10–15` lệnh đóng Free Trial và `30` ngày dữ liệu Crypto Maker `M2B`.

---

## Phần 5 — Danh Mục Tài Liệu & Bằng Chứng Gốc Liên Kết

- **Hồ sơ & Quyết định chủ sở hữu:** [PROFILE.md](../knowledge/owner/PROFILE.md) · [DECISIONS-JOURNAL.md](../knowledge/owner/DECISIONS-JOURNAL.md)
- **Lộ trình kỹ thuật & SOP Khai Trương:** [naqex-master-roadmap-2026-2027.md](../knowledge/playbooks/naqex-master-roadmap-2026-2027.md) · [ftmo-the5ers-live-launch-sop.md](../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md)
- **Bằng chứng toán học Prop, Quỹ đạo 60 tháng & Danh mục:**
  - [PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md](research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md) *(chứng minh `SYMCAP 1,75%` cắt cháy ngày `25,5% -> 4,7%`, nhảy bậc `10K -> 100K` gấp `3,21×`, bẫy `4%/8%` The5ers `50K/60K`)*
  - [TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md](research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md) *(quỹ đạo `60` tháng `2,52×`, tự nuôi VPS Tháng `20`, tránh mất `> 25k USD` trượt giá)*
  - [LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.md](research/LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.md) · [LAB12-ORTHOGONAL-MOMENTUM-V2-DISCOVERY-20261124.md](research/LAB12-ORTHOGONAL-MOMENTUM-V2-DISCOVERY-20261124.md) *(`0/36` chứng minh `A1_V1_LIVE8` là biên Pareto CFD intraday `swap = 0`)*
  - [PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md](research/PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md) · [MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md](research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md) · [PORTFOLIO-V1-VS-V2-ARCHITECTURE-STUDY-20261124.md](research/PORTFOLIO-V1-VS-V2-ARCHITECTURE-STUDY-20261124.md)
  - [QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md](research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md) · [QUANT-POD-4SLEEVE-ALLOCATION-20261124.md](research/QUANT-POD-4SLEEVE-ALLOCATION-20261124.md)
- **Vận hành Sống & Pháp lý:** [LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md](research/LIVE-NODE1-TELEMETRY-AND-SHADOW-AUDIT-20261124.md) · [FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md](../tooling/ai-engines/exports/deployment_kit/FTMO-THE5ERS-WRITTEN-CLEARANCE-EMAILS.md) · [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](../tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md) · [naqex-node-ops](../.agents/skills/naqex-node-ops/SKILL.md) · [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json)
