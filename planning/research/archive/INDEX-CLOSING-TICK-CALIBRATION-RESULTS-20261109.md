# Closing tick pilot: nguồn khớp M1, chưa đo latency broker hoặc edge

[Protocol](INDEX-CLOSING-TICK-CALIBRATION-PROTOCOL-20261109.md) `08501da` trước
source fetch; 8 giờ đã thu và đối soát, không new strategy PnL. Reuse installed
`dukascopy-node` 1.51.1; package, bundle, lockfile và cache/recovery helper hashes
khớp pilot đã audit trước. Không install/upgrade/provider/account/OAuth mới.

## Đã chứng minh được gì?

| Phần | Kết quả |
|---|---|
| Matrix nguồn | 2 assets ×4 ngày đã khóa, đủ8 logical requests; không chọn theo PnL |
| Raw → decoded ticks | 115.502 joint ticks /577.510 field checks qua separate Fraction decode; giá, timestamp, thứ tự và volume scale khớp |
| Tick → source-only M1 | 960 common side bars khớp toàn OHLC, 0 conflict; cả8 late signal BidClose15:29 khớp tick aggregate |
| Target timestamps | Đủ quote sau64 targets: entry/exit×4 archived-delay scenarios×8hours |
| Negative controls | 3 mutations price/clock/order bị reject |
| Scope | Chỉ đủ đăng ký economic latency comparison riêng; chưa full history, actual delivery/processing/broker latency hoặc edge |

4 dates: 02/01/2019, 01/07/2019, 03/01/2022, 01/07/2022. Cửa giờ như
protocol, không mở own2025+. Previous close và first-half09:59 không nằm trong
pilot: vẫn inherited evidence, không claim all-feature tick proof. Source match
cùng provider/agent không là independent feed hoặc human/model signoff.

## Chờ quote theo timestamp trong mẫu này

Bảng là **thời gian từ target đến first archived quote**, không thời gian broker
khớp lệnh. Mỗi ô có8targets/asset (entry+exit trên4dates). Không tính PnL hoặc
chọn delay bằng hiệu quả giao dịch.

| Target = decision + | US500: wait min–max | NASDAQ: wait min–max |
|---|---:|---:|
| 200 ms | 26–7.701 ms | 1–389 ms |
| 1 s | 18–6.901 ms | 0–94 ms |
| 2 s | 44–5.901 ms | 2–486 ms |
| 60 s, next-M1 baseline | 62–2.981 ms | 83–226 ms |

Last archived quote trước decision có age tối đa10.946ms ởUS500,917ms ởNASDAQ.
Không suy archive ít events thành thị trường không có quote, giá bất biến hoặc
broker/live quote stale; archive và delivery/heartbeat có thể khác. Next-M1Open
là interval proxy, không giả định measured latency60s. Nếu xây model mới cần
khóa first-quote/expiry/missing/exit behavior trước outcomes; không auto nới live
freshness/risk hoặc dùng một quote trong mẫu làm proof mọi ngày.

## Hậu kiểm và bước tiếp

Còn một method-transfer gap cần khóa rõ trước economic comparison: parent
ra ở Open15:59, còn paper dùng cash close16:00. Giảm delay nhưng giữ scheduled
exit cũ không tự tái hiện paper window. Thay scheduled exit là recipe/model
revision mới, không semantics-preserving optimization. Pilot hiện kết thúc
16:00, chưa chứng minh first-quote availability sau cash close; cần source
admission bổ sung nếu contract mới dùng thời điểm đó. Không tune giờ theo PnL.

Producer19,158s wall/16,282s CPU; reviewer8,820s wall/8,813s CPU. 0 cache hits
trong8hour sources mới; đã giữ raw seals để lần sau reuse. Source caches cũ
không rewrite, không patch canonical M1 hoặc old books. Mọi worker terminal0;
không broker/model calls/strategy simulation mới. Không GPU hoặc service mới.

Nếu tiếp nhận gần1.000giờ full development history, cần xem chi phí decode/hash/
review trước: phép ngoại suy tuyến tính từ8hours gợi ý Fraction review có thể
hàng chục phút, **chưa phải benchmark full workload hoặc ETA**. Bước hữu hạn
tiếp là profile trên chính pilot đã consumed, thử integer-grid/batched checks
nếu hotspot xác nhận, so toàn fields/OHLC/quote locators với frozen Fraction
oracle rồi mới chọn implementation. Không bỏ validation hoặc lấy sampled
parity làm universal correctness bound. Freeze full-history intake và economic
latency protocol riêng trước fetch/outcomes; không lặp8source fetch hoặc4books.

Catalogue vẫn77 records/58policy-model versions/25native/9controls; source
pilot không thêm strategy version. R076/R077 vẫn fail; chưa challenge candidate.
Consensus signal filter vẫn queue, không mở thêm variants trước calibration.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/index-closing-tick-calibration-v1/` giữ config/manifest/source
snapshots/hour exports/raw proof/seals/result/review/progress/events. Raw ở
existing `source-hour-cache-v1/`; không xóa hoặc gọi cache là backup độc lập.

- Result SHA: `b8439892eb87566ac8ae6bd0c05c052a1bff92378732899c2dc14131b7eebf64`.
- Review receipt SHA: `ba9e105ee5af756ba4877b2daf0db607d14310115fcac25715f13c8a0abf7b69`.
- Reviewer source SHA: `9031fec592fea53eb734741cefdac2f41648e84702cb43d522b02de5223ce6df`.
