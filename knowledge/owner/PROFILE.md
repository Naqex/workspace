---
doc_type: evergreen
domain: owner
updated_utc: 2026-11-25
layer: public_template_stub
---

# Hồ sơ Chủ sở hữu (Owner Profile — Public Template Stub)

> **Bản mẫu công khai (Layer 1 — Public Stub):** Dữ liệu cá nhân, ngân sách, khẩu vị rủi ro riêng và ghi chú vận hành thật của chủ sở hữu được lưu trong kho riêng tư cục bộ `private_vault/owner/PROFILE.md` (đã đưa vào `.gitignore` của Layer 1). Khi chạy trên máy local có `private_vault/owner/`, `tooling/knowledge/brain_cli.py` và `tooling/search/xerj.py` tự động ưu tiên đọc bản riêng tư (*Private-First*); khi chạy trên CI hoặc bản clone công khai, hệ thống lùi an toàn về bản mẫu này.

## 1. Chân dung vận hành & tư duy cốt lõi

- **Mô hình phối hợp với AI Agents:** Chủ sở hữu giữ vai trò giám sát hệ thống và rủi ro (*fail-closed* đối với vốn thật, lệnh sàn, dữ liệu Holdout niêm phong và thông tin đăng nhập); AI đảm nhiệm lập kế hoạch, nghiên cứu, kiểm định hồi quy và xây dựng hạ tầng offline.
- **Tiêu chuẩn kỹ thuật:** Ưu tiên kiến trúc tách lớp theo cấu hình (*factory*), mã nguồn gọn, tái sử dụng được, có kiểm định tự động và bằng chứng đo lường thật thay vì gắn cứng thủ công.
- **Phong cách báo cáo:** Trình bày ngắn gọn, rõ ràng, đi thẳng vào kết quả, số liệu kiểm chứng và rủi ro còn lại.

## 2. Mục tiêu dài hạn (North Star — Public Framework)

1. **Hệ thống nghiên cứu & quản trị rủi ro định lượng có kỷ luật:** Tối ưu theo giá trị kỳ vọng ròng sau chi phí (EV), bảo vệ Holdout nghiêm ngặt (`OrderSend = 0` mặc định khi nghiên cứu) và đa dạng hóa theo nhiều nhánh độc lập.
2. **Hệ sinh thái Naqex dễ bảo trì:** Duy trì workspace đa dự án sạch sẽ, phân tách rõ Layer 1 (công khai), Layer 2 (kho cá nhân riêng tư `private_vault/`) và Layer 3 (bí mật/mật khẩu ngoài Git).
3. **Bộ nhớ nghiên cứu local-first:** Lưu tri thức dạng Markdown kèm chỉ mục SQLite FTS5/Vector dùng lại được (`.runtime/knowledge/`), không khóa chặt vào một nhà cung cấp AI duy nhất.

## 3. Hồ sơ rủi ro & nguyên tắc bảo vệ

- **Quy đổi rủi ro song song:** Khi đánh giá rủi ro vốn thật, luôn quy đổi đồng thời theo tỷ lệ phần trăm và giá trị tiền tuyệt đối trong hồ sơ riêng tư tại `private_vault/owner/PROFILE.md`.
- **Khung phân loại rủi ro 4 tầng (`R4 -> R3 -> R2 -> R1`):** Luôn kiểm tra từ ngoài vào trong trước khi chỉnh sửa logic chiến lược:
  - **`R4` — Quy tắc nền tảng & Con người:** Luật tin tức, giới hạn tài khoản, can thiệp thủ công ngoài kế hoạch.
  - **`R3` — Khớp lệnh, Trượt giá & Hạ tầng:** Chênh giá mua/bán, trượt giá thực tế, độ ổn định mạng/máy chủ, đồng bộ đồng hồ.
  - **`R2` — Tập trung danh mục & Đối tác:** Trùng lặp phơi nhiễm giữa nhiều chiến lược hoặc rủi ro lưu ký tập trung.
  - **`R1` — Bản chất chiến lược:** Chỉ kết luận chiến lược suy giảm khi đã loại trừ sạch `R4`, `R3`, `R2` và có bằng chứng thống kê rõ ràng.
- **Tách biệt nghiên cứu và thực thi:** Nghiên cứu được mổ xẻ liên tục; thực thi tuân thủ bộ luật cứng và cảnh báo tự động thay vì can thiệp cảm tính giữa lệnh.
