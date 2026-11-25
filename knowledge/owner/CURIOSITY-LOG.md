---
doc_type: journal
domain: owner
updated_utc: 2026-11-25
layer: public_template_stub
---

# Sổ tay Tò mò & Câu hỏi Lớn của Owner (Curiosity Log — Public Template Stub)

> **Bản mẫu công khai (Layer 1 — Public Stub):** Nhật ký câu hỏi và ghi chú cá nhân thật của chủ sở hữu được lưu riêng tại `private_vault/owner/CURIOSITY-LOG.md` (gitignored ở Layer 1). Khi `private_vault/owner/` tồn tại cục bộ, `brain_cli.py log-curiosity` và `brain_cli.py owner-brief` tự động đọc/ghi tại đó; bản mẫu này chỉ giữ định dạng chuẩn cho CI và môi trường không có kho riêng tư.

## 2026-11-25

- **[Architecture & Knowledge Ops]** *Làm sao tách rạch ròi hạ tầng mở (Layer 1) khỏi hồ sơ chủ sở hữu, cấu hình vận hành riêng tư và chiến lược nội bộ (Layer 2) mà không làm gãy CI hoặc tìm kiếm cục bộ?*
  - **Tóm tắt / Kết quả:** Dùng cơ chế phân giải ưu tiên riêng tư (*Private-First*) trong `brain_cli.py` và `xerj.py`: tự ưu tiên `private_vault/owner/` khi tồn tại cục bộ, tự lùi về bản mẫu công khai `knowledge/owner/` trên CI/clone sạch, đồng thời giữ tuyệt đối 0 bí mật/mật khẩu (Layer 3) trong mọi kho Git.
