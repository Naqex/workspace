# Vì sao chưa có thành tích và nên tổ chức nghiên cứu tiếp thế nào?

Kiểm ngày 12/11/2026 theo yêu cầu owner. Đây là research/delta của
[task STRATEGY-E2E](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md), không phải
một taskqueue mới. Nguồn gồm kết quả project, source/runtime local, tài liệu
chính thức, bài nghiên cứu và cộng đồng. Không chạy backtest tài chính mới,
mở holdout, cài engine, bật agent/service hoặc gửi lệnh trong lượt này.

**Khuyến nghị:** giữ US500 làm nhánh chính; EURUSD là một nhánh đối chiếu nhỏ,
trước hết kế thừa kết quả và kiểm khả năng dùng dữ liệu. Mỗi nhánh chỉ một
giả thuyết chính trong một chu kỳ. Đi sâu tới quyết định giữ/gác/chưa biết
trước khi mở rộng. Chưa có ứng viên đủ bằng chứng để đề xuất challenge.

## 1. Đã tiến được gì, chưa tiến được gì?

| Mặt | Bằng chứng hiện có | Chưa được suy ra |
|---|---|---|
| Công cụ kỹ thuật | Có native execution, đối soát sổ, causal fixtures, hashes, reuse/recovery trong các phạm vi đã kiểm | Toàn hệ thống hoặc broker đích đã đúng |
| Phạm vi nghiên cứu | Có nhiều trial, năm, họ tín hiệu và kết quả âm được lưu | Số trial bằng số cơ hội độc lập hoặc lợi thế |
| Thành tích kinh tế | Một số đoạn/cấu hình dương; nhiều stress results âm, mẫu nhỏ hoặc chưa biết toàn kỳ | Có edge bền vững sau phí |
| Sẵn sàng cho quỹ | Đã nghiên cứu luật và có các module prop/lifecycle | Pipeline US500 đã kiểm đầy đủ tài khoản FTMO đích |
| Thu nhập | Chưa có evidence packet challenge/payout của chiến dịch này | Đã tạo nguồn thu chính hoặc có ngày chắc chắn bắt đầu có thu nhập |

Nhận xét của owner về tăng chiều rộng nhiều hơn chiều sâu là có cơ sở.
Không có số liệu đủ để gán phần trăm trách nhiệm cho code, chiến lược hay phí.
Không có lỗi mô phỏng nào vừa được chứng minh là nguyên nhân chung làm mọi
chiến lược thất bại; cũng chưa có chứng nhận toàn bộ mô phỏng không còn lỗi.

## 2. Kế thừa kết quả cũ thay vì thử lại từ đầu

| Nghiên cứu | Kết quả thật cần nhớ | Bài học cho vòng tiếp |
|---|---|---|
| [EURUSD Catalogue13](EURUSD-CATALOGUE13-RESULTS-20261108.md) | 624 cases = 24 versions × 13 sổ năm reset × 2 costs; 0/24 được giữ; tổng stress từng version đều âm | Không chạy lại 24 bản không đổi. Không kết luận mọi EURUSD/H1–M15 hiện nay đều thất bại: mẫu là 2010–2022 và coarse execution |
| [US500 multiframe](US500-MULTIFRAME-RESULTS-20261111.md) | 27 cấu hình liên quan; 11 dương tổng reference, 5 dương tổng stress. MA20/80 M15 và thêm H1 có cùng 19 trades, stress −24,04 USD; thêm M5 có 23 trades, −46,71 USD | Trong cohort đó H1 chưa thêm thông tin cho admissions; entry nhỏ hơn chưa cải thiện net. Không nhân 27 thành 27 edge |
| [R120](US500-R120-SAVED-REVIEW-20261112.md) | M15 không H1; 15 trades/3 năm, stress tổng +48,87 USD trên ba sổ reset 10k; 142/157 tuần không entry | Giữ research phụ. Không đủ mẫu/nhịp cho mục tiêu hiện tại; R121 mới là counterpart có H1 |
| [US500 recent](US500-RECENT-SCREEN-RESULTS-20261112.md) | Có setup đạt khoảng 3–5 cơ hội/5 phiên, nhưng phần đủ đường giá nhiều recipe vẫn âm; full net N/A khi có held gaps | US500 không mặc nhiên ít cơ hội. Nhiều tín hiệu và đủ giá ở entry chưa chứng minh chất lượng hay đủ đường giữ lệnh |
| [BR01/RS02](US500-CONTINUATION-DIAGNOSTIC-RESULTS-20261112.md) | Giá trước phí sau 15/30/60 phút rất yếu hoặc âm khi gộp; stress mean âm ở 24/24 annual cells đã xét | Không chỉ do phí cao; chưa có lý do quét exit/ATR/channel để cứu. Đây là markout diagnosis, không bác mọi cách thoát hoặc toàn family |
| [TC01](US500-SAME-CLOCK-RESULTS-20261112.md) | 673 signals/2022–24; tổng midpoint benchmark cũng âm; stress component âm cả ba năm | Giải được tần suất không đồng nghĩa giải được dự báo. Đã lệch hướng H1→M15 owner muốn, không tiếp tục làm lane chính |
| [Gold R043](GOLD-SMA50K-REVIEW-20261108.md) | Research survivor: 220 closed trades, 10/15 annual books stress dương; tổng stress +4.035,06 USD trên 15 sổ reset 50k | Không bỏ lịch sử tốt; giữ dự phòng ngoài scope. Chưa chứng minh time-fit/target execution/fresh validation để challenge |

