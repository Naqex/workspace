# Pullback US500 M15 — bản luật nền v1

11/11/2026. **DRAFT-SPEC / chưa đăng ký financial run / chưa có PnL hoặc edge**.
Owner giao soạn luật và báo cáo trước triển khai backtest. Bản này là một thiết
kế có thể kiểm tra; các số agent chọn chưa được gọi là thông số tối ưu hoặc
quyết định risk tài khoản thật. Không thay các protocol/receipts đã freeze.

## Đọc nhanh

Giá có hướng theo đường trung bình20/80nến → xuất hiện một nến hồi qua đường20
→ ghi đỉnh/đáy nến đó → đợi nến sau vượt mốc cộng đệm → xét vào cùng hướng.
Không vào ngay khi thấy giá đang giảm/tăng, không nhìn nến tương lai để chọn
một đáy/đỉnh đẹp. Một cơ hội chuẩn bị/ngày; không ép phải có lệnh mỗi ngày.

| Phần | Luật v1 | Trạng thái/lý do |
|---|---|---|
| Sản phẩm/khung | US500, quyết định từ nếnM15 đã đóng | Owner đã chọn |
| Họ chiến lược | Pullback theo xu hướng; cảBUY/SELL đối xứng | Owner ưu tiên trend; symmetry là baseline agent chọn |
| Lưới thử | k=0/0,05/0,10/0,15/0,20/0,25/0,30; đệm=k×ATR | Owner đã chốt7mức; không sweep thông số khác |
| Hướng tăng/giảm | SMA20>SMA80 / SMA20<SMA80 | Agent chọn, kế thừa periods của R004 để hạn chế thêm knobs |
| Nhịp hồi | Close chuyển qua phía ngược của SMA20 trong khi hướng SMA vẫn giữ | Agent chọn; không phải bất kỳ nến đỏ/xanh nào |
| Mốc xác nhận | High nến arm choBUY; Low nến arm choSELL | Agent chọn; biết ngay khi nến arm đóng, không cần futurepivot |
| Độ dao động | ATR14, Wilder alpha1/14, native first-TR seed | Agent chọn có explicit seed; không giả mọi ATR14 đều bằng nhau |
| Hạn tín hiệu | Tối đa4nếnM15 sauarm, và không quá11:00NY | Agent chọn để không giữ setup cũ mãi |
| SL | Cách entry2×ATRđã lưu lúc arm | Agent chọn từ baseline ATRstop cũ; không optimized |
| TP/thoát | KhôngTPcốđịnh; thoát khi hướng SMA mất hoặc12:00NY, tùy điều đến trước | Agent chọn để đo payoff thực tế, không áp RR đẹp trước |
| Ngân sách offline | 25USD planned risk trên book10.000USD, gồm modeled costs | Kế thừa scenario so sánh, không risk thật owner đã chọn |

SMA là trung bình cộng của giá đóng cửa. Period20/80, ATR14,4bar và2ATR là
**một bản thiết kế để kiểm nghiệm**, không trích từ một bài chứng minh US500M15.
Đệm0 là control cho cùng luật mới, không phải rerun R004 hoặc R094.

## Câu hỏi và lịch sử liên quan

Giả thuyết bác bỏ được: sau một nhịp hồi trong hướngSMA20/80, việc đợi giá
vượt nến bắt đầu hồi có thể chọn được các đoạn tiếp diễn đủ bù costs. Đệm
lớn có thể giảm tín hiệu nhiễu nhưng gây entry trễ/missed winners; phải đo cả
hai, không tối ưu accuracy phân loại phá giả riêng với net trading outcome.

Related R004: EURUSD H4 SMA20/80 pullback và relatedH1 versions đã thử/chưa
qualified, giữ negatives trong [catalogue](STRATEGY-CATALOGUE-20261107.json).
Khác ởUS500/M15, cash-session indicator stream, arm-bar level, fixedATRbuffer,
expiry và intraday exit. Đây là related adaptation, không independentedge hay
paper replication. R094/R095 ORB đã có kết quả riêng, không được cứu bằng
đổi tên hoặc đổi engine. Catalogue vẫn95records; chưa cấp trialID/R096.

