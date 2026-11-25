---
doc_type: evergreen
domain: owner
updated_utc: 2026-11-24
provenance: verified_from_workspace_and_owner_explicit_statements
---

# Hồ sơ Chủ sở hữu (Owner Profile — Evergreen)

> Tài liệu sống ghi nhận đúng những gì đã quan sát/xác nhận trực tiếp từ owner trong workspace (`AGENTS.md`, `projects/quant-trading/AGENTS.md` và các trao đổi trực tiếp). **Không suy diễn hoặc bịa chi tiết chưa xác nhận.** Cập nhật khi owner thay đổi định hướng hoặc hành vi thực tế trong paper/live trading bổ sung bằng chứng mới.

## 1. Chân dung vận hành & tư duy cốt lõi

- **Phong cách làm việc với AI Agents:** Đóng vai **Chủ sở hữu / Giám đốc Hệ thống & Rủi ro**, giao quyền tự chủ cao cho AI trong lập kế hoạch, nghiên cứu, tối ưu quy trình, xây code/UI và kiểm chứng offline; giữ quyền quyết định cuối (fail-closed) với tiền thật, lệnh sàn, mở khóa dữ liệu mật (Holdout), mật khẩu/API key và hạ tầng production.
- **Khẩu vị kỹ thuật & chất lượng:** Ưu tiên giải pháp **hệ thống hóa như dây chuyền sản xuất (factory, linh hoạt theo cấu hình, song song, tái sử dụng lâu dài)** thay vì chắp vá thủ công từng lượt. Ghét gắn cứng (*hardcoding*), ghét báo cáo dài dòng sáo rỗng, ưu tiên số liệu đo thật, tốc độ nhanh và có lớp kiểm định hồi quy bảo vệ tương lai.
- **Năng lực nền & tư duy tiếp cận:** IQ tự đánh giá mức tốt (`115–120`), tiếp thu nhanh các khái niệm định lượng/hệ thống khi được giải thích trực diện bằng tiếng Việt tự nhiên kèm lý do thật và số liệu cụ thể; tò mò sâu về bản chất (*first principles* — luôn hỏi *"đây đã là giới hạn/đẳng cấp cao nhất chưa, còn thiếu gì, cộng đồng thực tế làm ra sao?"*).
- **Vị thế năng lực thực tế hiện tại (owner tự xác nhận `2026-11-23`):**
  - *Điểm rất mạnh:* **Chuyên gia sử dụng & điều phối AI Agents** (orchestration, workflow đa tác nhân, hệ thống hóa dây chuyền) + **ngân sách AI Agents dư dả**.
  - *Khoảng trống thật cần bù:* Hoạt động độc lập (solo), **kiến thức trading ở mức cơ bản–khá**, **chưa từng trade tay thật** và **chưa có lịch sử lợi nhuận live (chưa profitable)**. Do đó hệ thống phải ưu tiên khóa cứng rủi ro, tách biệt nghiên cứu với thực thi, và nhanh chóng bước qua thực chiến Demo/Free Trial/vốn nhỏ để tích lũy dữ liệu khớp lệnh thật thay vì chỉ hoàn thiện backtest trên giấy.
- **Ngôn ngữ giao tiếp (cập nhật `2026-11-24`):** Mặc định trình bày bằng tiếng Việt đơn giản, dễ hiểu, gần gũi, đi thẳng vào kết quả và ý nghĩa thực tế (hạn chế thuật ngữ/từ viết tắt chuyên ngành); chỉ phân tích kỹ thuật chuyên sâu khi owner chủ động yêu cầu.
- **Kỳ vọng quy mô cho phiên tự chủ dài hạn (xác nhận `2026-11-24`):** Khi giao phiên tự chủ xuyên đêm nhiều giờ với budget AI dư dả, kỳ vọng kế hoạch phải được hiệu chuẩn theo đúng tốc độ thực tế của đội `swarm` (`~25–35` mốc/giờ) theo mô hình **nhà máy chạy chu kỳ liên tục** (mở rộng chiến lược trên dữ liệu/thị trường mới, tối ưu sâu hệ thống, đối soát thực chiến theo giờ tới sát giờ thức dậy), không muốn kế hoạch tĩnh quá nhỏ làm xong trong 1 giờ rồi bỏ trống phần lớn đêm.
- **Ưu tiên nén thời gian thông minh (xác nhận `2026-11-24`):** Không thích lộ trình cứng nhắc bắt chờ hàng chục ngày lịch khi có thể đạt hiệu suất và độ an toàn tương đương nhanh hơn; ưu tiên cổng dựa trên bằng chứng sự kiện thực tế + thử nghiệm vốn siêu nhỏ giới hạn lỗ (*micro-canary*) và luôn tận dụng thời gian chờ bằng cách chạy song song các nhánh độc lập có giá trị thật.