Các tổng reset ở bảng không là CAGR, một tài khoản liên tục hoặc lợi nhuận
hằng năm. Những study khác model/exit/sizing không xếp chung như một cuộc thi
cùng điều kiện. Kết quả mới không xóa một verdict lịch sử đúng trong scope.

## 3. Vì sao chưa tiến về thành tích? Xếp theo việc cần xử lý

1. **Chưa tìm thấy tín hiệu dự báo đủ tốt sau phí.** BR01/RS02/TC01 không chỉ
   có vấn đề cost; nhiều markout gộp đã yếu trước cost. Thêm data/engine/risk
   không tự tạo thông tin dự báo. Phân rã gross → spread → commission → slip
   → financing → net theo cùng trade set; không trừ spread hai lần.
2. **Một số bản dương quá hiếm hoặc phụ thuộc ít lệnh.** R120 có 15 trades,
   nên chưa biết đó là lợi thế lặp lại hay may mắn. Tần suất là đầu ra của luật;
   không ép quota hoặc nới filter sau khi xem outcome để đạt số lệnh.
3. **Nhiều phép đo là cùng ý tưởng đổi tham số.** MA/ATR/entryTF/risk là trials
   liên quan, không tự thêm cơ hội độc lập. Thử càng nhiều càng phải giữ lịch
   sử lựa chọn và kiểm trên dữ liệu mới; không chỉ giữ winner.
4. **Phương pháp và cách diễn giải từng bị lệch.** H1 cash-anchor/carry khác
   native H1; MA-arm zone khác level-retest; TC01 khác H1→M15. Điều này làm
   công sức không trả lời đúng câu hỏi owner, dù accounting có thể vẫn đúng.
5. **Dữ liệu và target model chưa khép kín.** Gaps trong đường giữ lệnh, proxy
   instrument/cost và full prop path còn thiếu qualification. N/A phải giữ;
   không sửa score để che thiếu bằng chứng.
6. **Đo tiến độ thiên về số lượt hoàn tất.** Cần báo số giả thuyết được giải
   quyết, số candidate qua từng cửa và blocker còn lại. Những diagnostic mới
   mất khoảng 30–83 giây cho producer + review, không phải toàn task. Chưa có
   bằng chứng CPU hay thiếu GPU đang là nút thắt chính của việc tìm edge.

Đây là chẩn đoán từ evidence, không phân rã nhân quả với tỷ lệ %. Kết quả âm
có giá trị nếu giúp đóng nhánh; không đủ để gọi là tiến bộ thu nhập.

## 4. Tập trung hay nhiều thị trường?

| Cách | Lợi | Hạn chế | Đề xuất |
|---|---|---|---|
| Chỉ US500 | Dễ hiểu sâu phiên Mỹ, costs và một bộ luật | Có thể khóa quá lâu vào một cơ chế yếu | Giữ làm nhánh chính, nhưng có điểm dừng |
| US500 chính + EURUSD phụ | Có đối chiếu ngoài thị trường, tái dùng tài sản FX đã có | Thêm trial/exposure/spec; hai sản phẩm vẫn có thể cùng chịu rủi ro USD | **Phù hợp nhất lúc này** nếu giới hạn nhánh phụ |
| Nhiều sản phẩm và nhiều setup cùng lúc | Khám phá nhiều hơn | Tăng số lựa chọn, công vận hành và khó biết vì sao một bản thắng | Chưa mở |

