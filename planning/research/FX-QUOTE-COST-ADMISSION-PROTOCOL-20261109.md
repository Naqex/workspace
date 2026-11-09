# FX quote-cost admission — protocol 09/11/2026

Đăng ký trước fetch/đọc bốn giờ joint ticks mới. Theo owner tiếp research
NHP/Fury; chỉ học yêu cầu engineering, không clone closed EA/khẳng định entry
của họ hoặc tạo candidate/PnL mới. [Campaign](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
C1/C2 còn mở; catalogue 81/58 giữ nguyên. Không revive exact NYMA4 negatives.

## Câu hỏi và fixture cố định

Joint Bid/Ask thực sự, khoảng vắng quote và chi phí giả định có thể đo đủ
chính xác để thiết kế nghiên cứu scalp riêng không? Chưa hỏi strategy có edge.
[BIS WP836](https://www.bis.org/publications/working-paper-836-fx-spot-and-swap-market-liquidity-spillovers)
liên hệ funding liquidity và spot spreads; không cung cấp alpha rule cho CFD.
[NHP listing](https://www.mql5.com/en/market/product/68327) chỉ mô tả pending/
SL/multiple pairs, không mở exact entry; Fury optional grid đã được survey.

Chọn lại hai dates của oil source pilot trước đây để đối chiếu winter/summer,
không theo PnL: 2019-01-09 và 2022-07-13. Mỗi ngày hai giờ New York 16:00–17:00
và 17:00–18:00. UTC tương ứng 21/22 ngày 2019 và 20/21 ngày 2022. Cả bốn giờ
là EURUSD từ existing Dukascopy/pinned dukascopy-node1.51.1, joint tick JSON,
raw price grid0.00001/pip0.0001, volumes millions, same-ms order giữ nguyên.
Source riêng lẻ, không execution/broker quote certification hoặc liquidity depth.

## Thu / kiểm / tính

- Bốn requests, một URL mỗi giờ, no retries/WAF/auth/new provider; reuse cache
  hiện có. Deadline180s/cumulative failure cap1, one writer/CANCEL, status/events.
- Raw/seal/producer/reviewer/native/lockfile/protocol hashes và snapshot trước
  requests; không overwrite output hoặc raw. Own2025+ đóng, broker/model calls0.
- Dùng native formatter và kiểm toàn bộ clock/Bid/Ask/volumes bằng Fraction
  delta decoder đã dùng trong NYFX tick source review; không sửa original helper.
  Same agent/provider, không gọi là independent human/feed signoff.
- Mỗi giờ: số quote, số phút có quote, tick-weighted spread p50/p95/max theo
  nearest-rank, gap lớn nhất gồm hai biên giờ. Empty hour là source unavailable,
  không forwardfill hoặc giả giao dịch được. Same-ms quote vẫn đếm riêng.
- Chi phí minh họa: spread quan sát + 0.5pip roundtrip commission (5USD/lot,
  pipvalue10USD/lot) +0 reference hoặc0.4pip roundtrip stress slippage. Đây là
  declared scenario, không phí verified của quỹ/account; không biến observed
  source spreads thành target broker spread hoặc time-weighted distribution.
- Synthetic tests/mutations: crossed/offgrid/nonfinite/out-of-scope/unordered,
  missing hour, percentile/timing, raw-price/clock/hash/binding/authority sai phải
  bị chặn trước gọi admitted. Không đọc returns để chọn giờ/SL/TP/threshold.

## Acceptance và cách dùng

Đạt fixture khi 4 scopes/seals/full raw transform và arithmetic review đúng;
đủ quotes chỉ cho biết nguồn có thể phục vụ bước thiết kế tiếp. Nếu thiếu thì
báo unknown, không tự đổi ngày/giờ. Không đặt cổng `spread thấp = có edge` hoặc
calibrate tín hiệu từ bốn giờ. Không khai thác lỗi feed/rollover; đây là đo chi
phí để tránh assumptions sai và chuẩn bị exclusions có căn cứ cho rule riêng.

Private output: `execution-v1/fx-quote-cost-fixture-v1/` trong root campaign.
Đo source/compute/review wall/CPU, giữ failures; không source-policy promotion,
new account, trade, holdout hoặc service. Bước sau: method admission cho quy
tắc sở hữu hợp pháp khác exact recipes đã gác; đăng ký trước economics nếu đủ
căn cứ, hoặc tiếp EIA khi có actual historical release/PIT/endpoint proof.
