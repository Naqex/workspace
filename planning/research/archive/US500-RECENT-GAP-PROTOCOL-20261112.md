# Kiểm phút thiếu chung RS01/RS02: source-only

Owner 12/11/2026 yêu cầu kiểm tiếp sau recent screen. Câu hỏi: phút
04/04/2025 11:02 New York (15:02 UTC) có tick nguồn thật để tái tạo không?
Giữ [results/unknowns](US500-RECENT-SCREEN-RESULTS-20261112.md) và mọi book cũ.
Đây là chẩn đoán source sau khi đã biết outcome 2025, không trial mới hoặc OOS.

## Phạm vi khóa trước source response

- Chỉ `usa500idxusd`, hour 2025-04-04T15:00Z inclusive →16:00Z exclusive;
  target minute15:02→15:03 UTC. Không mở RS02/2026 hoặc toàn năm tick.
- Reuse dukascopy-node1.51.1/native tick JSON, existing source-hour cache,
  explicit `checkResearchWindow` với owner grant
  `us500-recent-discovery-20261112` (2025→12/11/2026 exclusive).
- Một request source hour; deadline180s, shared recovery helper hữu hạn,
  không retry403/429/WAF/auth/schema. Không tài khoản/secret/provider trả phí.
- Pin script/protocol/native package/bundle/lock/helper, input inventory,
  recent source proof và hash các JSON Bid/Ask tháng04/2025; không sửa file cũ.
- Snapshot raw/native rows/hash/progress/events và kết quả review trong output
  mới `execution-v1/us500-recent-gap-source-v1/`. Broker/model calls0.

## Kiểm và tiêu chí quyết định

Reuse independent Fraction tick delta decoder của review gap-hour đã kiểm
trong campaign (`review-nasdaq-M1-gap-ticks-v1.py`), không native decoder làm
oracle cho chính nó. Kiểm toàn rows/ordering/side/price grid/volume và mutation
price/time/order; so OHLC từ tick với toàn bộ M1 đã có trong đúng giờ.

- Tick trong target + exact common-minute OHLC hai side, không bất thường:
  chỉ đủ đề xuất registration cho derived repair; chưa tự patch hoặc rerun PnL.
- Tick trong target nhưng common M1 khác hoặc schema/scale không khớp:
  chưa admit patch, lưu mismatch để chẩn đoán.
- Không tick trong target: ghi không phục hồi được bằng endpoint này; không
  ffill, invent price hoặc suy chắc chắn thị trường không có quote.
- Transport/source unavailable: ghi unknown; không đổi thành zero-tick.

Source cùng provider dù khác endpoint không phải feed độc lập. Tick absence
không chứng minh không thể khớp lệnh ở broker khác. Không tự nâng verdict
edge/prop/authority hoặc thay score vì probe này. Kết thúc bằng locator, delta
và bước nhỏ tiếp theo; không mở vòng tải toàn bộ lịch sử.