Gợi ý phân bổ **80% công sức US500 / 20% EURUSD**, là quyết định quản lý công
sức cho chu kỳ tới, không tỷ lệ vốn hoặc con số khoa học tối ưu. Nhánh EURUSD
ban đầu chỉ rà old trials, source, session và cost readiness; sau T1–T3 mới
có một development screen nhỏ nếu đủ dữ liệu/protocol. Không chạy lại toàn
catalogue hoặc tự mở 2025/26 vì đổi market/engine.

Giữ cách tổ chức H1 bias → M15 zone/setup → trigger → risk/entry/exit. USD/point,
lot, ATR distribution, phiên và news của hai sản phẩm cần spec riêng; không
copy giờ NY cash sang EURUSD hoặc coi SPY/ES/US500 CFD là cùng hợp đồng.
Nếu cần thay cơ chế cho FX, ghi rõ giả thuyết/version riêng trước outcome.

US500 baseline cần kiểm câu hỏi cụ thể: H1 có giúp điều kiện M15 tốt hơn so
với comparator đã khóa không? Bản level-retest dưới H1 vẫn cùng family với
RS02; phải nêu thông tin mới cần kiểm, không đổi tên rồi gọi edge mới.
Hai chu kỳ đổi luật không tạo evidence mới hữu ích → checkpoint/gác nhánh
theo task hiện hành. Không tự mở vô hạn market/filter để có winner.

**Nghiên cứu song song khác portfolio thật.** Khác ticker chưa đủ độc lập;
muốn phối hợp vốn phải đo return/exposure cùng thời gian và replay chung
account-wide risk. Engine parity cũng không là replication trên feed khác.

## 5. Năm engine thực sự hoạt động thế nào?

Kiểm metadata local 12/11: NautilusTrader 1.231.0; Backtesting.py 0.6.6;
Backtrader 1.9.78.123; VectorBT 1.2.0. LEAN HEAD sạch và đúng pin
`054ec0596a66f0ad09ca5101df424cf6697060a7`. Các build/smoke bên dưới là
receipts 11/11 được đọc lại, không chạy lại hoặc nâng ngày thực thi.

