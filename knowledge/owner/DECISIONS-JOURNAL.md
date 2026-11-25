---
doc_type: evergreen
domain: owner
updated_utc: 2026-11-25
layer: public_template_stub
---

# Nhật ký Quyết định & Trade-off của Owner (Decisions Journal — Public Template Stub)

> **Bản mẫu công khai (Layer 1 — Public Stub):** Nhật ký quyết định cá nhân đầy đủ của chủ sở hữu được lưu riêng tại `private_vault/owner/DECISIONS-JOURNAL.md` (gitignored ở Layer 1). Khi `private_vault/owner/` tồn tại trên máy local, `brain_cli.py owner-brief` và `brain_cli.py log-decision` tự động đọc/ghi vào kho riêng tư; bản công khai này chỉ giữ cấu trúc bảng chuẩn cho CI và bản clone sạch.

| Ngày | Quyết định | Lý do & Trade-off đã chấp nhận | Điều kiện xem xét lại |
|---|---|---|---|
| `2026-11-23` | **Dựng Knowledge Vault Markdown-first + chỉ mục SQLite FTS5/Hybrid cục bộ (`brain_cli.py`)** | Nhẹ, không cần daemon nền, không khóa vào một nhà cung cấp AI, dễ kiểm tra diff trên Git | Khi kho tài liệu vượt quy mô vài nghìn file hoặc cần nhúng đa phương thức |
| `2026-11-25` | **Áp dụng kiến trúc 2 tầng Public/Private Vault (`Naqex/workspace` Layer 1 + `private_vault/` Layer 2 gitignored)** | Giữ repo tổ chức sạch, không lộ thông tin cá nhân/OPSEC/preset trả phí; CLI ưu tiên đọc `private_vault/owner/` và tự lùi về bản mẫu khi chạy CI | Khi mở rộng thêm cộng tác viên hoặc đổi mô hình phân quyền kho dữ liệu |