## 2. Mục tiêu dài hạn (North Star — Đã chốt `2026-11-24`)

> Bản kế hoạch thực thi đầy đủ mọi khía cạnh đặt tại [TOP1-SOLO-QUANT-MASTER-PLAN.md](../../planning/TOP1-SOLO-QUANT-MASTER-PLAN.md).

1. **Tiệm cận cảnh giới "Chuyên gia độc lập bậc nhất (Top 1% Solo Quant)" thực tế, có tính chi phí (không ảo tưởng):**
   - **Thước đo cốt lõi:** Tối ưu theo **Tiền lời ròng kỳ vọng (EV)** và **Hiệu quả trên mỗi đồng phí bỏ ra** (`EV / 1 USD phí`), không chạy theo cực đoan "rớt ít nhất" (lỗ thời gian) hay "đậu nhanh nhất" (tiền vé ăn ngược vào lãi).
   - **Đích đến chỉ số thực chiến (sau mọi chi phí, tự vận hành 1 người + AI):**
     - **Độ đều lợi nhuận thực chiến:** **`2,0 – 3,0`** *(hiện tại riêng FX là `~1,1–1,5`; bản vẽ ghép 4 nhánh đã đạt `~2,25` trên giấy)*.
     - **Lãi năm / Mức sụt giảm tối đa (ở mức an toàn `1×`):** **`+18%..+30%/năm`**, sụt giảm tối đa **`6%–8%`** *(hiện tại riêng bộ 8 bot FX là `+8,3%..+12,7%/năm`, sụt `~6,5%–9,1%`)*.
     - **Tốc độ đậu quỹ 2 vòng (an toàn):** Rút từ mức nền `4,5–5,9 tháng` hiện tại xuống **`1,5–3,0 tháng`** *(xác suất đậu trong 6 tháng đạt `85%–95%`)* bằng cách ghép thêm chiến lược không trùng kiểu phá vỡ và chạy song song nhiều gói quỹ lệch pha.
     - **Vùng rớt vé thi tối ưu toán học:** Chấp nhận vùng rớt vé đầu **`22%–35%`** ở vòng thi để tối đa hóa tiền lời ròng (`EV/phí >= +2,5×`, hiện đạt `+3,25×..+7,17×`), sau đó **vừa sang tài khoản thật (Funded) lập tức hạ ga về `1,0×`** để giữ nguy cơ cháy tài khoản thật **`< 1%`**.
     - **Đa dạng nguồn kiếm tiền:** Vận hành **`4–6` nhánh độc lập không dính nhau** (Prop FX/Chỉ số trong ngày + Nhánh Prop mới khác kiểu phá vỡ + Crypto Spot không đòn bẩy + Crypto ăn phí Funding + Crypto Maker có điều kiện + ETF toàn cầu 0 phí qua đêm trên IBKR) để tiến tới sổ vốn tự có thoát phụ thuộc luật quỹ.
     - **Kỷ luật chi phí hạ tầng & dữ liệu:** Giai đoạn đầu duy trì gần như **`0 USD/tháng`** (`naqex-node1` + Heroku Student); chỉ nâng lên **`30–150 USD/tháng`** (VPS đặt sát sàn + dữ liệu sạch) khi **được chi trả hoàn toàn từ tiền lời thật đã rút**.
