# Đã sửa lớp chẩn đoán và workflow discovery — 08/11/2026

Thực hiện yêu cầu owner “sửa hết” sau [diagnosis](DISCOVERY-DIAGNOSIS-20261108.md).
Source/tool/protocol `592fa82`; product Trader giữ `7ab57907`, không đổi signal,
risk/cost/fillengine. [Protocol](SCREEN-CALIBRATION-REPAIR-20261108.md),
[recovery trước numerical](SCREEN-CALIBRATION-RECOVERY-20261108.md) và
[origin/transfer review](STRATEGY-ORIGIN-TRANSFER-REVIEW-20261108.md) giữ phạm vi.
Goal vẫn paused trong app; đây là task sửa được giao riêng, không mở gates.

## Thay đổi đã thực hiện

| Lát | Trước | Sau / bằng chứng |
|---|---|---|
| Screen→tick diagnosis | Có pilot4H4rules và annualAsia nhưng chưa một packet cho nhóm diagnostic mới |8newcases/4policies/2costs; exactdecision/entry/cash attribution, nofill/risk/sign flags; không tự reject/promote |
| Cost attribution | Tổng reference/stress dễ bị hiểu là khác biệt chỉ do phí | Tool riêng đọc624sealedrows, tính lại USD bằng declaredcommission/slip; tách gross sauembeddedspread, phí, fundingcredit, floating và rounding |
| Origin→adaptation | Nguồn có trong nhiều protocol nhưng thiếu một bản so sánh tập trung | Map6nhóm và original→project differences; workflow yêu cầu phân loại trước numeric mới, không coi indicator/paper là proofexactrecipe |
| Chọn lát tiếp | R019 mặc định dễ reuse | Ưu tiên câu hỏi transfer/cost-admissibility có dữ liệu; không tự mởbatch hoặc gọi paperreplicated |
| Recovery | Cachepilot cũ thiếu currentkey | Fail giữ trước numeric; verify sourcequote fields trong scope rồi recovery hữu hạn, không đổi binding cũ |

##8cases đã hoàn tất; không “8/8 chứng nhận screen chuẩn”

Prefix03–07/01/2022, initial10k/planned25USD, raw326.373ticks dùng lại cho từng
cost/policy; hai costs không independent samples. Warmup1.404.696ticks→550H1,
prefix→118H1; toàn bộ CoarseHour fields khớp oldcache bằng independentaggregation
trên raw currentreader. Oldpackets/hash/binding giữ nguyên, không rebind.

| Rule | Native net chuẩn/cao USD | Coarse−native chuẩn/cao USD | Kết luận đúng scope |
|---|---:|---:|---|
| Shock reclaim |0 /0|0 /0|Không có fill; inconclusive, không kiểm được khả năng bỏ sót |
| Prior-daybreak |−30,96 /−32,72|+0,24 /+0,24|4trades/cost; một stop/cost dùng firstquote vượtSL gây toàn delta |
| RSIreentry |−3,43 /−4,41|0 /0|1trade/cost; matched trong prefix này |
| SMAH4 |−21,83 /−22,80|+0,04 /+0,04|1trade/cost; stopfill giải thích toàn delta |

- Cả8case signal/time/counts/entryside/quantity/entryfill khớp; không native
  riskstop/rejection. Không có signflip trong mẫu. Cả6filledcases đều âm;
  đó không là lý do chọn lại window để cố có positivecase.
- Native/coarse khác tên reason`pilot_strategy_exit`/`strategy_exit` cho cùng
  event, financialvalues exact; không bugsemantics hoặc cần sửaengine.
- ReviewerCSV/Fraction riêng không importsimulator/reporthelper:326.373quotes,
  12closedpaths(6paths lặp qua2costs),24price-net arithmeticchecks;4stopcrossing
  checks(2paths lặp qua2costs). Entry/exitgiá nguồn và earliestSLcrossing khớp;
  toàn0,24/0,04delta là stopovershoot, không signal/funding drift.
- Đây là sameagentreview bằng implementation khác, không independentmodel/
  human certification.6paths không đủ calibration errorrate toàn bộcatalogue;
  không annualbound, không đo globalfalse-negative rate. SyntheticBUY/SELL/
  gap/pending/credit tests bổ sung kiểm software, không làm mẫu market độc lập.

**Không sửa coarse thành tick hoặc trừ một hằng số vào mọi PnL.** Việc sửa
là consumer phân loại đúng sai lệch/uncertainty và workflow không dùng triage
để reject family/challengepromote. Nếu sau này recipe/source/window mới có
uncertainty ảnh hưởng verdict, tiếp boundedtickreview đã đăng ký.

##624cases: giờ biết tiền bị mất ở đâu

