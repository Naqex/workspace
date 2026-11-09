# Đợt nghiên cứu chiến lược prop đầu tiên

Ngày đăng ký: **05/11/2026, Asia/Saigon**. Phạm vi thuộc
[AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md); kết quả thực thi và
bước tiếp thuộc [receipt hiện có](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Tài liệu này giữ protocol, nguồn và quyết định sàng lọc, không tạo ledger mới.
Đây là khảo sát/đăng ký trước thí nghiệm; **chưa có backtest mới hoặc candidate
được công nhận đạt**. Cửa sổ dữ liệu cuối phải qua kiểm consumed/coverage trước run.

## 1. Tập trung hai chương trình, giữ logic chiến lược dùng chung

Mục tiêu: tìm edge sau chi phí có thể duy trì trong điều kiện prop và tiếp cận
quy mô lớn hơn với rủi ro/chi phí cá nhân được kiểm soát. Ưu tiên của owner:
máy có thể chạy liên tục; chưa giới hạn holding period; phản ứng trước chuỗi lỗ,
profit giveback và ít giao dịch sẽ quan sát trong demo. Không tự gán risk budget.

- **Chuẩn chính: FTMO CFD 2-Step Swing**, reuse dữ liệu/spec và runner đã có.
- **Đối chiếu: The5ers High Stakes**, chưa chọn New/Classic, cỡ tài khoản hoặc mua.
- Chưa mở thêm hãng/chương trình. Không xây framework cho mọi prop firm.
- Tách quy tắc tín hiệu/khớp lệnh khỏi cấu hình luật chương trình. Đây là ranh
  giới nghiên cứu, chưa là tuyên bố đã có một engine nhận mọi rule profile.
- Cùng candidate/code được đánh giá riêng dưới từng luật và cost profile.
  Candidate tốt cho một hãng vẫn được giữ để nghiên cứu; không bắt buộc thắng
  cả hai, không lấy giao của mọi hạn chế rồi đổi chiến lược đến khi backtest đẹp.
- Nguồn ý tưởng có thể rộng; quảng cáo "pass challenge" không là bằng chứng.
  Tự viết code từ quy tắc minh bạch không tự chứng minh compliance/độc quyền.

## 2. Đối chiếu primary sources ngày 05/11

| Điểm ảnh hưởng chọn chiến lược | FTMO 2-Step Swing | The5ers High Stakes |
|---|---|---|
| EA | Được phép với điều kiện; EA bên thứ ba trùng giao dịch có cảnh báo allocation [F3] | FAQ yêu cầu sở hữu source/SL hiển thị [T4,T5]; Terms §11 còn yêu cầu approval bằng văn bản trước dùng automated software và hạn chế phần mềm bên thứ ba [T7] |
| Loss rules | Daily limit dựa balance tại reset Prague và 5% initial; total floor static 90% initial [F1] | FAQ: daily floor 95% của max(balance,equity) tại 00:00 server; total floor90% initial [T2]. Không đồng nhất với công thức FTMO |
| Điều kiện ngày | Tối thiểu4 ngày có mở vị thế mỗi phase, không phải4 ngày có lãi [F1] | Trang chương trình nêu3 profitable days; FAQ định nghĩa lợi nhuận ngày theo min(balance,equity) và mức0,5% initial [T1,T3] |
| Holding/news | Swing cho giữ qua market close và news, vẫn phải tránh forbidden practices [F2,F4] | Có thể giữ qua đêm; High Stakes hạn chế thực thi quanh tin quan trọng, khác việc giữ vị thế [T1,T6] |
| Chương trình/size | Chỉ xét2-Step Swing; không lấy luật1-Step/Instant áp sang [F1,F2] | New/Classic/size và scaling phải có phiên bản riêng; card động chưa xác minh đủ để freeze profile lớn [T1] |

Đây là paraphrase phục vụ thiết kế thí nghiệm, không phải kết luận pháp lý hoặc
cam kết hãng sẽ chấp nhận bot. Phải kiểm điều khoản hiệu lực cho đúng tài khoản,
quyền dùng code, risk practices, payout và scaling trước promotion/mua.
Không đổi code nhằm che giao dịch trùng, né luật hoặc vượt hạn mức allocation.

### Giới hạn xác minh cần giữ

- **Bổ sung05/11 sau khảo sát auto/semi-auto:** mô tả EA ban đầu chưa nêu đủ
  [T7, cập nhật28/10/2026]. Cần xác nhận bằng văn bản cho phần mềm/tài khoản
  cụ thể trước triển khai The5ers; quyền sở hữu source một mình chưa đủ.
  [Research kế thừa](PROP-AUTOMATION-AND-STRATEGY-EVIDENCE-20261105.md) giữ
  đối chiếu FAQ/Terms. Đây là delta compliance, không sửa protocol đã freeze
  hoặc công nhận run cũ đạt điều kiện hãng.
- [T2] nêu ngưỡng5% / 10%, trong khi card chương trình là nội dung động theo
  lựa chọn. Chưa có checkout/account-specific snapshot: **không** khẳng định
  cùng một bộ số áp dụng mọi size/New/Classic hoặc mọi tier sau scale.
- [T6] vừa cập nhật03/11/2026: cửa sổ thực thi tin ±2 phút, expiry khác giữa
  evaluation và Pro; không dùng trang overview cũ để công nhận đầy đủ.
- Chưa pin lịch tin point-in-time, timezone/DST server The5ers, cost/spec riêng
  The5ers hoặc điều kiện SL/TP trong news window. Profile đó chưa được chạy
  như mô phỏng account-verified. Không xóa SL để né quy tắc.
- FTMO snapshot hiện có không xác minh commission riêng/historical financing.
  QDM là nguồn thị trường khác broker; scenario không là tái dựng server fill.

Chuẩn chính ở đây là thứ tự triển khai kỹ thuật. Chưa kết luận FTMO có hiệu quả
kinh tế tốt hơn The5ers cho owner; quyết định challenge phải xét kết quả, phí,
ngân sách cá nhân và điều kiện thực tế tại thời điểm mua.

## 3. Danh mục ý tưởng và sàng lọc

Mức bằng chứng phân biệt: nghiên cứu hiện tượng, quy tắc tự định nghĩa, benchmark
đã có. Paper ở tần suất/thị trường khác chỉ hỗ trợ đặt câu hỏi; không chứng minh
quy tắc EURUSD/H4 có lời. Không tải/cài EA hoặc fork repo từ khảo sát này.

| ID | Ý tưởng | Nguồn và mức chuyển giao | Quyết định |
|---|---|---|---|
| C01 | Channel/Donchian breakout H4 | Baseline nội bộ đã có; thuộc nhóm trend, không phải tái lập paper [R1] | Giữ baseline, không tính là phát hiện mới |
| C02 | Moving-average crossover H4 | Biến thể trend đơn giản tự định nghĩa; [R1] không xác nhận tham số này | Chọn comparator đầu tiên; cùng họ C01 |
| C03 | Time-series momentum dài hạn D1/monthly | [R1,R2] có evidence ở futures/forwards và chân trời dài | Để sau: cần history dài, rollover/cost và universe đúng; không đổi12 tháng thành12 nến rồi gọi replication |
| C04 | Mean reversion theo z-score H4 | Giả thuyết đối chứng tự định nghĩa; [R4] chỉ cung cấp cơ chế mức giá, không kiểm công thức z-score | Chọn challenger khác họ; edge chưa biết |
| C05 | Chạm/reject support-resistance | [R4] có nghiên cứu microstructure FX; mức giá tác giả dùng không có trong QDM | Để sau: định nghĩa mức giá tái lập, không vẽ zone tùy kết quả; gần họ C04 |
| C06 | Breakout range theo phiên | Giả thuyết triển khai cần clock/session; [R5] là cảnh báo chi phí intraday, không bằng chứng London breakout | Dự phòng; cần H1/session và news calendar trước thử |
| C07 | Cross-sectional currency momentum | [R3], chiến lược tương đối nhiều đồng tiền | Để sau: EURUSD đơn lẻ không tái lập được; thiếu universe/cost tương ứng |
| C08 | Carry | [R6] nghiên cứu cả crash risk; swap CFD không đồng nhất forward carry | Để sau: thiếu rate/financing history; chưa phù hợp ưu tiên chống breach |
| C09 | News straddle/gap exploitation | Bị hạn chế trong [F4,T5,T6] | Loại khỏi đợt này |
| C10 | Tick/rollover scalp, latency arbitrage | Thực thi và nhiều hành vi bị cấm [F4,T4,T5] | Loại khỏi đợt này |

Không coi10 ý tưởng là10 thí nghiệm độc lập; C01/C02 cùng họ trend, C04/C05
cùng nhánh reversal. Chưa xếp lợi nhuận hoặc xác suất pass vì chưa có outcome.
Danh sách ngắn: **C01/C02/C04**; C06 là dự phòng có dependency, không tự thêm
vào run đầu. Mục tiêu trước là so hai cơ chế khác nhau trên cùng dữ liệu/cost.

## 4. Quy tắc ứng viên đăng ký trước outcome mới

Chỉ EURUSD CFD, H4 UTC, dùng nến đã đóng; cả hai chiều, một vị thế mỗi phiên.
Đây là quy tắc nghiên cứu, chưa là quyền demo execution hoặc đóng băng code.

| ID phiên bản dự kiến | Quy tắc cố định |
|---|---|
| C01 / donchian20-10-atr14-v1 | Giữ nguyên baseline trong [pilot](FOREX-PROP-PILOT-20261102.md#2-một-giả-thuyết-cố-định-để-kiểm-đường-chạy): channel20/10, Wilder ATR14, initialstop2 × ATR |
| C02 / sma20-80-atr14-v1 | Tính SMA20/80 từ close đã biết. Với d=fast−slow, long khi d trước<=0 và d mới>0; short khi d trước>=0 và d mới<0. Longexit khi d<=0, shortexit khi d>=0; không đảo chiều cùng sự kiện. Initial stop2 × Wilder ATR14, không trailing |
| C04 / z20-2-atr14-time6-v1 | Mean và population SD của20 close **trước** nến tín hiệu; z=(close mới−mean)/SD. Long nếu z<=−2; short nếu z>=2. Thoát long khi z>=0, short khi z<=0; hoặc sau6 nến H4 hợp lệ kể từ fill. Initial stop2 × Wilder ATR14; không trailing, không bình quân lỗ; SD bằng 0/thiếu warmup thì bỏ tín hiệu |

C02/C04 là adaptations/comparators do ta đăng ký, không sao chép source và
không gọi là exact replication của tác giả. ATR/indicator phải causal và có
warmup đủ; C02 cần ít nhất80 nến và trạng thái chênh lệch trước crossover.
Không lấy thiếu lịch sử làm giá trị0, không fill nến thiếu tùy tiện.

**Làm rõ trước numerical run 05/11:** time exit của C04 tính sáu lần đóng nến
H4 hợp lệ khi cùng một position ID còn mở, gồm nến chứa lần fill. Không đổi
sang sáu nến tổng hợp qua gap hoặc kế thừa tuổi của vị thế trước cùng chiều.
Warmup mới dùng cache **01–31/12/2021** cho cả C01/C02/C04; phải có ít nhất
81 nến H4 hợp lệ trước development. Warmup cũ 20–31/12 chỉ có 58 nến, nên không
đủ cho crossover đã có giá trị trước. Không thay manifest/baseline lịch sử;
runner mặc định vẫn giữ contract cũ, chế độ study dùng manifest mới có hash.
Lượt đầu chỉ chạy lại development **03–14/01/2022** để kiểm numerical integration
và đối chứng; không gọi đây là OOS. Không xếp hạng lợi thế từ hai tuần đó.

Reuse execution/accounting đã có: buy tại ask/sell tại bid ở quote có thể giao dịch sau
quyết định; SL theo quote/gap, không giả khớp đúng stop; không pyramiding hoặc
martingale. Tại cùng tick, đối soát thứ tự native risk/SL/pending actions trước
strategy action. Đóng/mở, timeout và cuối mẫu phải giữ cùng semantics cho 3 bản.
Không fake close cuối mẫu để đẹp target. Mọi code mới phải kiểm timing/size/exit
và baseline parity trước khi đọc outcome mới.

## 5. Dữ liệu, chi phí và rủi ro thí nghiệm

- QDM CLI/cache hiện có là nguồn ưu tiên; chưa cần feed hoặc package mới.
- Lát đã consumed chắc chắn: warmup 20–31/12/2021 và development 03/01–31/03/2022;
  hai tuần nằm trong Q1, không là hai mẫu độc lập. Q1 manifest hash trong receipt.
  Quote demo 02–05/11/2026 cũng đã quan sát; không gọi nó là holdout mới.
- Split dự kiến kế thừa pilot: development 2018–2022, validation 2023–2024,
  holdout 2025→cutoff đầy đủ hợp lệ. **Chưa xác nhận availability/consumed cho
  toàn bộ các vùng**; phải inventory manifests/receipts không đọc outcome trước.
  Nếu vùng nào đã được dùng trong tìm kiếm thì chuyển nhãn trước khi test,
  không âm thầm dịch mốc sau khi thấy kết quả. Holdout cuối chỉ mở sau freeze.
- Warmup lấy từ quá khứ trước mỗi window, không tính PnL warmup; không dùng
  dữ liệu sau cutoff. Gap/timezone/DST/duplicate order phải có báo cáo, không
  sort/dedup/fill để ép data đạt. Thiếu intrabar equity → prop result unknown.
- Reuse reference/stress commission, slippage, timed financing đã khai báo trong
  pilot để so code; nhãn **declared scenario** giữ nguyên. Thêm cost profile
  The5ers chỉ khi có nguồn; không áp FTMO cost rồi gắn nhãn The5ers verified.
- Research baseline 10.000 USD giả lập, rủi ro dự kiến 25 USD/lệnh gồm chi phí,
  internal daily 100 USD/overall 500 USD như pilot, một vị thế; không tìm risk size
  từ outcome. Đây không là vốn owner, ngân sách challenge hay risk grant.
  Khi chuyển size/tier phải tính lại min lot/step/margin/cost; không nhân return
  tuyến tính hoặc dùng hết leverage để gọi scaleup. Chưa có portfolio concurrent.

## 6. Đánh giá và quy tắc quyết định

1. **Gate correctness/compliance:** lookahead, accounting, source/license,
   broker semantics và quy tắc hãng. Không xác minh được thì ghi unknown,
   không pass. Không đòi cả hai hãng đều pass để giữ một candidate nghiên cứu.
2. **So sánh edge:** cùng inputs/cutoff/lot/cost với cash và C01. Báo net PnL,
   return, equity drawdown, losing streak, tail days, số trade, exposure/turnover,
   thời gian phục hồi và contribution của vài trade lớn. Chưa rank chỉ bằng PnL.
3. **Out-of-sample:** development dùng phát triển, validation dùng chọn;
   holdout final là xác nhận riêng. Tất cả changes/thử bỏ cuộc phải lưu, gồm
   vòng trước của baseline, kết quả hai hãng và các risk variants nếu phát sinh.
   Nhiều agent/batch không reset trial count; không cho search agent đọc final holdout.
4. **Stress:** spread/slippage/commission/financing tăng theo scenario có nguồn,
   gap/delay/missing ticks; độ nhạy tham số là thí nghiệm đã đăng ký bổ sung,
   không là cách chọn điểm lợi nhuận cao nhất. Source/code/input/rule hashes giữ
   trước outcome. DSR/PBO chỉ tính khi dữ liệu/số trial/giả định phù hợp [R7,R8].
5. **Prop overlay riêng từng chương trình:** evaluation phase 1→phase 2→funded
   survival trên nhiều start windows, rules reset đúng phase và timezone. Ghi
   first breach, equity headroom, days-to-target, qualifying days, funded survival
   90/180 ngày nếu đủ history, payout eligibility và phí theo scenario đã pin.
   Windows chồng nhau phụ thuộc nhau; không coi hit rate là xác suất thành công
   chính xác. Cửa sổ chưa đủ thời gian là censored/unknown, không loại để đẹp số.
6. **Giữ/loại:** lỗi đúng/sai hoặc vi phạm đã xác minh → loại bản đó. Net OOS
   không dương dưới cost scenario hoặc edge biến mất trong stress → không
   promote; chưa đủ sample/coverage/precision → inconclusive, không tự pass.
   Net dương và drawdown thấp vẫn chưa đủ nếu bất định lớn/phụ thuộc vài trade.
   Candidate chỉ được đề xuất shadow khi có bằng chứng tái lập và toàn bộ gap
   liên quan được nêu rõ; không hứa một ngưỡng Sharpe/trade count là chứng nhận.

Trước numerical run, freeze manifest tiêu chí chính/secondary và từng scenario;
không đổi ưu tiên prop/edge sau khi thấy ai thắng. Dừng candidate vô hiệu sớm
nhưng giữ evidence. Tận dụng replay song song theo output riêng khi runner đã
hỗ trợ, không chạy worker thứ hai ghi cùng job. Không gọi model cho mỗi tick.

## 7. Nguồn gốc, quyền dùng và bước triển khai

Đọc tài liệu gốc để lấy ý tưởng; chỉ tự viết implementation. Chưa nhập code,
weights, dataset hoặc package bên thứba; license từng tài sản phải audit trước
khi import. Quyền đọc paper không tự cấp quyền tái phân phối paper/code/data.
Giữ label evidence hiện tượng/replication/adaptation riêng cho từngcandidate.

Bước tiếp: kiểm manifest availability/consumed → đóng băng candidate contract
và numerical runner nhỏ reuse core → focused causal/accounting checks → chạy
development và validation theo protocol. Chưa mở final holdout, không thêm
engine/framework/provider hoặc tự mua challenge. Khi Paperclip có lại, công bố
protocol/báo cáo trên native task hiện hành hoặc một task mới đúng scope sau
dedup; không restart graph fixture cũ hay tạo management UI ngoài.

### Primary sources đã đối chiếu

- **F1** [FTMO Trading Objectives, đúng phần2-Step](https://ftmo.com/en/trading-objectives/).
- **F2** [FTMO Swing account](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/).
- **F3** [FTMO strategies/EA](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/).
- **F4** [FTMO forbidden practices](https://ftmo.com/en/forbidden-trading-practices/).
- **T1** [The5ers High Stakes overview, dynamic New/Classic cards](https://the5ers.com/high-stakes/).
- **T2** [High Stakes drawdown FAQ, updated15/09/2026](https://the5ers.com/faqs/what-is-the-drawdown-rule-for-high-stakes/).
- **T3** [Profitable day FAQ, updated05/07/2026](https://the5ers.com/faqs/how-do-you-define-a-profitable-day-in-the-high-stakes-program/).
- **T4** [The5ers EA/source/visible SL, updated22/07/2026](https://the5ers.com/faqs/can-i-use-an-ea-expert-advisor-can-i-set-a-stealth-mode-stop-loss/).
- **T5** [The5ers prohibited practices, updated03/11/2026](https://the5ers.com/faqs/prohibited-trading-practices/).
- **T6** [High Stakes general/news rules, updated03/11/2026](https://the5ers.com/faqs/what-are-the-general-rules-for-the-high-stakes-program/).
- **T7** [The5ers Terms §11, updated28/10/2026, đối chiếu05/11](https://the5ers.com/terms-and-conditions/).
- **R1** [Moskowitz/Ooi/Pedersen, Time Series Momentum 2012](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum).
- **R2** [Hurst/Ooi/Pedersen, Century of Trend Following 2017](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing).
- **R3** [Menkhoff et al., Currency Momentum Strategies, BIS WP366](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies).
- **R4** [Osler, Currency Orders and Exchange-Rate Dynamics, NYFed SR125](https://www.newyorkfed.org/research/staff_reports/sr125.html).
- **R5** [Neely/Weller, Intraday Technical Trading in FX, Fed St Louis WP1999-016B](https://fraser.stlouisfed.org/docs/publications/frbsl_wp/1999-016.pdf): nghiên cứu này không tìm được excess return sau chi phí/giờ giao dịch thực tế; không suy ra mọi intraday strategy đều thất bại.
- **R6** [Brunnermeier/Nagel/Pedersen, Carry Trades and Currency Crashes, NBER WP14473](https://www.nber.org/papers/w14473).
- **R7** [Bailey et al., Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).
- **R8** [Bailey/López de Prado, Deflated Sharpe Ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).
- **R9** [QuantConnect research guide](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide).
