# H1 bias → zone/setup M15: research cách xây bằng AI và kiểm chứng

Kiểm nguồn12/11/2026 theo owner yêu cầu, sau khi chỉnh lại hướngH1→M15.
**Đề xuất: một setup chính dùng mốc M15 đã phá rồi retest, giữ bản hồi quanh
MA hiện có làm đối chiếu. AI hỗ trợ nghiên cứu/code/kiểm; bot chạy luật rõ.**
Đây là research/proposal, chưa owner chốt exactzone, chưa executableprotocol,
backtest mới, installation hoặc promotion. Không chuyển sangTC01same-clock.

## Zone, setup và entry là ba thứ khác nhau

| Phần | Vai trò | Ví dụ BUY minh họa |
|---|---|---|
|Bias H1|Hướng ưu tiên tại thời điểm hiện tại|H1 theo định nghĩa đã khóa đang thiên tăng|
|Zone M15|Khoảng giá được phép chờ cơ hội|Vùng quanh một đỉnh cũ đã được xác nhận rồi bị phá lên|
|Setup|Chuỗi diễn biến cần xảy ra|Giá quay lại vùng đó trong lúc bias vẫn hợp lệ|
|Trigger/entry|Điều kiện cuối cùng trước xét order|Nến M15 đóng xác nhận bật lên, sau đó mới xét fill/risk|

Zone không là entrysignal và không chứng minh có institutionalorders. Vẽ
vùng lên chart không chứng minh live quan sát được vùng đó tại lúc cần vào.
Ví dụ level100,ATR1 thì zone99,9–100,1 vớiwidth0,1ATR là **số minh họa**,
không price thật/spec đã owner chốt. BUY/SELL phải định nghĩa đối xứng.

## Các loại zone có thể mã hóa

| Cách | Bot cần định nghĩa | Độ phức tạp / quyết định cho project |
|---|---|---|
|Hồi quanh MA/nến hồi|MA nào, chạm bằng close hay wick, nến nào tạo vùng, lúc nào vùng hết hiệu lực|Dễ đối chiếu code cũ; giữ comparator, chưa winner|
|Mốc đỉnh/đáy đã phá rồi retest|Đỉnh/đáy được biết khi nào, closebreak, biên vùng, lần retest nào và expiry|**Ưu tiên đề xuất**: thể hiện rõ H1direction→M15zone→trigger; chỉ một representative trước|
|FVG ba nến|Gap giữa nến1và3, vùng biết sau close nến3, policy fill/expiry/merge|Có thể code; giữ phương án sau, chưa mặc định profitable|
|Order block/supply-demand|Cách chọn nến gốc và displacement/break xác nhận, body hay fullwick, invalidation|Nhiều lựa chọn dễ đổi nghĩa/overfit; chưa ưu tiên khi owner chưa có manualrules cụ thể|

