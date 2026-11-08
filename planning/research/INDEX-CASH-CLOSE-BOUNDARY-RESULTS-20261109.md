# Cash close: nguồn có quote sau mốc 16:00 trên 8 giờ pilot

[Protocol](INDEX-CASH-CLOSE-BOUNDARY-PROTOCOL-20261109.md) `8a43077` trước fetch.
Đã thu/review 8 giờ mới, **14.847 joint ticks / 74.235 fields**, 240 common M1
side OHLC exact, 0 conflict. Cả 32 target timestamps tìm được quote. Chỉ đủ
source admission cho đăng ký economic scenario, chưa strategy PnL hoặc edge.

8 giờ trước close giữ nguyên, không fetch lại. Lát mới dùng integer inspector
và scoped pin guard đã benchmark; frozen Fraction oracle vẫn kiểm toàn tick
fields. 32 actual price/clock/order/volume mutations bị reject. Không sửa
old source/history, parent rules, fees hoặc verdict âm.

## Những con số nói gì?

Mỗi instrument-hour chỉ có **15 populated minutes**, không 60; không fill các
phút vắng bằng carried quote. Common M1 cùng thiếu đúng các phút không có tick,
không conflict; việc này chưa chứng minh tính liên tục market/broker thật.

| Target sau decision 16:00 | US500 wait sau target, min–max | NASDAQ wait sau target, min–max |
|---|---:|---:|
| 200 ms | 4–82 ms | 22–130 ms |
| 1 s | 2–125 ms | 30–83 ms |
| 2 s | 36–196 ms | 3–160 ms |
| 60 s | 217–15.018 ms | 52–1.820 ms |

Quote age cuối cùng trước close: US500 68–488 ms, NASDAQ 16–259 ms, trên đúng
4 ngày/asset. Đây là archived event timestamps, không actual arrival/processing
delay, slippage, thanh khoản khớp thật hoặc SLA. Không chọn latency bằng PnL;
chưa tính PnL. Không thể suy full history từ 8 giờ này.

## Vận hành, dữ liệu và hậu kiểm

Producer 6,618 s wall / 2,907 s CPU; reviewer 7,427 s / 7,422 s CPU. 0 cache
hits trên 8 requests mới, mọi workers terminal 0. Full pin checks 2, active
checks 17, hashed 637.735.211 B; input/canonical checks trước dùng và final,
raw/output/proof seals mỗi giờ, reviewer full-hash lại. M1/source inputs không
đọc giữa source loop. Không so timings với pilot 115.502 ticks như một speedup.

Private base: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Output `execution-v1/index-cash-close-boundary-v1/`: config/manifest/snapshots,
hours/proofs/seals/result/review/progress/events. Saved scripts:
`prepare-index-cash-close-boundary-v1.cjs`, `review-index-cash-close-boundary-v1.py`.
Node syntax check và Python compile đạt trước source; no-overwrite output guard,
deadline 180 s, bounded existing retry, no WAF/auth/provider fallback.

- Result SHA: `182cecb12017a4046201ab887abfb1072280ce5621ceaf0f0307ef3d52607c31`.
- Review SHA: `bb436944be05fda69d647733dde0046b33788ecf573378f77a994a913acfb829`.
- Reviewer SHA: `68c7269eaa4aee21d53aa3efa844995a041aeaa961a0932ee5d48e5f782e7837`.

Contracts đã được dùng trong consumer thật; không thêm format DB, dependency,
skill hoặc dịch vụ mới. Không có evidence cần tối ưu thêm decoder ở lát này.
Catalogue vẫn 77 records /58 policy-model versions; source pilot không thêm
policy. Goal active, chưa challenge-qualified.

**Tiếp:** khóa full source intake cho các regular development cashdays 2019/2022,
reuse 16 giờ pilot/cache, một writer và resume sealed hours. Economic recipe mới
cần đăng ký riêng entry 15:30/exit 16:00, primary 1 s, stress 2 s/proxy 60 s,
expiry/missing/BidAsk/cost/control/triage trước outcomes. Đó là method revision
có selection history, không sửa parent 15:31→15:59 thành pass hoặc claim paper
futures replication. Holdout2025+, broker, tài khoản và phí mới không mở.
