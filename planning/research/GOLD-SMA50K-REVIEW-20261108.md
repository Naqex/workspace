# Gold SMA50k: sổ tiền khớp, chưa ưu tiên challenge theo time-fit

**C2 follow-up 09/11:** [signal review](GOLD-SMA-SIGNAL-REVIEW-RESULTS-20261109.md)
đã đối chiếu 40.662 H4 evaluations/616 decisions/450 entry fills của 30 sổ
bằng integer SMA/Decimal80 ATR oracle riêng. Chưa phát hiện mismatch; đóng
khoảng trống signal trong phạm vi conditional recorded position path. Không
first-crossing stop/tick/target-spec/edge proof; các limitation khác bên dưới
giữ nguyên. Không rerun PnL hoặc nâng verdict challenge.

**Publicspec follow-up:** [renderedFTMOrows/clock review](FTMO-SYMBOL-AND-CLOCK-ADMISSION-20261108.md)
đã đọc được XAUrow trong browser sau lần textfetch/TLSfailure dưới đây.
Publiccontract100/Swing15/percentagefee và swappoints được ghi riêng; chưa đủ
point/mode/currentaccount/historicalcost để sửa oldoutcomes hoặc nâng verdict.

**Giữ làm research survivor, hạ ưu tiên qualification cho challenge hiện tại.**
Không đổi rules/risk/cost, không rerun simulator. Diagnostic của15Jan-start
annualbooks không cho thấy đã đạt closed-profit target trong≤12tháng; đây
không là phép bác bỏ mọi rolling start hoặc cả họ trend. C1/C2 vẫn chưa đạt.

## Vì sao kiểm và đã giữ gì?

Sau [Discovery9](METAL-DISCOVERY9-10-RESULTS-20261108.md), SMA50k là bản duy
nhất được giữ theo frozen10/15stressyears gate. Kết quả đã exposed, chưa
cleanOOS. [Preflight](GOLD-SMA50K-PREFLIGHT-20261108.md) commit`ea4c7f9` khóa
cách review trước diagnostics mới; không gọi đây là preregistration edge.

Parent: `metal-discovery9-screen/attempt-v1`, exactpolicy
`xauusd-h4-sma20-80-atr14-r025-v1`,50k/125USDplannedrisk, entrySMA20/80,
SL2ATR14/exitmấtdirection,15annualresets2010–24,declaredAsk/spread/slippage/
commission/swap. Old outcomes/pins giữ nguyên. Không thêm trialstrategy.

## Số liệu đọc lại và kiểm độc lập

Vốn mỗi book50.000USD, mỗi năm bắt đầu lại; tổng dưới đây không là một account
liên tục, CAGR hoặc lợi nhuận một năm. Equitynet gồm floating còn mở cuối mẫu.

| Diagnostic qua15annualbooks | Phí chuẩn | Phí cao |
|---|---:|---:|
|Tổng annualnetUSD / normalizedsum|+9.383,83 /+18,76766%|+4.035,06 /+8,07012%|
|Năm equitynetdương|11/15|10/15|
|Lệnh đã đóng; thắng/thua|219;58/161|220;53/167|
|Tổng financing đã ghi,USD|4.595,00|8.950,80|
|Net của5lệnh dương lớn nhất,USD|9.276,47|8.668,57|
|5lệnh đó / tổng contribution của tất cả lệnh dương|36,25%|39,25%|
|Annualnet trừ contribution5lệnh đó,USD|+107,36|−4.633,51|
|Books còn position cuối năm|6|5|
|Cashnet cao nhất ngay sau một lần đóng,USD|+2.363,73|+2.168,91|
|Books có checkpoint sau đóng≥5.000USD|0/15|0/15|
|Books có checkpoint sau đóng≥2.500USD|0/15|0/15|

Trend thường có ít lệnh lớn bù nhiều lệnh thua. Bảng concentration không là
ngưỡng loại mới hoặc strategy “bỏ5lệnh”; dùng để tránh nhầm tổng dương thành
lợi thế được phân bố đều. Bỏ5best là diagnostic hồi tố, không executablevariant.

