# Asia→London 2023 — recovery sau lỗi checkpoint

Kế thừa [protocol](H1-SURVIVOR-TICK-REVIEW-20261108.md) và
[campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md). Đây là sửa lỗi
engineering trên dữ liệu đã dùng, không phải trial đổi chiến lược hay clean OOS.

## Phạm vi khóa trước recovery

- Chỉ candidate `eurusd-h1-asia09-15tokyo-london-break-atr14x1p5-r025-v1`,
  warmup 01/11–31/12/2022 và evaluation 01/01–31/12/2023; exact raw/spec/risk/
  cost/prop profile/horizons kế thừa registration cha. Không mở 2025+.
- Lượt cha `h1-survivor-tick/batch-2023-v1/asia-break` dừng ở reference sau
  27.223.813 ticks. Không có completed scenario seal để reuse. Giữ attempt
  này; prepared inputs vẫn dùng khi binding hợp lệ, không sửa hash để reuse.
- Nguyên nhân: lệnh quyết định từ nến đã đóng vẫn pending, nhưng khoảng trống
  quote có thể thêm checkpoint financing sau quyết định. Validator cũ chỉ
  xét checkpoint gần nhất nên từ chối đúng lệnh đã xếp hàng. Bản sửa tìm
  canonical decision và kiểm mọi cash checkpoint sau đó giữ cùng operation.
  Chặn decision giả hoặc cash event thay lệnh vẫn bắt buộc.
- Source recovery ở checkout riêng `research-metals/trader`, numerical pins
  mới ghi trong JSON registration; không sửa D: source của ba worker khác.
  Optimization chỉ index trong một lượt validation và bỏ lượt ledger validate
  trùng trên typed result vừa được tạo. Không bỏ whole-history validation,
  pilot constraints hoặc transactional observer commit.
- Một numeric worker, tối đa 7.200 giây, batch 10.800 giây; preparation tối đa
  1.800 giây theo supervisor. Không automatic retry/mid-scenario resume. Đây
  là deadline, không ETA. Source snapshots/config/log/receipt lưu attempt mới.
- Protocol cha ghi 2 workers/batch, JSON cha lại còn `max_numeric_workers: 1`
  cùng recovery/prior-exposure text của Compression. Ghi nhận metadata copy
  defect; không sửa registration lịch sử hoặc gọi nó hoàn hảo. Bản này thống
  nhất 1 worker và lineage Asia→London; economics không thay đổi.

## Kiểm trước và sau run

Ca thực tế Dec2023 qua bản sửa: 442.341 ticks, candidate roundtrip/accounting
đạt, 6 closed trades, −9,42 USD reference; không annual kết luận. Retained-state
benchmark 6 flat windows/1.022 ticks/6.832 ledger events giữ exact final SHA:
baseline 8,89–9,02 giây; indexed 3,33–3,38; single validation 1,80–1,84 giây.
Không suy tỷ lệ này ra cả năm. Focused 77 tests/66 subtests đạt trước đăng ký.

Sau run phải đọc completed seal/dossier/accounting/3–6–12m prop paths và
source bindings; không dùng exit0 làm qualification. C1 chưa đạt nếu chưa có
selection-aware edge, fresh holdout và forward/reconciliation. C2 vẫn phải
review economic assumptions và metadata gaps, không chỉ integrity.

Không tăng risk, đổi rules/cost/window để cứu outcome. Kết quả âm giữ nguyên;
bug mới thì giữ attempt và sửa phần affected trước numeric retry có chủ đích.
