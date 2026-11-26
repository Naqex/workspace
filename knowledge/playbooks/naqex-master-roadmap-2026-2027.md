---
doc_type: evergreen
domain: knowledge
topic: naqex-master-roadmap-2026-2027
status: pointer_to_single_ssot
updated_utc: 2026-11-27
order_send_count: 0
holdout_rows_analysed: 0
canonical_owner: "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"
sources:
  - "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"
  - "planning/CURRENT-CONTEXT.md"
  - "planning/research/PORTFOLIO-REGISTRY.json"
  - "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
  - "planning/research/C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md"
  - "knowledge/owner/PROFILE.md"
  - "knowledge/topics/alpha-hypothesis-ledger.md"
  - "knowledge/topics/capital-scaling-prop-to-own-book.md"
  - "knowledge/topics/quarterly-quant-governance-playbook.md"
---

# Cẩm Nang Lộ Trình Naqex (`2026–2027`) — Trỏ Về Nguồn Sự Thật Duy Nhất

> **Nguồn sự thật duy nhất (Single Roadmap SSOT):** Toàn bộ kế hoạch tổng thể, mục tiêu định lượng, cổng chuyển mốc và quy tắc phân bổ vốn hiện hành nằm duy nhất tại **[planning/TOP1-SOLO-QUANT-MASTER-PLAN.md](../../planning/TOP1-SOLO-QUANT-MASTER-PLAN.md)**.
>
> Tệp này trong Kho Tri Thức (`knowledge/playbooks/`) chỉ giữ vai trò bản tóm tắt điều hướng khớp 100% với trạng thái đã khóa Vòng 3 + Bước 8 (không duy trì một lộ trình cạnh tranh thứ hai).

## Tóm Tắt Nhanh Các Khóa Bất Biến Hiện Hành (`27/11/2026`)

1. **Đội hình & thực thi:** Cố định **`7E` (`E1..E7`)** xuyên cả 3 pha trên **`1` Master EA duy nhất** (`Naqex_Master_Prop7E.mq5`, ứng viên **`C10_NEWS_ON`**, lịch tin đỏ **`492` sự kiện** `naqex_red_news_utc.csv`). Đã gỡ bỏ kiến trúc 8 EA rời cũ.
2. **Thước đo & kỷ luật vốn:** Ưu tiên **`Settled Cash`** (tiền mặt thực thu đã về ví) & ngày lịch thật; Năm 1 = **`0 VND`** kỳ vọng thu nhập từ trading. Chỉ nâng bậc sau `>= 2` chu kỳ rút tiền thật + đã hoàn 100% vốn gốc + còn đệm `>= 2×` giá vé mới (`treasury_ledger.py`). Đã gỡ bỏ `Gate-42`, thang `350K`, mua thẳng `The5ers 20K`, và luật chia cứng `30/50/20` trước hoàn gốc.
3. **Phạm vi Own-Book & `naqex-node1`:** Tập trung 1 bài toán chính (`FTMO 10K`; `The5ers HS 5K` chấm điểm song song). Các tác vụ Crypto Shadow/Maker trên `naqex-node1` đã **tắt** khi vốn riêng `< 10.000 USD` (chỉ mở Own-Book từng bậc từ `10k+` ETF gọn -> `25k+` Crypto/Carry `CEX <= 25%` -> `50k+` ETF đầy đủ -> `100k+` CME Micros).
4. **Trạng thái Holdout trung thực:**
   - `holdout_v1` (`2025-01-02..2026-11-20`, commit `521926f`): **`CONSUMED`** (cho bản nền v1).
   - `holdout_v2_prospective` (`>= 2026-12-01`) & khóa Dev `< 2025-01-01`: **`SEALED`** (`holdout_rows_analysed = 0`, `OrderSend = 0`).
5. **Chẩn đoán sự cố & tự phản biện:** Luôn kiểm ngược **`R4 -> R3 -> R2 -> R1`**, sử dụng quy trình 7 mũi [adversarial-self-audit](../../.agents/skills/adversarial-self-audit/SKILL.md) và SOP triển khai [ftmo-the5ers-live-launch-sop.md](ftmo-the5ers-live-launch-sop.md).

## Liên Kết Đọc Chi Tiết

- **Kế hoạch tổng thể duy nhất (SSOT):** [TOP1-SOLO-QUANT-MASTER-PLAN.md](../../planning/TOP1-SOLO-QUANT-MASTER-PLAN.md)
- **Trạng thái phiên hiện hành:** [CURRENT-CONTEXT.md](../../planning/CURRENT-CONTEXT.md)
- **Bảng đăng ký danh mục máy đọc được:** [PORTFOLIO-REGISTRY.json](../../planning/research/PORTFOLIO-REGISTRY.json) · **Khóa niêm phong Holdout:** [NATIVE_FTMO_HOLDOUT_LOCK.json](../../planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json)
- **Đối chiếu `C10_NEWS_ON` hậu-SSOT (Dev `< 2025-01-01`):** [C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md](../../planning/research/C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md)
- **Kho chủ đề nền tảng:** [alpha-hypothesis-ledger.md](../topics/alpha-hypothesis-ledger.md) · [capital-scaling-prop-to-own-book.md](../topics/capital-scaling-prop-to-own-book.md) · [quarterly-quant-governance-playbook.md](../topics/quarterly-quant-governance-playbook.md)
