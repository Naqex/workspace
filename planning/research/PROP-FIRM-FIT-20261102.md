# Chọn prop firm cho hệ thống AI và vốn ban đầu hạn chế

**02/11/2026 · WORK: DRAFT · REVIEW: DOCUMENTATION-ONLY · DOC: FULL.**
Owner mới ra trường, cho biết hiện có 15 triệu đồng và muốn ưu tiên prop firm.
Chưa biết khoản này có phải toàn bộ quỹ sinh hoạt/dự phòng hay không. Đây là
khảo sát nguồn chính thức, chưa xác minh KYC, checkout hoặc payout thực tế và
không là quyết định mua challenge. [Brief](AUTONOMOUS-TRADING-SYSTEM-BRIEF.md)
giữ lựa chọn của owner; [kết quả hệ thống hiện tại](../checkpoints/ai-integrations-20261031/STRATEGY-READINESS-20261102.md)
giữ giới hạn bằng chứng chiến lược.

## Quyết định của owner sau khảo sát

**Phạm vi nghiên cứu làm rõ 05/11:** tập trung FTMO 2-Step Swing và The5ers High Stakes,
FTMO làm chuẩn chính để reuse hệ thống hiện có. Dùng chung ý tưởng/logic, kiểm
riêng rule/cost theo chương trình/size/version; không tối ưu cho propfirm chung.
[Khảo sát và protocol mới](PROP-STRATEGY-ROUND1-20261105.md) đối chiếu nguồn chính
thức 05/11, gồm giới hạn xác minh The5ers New/Classic/tier. Phần khảo sát 02/11 bên
dưới giữ như lịch sử, không thay các nguồn cập nhật hoặc quyết định mua.

Owner chốt ngày 02/11/2026: **Forex major qua MT5; FTMO 2-Step Swing làm chuẩn
mô phỏng đầu tiên; offline → free trial → chỉ xét challenge trả phí khi có đủ
bằng chứng và duyệt ngân sách**. The5ers giữ làm ứng viên thử phí thấp sau đó.
Tại quyết định02/11, cặp/timeframe/cỡ tài khoản/risk chưa chốt; cập nhậtM15 ở
mục onlyone bên dưới. Lựa chọn này chưa cấp quyền
đăng ký/kết nối tài khoản, đặt lệnh, mua challenge hay tự retry. Các nhận định
bên dưới giải thích lựa chọn, không là kết quả kiểm chứng chiến lược.

## Trading làm thu nhập chính — làm rõ ngày 10/11/2026

**Owner xác nhận mục tiêu dùng trading làm thu nhập chính**, chưa xác nhận đang
có thu nhập trading hoặc đủ dự phòng. Owner muốn so sánh các mốc trước khi chọn
setup. Khoản 15 triệu nêu ngày 02/11 là lịch sử, không được suy thành tiền dự
phòng hiện tại. Chưa chọn budget, risk/lệnh, holding period hay mua challenge.

### Dự phòng sinh hoạt và ngân sách thử nghiệm

Dùng chi phí sinh hoạt thiết yếu thực tế (ăn ở, điện nước, y tế, trả nợ/người phụ
thuộc) để tính số tháng đủ sống khi **không có payout**. Bảng dưới là đề xuất lập
kế hoạch của agent, không phải luật quỹ hoặc ngưỡng đã kiểm định bằng thống kê.
Ví dụ **8 triệu đồng/tháng chỉ để minh họa**, chưa phải chi phí của owner:

| Số tháng đủ sống | Tiền minh họa | Hướng vận hành đề xuất |
|---|---:|---|
| 3 tháng | 24 triệu | Ít dư địa cho nghiên cứu, fail challenge và chờ payout; ưu tiên demo/free trial và nguồn thu khác, chưa nên phụ thuộc trading |
| 6 tháng | 48 triệu | Có thể thử quy mô nhỏ sau khi đủ bằng chứng và có ngân sách riêng; chưa mặc định bỏ nguồn thu khác |
| 12 tháng | 96 triệu | Mốc lập kế hoạch ưu tiên nếu muốn phụ thuộc chủ yếu trading; vẫn phải chứng minh edge, vận hành và dòng tiền thực nhận |
| 18 tháng | 144 triệu | Chịu gián đoạn lâu hơn; không làm bot tốt hơn và không tự cho phép nâng risk |

Dưới 3 tháng thì còn ít dư địa hơn hàng đầu. Tách tiền đủ sống theo kế hoạch,
khoản bất trắc ngoài dự kiến và ngân sách challenge/retry/vận hành; không tính
trùng cùng một khoản tiền. Ngân sách thử nghiệm phải là khoản mất được mà vẫn
giữ phần sinh hoạt đã dành riêng. Vốn danh nghĩa trên tài khoản quỹ và lợi nhuận
chưa rút không phải tiền mặt của owner. Quỹ đủ sống cần dễ tiếp cận và ít biến
động; không dùng chính bot trading để giữ tiền dự phòng.

