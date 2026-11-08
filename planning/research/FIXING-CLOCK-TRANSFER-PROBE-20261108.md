# Câu hỏi mới: exit14:00 →14:15 còn đủ lợi thế sau phí không?

Owner giao thực thi đợt kế tiếp từ evidence đã có, không chạy lại catalogue.
Goal mới hữu hạn: ghi quyết định versions cũ, chọn câu hỏi chưa được tách,
freeze trước outcome, kiểm data/code, thử hữu hạn và review/nextaction.
Không cam kết tìm winner/challengecandidate trong một đợt.

## Khác biệt với việc đã chạy

Parent `eurusd-h1-pre-ecb02ny-14berlin-atr14x1p5-r025-v1`, thuộcR021 và
[Discovery6](SESSION-DISCOVERY6-20261108.md), dùng exit14:00Europe/Berlin,
SL1,5ATR/mộtposition/risk25USD. Numerical cũ không tách ảnh hưởng15phút này
khỏi SL, sizing và H1state. [624cases](EURUSD-CATALOGUE13-RESULTS-20261108.md)
vẫn là negative/stress evidence; không sửa parent hoặc gọi bản mới độc lập.

Câu hỏi: với **cùng entry02:00America/New_York**, giữ SELL EURUSD đến14:15
Europe/Berlin thay vì14:00 có cải thiện closeablequote return trên cùng events
không, và primary14:15 có net dương sau hai costs đã khai báo ở cả2019/2022?
Đây là clock-transfer/cost-admissibility component; không SL/ATR/sizing/position
path/prop/accountbacktest hoặc fullpaperreplication.

[BoC2021-48 fullpaper](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf),
pp12–13/notes11,14 và§V.E/pp33–35(nội dung), đọc08/11, phân biệt localfix và
DST; midpoint-pattern khác net sau quotedspread. Method gốc có nhiều currency/
feed/windows. Entry02NY vẫn là parentcontrol; không tự đổi thành08Frankfurt
trong các tuần US/EU DST lệch nhau. Không claim currentofficialfixingcalendar
hoặc đem giảmindicativespread trong paper áp vào quotes của project.

## Frozen design trước outcomes

| Thành phần | Giá trị |
|---|---|
|Data|EURUSD2019 và2022 raw annual đãconsumed của `eurusd-observed-history-v2`, đúngseal/hash/rowcount;khôngdownload,không2025+|
|Denominator|Mọi Mon–Fri calendar date từngnăm, kể cả holiday/noquote;khônglọc ngày theooutcome|
|Entry|First quote tại/sau02:00NY trong60.000ms,inclusive; SELL, eligibility chỉ phụ thuộc entryavailable|
|Primaryexit|First quote tại/sau14:15Europe/Berlin trong60.000ms|
|Pairedclockbaseline|Cùng entry/direction/cost, exit14:00Europe/Berlin; paired delta chỉ trên events đủ cả2exits|
|Control|BUY đối hướng tại cùngentry vàprimaryexit, cùngcost;flat0 không làstrategy|
|Quotequality|Khôngcarry/interpolate. Thiếu/laterquote giữ status và denominator. Missingexit không được thay entryeligibility hoặc tự tính0PnL|
|Clocks|zoneinfoNY/Berlin, samecalendarlabel, end>entry, cảhai exits cách nhau900.000ms;DSTweeks giữ tự nhiên|
|Costs|ActualBidAsk;commission2,50USD/lot/side;slippage0reference hoặc0,00002/side stress;USDcontract100.000|
|Units|Per1standardlot vàpip, không accountPnL/risk25USD. Tất cả nằm trước declared22UTCrollover, financing0 là same-day scenario, chưa targetbrokerverified|
|No tuning|Khônggridgiờ/threshold/regime,khôngđổi entry/exit/fees đểcứu. Directioncontrol không được thayprimary sauoutcome|

2019 nằm trong samplepaper,2022đãexposed qua strategyresearch; cảhai không
cleanOOS hoặc hai independent validations. Không OOS/p-value/passprobability.

## Metrics và quyết định đã chốt

Mỗi năm/cost/view ghi alldates, entryeligible, resolved/unresolved, tổng/mean/
min/max/netpips, positive/negative và concentrationtop3positives. Giữ quote/
predecessor/sourceordinal để raworacle kiểm first-at/after; report missing/
lateentry/exits tách biệt. Paired mean/sumdelta vàcount chỉ trên commonmask;
không lấytổngprimary−tổngbaseline nếucoverage khác. Cùng entry/cost/unit nên
paireddelta là ảnh hưởng endpoint, không từ thay risk/sizing.

Chỉ ưu tiên wrapperreview nếu primary netpositive ở từng năm/cost, paired
delta dương từng năm, không unresolvedentryeligible và correctness khônggap.
Đây là workloadpriority heuristic mới đãfreeze, không ngưỡngindustry/edge.
Delta dương nhưng net âm chỉ chứng minh timingimprovement trongmẫu, chưa
tradeableedge. Bất kỳ điều kiện chưađạt giữ no-priority/inconclusive theo
scope; không bác cảfixingfamily hoặc mởholdoutđể kiếmpositive. Tuyệt đối
không gọi thànhstrategyqualified hoặc tựimplementbot từ component này.

## Execution và acceptance

Reuse typedcostprimitive/quotecontracts của core, không executionengine mới.
FocusedBUY/SELLcost, NY/EUDST, exact60s, firstquote/predecessor, missingfuture
isolation và pairedcommonmask tests trướcnumeric. Testfile/source/protocol/
parentconfig/result/rawseals được pin vàsnapshot trướcworker.

Mộtwriter, trần300s numeric, CANCEL ởprogress, terminalfailed vẫn ghi khi
CANCEL/deadlineđãset. Per-millionrowstatus/log/wall/CPU vàstructuredfailures.
Outputmới`execution-v1/fixing-clock-transfer-v1`, không overwrite/retry tựđộng.
Metadata/preflight không đọc PnLtrướcfreeze. Mỗi annualscan chỉ đọcraw1lần để
chọn3events/date; hash/order/count vẫn đốisoát parent. Không reread toànraw
cho từngside/cost. Oracle khácimplementation kiểm selection/arithmetic sau
numeric, giữsameagentreviewlabel; không rerunnumerical chỉ để review/report.

Acceptance: toàn2years/521weekdays có event/status, summaries/commonmask
reconcile, tampernegativefixtures đạt, actualquotes/source/cost arithmetic có
review; lưu version/selection/limits/decision vànextaction. Component chưa
risk/DD/prop/forward; firm/account/holdout/broker/paid/productiongates giữ.