[CME support/resistance](https://www.cmegroup.com/education/courses/technical-analysis/support-and-resistance)
mô tả previoushighs/lows, MA và role reversal khi vượt mốc. Đây là khái niệm,
không nghiên cứu chứng minh netedge của H1/M15US500 hoặc suất thành công.
Mức dễ code là đánh giá engineering của project, không census popularity.

**Lineage phải giữ:** R019 vàRS02 đã có negative/inconclusive riêng; RS02 là
kênh20nến retest, không cùng exactrecipe với confirmedswingM15+H1. Thêm H1
hoặc đổi định nghĩa level là relatedtrial mới, không bằng chứng cứu được
parent và không edge độc lập. Không rerun unchanged/che negatives.

## Người khác dùng AI agents như thế nào? Nguồn nào chứng minh được gì?

| Nguồn đã đọc | Hành vi có tài liệu | Phần tận dụng / giới hạn |
|---|---|---|
|[QuantConnect Mia](https://www.quantconnect.com/docs/v2/ai-assistance/predefined-agents/mia)|Agent làm việc với code, compile/backtest/log, sửa lỗi và paper workflow|Reuse cách trả về code+logs+notebook; tài liệu sản phẩm không chứng minh lãi hoặc capability đã cài local. Không dùng benchmark marketing làm edge proof|
|[Microsoft RD-Agent finance workflow](https://github.com/microsoft/RD-Agent/blob/main/docs/scens/model_agent_fin.rst)|Hypothesis→task/model→implementation→Qlib backtest→feedback; example có train/valid/test|Reuse research/development feedback có lý do và lưu từng trial. Example CSI300/factors khác chartUS500/M15; không drop-in priceactionbot|
|[BacktestBench](https://arxiv.org/abs/2605.17937), abstractv2 đã đọc|Summarizer/Retriever/Coder cho chuyển mô tả thành backtest, đánh giá correctness nhiều loại task|Ủng hộ tách specification/data/code và kiểm grounding; chưa đọc fullpaper hoặc tái hiện benchmark, không evidence funded payout|
|[Reddit trải nghiệm RD-Agent/Qlib](https://www.reddit.com/r/quant/comments/1x5rkjn/anyone_working_with_rdagent_in_qlib/)|Chủ bài tự kể nhiều thời gian dành cho assumptions/data/traceability; comments hỏi giữ đúng paper và untoucheddata|Lời kể chưa xác minh, không kết luận toànRD-Agent sai. Bài học là phải audit semantic drift và exposure dù framework có tên tuổi|
|[GitHub M15/FVG discussion81](https://github.com/joshyattridge/smart-money-concepts/discussions/81)|Người dùng đặt câu hỏi về swinglag/futuredependency khi ghép FVG+sweep rồi retest|Trạng thái unanswered; không có public backtest/payout đủ kiểm trong thread. Không lấy lời mời trao đổi riêng làm verification|

Trong nguồn đã đọc, **chưa có bằng chứng kiểm toán độc lập cho một AI-built
US500 H1→M15 setup đủ pass FTMO/payout**. Không suy ra không tồn tại. Các
nguồn chứng minh workflow/tooling hoặc đưa ví dụ, khác chứng minh edge cho
instrument/feed/cost/program của owner. Không thay câu hỏi này bằng việc
đếm agents, đổi provider hoặc cài thêm framework.

QuantConnect [Research Validation Agent](https://www.quantconnect.com/docs/v2/ai-assistance/predefined-agents/research-validation-agent)
có diagnostics trên residuals của model. Chỉ mượn nguyên tắc phản biện theo
assumptions; không áp ADF/Breusch-Godfrey/Breusch-Pagan/PSI như checklist bắt
buộc cho mọi zonebot hoặc gắn nhãn pass từ một p-value.

## Bẫy code thực tế: nhãn quá khứ không đồng nghĩa tín hiệu đã biết

Đã inspect [SMC source hiện hành](https://github.com/joshyattridge/smart-money-concepts/blob/master/smartmoneyconcepts/smc.py),
chưa import/cài/chạy library hoặc pin một bản dùng production:

- `swing_highs_lows` dùng forward-shift/rolling và cleanup lựa extremes; không
  thể feed label ở anchorbar trực tiếp vào tradingstate như đã biết lúc đó.
  Với thuật toán pivot riêng cần2nến phải, một đỉnh M15 ở09:45 chỉ có thể
  xác nhận sau10:15. Đây là **ví dụ pivot2-right**, không lag cố định cho mọi
  output của library hoặc lời khẳng định chỉ shift là sửa xong cleanup.
- `fvg` đọc nến kế tiếp so với index gắn nhãn; bullish gap ba nến chỉ được
  biết khi nến3đóng. `join_consecutive` còn có thể thay nhãn vùng trước.
- `MitigatedIndex`/`Swept`/break labels tính hồi tố phải phân biệt metadata
  đánh giá sau đó với feature dùng ngay. Không mang kết quả tương lai vào entry.
- Liquidityrange trong source còn dùng whole-input extrema; cần prefixaudit
  trước dùng live. Không kết luận library sai vì có retrospective annotations.

Mỗi vùng cần tối thiểu: origin/anchorbar, **available_at**, low/high, phương
pháp/parameters và thời điểm invalidated/expired. Bất biến chính là:
`available_at <= decision_at < fill_at`. Metadata để vẽ neo về anchor có thể
khác tradingavailability; sửa nến sau decision không được sửa eventprefix đã
phát hành. Ngoại lệ correction/sourcegap phải có event/receipt, không rewrite.

[Declared MIT license](https://raw.githubusercontent.com/joshyattridge/smart-money-concepts/master/LICENSE)
đã đọc; nếu reusecode còn phải pin/audit dependency và giữ notice. Lượt này
chỉ source reference, không vendorcode hoặc cấp quyền chạy package.

## Quy trình gọn đề xuất cho case này

Các vai trò có thể thực hiện nối tiếp; chưa dispatch thêm agents trong lượt
này. Role separation không tự là independenthuman/model/feed review.

| Vai trò | Đầu ra cần nhìn thấy | Cửa trước khi đi tiếp |
|---|---|---|
|Research/spec|Một trang luật H1/zone/setup/trigger/exit kèm nguồn và lineage|Ví dụ nến cụ thể khớp ý tưởng owner; không mơ hồ “zone đẹp”|
|Coder|Module/state machine trên data/engine hiện có|Mỗi zone/signal có timestamp và lý do rõ, không AI tự đổi rule mỗi lệnh|
|Verifier|Fixture tính tay, oracle/codepath khác, prefix/mutation review|Chỉ ra mismatch trước xét PnL; testpass không tự chứng minh edge|
|Runner|Protocol/code/data/cost hashes, từng phiên signal→order→fill, status/logs|Không dùng input không có quyền, không reuse khi bindings đổi|
|Review/decision|Bảng technical/economic/prop gaps, lý do giữ/gác và trialhistory|Không chỉnh từ winner rồi gọi cùng dữ liệu là OOS; không sửa scope âm thầm|

Đề xuất ban đầu: AI hỗ trợ bên research/code/review; **live signal/entry/risk
do luật xác định chạy** để tái hiện được và ít phụ thuộc token/latency. Nếu
sau này thêm AI tại decision phải version/pin inputs/model/output/audit riêng;
không là điều đã được chứng minh cần cho setupH1–M15.

## Kiểm định từ “đúng ý tưởng” tới “đáng dùng”

1. **Đúng nghĩa:** chốt H1bias là MA hay cấu trúc; không đổi cùng lúc cảbias,
   zone,entry,SL. Chart/replay các trường hợp chọn theo timestamp/side trước
   outcome: có setup, không setup, bị vô hiệu và missingdata. Người xem thấy
   từng nến lúc đó, không chỉ chart đầy đủ với đẹp nhất hindsight.
2. **Đúng thời điểm:** chỉ closedH1/M15 đã biết; swingconfirmation/zonebirth
   và expiry cụ thể; batch-prefix vs streaming, sửa futurebars không đổi
   pastsignals. Chặn sử dụng zone trướcavailable_at bằng regression/mutation.
3. **Đúng data/state:** clock/DST/baralignment/ATRseed/warmup; quote stale/gap,
   nhiều zone thì chọn theo rule trước, không chọn vùng lời sau đó. Tách trạng
   thái AVAILABLE→TOUCHED→CONFIRMED→ENTERED/EXPIRED/INVALIDATED; không hồi sinh
   zone đã hủy hoặc cho nến tạo vùng tự retest chính nó nếu spec không cho phép.
4. **Đúng thực thi/chi phí:** nativeengine cũ cho account/sizing/order/SL/cash,
   BUY/SELLBidAsk đúng, coststress, unknownpath không thành0; same-minute
   SL/TP ambiguity giữ unknown hoặc admittedpath, không chọn outcome thuận.
5. **Có giá trị kinh tế:** đếm cơ hội/tầng lọc trước; boundedfinancialscreen
   và đối chiếu bỏH1/bỏzone với comparators đã đăng ký khi trả lời đúng câu
   hỏi. Báo net/DD/expectancy theoR/tuần trống/concentration/costs, không chỉ
   winrate. Không diễn giải subgroup/variant dependence thành causal proof.
6. **Đủ bền và hợp quỹ:** giữ consumedmap/trials; chronologicalvalidation/
   stress và forward saufreeze.2022–24 đãexposed,2025đãselection ởstudies khác,
   2026exposure còn tùyrecipe; không gọi tự động unseen. Trước challenge cần
   targetfees/spec/news/reset/equityDD/profile và shadow/demo/reconciliation
   riêng; không dùng testpass hoặc số lượng lệnh chung làm chứng chỉ.

[Freqtrade lookahead-analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/)
so kết quả baseline với các lượt kiểm để phát hiện indicator/entry thay đổi;
ý tưởng phù hợp để thiết kế prefix checks. CLI của Freqtrade kiểm native
Freqtrade strategy, **không cắm trực tiếp để chứng nhận Nautilus project**.
[Recursive-analysis](https://www.freqtrade.io/en/stable/recursive-analysis/)
kiểm độ nhạy startup history của indicators; apply khi recursiveATR/EMA có
consumer, không ép SMAfinitewindow cần mọi test của EMA. Không chạy CLI này.

## Project đã có gì, còn cần gì?

Nguồn nội bộ đã đối chiếu: [draftH1/M15/M5](US500-MULTITIMEFRAME-DRAFT-20261111.md),
[protocol cũ](US500-MULTIFRAME-PROTOCOL-20261111.md),
[fulltable](US500-MULTIFRAME-FULL-TABLE-20261111.md),
[implementation](../../tooling/ai-engines/us500_multiframe.py) và
[fixtures](../../tooling/ai-engines/tests/test_us500_multiframe.py).

| Hạng mục | Thực tế đã inspect | Delta cần trước batch tiếp |
|---|---|---|
|H1–M15 engine/policy|`us500_multiframe.py` đã có B=H1filter+M15 vàC=M5; R121 cóH1, R120không|Chốt semanticbias/zone đúng ý owner, giữ negative lineage|
|H1clock|09:30cash-anchoredH1,20closedH1SMA; trước10:30 cócarry từ phiên trước|Audit đúng H1 muốn quan sát trên chart/targetfeed; đổi alignment/stream là semanticchange, không bugfix vô điều kiện|
|Zone cũ|M15armbar ở nhịp hồi quanhMA; confirm vượt high/lowarm+đệm|Không gọi là OB/FVG hoặc generic supportretest đã kiểm|
|Tests|Đã đọc fixtures H1asof/partial/futureinvariance, H1reject và M5clock/frozenbias|Đọc source chưa là reruntest; thêm confirmedzone lifecycle/prefix/oracle khi implement loại mới|
|Logs/protocol/qualification|Có sourcepins, nativebooks/review, cadence, status và savedresultreuse|Reusecontract; thêm zoneavailability/tracereasons trong owner hiện có, không tạo registry/runtime cạnh tranh|
|RD-Agent|LocalHEAD `484776c2` khớp runtimeguidepin|Không startWSL/Docker/provider hoặc tự thay engine cho zonebot; scenarioadapter cần task riêng|

Theo [QuantConnect consolidator docs](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/consolidator-types/time-period-consolidators),
hourbar có thể kết thúc đầu giờ hoặc customanchor. Vì vậy “H1” chưa tự định
nghĩa cùngstream trên hai hệ thống; không ngầm coi cashH1cũ là nativeMT5H1.

**Bước tiếp đề xuất:** một spec dễ đọc cho **H1bias hiện có + M15 confirmed
level→break→retest→M15trigger**, với MA-arm comparator đã có. Giữ H1definition
cố định cho controlledcomparison; muốn đổi bias sang cấu trúc là version
riêng. Trước code/numeric cần resolve clock/carry, pivotavailability, vùng,
zone selection/expiry, trigger/exit/risk/cost/split và ghi protocol. Chưa đặt
parameters mới, chưa mở grid7buffers×mọizone/entryTF, chưa gọi đây là exact
phương pháp manual owner hoặc yêu cầu chuyển sangM5/M1. Nếu thực hiện, mới
có thể đo cadence/net và quyết định giữ/gác; research không thay empiricaltest.

## Dấu vết lượt research

Đã đọc officialdocs/source/abstract và hai communitythreads nêu trên; nguồn
community là lời kể, không verifiedprofit. Đã inspect source/tests/protocol/
fulltable và localRD-AgentHEAD; không test/build/benchmark/backtest/price
reader mới, không broker/APIkey/OAuth/package/service/config changes. Existing
`strategy-research`, `strategy-qualification`, `evidence-continuity` đủ cho
workflow; chưa cần skill/framework mới. Nguồn Memory chỉ route lịch sửoperator
profile; authoritative currentcontext/ownercorrection và repo hiện tại được
dùng cho đề xuất này. Không cập nhật globalmemory.