| Engine | Cách xử lý | Cách dùng đầy đủ phù hợp project | Evidence local và phần thiếu |
|---|---|---|---|
| [NautilusTrader](https://nautilustrader.io/docs/latest/concepts/architecture/) | Market events → strategy → risk/execution → fills → account/portfolio | Executor chính cho US500 hiện có; native order/matching/cash, không tự viết lại sổ | Đã có native US500 studies. Chưa target MT5/FTMO cutover; docs latest 2.x không mặc định khớp installed 1.x |
| [LEAN](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/algorithm-engine) | Đồng bộ data theo time frontier; algorithm callbacks, order/reality models và portfolio | Đối chiếu sâu chọn lọc hoặc nghiên cứu needing native multi-asset models | Đã build và chạy SPY sample; sample chưa là common US500/BidAsk/SL parity |
| [VectorBT](https://vectorbt.dev/api/portfolio/base/) | Arrays/broadcast → Numba simulation loop → order records/equity/stats | Screening theo native Portfolio khi rule/model diễn đạt đúng; không chỉ vẽ signals | Native six-bar smoke; chưa target execution. from_orders/from_signals/from_order_func khác nhau; không copy PRO API sang bản đã cài |
| [Backtesting.py](https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html) | Strategy.init/next theo bar; simulated broker xử lý orders/cost | Prototype luật ngắn, oracle cho một câu hỏi xác định | Six-bar native smoke; default market next open. OHLC không cung cấp đường tick hoặc giải được mọi SL/TP cùng nến |
| [Backtrader](https://www.backtrader.com/docu/order-creation-execution/order-creation-execution/) | Cerebro + feeds/resampling + Strategy.next + broker/order notifications | Executor thứ hai đề xuất cho causal H1/M15 và kiểm order events | Six-bar native smoke; default next-bar market. Multiframe clock/availability và commission model phải bind riêng |

Chọn full framework nghĩa là thực sự dùng native data/order/fill/accounting
của engine phù hợp. Không bắt mọi trial đi qua năm engine. Một engine tính
chính, một engine kiểm chọn lọc; hai engine còn lại chỉ chạy khi đúng câu hỏi.
LEAN chưa có fixture đích thì chưa dùng làm “phiếu xác nhận” cho Nautilus.

**Phát hiện mới về phạm vi smoke:** `smoke.py` cấu hình Backtesting.py/VectorBT
0,50 USD/order; Backtrader dùng COMM_FIXED 0,25 USD/unit/order. Installed
`backtrader/comminfo.py:229–237` nhân abs(size), còn
`backtesting/backtesting.py:759–760` cộng fixed + relative notional. Ở size2
đều ra 0,50/fill; ở size1/3 công thức Backtrader cho 0,25/0,75. Đây là source
comparison, chưa native execution probe cho size1/3. Old smoke size2 vẫn đúng;
không chứng minh variable-size fee parity hoặc làm US500 history sai. Trước
promote cross-engine, khóa cùng fee function và thêm fixture size1/2/3.

### Phối hợp mà không tạo thêm một hệ thống quản lý

Một strategycard + source/known-at/cost contract đã khóa
→ screen nhỏ (incumbent hoặc VectorBT khi admitted)
→ native Nautilus event replay
→ Backtrader/LEAN kiểm chọn lọc bằng implementation riêng
→ robustness/fresh validation/prop
→ shadow/demo/reconciliation.

Đây là phân vai và dependency, không pipeline đã được triển khai đủ hoặc
bắt buộc thêm VectorBT trước mỗi run. Native Paperclip tiếp tục giữ task/run
khi dùng được; scripts/receipts hiện có giữ execution evidence. Không bọc
năm engine vào một manager/service mới hoặc cho chúng cùng điều khiển broker.

Trước nhận parity, cần expected trace trên: BUY/SELL, known-at/closed bars và
H1 anchor/DST, qty/rounding/cost, SL/TP ambiguity và gaps, cancel/reject/
partial fills nếu model có, pending/open end-state, cash/equity. Lệch phải
giải thích theo semantics. Dùng cùng dữ liệu không chứng minh feed đúng;
dùng chung signal function không là kiểm độc lập signal. Cần oracle/prefix
hoặc implementation khác cho phần đang kiểm, không chỉ so tổng PnL.

Giữ hash/version/input/attempt và một writer mỗi output. Đo riêng import/JIT,
load/prepare, simulation, review, total và cache cold/warm; đo cùng workload
trước khi tuyên bố engine nào nhanh hơn. Không nhân wall speedup lý thuyết
thành ETA; độ phức tạp reconciliation cũng là chi phí.

## 6. AI agents được dùng hiệu quả như thế nào?

| Nguồn đã đọc | Điều có thể học | Giới hạn cần giữ |
|---|---|---|
| [QuantConnect Mia](https://www.quantconnect.com/docs/v2/ai-assistance/predefined-agents/mia) | Agent lập kế hoạch, làm notebook/code, compile/backtest, sửa lỗi và xem paper divergence | Working code hay vendor benchmark không là bằng chứng có lợi nhuận |
| [Research Validation Agent](https://www.quantconnect.com/docs/v2/ai-assistance/predefined-agents/research-validation-agent) | Có bước phản biện nghiên cứu trước backtest | Bộ ADF/BG/BP/PSI nhắm residual model; không ép làm checklist pass cho mọi rule H1/M15 |
| [Microsoft RD-Agent](https://github.com/microsoft/RD-Agent) | Tách đề xuất/research và implementation/evaluation có feedback, lưu artifacts | fin_quant/factor/model gắn Qlib; không drop-in executor cho US500 CFD/FTMO |
| [QuantConnect MCP](https://www.quantconnect.com/docs/v2/ai-assistance/mcp-server/key-concepts) | Tool bridge để agent tạo project, compile/run/read results | Remote MCP cần dedicated paid assistant node theo docs hiện tại; local LEAN build không có nghĩa đang dùng MCP/Mia. Chưa kết nối/cài/mua |

Đề xuất cho repo: một chu kỳ rõ **research/spec → implementation → checks →
qualified review → quyết định**. Có thể do một agent thực hiện lần lượt;
không cần chạy nhiều agent chỉ để đủ vai. AI không tự sửa tiêu chí hoặc đọc
holdout để tối ưu sau khi thua. Code deterministic quyết định order/risk;
không gọi LLM ở từng tick/lệnh trong baseline. Tăng số agent không là tăng
số edge độc lập, và code reviewer dùng cùng assumption vẫn có thể cùng sai.

Reuse skill `strategy-research`, `strategy-qualification`,
`evidence-continuity`, `engineering-retrospective` và native-engine reference.
Chúng đã có rule lineage/causality/gates; lượt này chưa có lý do tạo thêm skill
hay framework. Cập nhật runtime guide/PLAN để sửa route và giới hạn smoke.

## 7. Đối chiếu tổ chức, paper và cộng đồng

- **Tài liệu phương pháp:** [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide)
  ưu tiên hypothesis; nếu code đổi khỏi giả thuyết thì quay lại thiết kế.
  Không biến heuristic thời gian/số backtest của platform thành chứng chỉ.
- **Nghiên cứu thống kê:** [Bailey et al., PBO, bản 2015](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
  xem rủi ro chọn winner trong nhiều trials. Paper yêu cầu trial information
  đầy đủ và performance đồng bộ khi áp CSCV; chính paper nêu PBO không sửa
  costs/leakage sai. Không tự gắn PBO cho các tổng annual khác model hoặc
  công nhận thấp PBO là có net edge. Đã đọc PDF lượt này.
- **Tổ chức đầu tư:** [AQR century trend research](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)
  là bằng chứng cho một họ trend/multi-market trên mô hình và horizon của họ.
  Nó không chứng minh H1/M15 một US500 CFD đủ lời hoặc pass quỹ. Đa dạng hóa
  có lý do nghiên cứu, không ép một người copy quy mô tổ chức ngay từ đầu.
- **Chính hãng prop:** [FTMO thử 91 hệ thống năm 2018](https://ftmo.com/en/blog/a-big-test-of-algo-trading-does-it-work/)
  báo lỗ khoảng 12,5% sau một năm dù đã chuẩn bị bốn tháng. Đây là một case
  lịch sử do hãng báo, không tỷ lệ thành công của mọi bot, không benchmark
  trực tiếp cho project. Nhiều hệ thống và nhiều tháng không bảo đảm edge.
- **Cộng đồng, tự thuật chưa audit:** [RD-Agent/Qlib](https://www.reddit.com/r/quant/comments/1x5rkjn/anyone_working_with_rdagent_in_qlib/)
  kể phần lớn công sức vào bugs/data/standardization/traceability;
  [AI strategy research](https://www.reddit.com/r/ai_trading/comments/1xfrw6e/after_a_year_building_strategies_with_ai_here_is/)
  kể finalist đẹp trong mẫu không qua tiêu chí ngoài mẫu. Chủ bài sau có
  sản phẩm riêng; không dùng số tự báo làm thống kê chung hoặc học nguyên
  tiêu chí winrate của họ. Bài học đối chiếu là guardrails cho AI và selection.
- [Thảo luận heuristic QuantConnect](https://www.reddit.com/r/algotrading/comments/1cx6dqm/looking_for_advice_regarding_quantconnect/)
  có người cũng mất tuần/tháng và phản biện con số cứng. Đây là trải nghiệm;
  không lấy comment sửa tiêu chuẩn thống kê hoặc kéo dài thử vô hạn.

Không tìm được nguồn đáng tin bảo đảm một người theo bộ quy trình này sẽ
có chiến lược đủ challenge trong X tháng. Chưa thể ước tính xác suất thành
công cá nhân từ dữ liệu công khai hoặc số backtest của project.

## 8. Mục tiêu có khó quá không? Tách thành các đích có thể kiểm

Mục tiêu cuối khó vì phải đồng thời có net edge, chịu drawdown, hợp luật,
đủ tần suất/time-fit và vận hành ổn. Payout đều để làm nguồn thu chính khó
hơn pass một lần. Đây là đánh giá theo yêu cầu, không có tỷ lệ khó đo sẵn.

| Đích, nối vào task có sẵn | Điều owner nhìn thấy | Cửa qua hoặc quyết định dừng |
|---|---|---|
| A — đúng bài toán, T1–T3 | Một card H1→zone→setup→trigger→risk/exit; vài ví dụ đúng/không đúng; cost/data/version rõ | Timing/accounting/fixtures đúng; material unknown được chặn, chưa gọi là edge |
| B — có tín hiệu đáng giữ, T4 | Cadence, net sau từng loại phí, ngày/tuần trống, uncertainty và matched controls | Recipe có lý do đi sâu theo protocol khóa trước; yếu → gác, chưa biết → ghi thiếu gì |
| C — bằng chứng đủ chắc, T5–T6 | Frozen candidate, dependent-sample uncertainty, stress/concentration, thử mới đúng exposure | C1/C2 review theo scope; không chọn một score đẹp làm chứng chỉ |
| D — hợp quỹ và chạy được, T6–T7 | Full equity/news/session/phase path, time-fit 3/6/12m, shadow/demo trace và recovery | Target profile/mismatch bounds/stop criteria đạt; demo không thay economic evidence |
| E — challenge/payout, T8–T9 | Decision packet, sau đó actual account/reward records | Chỉ thực hiện theo quyền tài khoản cụ thể; không nhận pass/payout từ backtest |
| F — thu nhập chính, Q12 | Payout ròng qua nhiều kỳ, retry/operation fees, reserve và mức đều | Một payout chưa đủ; không tăng risk cho vừa sinh hoạt |

Với FTMO CFD 2-Step hiện tại, [objectives](https://ftmo.com/en/trading-objectives/)
nêu target 10%/5%, daily loss 5% initial, overall static 10%, ít nhất bốn
trading days mỗi evaluation phase. Rules phải bind đúng tài khoản/ngày.
[News](https://ftmo.com/en/faq/can-i-trade-news/) và
[holding](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/)
có exceptions cho Challenge/Verification/Swing; funded Standard bị hạn chế
execution quanh selected news và giữ qua closure >2h. Vì đích là payout,
không thiết kế chỉ dựa vào quyền thoáng hơn lúc thi. The5ers vẫn cần profile
riêng; không tự đổi quỹ/program trong vòng này.

**Chia chặng giúp phát hiện sai và dừng sớm, không bảo đảm có edge.** Các
ngưỡng quyết định phải đăng ký trước số liệu; chọn statistical tools theo
sample/dependence/câu hỏi. Không có magic number trades, winrate hoặc thời
gian test. Dữ liệu đã dùng 2025/26 phải giữ exposuremap; thiếu clean OOS thì
freeze và tích lũy forward phù hợp, không đổi tên replay thành forward.

## 9. Việc cụ thể kế tiếp và cách báo tiến độ

1. T1: hoàn thiện một card US500 H1→M15 với clock/carry/level known-at và
   comparator cũ; giải thích thông tin mới cần kiểm so với RS02 âm. Chưa quét
   tham số hoặc thêm M1/FVG/OB. EURUSD đồng thời chỉ rà evidence/readiness.
2. T2–T3: khóa source/cost admission, kiểm các semantic cases bị ảnh hưởng;
   nếu dùng engine thứ hai, xử lý fee/timing fixtures trước market parity.
3. T4: một screen nhỏ mỗi lane đã đủ điều kiện; không chờ năm engine hoàn
   thiện mới kiểm hypothesis, không rerun completed study không đổi.
4. Chỉ đưa survivor hoặc near-miss có câu hỏi rõ sang T5–T7. Không có survivor
   thì báo đúng lý do và gác nhánh theo budget, không tự cấp challenge.

Mỗi checkpoint báo: đang T nào; số **card → technical pass → economic
survivor → fresh/robust candidate → demo-qualified → challenge/payout**;
blocker và quyết định tiếp. Đếm cả các số 0. Count/version/year/cost books
báo riêng, không đặt cạnh số candidate như cùng đơn vị.

Hiện tại: **0 candidate đủ challenge; chưa freeze card mới; chưa promote
cross-engine parity.** Research này bổ sung chẩn đoán và phân vai; không
chuyển trạng thái kinh tế vì tài liệu hoàn thành. Không còn job nào do lượt
research này khởi động để owner phải chờ thêm một giờ.

### Dấu vết kiểm chứng lượt này

Đã đọc reports/receipts nêu trên, kiểm installed metadata bốn wheel, LEAN
HEAD/clean, fee implementations và official sources. Không lặp smokes cũ,
không native run size1/3, không sửa frozen protocol hoặc numerical code.
Ba receipt cũ có source/lock SHA khớp Git blobs/LF; working bytes hiện CRLF
nên raw SHA khác. Đã phân biệt hai identity, không sửa receipt hoặc gọi raw
binding khớp. Khác newline không là bằng chứng có strategy/code change.
Runtime guide sửa câu chưa-promote đã lỗi thời so với native US500 studies;
PLAN/context/index dẫn báo cáo này. Local references/diff được kiểm trước
commit; receipt kiểm tra giữ ở `execution-v1/strategy-depth-audit-v1/` trong
private campaign evidencebase do current context chỉ định.
