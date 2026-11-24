---
doc_type: evergreen
domain: owner
updated_utc: 2026-11-24
---

# Nhật ký Quyết định & Trade-off của Owner (Decisions Journal)

> Lưu các quyết định chiến lược xuyên dự án (ngày, lý do, đánh đổi đã chấp nhận, điều kiện xem xét lại). Không thay thế ADR kỹ thuật trong từng dự án mà nối tới chúng.

| Ngày | Quyết định | Lý do & Trade-off đã chấp nhận | Điều kiện xem xét lại |
|---|---|---|---|
| `2026-11-23` | **Chuyển sang kiến trúc Quant Factory 4 lớp không gắn cứng** (`configs/` JSON + `.npz` zero-pickle + Numba JIT + `Naqex_PropGuard.mqh` + `system_doctor.py`) | Bỏ nút thắt tuần tự và copy-paste ở `passN_*.py`; chấp nhận giữ `pytest_full ~25s` (1.567 tests) thay vì rewrite tests cũ vì đã đạt sweet spot | Khi thêm lớp tài sản hoàn toàn mới (Futures/Options) hoặc `pytest_full > 60s` |
| `2026-11-23` | **Đưa raw JSON `> 1 MiB` sang E: Cold Archive, giữ tóm tắt có SHA trong Git** | Sửa dứt điểm `check_anti_bloat.py`, giữ repo nhẹ và đọc nhanh cho AI; bản raw luôn khôi phục nguyên byte từ E: | Khi tạo bất kỳ biên nhận mới `> 900 KB` |
| `2026-11-23` | **Mở khóa Holdout `2025–2026` một lần duy nhất trên kho tách biệt (`.runtime/holdout-m1-cache/`)** | Giữ nguyên vẹn kho Development `2018–2024` & 1.567 tests; chấm điểm không thiên lệch (`M = 1`) ra kết quả `9/9` dương, `PORT_7E = GO` | Không mở lại để chỉnh tham số; bước tiếp là MT5 Real-Tick + Free Trial `14` ngày |
| `2026-11-23` | **Chọn Phanh Vol 1 chiều `[0.55, 1.00]` + Trần `1%/mã` Funded** | Loại Vol-Targeting 2 chiều (`1.35×`) vì làm tăng Daily DD; trần `1%/mã` phòng luật gộp FTMO mà không giảm lãi | Sau khi có dữ liệu TCA thực tế từ FTMO Free Trial |
| `2026-11-23` | **Khởi động Nhánh Alpha #2 Crypto Spot (`projects/quant-trading`) song song Nhánh FX/Index Prop** | Tương quan `r = 0.02`, nâng Pod lên `Sharpe 1.91–1.99`; giữ Spot Long/Cash không đòn bẩy trước khi xét Futures/Funding | Khi thay xong rổ 5 coin bằng lọc thanh khoản trượt nhân quả (loại survivorship bias) |
| `2026-11-23` | **Dựng Knowledge Vault `knowledge/` (Markdown Source of Truth) + SQLite FTS5/Hybrid (`brain_cli.py`) + Multi-Source `research_cli.py`** | Tránh vector DB nặng/daemon nền, tránh nhốt memory vào 1 nhà cung cấp AI; giữ dữ liệu chủ sở hữu minh bạch, Git-diff được, tra cứu `< 30 ms` | Nếu số tài liệu vượt `5.000+` file hoặc cần nhúng đa phương thức (ảnh/audio) sâu hơn |
| `2026-11-24` | **Chốt bộ máy Prop #1 `A1_V1_LIVE8` & chuyển toàn bộ vận hành 24/7 sang Home-VPS `naqex-node1` + Heroku EU + Telegram Guard** | Nghiên cứu v1 vs v2 chứng minh cắt bớt bot làm tụt lãi và tăng DD; giữ `A5_V2_ROBUST_TIER_9E_EUR` làm dự phòng khi trượt giá `>= 1,5×`. Tách hoàn toàn máy dev khỏi tải nền `0` tác vụ | Khi trượt giá thực trên live vượt `1,5×` stress hoặc khi đã rút lãi đủ thuê VPS sát sàn |
| `2026-11-24` | **Chốt bộ mục tiêu "Chuyên gia độc lập bậc nhất (Top 1%)" & Kế hoạch 6 khía cạnh ([TOP1-SOLO-QUANT-MASTER-PLAN.md](../../planning/TOP1-SOLO-QUANT-MASTER-PLAN.md))** | Tối ưu bằng **Tiền lời ròng kỳ vọng (EV)** ở vùng rớt vé thi `22%–35%` (vòng thi) rồi hạ cứng `1,0×` (`< 1%` cháy khi Funded); chẩn đoán rủi ro bắt buộc `R4 -> R3 -> R2 -> R1`; chi phí hạ tầng `30–150 USD/tháng` chỉ mở khi tự nuôi từ lãi thật | Rà soát định kỳ theo từng mốc qua cửa (sau `14` ngày Free Trial, sau `2` lần rút lãi, và định kỳ hàng quý) |
