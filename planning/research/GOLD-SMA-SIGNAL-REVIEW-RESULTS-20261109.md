# SMA vàng: tín hiệu đã khớp oracle riêng, chưa đủ điều kiện challenge

Theo [protocol](GOLD-SMA-SIGNAL-REVIEW-PROTOCOL-20261109.md) freeze `da2ef8e`,
đã đối chiếu đủ 30 sổ Discovery9 cũ: 15 annual-reset years 2010–2024 × hai
declared costs, exact SMA20/80–ATR14, vốn 50k/risk125USD. **Không tìm thấy
sai lệch SMA/ATR, quyết định, sizing hoặc mapping quyết định→fill trong phạm
vi kiểm.** Không tính lại PnL, thay rule, giảm phí hay mở holdout mới.

## Đã kiểm gì?

| Lát | Bằng chứng thực thi |
|---|---|
| Binding | Raw hash gốc, 21 original source snapshots và 34 baseline artifacts gồm 30 exact SMA50k books còn khớp; không thay bằng current Trader khác version |
| Source aggregation | Dựng lại integer-tick H1 từ 5.399.878 Bid M1 rows đã exposed; 91.101 H1. H4 nhận đủ bốn giờ; excluded H4 khớp từng book, không padding |
| Tín hiệu và không tín hiệu | 40.662 H4 evaluations qua 30 books: 616 quyết định khớp và 40.046 no-signal; đếm cả hai scenarios trên cùng dữ liệu, không 40.662 quan sát độc lập |
| SMA/ATR/sizing | SMA cross/equality bằng integer sums; Wilder ATR precision80 so native28 với frozen absolute tolerance1e-23USD; stop distance và quantity khớp mọi quyết định được ghi |
| Bàn giao sang fill | 450 entry fills và 166 strategy exits khớp queued decisions tại first modeled minute của H1 tiếp theo có nguồn; 0 pending cuối năm. 450 entries gồm 439 closed + 11 còn mở ở các annual books/scenarios |
| Negative checks | 5 focused tests đạt; 6 actual mutations về time/side/distance/quantity/omission/duplication đều bị reject |

Oracle [h4_sma_signal_oracle.py](../../tooling/ai-engines/h4_sma_signal_oracle.py)
không import simulator, candidate hoặc indicator implementation. SMA dùng
`4*sum(last20)-sum(last80)` thay hai phép chia; ATR được tính riêng trong
Decimal80. Constant spread/2 dịch toàn OHLC nên không đổi SMA difference/TR;
không giả Ask được quan sát. Warmup bắt đầu Nov1 năm trước, reset từng book.

**Giới hạn quan trọng:** side/position tại lúc quyết định lấy từ sealed trade
path. Stop trong H1 được xem đã đóng trước H4 observe như coarse semantics.
Vì vậy đây là conditional signal-path audit, chưa là một simulator độc lập
chứng minh mọi stop/gap/position transition đúng. Kiểm giá/sổ tiền trước vẫn
có scope riêng; chưa first-crossing ticks, target-feed/spec/fees, native prop,
clean OOS, prospective reconciliation hoặc owner handover. Cùng agent với
code/số học khác, không independent human/feed sign-off.

## Thời gian, tái sử dụng và quyết định

| Phase | Wall đo được |
|---|---:|
| Hash/bind receipts | 5,133 s |
| Dựng H1 từ raw và lưu derivative | 35,136 s |
| Toàn bộ signal/fill comparisons | 0,836 s |
| 6 actual mutations | 0,004 s |
| **Toàn controller** | **41,207 s**, CPU36,000s |

Không tính research/authoring/tests/Git vào 41s; không so thành speedup với
review cũ khác workload. 5-test unittest body0,003s, không end-to-end wall.
Không failure/retry hoặc job còn chạy. Không có evidence cần GPU/Rust hoặc
framework/skill mới. Lần này phải đọc raw để dựng oracle input; `hours.json`
và manifest hash đã giữ để lượt sau dùng đúng bindings không phải đọc lại.

Delta C2: khoảng trống “chưa có SMA/ATR signal oracle” trong [review cũ](GOLD-SMA50K-REVIEW-20261108.md)
đã được đóng **trong phạm vi conditional ở trên**. Không phát hiện bug cần sửa
producer/PnL. Verdict giữ research survivor/low challenge priority: time-fit
đã yếu và target funding/spec còn thiếu. Không dùng correctness pass làm
economic pass, không thêm trial hoặc thay 90 records/58 account-policy versions.
Goal active, C1/C2 toàn chiến dịch chưa đạt.

Bước tiếp của Gold cần evidence mới về target contract/cost hoặc một hypothesis
triển khai có cơ sở, không rerun cùng books hoặc tiếp stop/lot/holding grid.
Hướng [vàng–bạc đã rà lại](GOLD-SILVER-METHOD-DELTA-20261109.md) cũng giữ gác;
không dùng full-sample regime labels để cứu historical outcomes.

## Artifact tái hiện

Private campaign root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
controller `review-gold-sma-signals-v1.py`, attempt
`execution-v1/gold-sma-signal-review-v1/`. Giữ manifest, frozen protocol,
reviewer/oracle snapshots, hours derivative, events/progress/result.

| Artifact | SHA256 |
|---|---|
| Manifest | `e7f190cbbf88c87c3cef50c05f0995fcaf5888f1e2e6a40eee31ef6d1f51cff4` |
| Result | `d199ecba1389d53da60134b98a1fbe5b64325815335c95069ff2947816120d91` |
| H1 derivative | `ee51e4c63a4255916c2d47f7b6fbe755f564b073e0a28683e853d2cbde559328` |
| Reviewer snapshot | `432dbbe581c01a11623d1ef97277fb9705ce2ae9014d3dee114d8cb4e612df3a` |
| Oracle snapshot | `28a4894e29b477b8bf5344a3e564872f401c74cf60f1ca92cc6378e821559b17` |

Command đã chạy: bundled Python3.12.14 `-m unittest discover -s
tooling/ai-engines/tests -p test_h4_sma_signal_oracle.py -v`, rồi bundled
Python với exact saved controller ở trên. Handle79741 đã terminal exit0.
0 simulator/market-network/broker/model calls; không thay source/runtime
Trader, secrets, account hoặc own market2025+.
