# S02 — kiểm tra danh mục Gold + EURUSD + GBPUSD trên cùng sổ

Đăng ký ngày 17/11/2026, **trước kết quả S02**. Owner đã giao tự chủ nghiên
cứu độc lập toàn bộ mục tiêu. Đây là phép kiểm Development hữu hạn kế tiếp
[S01](SOLO-GBP-CONFIRMATION-PROTOCOL-20261115.md), không là quyền broker,
mở holdout hay xác nhận đủ điều kiện Challenge.

## Câu hỏi và điều kiện bắt đầu

S01 cho thấy GBP bổ sung lợi nhuận và cải thiện Net/DD trên các đường M1 cộng
riêng. S02 kiểm tra kết luận đó còn giữ được khi các lệnh dùng **cùng số dư,
giới hạn rủi ro, mốc đổi ngày và vòng tài khoản**. Không thêm cơ chế tín hiệu,
đổi entry/SL/exit, chọn BUY/SELL hoặc quét sizing.

Chỉ chạy giá thật sau khi:

1. Đối soát độc lập S01 source-v2 không còn sai khác material trong 300 tín
   hiệu, toàn accepted/rejected intents và tiền tại risk150/75. Oracle
   ngày17/11 bắt được một false reject đúng ngưỡng15% của economics-v1.
   S02 chờ [bản sửa chính xác ngưỡng](SOLO-GBP-COST-GATE-CORRECTION-20261117.md)
   và independent review; không dùng 286 fills cũ như cohort mặc định.
2. Code S02, fixture và independent review đạt trong scope; protocol/code
   được commit trước registration/run. Giữ producer S01 `7f9dd4c` và input
   hashes; thay module dùng chung không được sửa receipt S01 hay gọi lại
   historical verifier như thể code chưa đổi.
3. Registration pin protocol, code, source manifests, trade books, independent
   S01 review và config. Một writer, output mới, failure giữ nguyên; retry
   chỉ sau giải thích lỗi và attempt mới, không ghi đè.

## Dữ liệu và phép so sánh đã khóa

Chỉ `[2022-01-01 00:00 UTC, 2024-01-01 00:00 UTC)`.
Không mở giá 2024–2026. Không download hay tái sinh tín hiệu trong runner.

Nguồn chỉ đọc từ baselines trong registration S01 và GBP source-v2:
Gold A Original, EURUSD `SWEEP.ASIA.LONDON.DAY`, GBPUSD cùng recipe. Kiểm
Gold events của cả hai cost models giống nhau và metadata regime không
thay quyết định/SL. Kiểm asset, unique signal, decision, entry/exit ordinal,
executable Bid/Ask, deadline biết trước, cutoff, held hours và checksum.
Hai FX phải flat trước rollover theo actual events; không mặc định swap0
nếu đường giữ lệnh không chứng minh điều đó.

| Thành phần | Baseline | Candidate |
|---|---|---|
| Gold A Original | Risk150 USD/lệnh | Risk150 USD/lệnh |
| EURUSD sweep | Risk75 USD/lệnh | Risk75 USD/lệnh |
| GBPUSD sweep | Không có | Risk75 USD/lệnh |
| Gold costs | SYM_FLAT và ASYM_FLAT | Cả hai model giống baseline |
| FX costs | Paired spread; commission5 + slip4 USD/lot/vòng | Giống baseline |
| Tham số entry/SL/exit | Sealed events | Giữ nguyên; chỉ thêm GBP |

Đây là **một fixed sizing policy** trong mọi phase, khác policy V3
CORE200/175/125 và SAT100/100/75. Không chỉ truyền `fixed_risk` vào code cũ
vì adapter cũ bỏ qua nó. S02 không áp V3 equity throttle; cap/reserve/halt
vẫn giữ. Legacy default vẫn giữ cho consumer cũ.

Một sổ 50.000 USD, gross open stop risk tối đa500 USD, daily realized halt
1.000 USD, internal reserve floor46.500 USD. Không net hai vị thế ngược
chiều để giảm stop budget. Reserve dùng toàn funding âm đến deadline biết
trước; không dùng actual future exit để giải phóng dự phòng khi vào lệnh.

## Thời gian, đường giá và kế toán

- Thứ tự stream: `(timestamp, asset_rank, source_ordinal)`, Gold0, EUR1,
  GBP2. Đây là quy ước tái hiện giữa các feed, không chứng minh thứ tự broker.
  Clock reset/swap xử lý trước quote cùng timestamp; tại cùng quote,
  exit trước entry. Không đổi thứ tự cross-asset sau khi thấy cap/rejections.
- Mỗi asset giữ Bid/Ask, thời gian quote, ordinal và source hour riêng. Quote
  Gold mới không làm EUR/GBP mới theo. Không dùng quote tương lai cho reset.
  Missing held hour, quote không hợp lệ, ordinal lệch hoặc timestamp tương
  lai là lỗi dữ liệu; run không có verdict kinh tế hợp lệ.
