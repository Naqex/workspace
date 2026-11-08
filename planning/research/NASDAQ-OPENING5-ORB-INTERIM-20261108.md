# Opening5: phần đã đóng dương, kết quả cả năm vẫn chưa xác định

[Protocol](NASDAQ-OPENING5-ORB-PROTOCOL-20261108.md)173928e, implementation
d5aad5b.8modeledbooks đã terminal và separate Fraction first-hit/sizing/cash
review khớp; chưa retained/challengequalified. Không gọi annualnet khi đangunknown.

Initial10kUSD mỗi year, plannedrisk25USD/entry, không compound. Đây là account
nghiên cứu theo declared NASDAQ geometry/costs, không broker lot/actualaccount.

| Năm | Closed trades trước nguồn bị thiếu | Lãi đã đóng chuẩn/cao,USD | Annual equity net |
|---|---:|---:|---|
|2019|16|+186,21 / +136,98|N/A, unknown từ25Jan14:49UTC|
|2022|191|+769,11 / +649,63|N/A, unknown từ18Oct15:24UTC|

MissingM1 xảy ra khi đang SELL, không phải lỗi process hoặc signal. Giữ
position/SL/TP/lastknownmark, chặn235laterentries2019 và51năm2022; không
resume giả vào ngày sau hoặc gánunknowntrade0. Không dùng partialprofit này
để chọn winner, dự đoán pass quỹ hoặc bỏ nguồn thiếu khỏi denominator.

12tests/22wireFractionfixtures trước history; fullreview8books/2.012session
rows/414closedtrade-costrecords, cả4unknownactivebooks và4nullflatbooks khớp.
25.970distinct heldsourceM1bar observations trước unknown qua2years; quoted
case counters lặp theo cost không là samples độc lập.8mutations entryquote/
side/SL/quantity/time/fees/missingtrade/authority reject. Sameagent/provider,
không independenthuman/modelaudit hoặc tick/prop/OOS/forward/handover proof.

ProducerPID21080 terminal0,12,692s/CPU12,516s; reviewer6,389s. Numeric partial
sourcefreeze làm giảm lượng replay, không speedupbenchmark hoặc edgeverdict.
Không cần thêmperformancework ởlát này; nguồn thiếu là blocker đúng phạm vi.
Private`execution-v1/nasdaq-opening5-orb-v1` giữ immutable8books/pins/snapshots/
config/progress/events/results/review. ResultSHA
`baacc9d4ecbc5642a7a8c2511bb1f021960a36d5a4e6c09f84baab5d14dc02f5`,
review receiptSHA`da46d524b8fcfa30876228e914810b3d4b380a508c365593c214a404b342135e`.

**Tiếp:** [targeted tick source review](NASDAQ-M1-GAP-TICK-PROTOCOL-20261108.md)
cho toàn22missingcashminutes của6devdates,8distincthours xác định từtimestamp
census, không chọn theo PnL. Giữ rules/risk/cost/TP10R; chỉ có nguồn thật và
review đạt mới được tạo datarevision/attempt mới rồi rerun affectedscope.
V1 vẫn inconclusive; Source/sourcefidelity pass không tự clear unknownposition.
