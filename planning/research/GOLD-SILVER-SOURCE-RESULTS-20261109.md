# Vàng/bạc: source fixture đạt, chưa kiểm quan hệ hoặc lợi nhuận

Continuation09/11: [full formation results](GOLD-SILVER-FORMATION-RESULTS-20261109.md)
đã hoàn tất source2018/2021 và fixed diagnostics; nguồn đủ, cả hai formations
không qua prefilter. Bên dưới giữ scope của source pilot trước continuation,
không là yêu cầu fetch lại pilot hoặc status formation còn đang chờ.

Theo [protocol](GOLD-SILVER-SOURCE-PROTOCOL-20261109.md) `9db5c3d`, bốn H1
exports01/11/2018 của XAU/XAG × Bid/Ask đã thu và kiểm xong. Chỉ đủ đăng ký
formation history tiếp theo, chưa statistical pass/account policy/edge.

| Phần | Kết quả |
|---|---|
|Source day|23 H1 mỗi side/asset; tổng92bars,460price/volume fields|
|Raw exposure|4month responses11/2018;497explicit hours/source, giữ raw/hash|
|Transform|Canonical decoder và Fraction integer-delta path khớp; export chỉ giữ source-listed day, không padding|
|Side quality|Bid/Ask cùng23hours/asset, Open/Close không crossed; không actual joint ticks|
|Negative controls|Sai price/clock/side/count/authority bị bắt; follow-up hash-metadata mutation bị từ chối, không sửa raw bytes|
|Timing|Producer1,126s; full review0,071s; không benchmark toàn research|
|Authority|0strategy/statistical/model/broker calls; không mở own2025+ hoặc thay runtime|

Reuse installed pinned provider library và H1 helper; không dependency, MCP,
service hoặc global config mới. Request/cache hit breakdown chưa instrument;
không claim tất cả là network hoặc cache hit. Không tiếp tục tải full history
dưới quyền của source pilot: bước đó cần protocol riêng trước fetch.

Primary [CESifo12559 abstract](https://www.ifo.de/en/cesifo/publications/2026/working-paper/long-run-linkages-and-parameter-instability-gold-silver)
cho thấy quan hệ có thể khác theo giai đoạn trên futures. Chưa đọc full paper;
không suy spot CFD ổn định hoặc paper chứng minh bot sẽ có lời. Literature
aggregate đến2025 đã exposed; own holdout2025+ vẫn đóng. Sample day này không
chứng minh full-year coverage, relation stationarity, costs/hedge/prop fit.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/gold-silver-source-v1` giữ config/manifest/raw proofs/exports/
source snapshots/result/review/hash-mutation/status/events; worker PID26236 và
reviewer terminal0. ResultSHA
`72c3b9697e2c1d57e95121ad18ff9b01eb320650a8db3f57b1f986eba09b53f7`;
reviewer codeSHA `7d46f392b3e340aa811991898a344b16c092eb3fc858f66d269e321cf43ad142`.

**Tiếp:** đăng ký full formation sources2018/2021 cho fixed yXAU/xXAG,
16UTC Close/known17UTC, frozen US cash dates như sample design; không tự gọi
đây là metals trading calendar. Source review/complete census trước fixed
Engle–Granger/Decimal review; thiếu source giữ inconclusive, không asof hoặc
drop ngày. Chưa đọc pair PnL2019/2022; chưa hedge weights, SL hoặc economic
outcomes mới. Catalogue67records/46researchpolicies/25native sau khi thêm R067
source-only hypothesis; số hồ sơ không là số strategies đã code/independent edges.
Goal C1/C2 active, chưa ứng viên challenge.
