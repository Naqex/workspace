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
- **Ngôn ngữ giao tiếp:** Tiếng Việt tự nhiên, súc tích, đi thẳng vào kết quả và quyết định có ích; giữ thuật ngữ tiếng Anh chuẩn ngành kèm giải thích ngắn lần đầu.
- **Kỳ vọng quy mô cho phiên tự chủ dài hạn (xác nhận `2026-11-24`):** Khi giao phiên tự chủ xuyên đêm nhiều giờ với budget AI dư dả, kỳ vọng kế hoạch phải được hiệu chuẩn theo đúng tốc độ thực tế của đội `swarm` (`~25–35` mốc/giờ) theo mô hình **nhà máy chạy chu kỳ liên tục** (mở rộng chiến lược trên dữ liệu/thị trường mới, tối ưu sâu hệ thống, đối soát thực chiến theo giờ tới sát giờ thức dậy), không muốn kế hoạch tĩnh quá nhỏ làm xong trong 1 giờ rồi bỏ trống phần lớn đêm.
- **Ưu tiên nén thời gian thông minh (xác nhận `2026-11-24`):** Không thích lộ trình cứng nhắc bắt chờ hàng chục ngày lịch khi có thể đạt hiệu suất và độ an toàn tương đương nhanh hơn; ưu tiên cổng dựa trên bằng chứng sự kiện thực tế + thử nghiệm vốn siêu nhỏ giới hạn lỗ (*micro-canary*) và luôn tận dụng thời gian chờ bằng cách chạy song song các nhánh độc lập có giá trị thật.

## 2. Mục tiêu dài hạn (North Star)

1. **Tự do hóa bằng hệ thống định lượng (One-Person Quant Pod):** Xây dựng hệ thống đa nguồn lợi thế độc lập (trước mắt: **Nhánh #1 Intraday FX/Index Prop** cho FTMO/The5ers + **Nhánh #2 Crypto Spot Quant** không đòn bẩy; dài hạn: tài khoản vốn riêng thoát phụ thuộc luật quỹ), hướng tới mục tiêu thực tế `Sharpe live 1.5–2.2+`, `Calmar 1.5–2.5+`.
2. **Làm chủ hệ sinh thái sản phẩm Naqex:** Duy trì workspace đa dự án gọn gàng (`projects/trader`, `projects/quant-trading`, `projects/vi-dubber`, `projects/integrations`, `education`) có tính kế thừa cao giữa các phiên AI.
3. **Bộ não nghiên cứu & học hỏi liên tục (Personal Research & Memory Engine):** Biến mọi lượt tự nghiên cứu (agent chủ động) và nghiên cứu theo chỉ đạo (EN/VI/CN/RU/Reddit/Docs/Papers) thành tài sản tri thức có cấu trúc, tra cứu tức thời, giúp AI hiểu sâu owner hơn qua thời gian.

## 3. Hồ sơ rủi ro & hành vi giao dịch (nguồn: `projects/quant-trading/AGENTS.md`)

- **Cơ cấu tài sản:** Đã có lớp phòng thủ riêng (chứng chỉ quỹ và tiền gửi), nên nhánh quant được định vị hướng tới tỷ suất lợi nhuận/rủi ro cao hơn — nhưng **không** tự động cho phép đòn bẩy mù quáng hay bỏ giới hạn lỗ.
- **Độ chịu lỗ theo quy mô vốn (tuyệt đối bằng VND/USD):** Vốn thử nghiệm nhỏ chấp nhận rủi ro cao hơn; vốn lớn coi drawdown `15%–20%` là quá cao; vốn rất lớn coi `5%` đã đáng kể. Khi bàn vốn thật, luôn quy đổi song song `%` và số tiền tuyệt đối.
- **Điểm mạnh hành vi:** Ít FOMO, có thể kiên nhẫn chờ hoặc chịu chuỗi lỗ nếu hiểu rõ nguyên nhân gốc và thấy số liệu/cơ chế minh bạch; phản xạ tự nhiên khi có bất thường là điều tra trước khi hành động.
- **Rủi ro hành vi chính cần hệ thống bảo vệ:** Khó chịu khi lợi nhuận đã có bị trả lại (*profit giveback*) và có xu hướng muốn can thiệp theo tình huống thay vì để luật cứng chạy hết lệnh. **Biện pháp thiết kế:** Tách biệt tuyệt đối giữa *nghiên cứu* (được mổ xẻ mọi lúc) và *thực thi* (khóa luật cứng, có bộ giám sát `CUSUM/SPRT` và `AccountOrchestrator` tự hạ rủi ro thay vì sửa lệnh giữa chừng bằng cảm tính).
- **Công sức bảo trì:** Sẵn sàng đầu tư thời gian tỷ lệ thuận với bằng chứng lợi nhuận thực tế; ưu tiên quy trình ít phải canh thủ công, có cảnh báo tự động khi bất thường.
