# TC01: momentum cùng giờ qua các ngày — component probe

12/11/2026. Owner giao tiếp nghiên cứu sau [reviewR120](US500-R120-SAVED-REVIEW-20261112.md).
Một related hypothesis mới; không mặc định độc lập với price/calendar families.
Giữ US500, decision clock M15, intraday; không mở thị trường giao dịch khác.

## Lý do thử và các hướng chưa chọn

[Heston/Korajczyk/Sadka, author preprint](https://arxiv.org/pdf/1005.3535),
đọc12/11: kết quả cross-sectional stock returns lặp cùng half-hour giữa ngày;
institutional scheduled flows là một giải thích được đặt ra. Paper không
chứng minh index time-series/US500CFD hoặc chi phí target. TC01 là giả thuyết
transfer riêng, không paper replication hoặc copy strategy có edge sẵn.
20regularsessions và slot10:00–10:30 chọn ex ante như một month/morning
representative, không do thấy PnL đẹp; không quét slots/lookbacks.

Đã rà catalogue: phá kênh/retest/MA có negatives; first→last và rest-of-day→
last30 cũng đã kiểm, không đổi tên chạy lại. TC01 dùng lịch sử **cùng slot ở
20ngày trước**, khác predictor chuyển động đầu→cuối cùng một ngày. Cross-asset
lead-lag cần source/timing khác, và paper index/futures không chứng minh
NasdaqCFD dẫn US500CFD; không mở lane đó. VWAP/orderflow/GEX cần volume/flow/
options data thích hợp chưa admitted. Không chọn positive-controlGMM từ
[MNQpreprintv3](https://arxiv.org/pdf/2605.04004): chính tác giả ghi selection,
overlap và full-sample ATR issues; không suy mọi OHLCV vô dụng hoặc GMM là đáp án.
[Hedging-demand paper](https://academicweb.nd.edu/~zda/intramom.pdf) hỗ trợ
nghiên cứu cơ chế quanh close, nhưng các related ownrecipes đã có negatives.

## Contract trước outcomes

- Source: reuse admitted pairedM1 Bid/Ask `us500-explicit-source-v1/2022..2024`
  bằng existing frozenproof/calendar loader. Không raw re-export/download,
  không2025/2026, account/provider/broker. Ba năm đều development đã exposed.
- Một decision10:00NY/ngày thường390minutes; halfdays giữ count/skip, không
  đưa vào20regularsessions. Annualcoldreset:20regularsessions đầu warmup,
  không ghép previousyear hoặc gọi đây là dữ liệu không có cơ hội.
- Predictor: arithmetic mean của20BidOpen returns giữa10:01→10:31NY trên
  **20regularsessions trước**, tính dấu bằng Fraction. Thiếu một endpoint ở
  lịch sử giữNone, chặn signal cho tới khi ra khỏi window; không last20valid,
  không ffill. Cần pairedminute09:59 hiện tại làm availability gate đã biết
  tại10:00. Score>0BUY,<0SELL,=0đứng ngoài. Không ATR/MA/thresholdgrid.
- Chọn signal trước nhìn current10:01/10:31. Entry/exit **component endpoint**
  lần lượt10:01 và10:31NY; BUYask→bid, SELLbid→ask. Mỗi hypothetical unit trị
  giá1USD/point; không lot,10kaccount/risk25USD, OrderSend hoặc native orders.
- Reference/stress extra slippage0,25/0,75point mỗi chiều; commission0 declared,
  embeddedspread. Midpoint-of-minute-opens chỉ decomposition benchmark, không
  observed synchronous tick hoặc executablefill. Không crossingrollover.
- Đây là endpoint-only component **không SL**: không candidate đủ chạy thật,
  không dùng làm account/equity/DD/prop proof. Ghi interiorM1gap census riêng,
  không cần interiorquotes để tính endpoint return nhưng không suy stop/path
  completeness. Thiếu endpoint→netN/A, giữ plannedrow và knownsubset riêng.
- BUY/SELL constant controls trên đúng plannedcohort. Không làm reverse-score
  để cứu loser. Cùngcohort/cost/predictorlookback, không causal randomizedcontrol.

## Stage và cửa ưu tiên đã khóa

1. Focused fixtures:20day warmup/bothsign/zero/equality, missing-history/current
   quote, annual/halfday, current/future price không đổi signal, BidAsk/slippage/
   decomposition và null. Snapshot/pin/test trước numericalreader.
2. Cadence: báo regular/all scheduled sessions, reasons, rawsignals/available
   entryquotes và weekly/monthly gồm0. Floor>=200signals tổng,>=50/năm chỉ
   workloadheuristic từ đợt trước, không statisticalcertificate. Không đạt thì
   lưu cadence và dừng trước component outcomes, không đổi spec/floor.
3. Nếu qua cadence, endpoint probe cùng recipe/cost trên cả3năm. Chỉ giữ cho
   review next-stage khi full endpoint net known và stress total>0,>=2/3years
   stressdương, đồng thời tổng stress tốt hơn cả hai constant controls trên
   cùng cohort. Đây là frozen priority heuristic, không chứng nhận edge.
4. Không đạt→park exactTC01; thiếu dữ liệu→inconclusive. Không tự chạy native/
   2025+/horizon/lookback/slotgrid từ kết quả. Nếu qua→đề xuất protocol native
   có sizing/SL/pathreview/targetcost/OOS trước chạy tài khoản hoặc challenge.

Một writer,deadline300s,CANCEL/status/events/per-yearcheckpoint và lỗi giữ
nguyên; không autoretry/overwrite. Reuse load mỗi năm cho cảcadence/component,
không resimulation. Private owner: `execution-v1/us500-same-clock-v1/`.
Existing skills/tools đủ; không AI training/framework/skill mới hoặc Goal.
