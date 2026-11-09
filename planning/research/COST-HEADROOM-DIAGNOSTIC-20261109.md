# Phân biệt tín hiệu và chi phí: chẩn đoán biên an toàn

09/11/2026, sau owner hỏi cách tận dụng phân rã phí. Kế thừa
[chẩn đoán có chọn lọc](SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md) và
[cây phân tầng](HIERARCHICAL-PNL-ATTRIBUTION-20261109.md), không chạy lại catalogue.
Đây là diagnosis trên kết quả đã xem, không thí nghiệm chọn threshold mới.

## Câu hỏi khóa trước tính thêm

Chọn R086 vì reference dương/stress âm, phí funding chưa được xác minh;
không chọn mọi loser hoặc thay frozenverdict. Dùng sealed32rows/summary/result/
review của `execution-v1/us500-fomc-momentum-v1/`; chỉ phân rã8books gồm hai
năm2019/2022 ×event/matchedanchor ×reference/stress **primaryrule**.
Không đọc raw mới/market2025+, không entry/exit/risk/newPnLsimulation.

Tách trên cùng path: midpointpricebenchmark, embeddedspread, commission,
slippage, funding debit/credit, rounding và net; giữ USD/researchunit rõ.
CoregrossBidAsk đã chứa spread nên không trừ lần hai; fieldspread0 không
nghĩa totalspread0. Unknown không thành0. Benchmarkmid riêng side chỉ là
accountingreference, không executableprice hoặc measuredmarketimpact.

Đầu ra tính thêm:

1. Cashcostpool và % từng khoản; so gross-mid với net. Price-losses/winners
   khác costpool, không cộng exitreason/losingtrades vào cùngpie.
2. Net trên mỗi plannedwindow và exposedtrade, có mẫu số riêng; khôngROI.
3. Additionalroundtripcostbudget = net/exposedtrades trên fixedpath. Âm
   nghĩa cần tiết kiệm, không room để trả thêm; không nhânlot tạo edge.
4. Fundingbreak-even với **giữ nguyên side/fills/slip**: tìm largest integer
   annualbasispoint trong0–10000 khiến tổngnet khôngâm, cents từngdebit theo
   oldclock22UTC/weekends. Bracket quanhboundary báo cùng, không tối ưu hay
   khuyến nghị một broker/rate. Trường không bracket/unknown →N/A, không
   épboundary. Linearunroundedbound chỉ đối chiếu rounding, không targetfee.

Đổi phí có thể đổi lot/stop/eligibility ở accountpolicy; fixedpathdecomposition
không là replay policy mới. R086componentfixedunit không mô phỏng account.
Giảmturnover/holding hoặc spreadfilter là strategyversion khác và cần đăng
ký trước/out-of-sample phù hợp, không cộng khoản tiết kiệm vào net cũ.
Break-even là lịch sử đã quan sát, **không mức an toàn triển khai** hoặc
thống kê chứng minh expectededge; chưa CI/uncertainty/stresspath/propfit.

## Kiểm chứng và quyết định

Producer Decimal và reviewer Fraction/closedformkhác, đủ8books/64cases,
reconcile allcomponents với oldnet; positive/negative/zero, BUY/SELLspread,
fundingboundary/rounding, noexposure, authority và monetarymutations.
Lưu config/pins/snapshots/result/review/wallCPU, nooverwrite; không sửa old
attempt/protocol. Chi phí thật/program/symbolunits thiếu thì vẫnunknown.