13resultseals/source/config/matrix và48summarytotals được kiểm lại. Gross ở
đây là biến động giá đóng theo Bid/Ask **đã chứa spread**, không frictionless
alpha. Đây là tổng13annualresetbooks, không account liên tục/CAGR/lợi nhuận
một năm. Funding có cả debit/credit; floating giữ riêng, không ép đóng cuối mẫu.

| Stage contribution của24policies | Reference: số tổng dương | Stress: số tổng dương |
|---|---:|---:|
|Closedgross sauembeddedspread, trướccommission/slip/funding|15|15|
|Closedpricenet saucommission/slip, trướctimedfunding|7|2|
|Net equity, gồmfunding vàfloating cuối cácbook|6|0|

Các counts này là diagnostics theo stage, không causalranking của strategies
và không24independentedges. Scenario thay sizing theo cost; gross khác nhau
giữa scenarios nên không lấynetdifference làm“tổngphí tăng thêm” cố định.

Ví dụ reference, USD tổng13books:

| Rule | Gross sau spread | Commission | Fundingdebit | Floatingnet | Net equity |
|---|---:|---:|---:|---:|---:|
| Prior-daybreak |+1.278,49|1.148,90|0|0|+129,59|
| SMAH4 |+95,58|37,15|269,22|+102,67|−108,12|
| RSIreentry |−2.864,77|1.025,70|435,09|+5,38|−4.320,18|

Do đó có bản gross mỏng bị turnover/fees ăn hết, có bản chịu funding và có
bản gross đã âm. Không quy toàn bộ cho hệ thống hoặc toàn bộ cho commission.
Openfloatingnet không được tách gross/cost từ coarse row vì thiếu closequote;
tool báo giới hạn đó thay vì tự suy/đếm phí hai lần.

## Kiểm chứng và thời gian

| Việc | Wall thực đo | Evidence / giới hạn |
|---|---:|---|
|7newdiagnostic tests|0,263s|BUY/SELL, credit/open, negativegross, rounding; tampercost/fill/cash/count/funding/Nan; source/seal/matrix/summary rejects; same-total khácsignal/entry bị giữreview |
|Existing product focusedtests|1,67s|22tests+18subtests coarse/intraday; không fullproductcertification |
|624rowcostdiagnostic|4,101s|48groups, không simulation;source/config/proof hashes trongoutput |
|Attempt1preflightfailure|0,625s|Cachekeydrift;0numericalcases,khôngauto retry |
|Attempt2preparation/raworacle|22,782s|Fullwarmup+evalprefix;khôngadopt toànQ1 |
|Native8cases, timer cộng|22,833s|Currentnativecore, fullprefixobservedquotes/case |
|Coarse8cases, timer cộng|0,184s|Ít semantics hơn native; không exact-engine speedup |
|Attempt2toànlượt|46,110s|CPU38,859s; includeprep/compute/write/reviewpacket, chưa independentCSVreview |
|IndependentCSV/Fractionreview|14,810s|Khôngsimulationcall; đọc lạiquote prefix để firstcrossingoracle |

Không cộng wall của các việc song song thành end-to-end. Activeagent/research/
code time chưa có đồng hồ riêng; không dựng từ Git timestamps. Không cần
GPU/Rustrewrite hoặc hệthống mới cho workload này.

## Receipt, version và trạng thái tiếp

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/screen-calibration-repair-v1`.

- `attempt-1/failure.json`, source-snapshot vàfailedprogress giữ0,625sfailure.
- `attempt-2/manifest.json`, `input-review.json`, `result.json`, `completed.json`,
  percasecomparison/checkpoint/decisions/coarse/native vàsource-snapshot.
  Native resultSHA`a97bd035bf12aa41cf4a44a848e1b25622999cea4a7241dbdbd4c2b01f4e9160`.
- `independent-review.json`, reviewerSHA
  `cc970410901201cc48f9228e871098f9b82f52d66f6025d23194e90729656c07`.
  `cost-diagnostic.json` giữ624decompositions và48aggregate/sourceproofs.
- Numericalsession13257 vàreviewsession24906 đã terminalexit0. Không còn job
  nền của phần sửa; không gửi model/brokercalls hoặc đọc2025+.

Decision: acceptance hữu hạn của taskrepair đã có evidence ở trên; không
đóng C1/C2campaign. Không thấy materialsignal/accountingbug mới trong mẫu;
coarsestopapproximation vẫn có bias, không giả là đã xóa bias toànhistory.
Targetbroker/currentcosts/historicalrealism, cleanOOS, nativeprop vàforward
vẫn cần ở stage tương ứng; không thể tự điền bằng doc/tool. Giữ oldoutcomes,
không tăngrisk/hạcost hoặc generatevariants để hứa có winner.

Khi tiếp research: freeze một mechanism/cost-admissibility probe có cơ sở từ
originmap, giữ absence/qualityfailure và alltrials; không mở lại oldbatch hoặc
dispatch R019 mặc định. Task sửa không tự resume appGoal đãpaused.