Primary references về khái niệm: [SMA](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma),
[ATR](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr),
[NYSE sessions](https://www.nyse.com/trade/hours-calendars), đọc11/11. Các nguồn
không xác nhận hiệu suất của các thông số agent chọn hoặc exact FTMO fills.

## Dòng dữ liệu, indicator và thời điểm biết

- Source research: paired-source M1 Bid/Ask USA500.IDX/USD Dukascopy từ
  accepted four-quarter proofs2022–24 của [opening protocol](US500-M15-OPENING-SCREEN-PROTOCOL-20261111.md).
  Đây là proxy, không target FTMO feed. Không network/fetch hoặc2025+ ở bước này.
- Giữ timezone America/New_York/DST. M15 dựng từ15expectedM1 trọn vẹn, cảBid/
  Ask có raw-binding/grid hợp lệ. Signal/indicator dùng **BidOHLC**, không
  side-extrema average thành mid; execution giữ hai side riêng.
- Indicator stream chỉ gồm các nến trong **phiên cash NYSE**09:30→16:00 bình
  thường. Ngày đóng sớm tiêu thụ đúng nến lịch phiên ngắn để warmup/state nhưng
  không arm/trade; ngày nghỉ không tạo nến giả. Đây không phải ATR trên mọi
  giờ quote CFD của MT5; không gọi hai stream indicator tương đương.
- SMA20/SMA80 lấy20/80Bidcloses quan sát theo calendarstream; không reset đầu
  ngày. Native ATR14 dùng TrueRange=max(H−L,abs(H−previousClose),abs(L−previousClose)),
  firstTR=H−L, A1=TR1, At=(13×A(t−1)+TRt)/14. Include previous session close,
  nên gap qua đêm/cuối tuần được tính dù strategy dự kiến flat intraday.
- Tối thiểu81consecutive expected closedM15bars sau khởi tạo/reset mới arm:
  cả current/previous SMA80 đều ready. Firstyearbook cold-start bằng phần đầu
  năm đó; các barwarmup không là outcome và phải báo dates/counts. Không lấy
  previousyear/2021 ngầm. Các annualbooks độc lập, không CAGR liên tục.
- Một expectedM15 bị thiếu: đánh dấu missing causal ngay khi tới deadline,
  hủy setup/entry mới trong ngày, reset indicator readiness cho tới đủ81bar
  hợp lệ sau đó. Overnight/weekend/holiday theo lịch không phải missingbar.
  Không đọc coverage cuối phiên/năm để xóa một entry xảy ra trước đó.
- Reset indicator không xóa vị thế/ledger. Nếu gap xảy ra khi đang giữ lệnh,
  giữ unresolved flag; tiếp quản lý/reconcile theo execution owner, không
  coi recovery-model PnL là exact full-path equity.

Native capability đã inspect: Nautilus1.231.0 `AverageTrueRange` default là
SIMPLE, không WILDER; WILDER dùng native first-input seed, khác kiểu seed bằng
SMA của14TRđầu. Chọn explicit `MovingAverageType.WILDER,use_previous=True`.
Không normalize seed hoặc giả parity với MT5/LEAN chỉ vì cùng nhãnATR14.
Mọi numeric nativefloat/rounding boundary phải được đối chiếu oracle trước
financial pilot; giá/quantity thực thi vẫn tuân thủ grid và exact money math.

## State machine và luật mua/bán

Mỗi bookk có state riêng: READY → ARMED → PENDING → OPEN → DONE; cancellation
từARMED/PENDING điDONE trong ngày. Latch arm/attempt một lần/ngày, kể cả nếu
expiry hoặc risk/fill bị từ chối. Ngày mới chỉ reset latch khi đã xác minh flat;
position/unknown chưa clear thì không arm thêm. Không add-on, martingale hay
same-event reversal. Cùng indicator inputs dùng chung giữa7books.

### Arm — chỉ xem các nến đóng10:00/10:15/10:30/10:45NY

Không dùng nến09:45để arm vì previousclosedbar có thể ở phiên trước, chưa là
intraday pullback. Hai bar so sánh phải cùng phiên, có prefix tới lúc đó hợp lệ.

| Điều kiện | BUY | SELL |
|---|---|---|
| Hướng ởbartrước vàbarhiện tại | SMA20>SMA80 ởcảhai | SMA20<SMA80 ởcảhai |
| Closebartrước | >SMA20trước | <SMA20trước |
| Closebararm | <=SMA20hiện tại | >=SMA20hiện tại |
| Giá mốcL | High của bararm | Low của bararm |
| A lưu lại | ATR14 tại closebararm, phải finite và>0 | NhưBUY |

Ngay lúc arm lưu side/L/A/armtime/expiry và source hashes. L vàA **không dời**
theo nến hồi tiếp, high/low mới hoặc ATR mới. Các bar arm/previous đã đóng
mới được dùng; không cần ZigZag/pivot có nến bên phải chưa xuất hiện.

### Confirm — chỉ từ bar kế tiếp

- Với bar đóngt ở một trong4bar kế arm vàt<=11:00NY: cập nhật indicators bằng
  bar đã đóng, rồi kiểm hướng ban đầu còn giữ. Bằng nhau hoặc đổi hướng thì
  CANCEL trước khi xétconfirm; không chuyểnBUYthànhSELL trong cùng setup.
- BUY cần Close(t)>L+k×A; SELL cần Close(t)<L−k×A. **Bằng threshold chưa đủ.**
  So exact rational threshold với price-grid closes; không tự round threshold
  xuống để bật tín hiệu. Level/order prices sau đó có quy tắc rounding riêng.
- Kiểmconfirm ởbar thứ4 trước khi expiry. Nếu chưađạt ởbar4 hoặc hết11:00,
  CANCEL. Không nới sốbar hoặc rearm vì đã thấy cơ hội mới đẹp hơn.
- Không thêm điều kiện retest-width, nến mẫu, volume/ADX/AI/news classifier,
  higher-timeframe hoặc tham số chọn sau khi xemPnL trong vòng này.

### Fill, bảo vệ và thoát

- Decision tạiM15close, entrymodel ởexact M1Open sau60giây, như old indexed
  researchbook. BUY dùngAsk, SELL dùngBid và modeled slippage; đây là declared
  timing model, không measured MT5 latency. Thiếu exact fill minute thì reject
  vàDONE, không dời đến giá thuận lợi sau đó.
- Tạifill giữ cùng25USD planned-stopbudget/cost-accounting/sizing admission;
  không giữ cùnglot để giả risk bằng nhau. Không đủminlot/margin thì reject.
  Không dùng tương lai để lấy fill/risk. Contract/lot-grid của researchproxy
  lấy từ pinned shared spec; target account spec chưa verified thì không
  nâng thành FTMOaccount replay hoặc tạo broker instruction.
- SL khoảng2A tính từ modeled entryfill, roundra ngoài grid; BUYSLphía dưới,
  SELLSLphía trên. SL không trailing/breakeven và không nới sauentry.
- Theo dõi barrier trênBidchoBUY/AskchoSELL. Gap quaSL dùng adverse first
  executable open theo admittedmodel, không bảo đảm chỉ mất25USD. Không dùng
  M15high/low hoặc synthetictick để giả exact intraminute crossing.
- Nếu hướngSMA mất ở mộtM15close sauentry, đặtEXIT với cùng60secondlag;
  nếu chưa thoát thì EXITdecision12:00NY/fill12:01NY. Hướngmất làSMA20<=SMA80
  vớiBUY, >=vớiSELL. SL vẫn active trong thời gian chờthoát.
- KhôngTPfixedRR. Exit vìSL/hướngmất/noon theo eventtrace, protective handling
  không bị tắt để thực hiện scheduledexit. Khi raw granularity không chứng
  minh được thứ tự cần thiết thì unknown/review, không chọn thứ tự theoPnL.
- Thiếuexit/heldpath hoặc chưaflatcuốimẫu: fullnet/qualificationN/A; không
  forceclose giá cuối chỉ để tạo report đẹp, không xóa cácngàyđó khỏi risk.

## Chi phí và phạm vi quỹ

Reuse declared offline assumptions của sharedindexbook: capital10.000USD,
plannedrisk25USD/order gồm modeledcosts, contract1USD/point/lot,min/step0,01lot,
max50lot/grid0,001/leverage10; chưa target account specs. Roundtrip quantity
phải qua cùng risk check cho mỗik/scenario. Đây không lựa chọn lot/risk thật.

Reference commission0, spread đã ởBid/Ask, extra slippage0,25point/chiều;
stress0,75point/chiều. Không trừ spreadlần2 hoặc thay costs theo outcome.
Unexpectedcarry giữ declaredfunding1/2USDperlot/calendarday của sharedmodel
và unresolvedpath. Chưa historicaltargetswap/dividends/observedfills proof.

FTMO2-StepStandard cả funded là đích, **chưa phải compliance của bản này**.
Targethours/minlot/margin, lịch news hạn chế và marketclosure theo đúng
product/phase còn cần admission riêng; không xóa trade ex-post bằng lịch
không known-at. Không gửiOrderCheck/OrderSend hoặc mởholdout từ draft.

## Ví dụ giả định để kiểm hiểu luật

Không phải quotes/backtest. Đã warmup, SMA20>SMA80 ởmọibarđangxét, trừ case
hủy riêng.09:45close5008>SMA20trước5004;10:00bararmH5010/L4998/C5000,
SMA20hiện5002,SMA80hiện4980,ATR14arm20. L=5010,A=20 giữ nguyên.

Sau đó10:15close5011,10:30close5014,10:45close5017, hướng vẫn giữ:

| k | Threshold phải vượt | Decision BUYđầu tiên | Model fill-time nếu đủ data/risk |
|---|---:|---|---|
|0|5010|10:15|10:16|
|0,05|5011|10:30|10:31|
|0,10|5012|10:30|10:31|
|0,15|5013|10:30|10:31|
|0,20|5014|10:45|10:46|
|0,25|5015|10:45|10:46|
|0,30|5016|10:45|10:46|

Ví dụk0,10nếu modeledfill thực tế5015 thì SL4975trướcgridrounding; không
suy lot hoặc tiền thắng/thua khi chưa cóquote/costspec đủ. Bảng chỉ expected
signal/fill-time, không khẳng định giá khớp bằnggiáđóng, fillthànhcông hoặc edge.
SELLmirror: L4990, A20 vàcloses4989/4986/4983 cho cùngdecisiongroups theo
strict<. Equality phải kiểm cảBUY/SELL;không ép cả7kra7tradepaths khác nhau.

Case phải giữ trong fixtures kế tiếp: noarm/ATRnotready/ATR0, confirmchínhbararm,
threshold equality, hướngmất vàconfirmcùngbar, confirmbar4, expired/no-rearm,
shortmirror, unexpectedgap/heldpathunknown, missingfill/riskreject, stopgap,
trendexit/noonpending và openposition cuối mẫu. Fixture định trước outcome,
không dựa vào backtestPnL để suy “code đúng”.

## Engine, acceptance và bước tiếp

Nautilus1.231.0 là native event-engine implementation đầu tiên đề xuất; dùng
nativeSMA/ATR/Strategy/orders/cache/portfolio, data adapter admittedM1/BidAsk.
Không chỉ gọi incumbentbook rồi gắn nhãnNautilus. Incumbent là compatibility/
financial comparator; LEAN hoặc Backtrader chỉ crosscheck selectedfixtures
sau mapping source/clock/fill/fees. VectorBT dùng exploratorysignals nếu có
ích, không nhân mọi study qua5engine hoặc thay intrabarproof bằngvectorPnL.

**Đã làm trong lượt này:** đặc tả, đọc nativeindicator implementation/API,
kiểm arithmeticBUY/SELL/equality và seed behavior trên dữ liệu giả định.
**Chưa làm:** executablepolicy, causal/stop/riskfixtures, registration/hashfreeze,
nativeUS500parity, financialbatch7k hoặc quỹqualification. Không jobnền phải đợi.

Trước financialrun: pin studyprotocol/code/data/spec/version, ghi đủ trial
lineage; mỗiyearload/makeM15/indicators một lần dùngchung7k. Chỉ2022–24exposed,
không cleanOOS. Báo phase load/indicator/signal/simulation/review/timers và
status/cancel/deadline/onewriter theo workflow hiện có. Không hứa samewalltime.

Báo cáo sau batch cần signals→admitted→fills→closed/unresolved, sốlệnh/tuần và
ngày0lệnh, net/R/cost components, winrate/averagewin/loss, equityDD/daily-loss
headroom (nếu source đủ) tách closedbalanceDD, missed/delayedentries theo cùng
arm-opportunityID và variance/dependence. Giữ mọik/negative/unknown; tìm vùng
ổn định thay winnermaxPnL, không tự promote bằng một threshold triage.

Native seed/equality probes không chứng minh policy correct, edge hoặc pass
challenge. Exact test commands/results chỉ ghi khi thực sự chạy; self-review
trong lượt này không được gọi independent review. Không cần skill mới: dùng
strategy-research/native-engines → strategy-qualification hiện có.