Kết quả sẽ bổ sung tại chính report này; existing skills đã bao phủ D0→D1→D2,
chưa cần skill/toolmanager mới. Chỉ một câu hỏi hữu hạn, không feesearchgrid.
Phương pháp TCA đối chiếu [AQR2018](https://www.aqr.com/Insights/Research/White-Papers/Transactions-Costs-Practical-Application)
đã đọc lại; đó là hướng phân tích, không chứng nhận strategy hoặc quỹ cụ thể.

## Kết quả đã đối soát — fixed path R086

8books/64trade-costcases, khôngmarketreplay. Bảng chính là **stress**, mỗi năm
8eventwindows; USD/researchunit, khôngUSD/account hoặcpercentreturn:

| Khoản |2019|2022|
|---|---:|---:|
|MidpricebenchmarkPnL|+183,7500|+317,8715|
|Embeddedspread|−2,8640|−3,5305|
|Commission|0|0|
|Slippage|−12,00|−12,00|
|Fundingdeclared|−232,22|−317,00|
|Roundingresidual|+0,0040|−0,0010|
|Net|**−63,33**|**−14,66**|
|Funding/tổngcostpool|93,98%|95,33%|
|Additionalroundtripcostbudget/trade|−7,91625|−1,83250|
|Largestannualfundingbp cónet≥0|1162bp=11,62%|1526bp=15,26%|
|Net tại boundary và+1bp|+0,12→−0,10|+0,18→−0,04|

Rateboundary sử dụng source entryAsk/cents/night/clock đã khai báo, không
FTMOrate hoặc đề nghị11,62%. Khôngfunding cũng chưa biến backtest thànhedge.
Rounding khiến đây là bracket1bp, khôngrootliêntục exact. Hai referencebooks
boundary12,18%/15,66%, khác stress vìslippage. Matchedweek đã âm ngay cả khi
funding0, nên không có nonnegativefundingboundary trongscope, không ép0%.

**Hành động có ích:** ưu tiên exactfunding/spec nếu có source mới; giảmspread
hoặccommission đơn thuần không bùstressloss ở đây (commissionđã0, spreadchỉ
2,864/3,531USD). Không cần feesearch hoặc chạyR086lại để thấy điều đó. Không
chọn lạiholding/BUY/SELL từ mẫu đãxem, tănglot, hoặc thaystressthreshold.

Cùng cách đọc áp cho Gold qua [existingdiagnosis](SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md):
funding77,75%costpoolstress, nhưng nhóm>5days cũng mang nhiều netdương;
cắtshorterholding có thể bỏ chínhwinner. Chưa có basis cho tựđộngmax5days.
Không gộp R086USD/unit và GoldUSD/annualresetbook thành chung mộttổng.

## Kiểm chứng, lỗi và lưu

Decimalproducer/Fractionreviewer đủ8books/64cases, cost/average/percent/
boundary/cents/sign/flatzero fixtures;6mutations net/spread/funding/%/boundary/
authority bịreject. Arithmetic khác nhưng sameagent, khôngindependentfeed.
Firstattempt phát hiện diagnostic dùng rounded`gross_account` so với price
delta chưa cents; giữ failedproducer/failure, sửa **diagnostic** sang tách
unrounded`gross_quote` và residual. Oldfinancialnet khôngđổi/khônginvalidated.

Privatebase campaign; `execution-v1/fomc-cost-headroom-v1/` giữfailure;
`execution-v1/fomc-cost-headroom-v1-attempt2/` giữ books/manifest/snapshots/
result/review. Savedproducer/reviewer `diagnose-fomc-cost-headroom-v1.py` và
`review-fomc-cost-headroom-v1.py`. Producer0,041s/review0,062s;
không gọi đây là totalresearchtime.0newtrials/raw/network/model/brokercalls.
Catalogue86/58, R086gatekhôngđổi, chưa challenge. Không cần thay skill đã có.

Lượt tiếp có ví dụ khác tại [R087results](JAPAN-US-CASH-REACTION-RESULTS-20261109.md):
2019knownmid dương nhưng spreadlớnhơn,2022knownmidđãâm. Đây là bằng chứng
cần phân loại signal/cost theo từngcohort, không mặc định mọi chiến lược lỗ
đều do phí hoặc mọi bản grossdương đáng được tối ưu. R087khôngretained;
khôngmởdiagnosisgrid sauoutcome. Catalogue hiện87/58, chưachallengecandidate.