### Các mốc đã yêu cầu:3/6/12calendar months

Mỗi mốc là prefix của cùng annualbook bắt đầuJan1; không reset giữa năm hoặc
ghép năm. Cashnet là cashcredits của lệnh đã đóng trừ toàn bộ financing đã
đến hạn, bao gồm financing của vị thế còn mở. **Không là equityreturn hoặc
prop pass-rate.** Hai costs/prefixes cùngbook không là samples độc lập.

| Prefix | Cashnet min→max chuẩn,USD | Cashnet min→max cao,USD | Books cashdương chuẩn/cao |
|---|---:|---:|---:|
|3tháng|−498,83→+1.403,53|−527,85→+1.233,33|6/15 /6/15|
|6tháng|−1.111,27→+1.726,99|−1.082,28→+1.589,49|6/15 /6/15|
|12tháng|−1.910,43→+2.101,98|−1.930,54→+1.846,75|11/15 /10/15|

Boundary còn position chuẩn/cao:3tháng7/6books,6tháng7/7,12tháng6/5. Không
forceclose để tính target;0closeintervals cắt boundary trong90prefixcases.
SL exits vẫn có modeledM1/H1 interval, không exact firstcrossingtick.

[FTMO2-Step](https://ftmo.com/en/2-step-challenge/) kiểm08/11 xác nhận10%/5%,
5%daily/10%overall,4days/unlimited. [FTMO Academy](https://academy.ftmo.com/lesson/profit-target/)
yêu cầu closed profit và tất cảpositions đóng. Với50k, targets5.000/2.500USD
là references; dòng2.500 không là actualphase2 vì chưa reset/runphase2. Không
chia5.000 cho meanannualnet để dự đoán số năm pass. Không suy targetkhôngđạt
cho bất kỳ rollingstart nào, hoặc no-breach từ cash khi thiếu intrabar equity.

## C2: scope đã kiểm và còn thiếu

- Rehash raw export, originalprotocol,21source snapshots và34baselinefiles
  (4aggregate/metadata +30bookfiles), perbook JSONexact với aggregate.21snapshot
  hashes khớp manifest; rawhash giữ`d209df9...471b9`. Không sửa oldartifacts.
- Reviewer stdlib/Decimal riêng, không import simulator/cost helper:30book
  gross/commission/slippage/net, tất cả weekdayfundingevents20/40×lot với
  Wednesday×3, missing/duplicate/eventclock, trade/cash/equitycounts khớp.
  Openmark được tính lại từ finalsourceH1close+declaredAsk, không chỉ đọc số
  floating khai báo.30books positions không overlap;2oldsummaryscenarios exact.
- Giá vào/atopenexit và SLinside-modeledrange/exitinterval đối chiếu source
  H1 được dựng bằng reviewer riêng. Có earlierqueuedintent/quantity tương ứng;
  **chưa independentSMA/ATRsignal-oracle hoặc stopfirstcrossingtick proof**.
-5in-memorymutations đều reject:commission,wrongfunding,missingfunding,
  entrycount,inputhash.90prefixcashvalues khớp codepath tích lũy chronological
  events riêng. Sameagentreview, không independenthuman/modelsign-off.
- Raw5.399.878M1rows→91.101observedH1;18.486adjacentgaps>60s, max275.460s;
  schema/order/OHLC/grid/volume/scope/counts khớp.4.386H1 có<60M1 quan sát,
  giữ nguyên thay vì padding. Gaps gồm closures/unknownfeedloss, chưa phân loại
  theo targetbroker; partialbar không tự là corruptedbar. Không đọc2025+.
- CurrentD:Trader7ab57907 khác14/21files vềbytes:4ASTexact,10ASTkhác. Không
  tuyên bố currentcode có parity hoặc tự sửa pins để reuse; review chỉ chứng
  minh artifacts từ originalsourcesnapshot trong scope trên. Không numerical
  rerun currentcode để che khác biệt. C:research-metalsWIP không bị sửa.

## Target costs/clock: thêm bằng chứng, không âm thầm đổi phí

[FTMO25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
công bố MetalsCFD0,0007%volume/side từ29/09/2025; khác declaredfixed2,50USD/
lot/side. Đây là publishedpolicy lịch sử đọc lại08/11, chưa là xác minh quote/
spec/currenttargetaccount hoặc retrospectivecost2010–24. Không áp như “phí
thật” rồi sửa outcome/sizing từ artifacts, không giả swap20/40 làFTMOverified.

[InfrastructureFAQ](https://ftmo.com/en/faq/how-does-the-ftmo-technical-infrastructure-work/)
nêu modeledexecutiondelay tới200ms và commissions xemwebsite/platform. Đây
là điểm cần tick/delaystress khi qualification, chưa chứng minh simulator có
brokerrealism. Webtext [symbols](https://ftmo.com/en/symbols/) không trả XAUrow;
directpublicHTMLfetch lỗiTLSUnexpectedEOF, không bypassTLS/chuyển sang account
khác hoặc gọi đã xác minh geometry/swap. Targetfees/spread/slippage/swap/
brokerclock/dailyreset và nativeprop vẫn unknown trong scope cầnthiết.

## Hậu kiểm, thời gian và bước tiếp

| Phase thực đo | Wallseconds | Quyết định |
|---|---:|---|
|Binding/hash/sourcecompare|4,647|Reuse originalartifacts, không simulatorrerun|
|Independentfinancial +5negativecases|0,065|Đạt declared-model invariants; không edgeproof|
|Independentfullrawclock/grid/OHLCscan|59,377|Chi phí lớn nhất của review; không cần reread cho cùngbindings|
|Sourcequote/prefix/concentrationdiagnostics|5,153|Đạt30books;90prefix crosscheck riêng sau run|
|Primaryreview toàn lượt|69,292|CPU54,078s;không tính research/web/crosschecktime vào đây|

TimerCPU lấy exact`result.json`; giữ unknown cho activehuman/agentresearchtime.
Không gọi69s là speedup so117sDiscovery9:workloadreview khác simulation180rows.
Không bugproducerfinancial material mới trong phạm vi đã kiểm. Không cần tạo
skill/tool mới:decisiontrail/review đã thuộc3existing skills và researchowner.

**Decisiondelta:** từ “survivor50k cần kiểmtime-fit” sang “retainedresearch,
deprioritizechallengequalification hiện tại vì closed-cash evidence yếu và
concentration/realismgaps”. Không tăngrisk, đổiexit, bớtphí hoặc chọn riêng
năm đẹp. Có thể revisit khi có registerednewmechanism/data/brokercontract,
không rerun cùngbook để tìm kết quả khác. Original gate10/15 vẫn làpass nhưcũ;
không relabel thành failure của gate cũ.

Tiếp C2: R049IBS02hold còn outcome expanded/filtered đã biết; sửa đúng ảnh hưởng
sourceonly trên2022–24 trước discovery/longbatchmới. R050/R052 đã corrected,
không rerun. Sau đó tiếp boundedhypothesis theo datasupport/targetcostfit,
không mở2025+/broker/account/payment. C1 còn cleanOOS, nativeprop/tick và
prospectiveforward/reconciliation, chưa có challengecandidate.

Privateattempt: `execution-v1/gold-sma50k-evidence-review-v1/review.py`,
`manifest.json`, `progress.json`, `result.json`, `prefix-crosscheck.json`,
`additional-review.json`. ReviewerSHA`68e5729c7a79fb0448ace023ae4c5e75faab418cda9bf22954a7a8a4f3841229`,
resultSHA`ba1f6d5d08fdd065e8ecb21e223cedf763074db96edcf04716f1f980cd179927`.
Processsession40862 terminalexit0;publicHTMLsession53686 terminal0 vớiTLSfailure
đã được ghi ở đây. Khôngjobnền,callsbroker/model/newsimulation đều0.
