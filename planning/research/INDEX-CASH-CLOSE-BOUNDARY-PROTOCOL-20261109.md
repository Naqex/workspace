# Bổ sung nguồn tại cash close, trước economic recipe mới

Theo gap đã ghi trong [closing pilot](INDEX-CLOSING-TICK-CALIBRATION-RESULTS-20261109.md)
và [performance results](INDEX-TICK-REVIEW-OPTIMIZATION-RESULTS-20261109.md).
Mục đích: biết source Bid/Ask có quote sau 16:00 và phép biến đổi có giữ đúng
nguồn không. Không PnL, không thêm strategy version chỉ vì thu nguồn.

Ngày/assets giữ từ pilot trước, không chọn từ outcome: first regular cashday
tháng 1 và 7 của development years 2019/2022; `usa500idxusd`, `usatechidxusd`.

| Ngày | Giờ UTC bổ sung | Giờ New York |
|---|---|---|
| 02/01/2019 | 21:00–22:00 | 16:00–17:00 |
| 01/07/2019 | 20:00–21:00 | 16:00–17:00 |
| 03/01/2022 | 21:00–22:00 | 16:00–17:00 |
| 01/07/2022 | 20:00–21:00 | 16:00–17:00 |

8 instrument-hours mới, không fetch lại 8 giờ 15:00–16:00 đã sealed.
Mỗi request đúng một native hourly URL; one writer, deadline 180 s, CANCEL,
progress/events/PID/sealed-hours/failure. Output mới private
`execution-v1/index-cash-close-boundary-v1/`, raw cache owner cũ. Không own
2025+, new provider/account/OAuth/paid service, broker hoặc runtime restart.

## Intake và correctness trước kết luận

- Reuse pinned `dukascopy-node` 1.51.1, existing recovery/cache/process/format;
  batch 1, request interval 300 ms, native retry 0, WAF/token cache off.
  Transient retry chỉ bounded existing helper, giữ cap/deadline; không retry
  403/429/auth/schema hoặc đổi source. Source empty vẫn giữ, không carried quote.
- Dùng `source_pin_guard.cjs`: full parent/canonical inputs trước use/final;
  active collector/reviewer/protocol/helpers/package/config trước/sau mỗi hour.
  Canonical M1 không đọc trong loop, consumer full-hash lại trước use. Raw bytes,
  output/proof hashes mỗi hour, frozen source snapshots. Fail latch không được
  reset trong cùng attempt để hợp thức hóa complete.
- Python consumer dùng integer columns mới, đối chiếu **toàn native tick fields**
  bằng frozen Fraction oracle của pilot trước, không sửa oracle. Giữ exact
  grid 0,001, native volume scale, timestamp/ordinal, duplicate clock và missing.
- So mọi common M1 side OHLC với source-only canonical history đã admitted;
  ghi riêng ticks without M1 / M1 without ticks / mismatch, không ép đầy đủ.
  Cả archive mới và canonical parent vẫn cùng provider, không independent feed.
- Tìm first archived quote ở 16:00 + 200 ms / 1 s / 2 s / 60 s; giữ source
  ordinal, target/first/wait, Bid/Ask/volume. Dùng giờ cũ để báo last quote age
  trước close; không forward-fill. Actual price/clock/order/volume mutations
  phải bị reject. No quote/mismatch giữ unknown/inconclusive cho đúng scope.

Được admission cho đăng ký economic scenario nếu đủ 8 exact scoped outputs,
full fields parity, không source conflicts và 32 targets có quote. Chỉ có giá
archived tại target, chưa actual delivery/fill/broker latency, full history,
previous-close/09:59 tick proof, clean OOS, account/prop hoặc edge.

## Method và bước tiếp đã định trước outcomes

Đọc lại 09/11/2026 [Baltussen và cộng sự, JFE 2021](https://academicweb.nd.edu/~zda/intramom.pdf),
§1: rROD dừng ở đầu nửa giờ cuối, rLH kéo tới close. Bản parent dùng entry
15:31/exit 15:59 khác window; không gọi đổi exit là sửa tốc độ hoặc tự xóa
parent negatives. CFD khác futures, không claim paper replication hay gamma.

Pilot không chọn delay có PnL đẹp. Nếu admission đạt, chốt scenario primary
1 s, stress 2 s và proxy 60 s, entry decision 15:30, scheduled exit decision
16:00, missing/expiry và costs trong **economic protocol riêng trước PnL**.
200 ms chỉ source diagnostic; không thêm scenario vì pilot PnL (không đo).
Nếu source không đạt, lưu gap/partial proofs rồi chọn next bounded action;
không tự chase archive toàn bộ hoặc biến unknown thành zero.