2. **Làm chủ hệ sinh thái sản phẩm Naqex:** Duy trì workspace đa dự án gọn gàng (`projects/trader`, `projects/quant-trading`, `projects/vi-dubber`, `projects/integrations`, `education`) có tính kế thừa cao giữa các phiên AI.
3. **Bộ não nghiên cứu & học hỏi liên tục (Personal Research & Memory Engine):** Biến mọi lượt tự nghiên cứu (agent chủ động) và nghiên cứu theo chỉ đạo (EN/VI/CN/RU/Reddit/Docs/Papers) thành tài sản tri thức có cấu trúc, tra cứu tức thời, giúp AI hiểu sâu owner hơn qua thời gian.

## 3. Hồ sơ rủi ro & hành vi giao dịch (nguồn: `projects/quant-trading/AGENTS.md`)

- **Cơ cấu tài sản:** Đã có lớp phòng thủ riêng (chứng chỉ quỹ và tiền gửi), nên nhánh quant được định vị hướng tới tỷ suất lợi nhuận/rủi ro cao hơn — nhưng **không** tự động cho phép đòn bẩy mù quáng hay bỏ giới hạn lỗ.
- **Độ chịu lỗ theo quy mô vốn (tuyệt đối bằng VND/USD):** Vốn thử nghiệm nhỏ chấp nhận rủi ro cao hơn; vốn lớn coi drawdown `15%–20%` là quá cao; vốn rất lớn coi `5%` đã đáng kể. Khi bàn vốn thật, luôn quy đổi song song `%` và số tiền tuyệt đối.
- **Khung phân loại & gắn nhãn rủi ro 4 tầng (`R4 -> R3 -> R2 -> R1`, chốt `2026-11-24`):** Khi có thua lỗ hoặc sai lệch, **luôn kiểm tra ngược từ ngoài vào trong** trước khi đụng vào mã nguồn chiến lược:
  - **`R4` — Luật quỹ, sàn & Con người:** Dính luật tin đỏ, IP dùng chung, quỹ đổi luật, hoặc tự tay can thiệp giữa lệnh.
  - **`R3` — Khớp lệnh, Trượt giá & Hạ tầng:** Chênh giá mua/bán giãn rộng, trượt giá thực cao hơn giả định, lỗi mạng/máy chủ, lệch đồng hồ.
  - **`R2` — Trùng lặp danh mục & Dồn tiền một chỗ:** Nhiều bot cùng đánh 1 đồng tiền (khóa trần `<= 1,0%`/mã) hoặc dồn quá nhiều tiền trên sàn Crypto tập trung (khóa tổng CEX `<= 25%`).
  - **`R1` — Rủi ro THẬT của chiến lược:** Chỉ kết luận chiến lược mất lợi thế khi đã loại trừ sạch `R4`, `R3`, `R2` và bộ giám sát thống kê (`CUSUM/SPRT`) báo vượt ngưỡng.
- **Điểm mạnh hành vi:** Ít FOMO, có thể kiên nhẫn chờ hoặc chịu chuỗi lỗ nếu hiểu rõ nguyên nhân gốc và thấy số liệu/cơ chế minh bạch; phản xạ tự nhiên khi có bất thường là điều tra trước khi hành động.
- **Rủi ro hành vi chính cần hệ thống bảo vệ:** Khó chịu khi lợi nhuận đã có bị trả lại (*profit giveback*) và có xu hướng muốn can thiệp theo tình huống thay vì để luật cứng chạy hết lệnh. **Biện pháp thiết kế:** Tách biệt tuyệt đối giữa *nghiên cứu* (được mổ xẻ mọi lúc) và *thực thi* (khóa luật cứng, có bộ giám sát `CUSUM/SPRT` và `AccountOrchestrator` tự hạ rủi ro thay vì sửa lệnh giữa chừng bằng cảm tính).
- **Công sức bảo trì:** Sẵn sàng đầu tư thời gian tỷ lệ thuận với bằng chứng lợi nhuận thực tế; ưu tiên quy trình ít phải canh thủ công, có cảnh báo tự động khi bất thường.
