# PreECB: đường giá trước 14:00 — đăng ký 08/11/2026

Owner giao đo MAE/MFE/path risk và bàn giao dễ hiểu. Đây là chẩn đoán tiếp từ
[attribution](PRE-ECB-WRAPPER-ATTRIBUTION-RESULTS-20261108.md), trên dữ liệu đã
exposed 2019/2022, không clean OOS hoặc chiến lược mới. Giữ entry SELL 02:00
New York, endpoint 14:00 Berlin, quantities đã quan sát và cost cũ. Không tối
ưu ngưỡng, đổi stop/lot hoặc gửi lệnh; parent vẫn parked.

## Đo trước khi xem outcomes mới

- Commonmask đúng 519 dates của attribution, mỗi ngày một SELL, không nhân đôi
  hai cost scenarios. Giữ riêng mọi ngày thiếu entry/exit, đặc biệt 25/12/2019;
  không fill0 hoặc dựng account carry từ mask thiếu.
- Entry Bid và endpoint Ask lấy từ raw-bound component đã review. Chỉ dùng H1
  observed cache nếu loader hiện hành nhận đúng raw/runtime/source/hash seal;
  không sửa key hoặc rebuild để ép pass. Entry/exit phải khớp time, sequence,
  Bid/Ask đầu giờ. Cả hai targets là whole UTC hour dù DST thay đổi.
- Lấy extrema Ask của các giờ [entry-hour, exit-hour) cộng **quote đầu tiên**
  tại endpoint. Không dùng high/low của cả exit-hour vì sẽ nhìn tương lai.
  Thiếu giờ, sai endpoint hoặc sequence continuity thì ghi unresolved/fail;
  không mượn extrema Bid/mid cho SELL. Có đủ observed hours không chứng minh
  thị trường/feed/broker không có gaps, hoặc timestamp của extrema.
- MAE=max(0,maxAsk-entryBid), MFE=max(0,entryBid-minAsk), đổi pip bằng 0,0001.
  Worst hypothetical liquidation dùng lot đã quan sát, contract100k và round
  trip commission5USD/lot; stress thêm slip0,00002 mỗi side (tổng4USD/lot).
  Chia worst loss cho planned25USD để diễn giải R, **không** prop/account DD.
  Vẫn đo đến14:00 dù parent đã SL: đây là counterfactual path, không actual
  held-position excursion và không chứng minh noSL policy an toàn.
- Báo từng năm: count, nearest-rank p50/p90/p95/max MAE/MFE và worst loss/R,
  số dates worst loss>25USD, endpoint reference/stress net; nhóm endpoint
  reference positive có MAE riêng. Không gọi endpoint winner là biết trước.
  Không estimate pass probability hoặc bootstrap/DSR từ các số tổng này.

## Kiểm và giới hạn

Fixtures: hand-calculated SELL/spread/cost/R, endpoint-hour future extreme
excluded, UTC/DST alignment, missing hour, source/sequence mismatch, no double
count cost rows, invalid quantity/NaN. Rà độc lập **4 resolved dates sớm nhất
mỗi năm** theo entry trước numeric: raw byte scan/hash toàn nguồn nhưng chỉ
parse selected intervals, tính min/max Ask bằng implementation khác. Giữ
source sequences/endpoint proof; kiểm actual selected paths và negative
tampering. Review cùng agent bằng code khác, không kiểm toán độc lập.

Deadline numeric180s, rawreview180s, status/events/failure/CANCEL, output mới
`execution-v1/pre-ecb-path-risk-v1`; không overwrite/retry tự động. Pin source,
protocol/tests/fixtures/input seals trước compute. Lưu runtime/wall/CPU và
reuse so với simulationcalls0; không bịa speedup toàn pipeline. Sau kết quả
chỉ quyết định có đủ căn cứ thiết kế stop version mới hay còn data/risk gaps.
2025+, broker, tài khoản/provider mới, challenge payment/production vẫn đóng.