[CFPB về emergency fund](https://www.consumerfinance.gov/an-essential-guide-to-building-an-emergency-fund/),
đọc 10/11: khoản cần có phụ thuộc hoàn cảnh và cần quản lý dòng tiền. Nguồn này
không đặt chuẩn riêng 12/18 tháng cho prop trading; các mốc trên là khuyến nghị
thận trọng cho mục tiêu thu nhập chính chưa được chứng minh của owner.

### Thời gian giữ lệnh không phải chu kỳ thu nhập

Nghiên cứu hiện có cả intraday và swing nhiều ngày; chưa chọn một bot để giao
dịch challenge. M1/H1/H4 là khung dữ liệu, không tự quyết định giữ lệnh bao lâu;
mục tiêu pass trong 3/6/12 tháng cũng không phải holding period. Intraday có thể
giảm phơi nhiễm qua đêm, nhưng turnover/spread/slippage vẫn có thể làm mất edge.
Swing có ít cơ hội hơn hoặc thêm funding/gap risk; không loại chỉ vì ít lệnh.
So sánh hai hướng bằng net equity, chi phí thực tế, drawdown, thời gian không có
payout và độ phù hợp với luật funded; không ép vào lệnh để tạo thu nhập mỗi ngày.

FTMO Swing là loại tài khoản, không bắt buộc giữ lệnh nhiều ngày. Kiểm lại
[Swing FAQ](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/)
và [holding FAQ](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/)
ngày 10/11: Swing được miễn hạn chế giữ qua market break >2 giờ tương ứng, base
leverage thấp hơn Standard. Không diễn giải Standard cấm mọi overnight.

[Reward FAQ FTMO](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/), đọc 10/11:
có thể yêu cầu từ ngày 14 sau lệnh đầu trên tài khoản tương ứng, phải đóng vị
thế/lệnh chờ, đạt điều kiện và qua review/thanh toán. Đây không phải lương chắc
chắn hai tuần/lần; evaluation PnL không là tiền sinh hoạt. Không suy cùng cơ chế
reset loss limit/payout cho mọi chương trình. Sau withdrawal cần tính lại
headroom theo đúng hợp đồng, không giữ sizing dựa trên lợi nhuận đã rút.

Setup cần đánh giá thêm: thời gian không nhận được tiền, payout ròng sau split/
phí/thuế và chi phí retry/vận hành, mất tài khoản/gián đoạn hãng, nhu cầu sinh
hoạt và nguồn thu thay thế. Khoản thuế chưa được tư vấn/xác minh riêng cho owner.
Không suy từ số dư mô phỏng hoặc một payout thành thu nhập bền vững. Không đổi
risk/lệnh theo số tháng dự phòng, không tăng lot để bù thiếu tiền sinh hoạt.

**Giới hạn hiện tại:** [báo cáo bằng chứng](OWNER-EVIDENCE-REPORT-20261108.md)
vẫn ghi chưa có ứng viên đủ bằng chứng đề xuất mua challenge. Chưa có cơ sở
tính xác suất hết tiền dự phòng hoặc dự báo thu nhập cho owner. Bản cập nhật này
chỉ lưu mục tiêu và phương án; chưa chọn thay owner hoặc thay cấu hình bot,
protocol đã freeze, quyền broker/holdout hay trạng thái Goal.

## Only one: hồ sơ mục tiêu và các case để owner chọn — 10/11/2026

**Quyết định mới của owner:** thử onlyone trong thời gian tới để thu hẹp nghiên
cứu theo mục tiêu; yêu cầu nhắc lại mục tiêu, so timeframe/risk/frequency/winrate
trước chọn case. Không đồng nghĩa chốt case cụ thể, phải trade hằng ngày hoặc
đóng hết các hướng nghiên cứu cũ. Không có numeric run/strategy/filter mới.

**Xác nhận tiếp10/11:** owner chốt **M15 làm khung tín hiệu cho vòng onlyone
đầu tiên**. Sản phẩm, cơ chế, holding, tần suất, winrate và risk thật vẫn cần
chọn; xác nhận khung không tự phê duyệt toàn bộcaseA/EURUSD hoặc gửi lệnh.

| Nội dung | Đã chốt từ owner | Còn thiếu / cách hiểu |
|---|---|---|
| Thu nhập | Hướng tới trading là nguồn chính | Chưa xác nhận hiện profitable hoặc mức thu nhập ròng/sinh hoạt cần mỗi tháng |
| Nguồn vốn | Ưu tiên vốn prop và kiểm soát rủi ro cá nhân | Vốn danh nghĩa không tiền mặt owner; chi phí challenge/retry và reserve chưa chốt |
| Đích | Có edge sau phí, đủ cơ sở challenge, giữ tài khoản/payout nhiều kỳ | Chưa có candidate challenge-qualified; không tối ưu chỉ một lần pass nhanh |
| Chuẩn chính | FTMO CFD2-StepSwing/MT5;The5ersHighStakes đối chiếu sau | Cỡ tài khoản/package/chi phí đích chưa pin; mỗi chương trình cần qualification riêng |
| Cách nghiên cứu | Recent-first từ2022 và thử onlyone |2025+reserved giữ gate; không sửa oldoutcomes hoặc tự mở data |
| Vận hành | Owner nói có thể để máy24/7, trừ sự cố bất khả kháng | Đây là khả năng owner khai báo, không runtimeuptime đã đo; cần supervision/recovery |
| Holding/timeframe | **M15 đã chốt cho vòng onlyone đầu** | Thời gian giữ lệnh/day-swing chưa chốt; khung nến không tự quyết định holding hoặc số lệnh |
| Risk/winrate/frequency | Chưa có lựa chọn cuối |0,25% là baseline nghiên cứu đã dùng, không optimum hoặc authorityrisk thật; không tự đặt quota lệnh |
| Thời hạn | Owner muốn so các mốc3/6/12tháng | Chưa deadline cá nhân hoặc dự báo pass; khác thời gian giữ một lệnh |

### Ba case để cân nhắc, chưa có chiến lược chứng minh đúng các tần suất này

| Case tổ chức nghiên cứu | Khung quyết định/holding minh họa | Tần suất mong muốn và đánh đổi |
|---|---|---|
| A.Intraday có chọn lọc — agent nghiêng về để bắt đầu | KhungM15 owner đã chốt; một sản phẩm và holding intraday vẫn là đề xuất | Canh cơ hội hằng ngày, mong khoảng2–5lệnh hợp lệ/tuần; không quota. Có phản hồi đều hơn sparseevents nhưng fees/tail/clock cần đo |
| B.Short swing | Một sản phẩm, khungH4, giữ1–5ngày theo rule được kiểm | Chấp nhận ít cơ hội hơn, nhiều ngày không vào; thêm funding/gap và payoutflatness cần đo |
| C.Sự kiện thưa | Một sản phẩm, eventcalendar và một khung quyết định đã chọn | Có thể vài cơ hội/tháng; hợp cơ chế cụ thể nhưng tích lũy evidence và chuyển thành dòng tiền có thể chậm; không tự loại khi có edge |

Khung và frequency là sở thích vận hành đề xuất, không observedstatistics,
statistical minimums hoặc bộ lọc tự loại. Chưa chọn cơ chế/entry/exit hoặc biết
caseA có netedge. Scalping siêu ngắn chưa ưu tiên vì execution/cost sensitivity,
không kết luận mọi scalper đều thất bại. Cần đo frequency/holding thực tế, không
đổi threshold để ép đủ2–5lệnh hoặc closewithin-day khi chưa replayversion mới.

Nếu owner chọnA, gói nghiên cứu agent đề xuất hiện là **EURUSD + M15 + intraday +
FTMO2-StepSwing profile**, theo [đối chiếu cộng đồng/quỹ10/11](TIMEFRAME-SELECTION-ONLYONE-20261110.md).
Đề xuấtH1 ban đầu được thay về mặt tư vấn, không sửa oldprotocols hoặc coiM15
optimal đã đo. Owner đã chốt riêngM15, chưa xác nhận toàncase. EURUSD có data/validators reuse giảm setupcost,
chưa là thị trường có edge tốt nhất. Cơ chế kinh tế vẫn phải được chọn và khóa
trước outcome; không rerun các EURUSDversions đã gác để mong kết quả khác.
Swing là loại tài khoản, không bắt bot giữ nhiều ngày. The5ers không phải cùng
broker/feed/cost và chưa là một deployment thứ hai.

### Đề xuất chọn tiếp sau M15 — chưa là quyết định của owner

Owner hỏi thêm lựa chọn. Agent đề xuất giữ **EURUSD** để reuse dữ liệu và
validators; đây là lợi ích triển khai, chưa chứng minh EURUSD có edge tốt nhất.
Ba hướng để owner hiểu và chọn một câu hỏi nghiên cứu, không chạy cả ba:

| Hướng | Ý tưởng dễ hiểu | Đánh đổi chính |
|---|---|---|
| A. Breakout | Giá ra khỏi vùng đã xác định, kỳ vọng tiếp tục đi | Luật tương đối rõ; phá vỡ giả và spread/slippage khi biến động là rủi ro |
| B. Pullback theo xu hướng | Giá đang đi một hướng, chờ lùi rồi có dấu hiệu đi tiếp mới vào | Agent nghiêng về để owner học/kiểm luật; xác định trend và pullback phải khách quan, có thể lỡ đoạn giá chạy thẳng hoặc gặp đảo chiều |
| C. Phá vỡ thất bại | Giá vượt biên rồi đóng trở lại vùng cũ, kỳ vọng hồi vào trong | Điều kiện vào có thể định nghĩa rõ; dễ thua nếu xu hướng mạnh tiếp diễn, không mặc định winrate cao |

Đây là cách tổ chức ý tưởng, không ba edge độc lập đã admitted. Các bản
breakout prior-day/session, retest R019 và pullback20/80 trước đây đã không
được giữ sau cost screen; giữ nguyên kết quả âm và lineage trong
[catalogue](STRATEGY-CATALOGUE-20261107.json). Không bê recipe cũ sang M15
hoặc đổi SL/giờ/filter rồi tự coi là hướng mới có cơ sở. Owner chọn sở thích
nghiên cứu trước; trước triển khai cần nêu giả thuyết có thể bác bỏ, khác biệt
có cơ sở so với parent và admission review. Nếu chưa có khác biệt hợp lý thì
báo chưa đủ điều kiện chạy, không mở grid để cứu loser.

Nguồn đọc lại10/11: [FTMO Academy](https://academy.ftmo.com/lesson/how-to-create-a-trading-idea/)
phân loại trend/range, breakout/holding level và yêu cầu entry/exit/risk rõ;
không xác nhận hiệu suất bot. [NY Fed, Osler2001](https://www.newyorkfed.org/research/staff_reports/sr125.html)
liên hệ order clustering với phản ứng tại level và momentum sau khi vượt
level; bằng chứng lịch sử một dealing bank, không proof net CFD hiện tại
hoặc cho phép suy stop map từ nến. Ưu tiên B là judgement về khả năng giải
thích/kiểm luật, không ranking hiệu suất. Winrate, RR và tần suất còn unknown;
0,25% chỉ baseline offline, chưa risk thật. Không numerical/broker/holdout run.

**Trao đổi tiếp10/11 — timeframe nhỏ hơn:** owner hỏi có nên nhỏ hơnH1, chưa
chốtM15/M30/H1 tại thời điểm hỏi; sau đó giao research rồi đề xuấtchốt, dẫn tới
M15 ở report trên. H1 ban đầu là defaultreuse, không kết quả so sánh tối ưu.
M15 là lựa chọn có thể cân nhắc nếu cơ chế cần quan sát thay đổi trong khoảng
30–90phút; H1 có thể đủ cho cơ chế kéo dài nhiều giờ. Các khoảng này minh họa
độ phân giải, không suy holding/tần suất từ timeframe. Chọn theo thời gian của
cơ chế trước, không quét nhiều khung rồi chỉ giữ winner trên cùngdata. M1/M5
chỉ ưu tiên khi có lý do kinh tế/execution cụ thể; không nói mọi lowerTF kém.
Nhiều nến không thêm independentopportunities; oneTFtínhiệu vẫn có thể dùng
tick/M1 để mô phỏng SL/fill đúng. Ví dụ riêng:1pipcost trên5pipgross=20%, trên
20pipgross=5%, chưa observedcost/netedge. [FTMO infrastructure](https://ftmo.com/en/faq/how-does-the-ftmo-technical-infrastructure-work/)
và [QC slippage](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/slippage/key-concepts)
mở10/11 xác nhận commissions/delay/slippage cần mô hình; không xác nhận khung
nào tối ưu. Chưa đổi case/rules/risk/config hoặc mở numericalrun/holdout/broker.

### Risk và winrate để owner hiểu lựa chọn

Đề xuất giữ **0,25%/trade làm mốc so sánh offline** để reuse baseline;10k×0,25%
=25USDplannedSLrisk=1R. Chưa chốt risk giao dịch, daily/accountbudget, accountsize
hoặc phép chạy lại riskgrid. PlannedSL không guaranteedmaxloss khi gap/slippage;
không lấy mức5%/10%maxloss của hãng làm budget nên dùng. Sau khi có netedge mới
review sizing và tổng exposure phù hợp; không tănglot để đủ sinh hoạt.

Không khóa winrate≥60/70/80% trước. Xét averagewin/averageloss thực tế, costs,
losingstreak/tails và thời gian khôngpayout. TP/SL danh nghĩa không bắt buộc bằng
average realizedRR vì có timeexit/trailing/partial hoặccosts. Hai ví dụ dưới
chỉ minh họa10lệnh,1R=25USD,loss=1R vàfee2,50USD/lệnh riêng:

| Ví dụ | Winrate/averagewin trước phí | Tổngnet10lệnh |
|---|---|---:|
| A |4thắng×50USD,6thua×25USD;40%,2Rwin|200−150−25=+25USD|
| B |7thắng×12,50USD,3thua×25USD;70%,0,5Rwin|87,50−75−25=−12,50USD|

Không dự báo nhóm10trade tương lai có đúng4/7wins, không chứng minh expectancy
hoặc riskcap thật. Lệnh hằng ngày không bảo đảm lãi/payout hằng ngày; để chọn
accountsize/dòng tiền cần mức sinh hoạt/reserve/ngân sách thử nghiệm thực tế.
Không sử dụng lại15triệu lịch sử hoặc8triệu/tháng minh họa như facts hiện tại.

Nguồn chính thức mở10/11: [FTMO Swing](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/)
giữ flexibilityholding/news tương ứng, baseleverage1:30; [2-Step objectives](https://ftmo.com/en/trading-objectives/)
target10%/5%,daily5%/overallstatic10% theo equity/clock của chương trình, không
nhầm1-Step/Instant. Chỉ kiểm scope cần cho bảng lựa chọn, chưa toàntermsaudit.
[The5ers page](https://the5ers.com/high-stakes/) đọc cùng ngày giữ targetphụ;
chưa refresh/resolve mọi NewClassic/inactivity/approvalgap trong lượt này.

## Thời gian challenge và độ phù hợp chiến lược — kiểm lại 05/11/2026

**Có research trước; còn thiếu bước áp vào đánh giá ứng viên.** Round1 và bản
02/11 bên dưới đã ghi unlimited/minimum days/inactivity/payout, nhưng screen
vừa chạy chủ yếu kiểm PnL và cost stress. Chưa mô phỏng đầy đủ thời gian qua hai
phase hoặc đến payout. Phần này cập nhật interpretation; không đổi tiêu chí,
rules/risk/cost hoặc protocol của hai bài đã freeze.

### Các đồng hồ khác nhau

| Điều kiện | FTMO 2-Step Swing | The5ers High Stakes | Ảnh hưởng chọn chiến lược |
|---|---|---|---|
| Hạn hoàn thành evaluation | Không có tối đa; ≥4 ngày giao dịch mỗi phase, không cần liên tiếp | Unlimited; ≥3 ngày có lãi mỗi phase | Ít lệnh vẫn có thể thi; phải tính thời gian đạt đủ cả target và số ngày |
| Kích hoạt / không hoạt động | Challenge Terms §5.8.4: mở lệnh đầu trong30 ngày từ khi từng phase được cấp, nếu không bị suspend; có6tháng xin renewal. §13.2.3(a): hãng có quyền chấm dứt Challenge sau30 ngày lịch liên tiếp không mở lệnh mới | FAQ03/11: evaluation30 ngày từ đăng ký, Pro60 ngày. Trang chương trình vẫn ghi30 ngày tổng quát: **còn xung đột phạm vi** | Đo khoảng cách giữa lần mở lệnh; giữ lệnh lâu không tự đáp ứng điều kiện mở lệnh mới của FTMO. Không thêm lệnh giả chỉ để đủ hoạt động |
| Thế nào là ngày đủ điều kiện? | Có mở vị thế; không bắt buộc ngày lãi | Lãi tính theo `min(balance midnight, equity midnight) − balance ngày trước` ≥0,5% vốn ban đầu | Trên10.000USD, The5ers cần≥50USD/ngày; có nhiều ngày vào lệnh chưa đủ |
| Giữ lệnh / news | Swing bỏ hạn chế giữ qua đêm/cuối tuần và hạn chế news tương ứng; forbidden practices vẫn áp dụng | Cho giữ qua đêm/cuối tuần; không khớp lệnh ±2phút quanh tin high-impact | Kiểm cả exit/SL khớp quanh tin, swap/rollover/gap; không chỉ giờ tín hiệu |
| Từ funded/Pro tới thưởng | Yêu cầu từ ngày14 sau lệnh đầu trên FTMO Account; phải đóng vị thế/lệnh chờ, còn review và xử lý thanh toán | Pro có lịch yêu cầu hai tuần; cần đủ ngày lãi và payout minimum/cap của đúng tier | Pass challenge khác tiền thực nhận; evaluation PnL không rút được |
| Trial/demo | Free Trial14ngày,2-Step target5%, tối thiểu2ngày; kết thúc nếu không trade7ngày đầu | Chưa có tài khoản của owner để kiểm | **Không lấy hạn14ngày của FTMO Free Trial làm hạn challenge trả phí** |

Nguồn chính thức đọc05/11:

- [FTMO thời gian 2-Step](https://ftmo.com/en/faq/how-long-does-it-take-to-become-an-ftmo-trader/)
  và [objectives](https://ftmo.com/en/trading-objectives/): target10% rồi5%,
  ngày giao dịch và unlimited. Mốc8ngày cho hai vòng là tối thiểu lý thuyết,
  không phải thời gian dự kiến hoặc cam kết pass.
- [FTMO Challenge Terms, cập nhật04/08/2026, §5.8.4, §5.8.6, §13.2.3](https://cdn.ftmo.com/docs%2Fterms-and-conditions%2Ff8d5ca5086964c86a6ee2a77f20bdbd7),
  PDF22trang, pp.7–8/15–16. Thêm §13.2.3(b): giữ mức lỗ8–10% hơn30ngày là
  căn cứ chấm dứt khác; giao dịch né điều khoản không khắc phục nó. Đây là
  **evaluation contract**, chưa suy cùng luật cho funded hoặc agreement checkout
  cụ thể. Web parser không đọc được URL trong lần kiểm lại; đã tải từ CDN chính
  thức, kiểm PDF header và trích nội dung bằng bundled pypdf, giữ bản private.
- [FTMO Swing](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/),
  [Free Trial](https://ftmo.com/en/ftmo-free-trial/),
  [reward](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/): Swing thuộc2-Step;
  reward review thường1–2ngày làm việc, gửi tiền thường1–2ngày làm việc sau invoice
  được duyệt; còn KYC/hợp đồng/chuyển phase, không cộng thành ETA bảo đảm.
- [The5ers general rules,03/11](https://the5ers.com/faqs/what-are-the-general-rules-for-the-high-stakes-program/),
  [program](https://the5ers.com/high-stakes/),
  [minimum days,30/10](https://the5ers.com/faqs/is-there-a-minimum-trading-day-or-minimum-position-requirement/),
  [profitable day,05/07](https://the5ers.com/faqs/how-do-you-define-a-profitable-day-in-the-high-stakes-program/),
  [payout,03/11](https://the5ers.com/faqs/payout-policy-and-hub-credit-in-the-high-stakes-program/).
  Payout tối thiểu150USD **sau split**, thêm minimum P&L/cap cho50K/100K.
  Chưa rõ việc reset3ngày lãi từng chu kỳ payout; không tự gán. Không áp câu
  “Level1 không có minimum days” của ngữ cảnh chương trình khác vào High Stakes.
  New/Classic/tier vẫn phải pin đúng lựa chọn; không suy mọi gói có cùng targets.

Các nguồn02/11 bên dưới giữ ngày kiểm lịch sử. Mục hiện tại cập nhật riêng các
điều kiện thời gian; chưa tái xác minh toàn bộ giá, eligibility hoặc tài chính hãng.
The5ers automation approval theo Terms§11 vẫn là gap đã biết, không được giải
quyết bởi việc đáp ứng ngày lãi hoặc unlimited time.

### Đối chiếu ledger đã có, không chạy lại backtest

Diagnostic hậu kiểm20snapshot:5candidate×2costs×Q1/2022,Q1/2023; kiểm artifact
hashes và đối soát cash ngày về balance cuối. Q1/2023, cost-stress:

| Ứng viên | Số ngày mở lệnh, Europe/Prague | Khoảng nghỉ lớn nhất giữa hai lần mở | Giữ lệnh đã đóng lâu nhất |
|---|---:|---:|---:|
| Donchian |12|18,67ngày|296giờ|
| SMA |5|55,50ngày|668giờ|
| Z-score |24|7,67ngày|76giờ|
| Pullback |5|30,67ngày|488giờ|
| UTC range |48|5,00ngày|8,001giờ|

SMA/Pullback có cờ inactivity đáng kiểm; đây chưa là phán quyết tài khoản hết
hạn vì còn activation, calendar boundary, định nghĩa activity và exceptions.
Thời gian giữ chỉ gồm lệnh đã đóng; không che vị thế Donchian/Pullback còn mở.
Không bản nào đạt tăng balance được ghi nhận1.000USD trong đường Q1/2023 đang
xem. Đây là **chưa đạt trong cửa sổ quan sát**, không là fail vì deadline do ta đặt.

Riêng UTC range, ngày cash tốt nhất ở reference/stress lần lượt21,04/20,96USD
(Q1/2022),41,64/41,48USD (Q1/2023). Với cả bốn cách chia ngày UTC+0/+1/+2/+3,
**0 ngày đạt50USD**. Do `min(balance,equity) ≤ balance`, số ngày cash đạt ngưỡng
chỉ là trần trên của số ngày đủ luật hãng trong cùng cách chia ngày. Chưa có
midnight-equity/calendar/cost profile The5ers được xác minh, nên đây là cảnh báo
với cấu hình đang thử, không chứng nhận broker hoặc full-rule failure.

Evidence private: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q12023-robustness-20261105/time-fit-review-20261105/`
giữ `audit_existing_ledgers.py`, `time-fit-review.json` và PDF/text Terms FTMO.
Post-hoc,0numerical workers/giá mới; không dùng outcome này sửa frozen screen.

### Điều chỉnh cách chọn và bài kiểm tiếp theo

Ưu tiên UTC range trong receipt trước chỉ là **ưu tiên research sau cost-screen**,
chưa chứng minh phù hợp thời gian/prop. Không chốt winner từ hai quý không liên
tiếp. Z-score đổi dấu giữa hai quý cũng chưa có edge ổn định. Không kéo dài mẫu
bằng ngoại suy tuyến tính hoặc nhân lot từ lợi nhuận một quý.

Trước study tiếp, đăng ký time-fit cùng edge/risk: phase1→reset→phase2, target
khi flat/đủ ngày hợp lệ, first breach, activation/inactivity, holding/news/swap,
rồi funded eligibility→payout request→tiền thực nhận. **Owner xác nhận05/11:
chưa chốt hạn cá nhân; so sánh các mốc3/6/12tháng trước**, giữ ưu tiên rủi ro thấp,
không ép tăng lot. Đây là horizon đánh giá, không phải deadline hãng hoặc cam
kết pass. Protocol tiếp khóa ngày bắt đầu/kết thúc và cách tính tháng lịch;
90/180/365ngày ở đề xuất ban đầu chỉ là xấp xỉ, không đồng nhất tháng lịch.
Báo reached/breached/not-reached-within-observation/unknown và coverage; không
coi mẫu ngắn là đã đánh giá đủ12tháng hoặc windows chồng nhau độc lập.

Ví dụ cùng cấu hình nominal risk25USD/trade trên10.000USD: target10%=1.000USD
≈40R; phase2 5%=500USD≈20R; ngày lãi0,5%=50USD≈2R. Đây là quy đổi đơn vị,
không dự báo số trades/thời gian pass hoặc đề nghị tăng risk. Mục tiêu vẫn là
lấy vốn quỹ với rủi ro kiểm soát, không ép giao dịch để pass nhanh.

**Đã có evaluator lifecycle offline ở scope mô phỏng.**
`projects/trader/foundation_v2/trading_workspace_v2/prop_session.py` hiện đã
kiểm phase target, daily/overall loss, static/trailing HWM, reset/DST, minimum
qualifying days, max calendar days, carry/position policy và thứ tự fee/reset;
`evaluate_prop_lifecycle_event` giữ revision/event sequence và fail-closed khi
thiếu dữ liệu. `tests/test_ftmo_swing_offline.py`, `test_ps02_prop_lifecycle.py`
và replay-connection tests đã đạt **55 tests, 24 subtests** ở lần kiểm
06/11/2026.

Evaluator này chưa đóng các gap firm-specific: activation/inactivity policy,
news/overnight/weekend exceptions theo terms hiện hành, payout/eligibility,
historical broker fills và live reconciliation. Vì vậy nó đủ để đăng ký và
đánh giá time-fit offline theo profile đã pin, chưa đủ để kết luận pass quỹ hoặc
time-to-payout. `semantics/prop_profile.py` vẫn là loss-floor oracle đơn giản;
không dùng nó thay lifecycle evaluator cho hai-phase study.

## Cơ sở lựa chọn và các phương án đã khảo sát

1. Dùng **FTMO 2-Step Swing** làm mục tiêu mô phỏng đầu tiên; bắt đầu offline,
   rồi free trial khi hệ thống đủ sẵn sàng và owner cho phép đăng ký/kết nối.
   Đây là đánh giá theo luật, nhịp giao dịch và khả năng reuse MT5; không phải
   xếp hạng lợi nhuận hoặc chứng nhận an toàn tài chính của công ty.
2. **The5ers High Stakes gói nhỏ** là ứng viên thử phí thấp sau khi có bằng
   chứng. Giá rẻ không thay các gate chiến lược/automation và xác minh checkout.
3. **HyroTrader Two-Step** giữ làm phương án crypto cần khảo sát sâu hơn; chưa
   kết luận tư cách đăng ký của owner hoặc khả năng tích hợp API cụ thể.
4. Topstep chưa ưu tiên cho kiến trúc tự chủ có thể chạy trên server; loại
   FundedNext CFD khỏi shortlist hiện tại vì chính sách Việt Nam.

**Hiện chưa chi tiền challenge.** Không dùng cả 15 triệu làm ngân sách retry,
không mua nhiều tài khoản hoặc coi phí được hoàn là chắc chắn thu hồi được.
Mỗi lần retry sau này phải có lý do/bằng chứng mới và trần phí được owner duyệt.

## So sánh nhanh

Quy đổi **minh họa**, không phải tỷ giá ngân hàng: $1 = 26.000đ, €1 = 30.000đ.
Giá trước phí thẻ, chênh lệch ngoại tệ, thuế/add-on và thay đổi tại checkout.
Không dùng mã affiliate hoặc khuyến mãi cộng đồng làm giá chuẩn.

| Chương trình | Phí công bố để tham khảo | Automation và điểm cần chú ý | Đánh giá cho case này |
|---|---|---|---|
| FTMO 2-Step Swing | Free trial 0đ; trang promo chính thức có mốc €89 cho $10K ≈ 2,67 triệu; chưa chốt giá Swing tại checkout | Cho EA; Swing không hạn chế news/giữ lệnh cuối tuần. Luật giao dịch khác vẫn áp dụng | Ưu tiên làm chuẩn mô phỏng, chưa mua |
| The5ers High Stakes $2,5K | Trang chương trình hiện hiển thị $19 ≈ 494.000đ; cần kiểm đúng biến thể/gói tại checkout | EA được phép có điều kiện, phải sở hữu source, SL hiển thị; có luật news và ngày có lãi | Ứng viên phí thấp, chưa phải lựa chọn được owner chốt |
| HyroTrader Two-Step $5K | Bảng giá của hãng $59 ≈ 1,534 triệu | Cho tự động hóa chiến lược của mình; perpetual có margin/funding, tư cách sử dụng sàn kiểm riêng | Giữ làm nhánh crypto, chưa mở quyền futures |
| Topstep $50K Standard | $49/tháng + API $14,50/tháng với mã Topstep công bố; activation $149 khi đạt | API cho tài khoản mô phỏng; truyền lệnh phải từ thiết bị cá nhân, không VPS/server | Chưa ưu tiên: phí lặp, kiến trúc và nhịp giao dịch khác |
| FundedNext CFD | Không so giá khi không đạt eligibility | Help Center liệt kê Việt Nam trong danh sách hạn chế | Loại ở thời điểm khảo sát |

Nguồn giá: [FTMO promo](https://promo.ftmo.com/u26a-path-to-confident-trading/),
[The5ers High Stakes](https://the5ers.com/high-stakes/),
[HyroTrader bảng giá của hãng](https://www.hyrotrader.com/blog/how-much-does-a-funded-account-cost/),
[Topstep pricing](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions).
Nguồn quyền automation/eligibility nằm trong từng mục bên dưới. Chưa vào
checkout hoặc cung cấp thông tin cá nhân; các mốc trên không là báo giá mua.

## FTMO: phù hợp để mô phỏng trước

- Trang eligibility hiện không liệt kê Việt Nam trong danh sách hạn chế. Đây
  là kiểm tra chính sách công bố, không thay xác nhận KYC/thanh toán cá nhân:
  [Who can join](https://ftmo.com/en/faq/who-can-join-ftmo/).
- [Swing](https://ftmo.com/en/faq/ftmo-swing-account-type/) chỉ thuộc 2-Step,
  bỏ hạn chế news/giữ lệnh qua đêm và cuối tuần. Các rủi ro gap/swap vẫn phải
  mô phỏng. Không suy ra mọi sản phẩm 1-Step/Instant có cùng luật.
- [2-Step objectives](https://ftmo.com/en/trading-objectives/): target 10% rồi 5%,
  daily loss 5%, maximum loss 10% theo vốn ban đầu; ít nhất 4 ngày giao dịch mỗi
  phase, không giới hạn thời gian. Daily reset theo 00:00 CE(S)T, phải xử lý DST
  và equity gồm lãi/lỗ đang mở, swap, commission; không chỉ kiểm balance cuối ngày.
- [EA/algorithmic trading được phép](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/),
  nhưng forbidden practices vẫn áp dụng. Chưa có xác nhận riêng về toàn bộ
  kiến trúc AI nhiều agents của workspace; cần mô tả luồng thực tế trước dùng.
- [Free trial](https://ftmo.com/en/ftmo-free-trial/) 14 ngày, tạo lại được từng
  tài khoản một. Trial có target và số ngày tối thiểu giảm so challenge thật;
  pass trial không là pass challenge hoặc bằng chứng chiến lược bền vững.
- [Payout](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/) có thể yêu cầu
  từ ngày 14 sau lệnh đầu, phải đóng vị thế/lệnh chờ và qua review. Số dư mô
  phỏng không thuộc sở hữu của trader; không coi nó là tiền có thể rút.

Mốc €89 lấy từ trang promo của chính FTMO cho $10K 2-Step; trang sản phẩm render
không cung cấp đủ giá cấu hình Swing trong lần đọc. Chưa coi đây là giá cuối.

## The5ers: phí vào nhỏ, có thêm ràng buộc chiến lược

- [Eligibility](https://the5ers.com/faqs/who-can-join-the5ers/) và
  [Terms 28/10](https://the5ers.com/terms-and-conditions/) không nêu Việt Nam
  trong danh sách công bố đã đọc; vẫn cần KYC cá nhân và điều kiện hiện hành.
- High Stakes đang hiển thị gói $2,5K giá $19; target 10%/5%, daily 5%, total 10%,
  có 3 ngày có lãi mỗi phase. Ngày có lãi đòi ngưỡng 0,5% theo cách tính của hãng;
  không thể thay bằng một lệnh nhỏ để đủ ngày. [Trang chương trình](https://the5ers.com/high-stakes/).
- [EA policy](https://the5ers.com/faqs/can-i-use-an-ea-expert-advisor-can-i-set-a-stealth-mode-stop-loss/)
  đòi sở hữu source và SL phải hiển thị. Cấm một số dạng copy/HFT/arbitrage.
  Cần làm rõ bằng văn bản cách áp dụng với code AI hỗ trợ và thư viện upstream;
  việc có source code trên máy không tự chứng minh phù hợp điều khoản.
- [General rules 15/09](https://the5ers.com/faqs/what-are-the-general-rules-for-the-high-stakes-program/)
  cấm khớp lệnh trong khoảng 2 phút trước/sau tin high-impact; giữ lệnh qua tin
  được phép. Inactivity: evaluation 30 ngày, funded 60 ngày theo FAQ. Trang
  chương trình ghi 30 ngày tổng quát: cần hỏi rõ phạm vi; không tự chọn bản dễ hơn.
- [Payout policy 14/09](https://the5ers.com/faqs/payout-policy-and-hub-credit-in-the-high-stakes-program/)
  tách 10%/20% Hub Credit không rút được và 70% fee refund có điều kiện ở funded
  stage. Không diễn giải nhãn Refund thành hoàn 100% tiền mặt. FAQ có payout cap
  cho $50K/$100K; chưa xác nhận cap/minimum của gói $2,5K, cần hỏi trước khi mua.

Suy luận: yêu cầu ngày có lãi và inactivity có thể không khớp chiến lược D1 ít
lệnh. Không tăng rủi ro hoặc ép thêm lệnh chỉ để đạt các yêu cầu đó.

## HyroTrader: nhánh crypto có điều kiện

- [Terms 29/09 §10.2](https://www.hyrotrader.com/terms-and-conditions/) cho phép
  tự động hóa chiến lược của chính người dùng, kể cả agent/MCP nếu hãng cung
  cấp; cấm hệ thống thực hiện chiến lược của người khác/copy signal. Điều khoản
  nhắc MCP không chứng minh endpoint/tool đã sẵn dùng hoặc được tích hợp.
- Cùng Terms §12: danh sách hard block không nêu Việt Nam, nhưng còn enhanced
  due diligence, danh sách trên platform và eligibility của sàn riêng. Vì vậy
  **chưa đánh dấu owner đủ điều kiện** chỉ từ việc không tìm thấy tên Việt Nam.
- [Trang hãng](https://www.hyrotrader.com/) mô tả kết nối demo Bybit/BloFin và
  perpetual; đây không phải BTC/ETH spot. Cần kiểm funding, margin, mark price,
  minimum size và cấu hình risk riêng trước đánh giá chiến lược.
- [Bảng giá](https://www.hyrotrader.com/blog/how-much-does-a-funded-account-cost/)
  Two-Step $5K: $59; có payout cap theo cỡ tài khoản. Cần đọc đủ agreement funded,
  cutoff tính cap và điều kiện giữ/hoàn phí trước quyết định. Chưa coi marketing
  hoặc việc có API là bằng chứng payout tin cậy.

Không tự chuyển spot candidate sang perpetual hoặc mở futures từ khảo sát này.

## Vì sao chưa ưu tiên Topstep và FundedNext CFD?

Topstep [eligibility 04/09](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)
cho Việt Nam đi Combine→Express, có tổng payout cap công bố, không LFA. Không
diễn giải là cấm mọi tài khoản hoặc bảo đảm payout. [API 17/09](https://help.topstep.com/en/articles/11187768-topstepx-api-access)
cho tự động hóa nhưng yêu cầu lệnh xuất phát từ thiết bị cá nhân, không VPS,
VPN hoặc server relay; API không dùng cho LFA. Đây là ràng buộc với hướng vận
hành detached/server của workspace, không là kết luận về mọi futures prop.

Với Standard 50K + API ở giá giảm chính thức, ba tháng rồi đạt tốn giả định
3 × ($49 + $14,50) + $149 = $339,50 ≈ 8,827 triệu, chưa tính reset/thuế/phí khác.
[MLL](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)
của 50K chỉ $2K lúc đầu và trailing theo quy tắc của từng stage; không so 50K
buying power với 50K vốn sở hữu hoặc với 10% static loss của FTMO 2-Step.

FundedNext [CFD restricted countries 27/08](https://help.fundednext.com/en/articles/8020080-are-any-countries-restricted-on-fundednext-cfds)
liệt kê Việt Nam và có biện pháp chấm dứt tài khoản vi phạm. Không chọn chương
trình đó hoặc dùng VPN để lách. Kết luận scope **CFD**, không tự áp cho mọi
chương trình futures của cùng thương hiệu. Không cần tối ưu giá/add-on cho
một sản phẩm chưa đạt eligibility.

## Điều này thay đổi kế hoạch của mình thế nào?

- Prop là nguồn thu nhập theo hợp đồng có điều kiện, không là nguồn tài sản
  lớn được chuyển về sở hữu. Cần đánh giá cả xác suất fail, phí retry, rule
  changes và khả năng nhận payout, không chỉ lợi nhuận chiến lược.
- Vốn nhỏ không buộc phải rủi ro cao. Ví dụ minh họa: $2,5K × 1% lợi nhuận × 80%
  share = $20 ≈ 520.000đ trước thuế/phí. Đây là phép tính quy mô, không dự báo tháng
  nào cũng đạt 1%. Gói nhỏ có thể phục vụ chứng minh quy trình, chưa là lương.
- Owner đã chốt nghiên cứu Forex major qua MT5 cho nhánh prop đầu tiên vì
  tài sản reuse và luật Swing; cơ sở đề xuất là đánh giá engineering,
  không chứng minh Forex có edge cao hơn hoặc vàng/crypto không phù hợp.
- Giữ crypto spot làm baseline kỹ thuật và lịch sử đã có; không bỏ dữ liệu,
  engine hoặc sửa nghiên cứu cũ thành kết quả Forex/CFD/perpetual.
- Backtest prop cần mô phỏng equity intraday, daily-reset/DST, swap, margin,
  news, inactivity, minimum days, payout và fee theo đúng product/version.
  Dữ liệu D1 không đủ xác nhận một tài khoản chưa từng chạm daily loss trong ngày.
- Max drawdown tính từ đỉnh và giới hạn lỗ static tính từ vốn ban đầu khác nhau.
  Không suy trực tiếp DD 12–14% cũ thành pass/fail prop; cần kiểm đường equity và
  luật trên cùng dữ liệu, có phần đệm cho slippage/gap/lỗi vận hành.

## Bước tiếp, trước mọi khoản chi

Hướng đã chốt; bước tiếp là đăng ký một contract nghiên cứu prop cụ thể theo
FTMO 2-Step Swing: sản phẩm, universe, dữ liệu/cutoff, benchmark, phí, risk budget
và luật đánh giá. Kiểm offline trước, rồi mới đề nghị owner tạo demo/free trial.
Chưa mua challenge, tạo tài khoản, gửi support, gọi provider/broker hoặc đặt lệnh.
Chưa audit độc lập tài chính doanh nghiệp, tranh chấp payout hay pháp lý/thuế
cá nhân tại Việt Nam; sự hiện diện trên website không thay những bước đó.