- Tuổi quote trên mỗi asset đang giữ được đo tại entry/reset/swap/exit và
  trong đoạn mark-to-market; báo ba nhóm `<=60s`, `(60s,15min]`, `>15min`.
  Phải bao phủ toàn elapsed holding intervals kể cả khi cả ba stream đều
  im lặng: lưu start/end/duration và tỷ lệ thời gian unknown, không chỉ
  kiểm row có tick rồi bỏ outage trước quote mới. Không tạo giá cho gap.
  Ngưỡng15phút kế thừa source-path gate, **không** là bằng chứng quote broker
  còn thực thi được. Mọi khoảng `>15min` giữ trạng thái path unknown cho
  kết luận không-breach, trừ khi có calendar/source proof riêng đã đăng ký
  trước run. Không ngầm gắn nhãn nghỉ phiên cho gap chỉ vì giờ trông hợp lý.
  Có thể xuất các số điều kiện trên quotes quan sát được; không promote khi
  còn unknown material. Không thêm filter vào lệnh theo outcome tuổi quote.
- Tạo đủ midnight `Europe/Prague` trước cutoff, kể cả midnight cuối nằm
  ngày UTC trước đó; kiểm DST. Daily anchor là balance, floating/costs/swap
  nằm trong equity theo accounting model được công bố.
- Giữ funding accrued trong floating đến close và reserve full horizon;
  không trừ accrued thêm lần nữa. Floating hiện reserve một phía slippage,
  closed cash settle cả hai phía. Đây là mô hình kế thừa, cần nêu riêng
  phần khác execution thực tế.
- Annual/continuous diagnostic phải đo **toàn bộ** đoạn giá, không cắt ở
  first prop threshold rồi bỏ đáy tiếp theo. Monthly lifecycle chốt witness
  first breach và snapshot vị thế mở; không phát sinh close giả. Cash bridge
  khi còn open phải tính đúng entry fee từng asset.
- Tiền USD là kết quả chính. `portfolio_common_R = net_USD / 150`;
  `equity_DD_common_R = equity_DD_USD / 150`. Tổng R theo risk riêng từng lệnh
  chỉ là statistic phụ, không dùng thay portfolio return hoặc Net/DD.

## Ngân sách chạy và đầu ra

Hai systems × hai swap models ×27 accounts = **108 accounts**:

- Hai annual diagnostic, bắt đầu đầu2022 và đầu2023, kết thúc cuối năm.
- Một continuous diagnostic toàn2022–2023.
- 24 monthly-start lifecycle từ01/2022 đến12/2023, cùng cutoff cuối2023.

Diagnostic dùng cùng admission guards, không reset phase hay ngắt đường
giá khi chạm ngưỡng. Lifecycle dùng target10%/5%, minimum4 trading days,
daily loss5%, static loss10%, phase transition khi flat. Reward model kế
thừa là proxy30ngày, tối thiểu20 USD, split80/20 và debit toàn profit;
việc reset anchor/peak khi payout **chưa xác minh với tài khoản đích**.
News, margin, broker netting mode, target feed/slippage và lịch thực tế chưa
đủ thì `prop_qualified=false`; các mô phỏng funded/payout chỉ là proxy.

Báo netUSD, commonR, mean tradeR, annual/pooled equityDD/daily/static,
admission/rejection với state, concurrency/stop exposure, top3 dependency,
quote-age/coverage, full cash/fee/funding/phase/reward bridges; số P1/P2,
time-to-target có right-censoring, unique funded paths và proxy payout.
Các monthly starts chồng lấn không là các lần thử độc lập hay xác suất pass.

Output duy nhất:
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S02-three-asset-replay/`.
Không gọi legacy CLI có global JOB trỏ campaign gốc. Reuse pure components
và explicit own paths; data readers cutoff END. Log phase/counter, failure,
source hashes và process identity; không log từng tick.

## Quyết định sau S02

Không dùng S02 để tối ưu weights hoặc tìm variant thắng. Trước review
Historical Validation2024 cần: correctness/path đầy đủ; không modeled breach
trong lifecycle; candidate annual net không âm ở cả năm/model; pooled
Net/equityDD cao hơn baseline ở cả model theo common USD. Báo riêng phần
return tăng do thêm vốn risk; DD tuyệt đối tăng không được che bằng ratio.
Nếu không đạt, gác đúng composition hoặc giữ inconclusive theo nguyên nhân.

Đạt các điểm này chỉ cho phép xem xét freeze2024 tiếp, không chứng nhận
edge ngoài mẫu hay prop compliance. Kiểm target-cost/news/margin/forward
vẫn là việc phải hoàn thành để đề xuất Challenge. Không mở2024 tự động chỉ
vì runner trả eligible; cần protocol và composition freeze riêng.

## Kiểm thử bắt buộc trước run

Giữ two-asset default parity; ba stream có tied timestamps/multiple
ordinals và EUR ở giữa; stale GBP dù Gold mới; missing/future quote;
fixed risk mọi phase; complete nonrolling path; breach snapshot/cash bridge
cả Gold và FX; commonR; cap/reserve/halt; future-exit mutation không đổi
admission; Prague DST/end boundary; funding triple; phase/reward tie;
source/cutoff/output tamper; cùng Gold/EUR events giữa hai systems.

Independent scalar merge/account arithmetic phải khác code được kiểm;
không import producer joint merge rồi gọi đó là independent source oracle.
Review kết quả gồm cả admissions/rejections, không chỉ tổng tiền cuối kỳ.
