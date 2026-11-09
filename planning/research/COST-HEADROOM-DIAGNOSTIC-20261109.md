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

## Cách dùng kết quả để chọn đúng việc cần tối ưu

Đối chiếu bổ sung09/11 sau R088, trên kết quả đã xem; **không backtest hoặc
thử ngưỡng phí mới**. Không sửa các verdict/protocol đã khóa. Catalogue hiện
88 hồ sơ/58 account-policy versions; không có ứng viên challenge-qualified.

Đã có công cụ phân rã, nhưng mức bao phủ khác nhau: Gold có cây tới từng
lệnh, R086 có diagnostic biên chi phí, R087/R088 có phân rã component/cohort.
Chưa tuyên bố cả88 hồ sơ đều có cây attribution chuẩn hóa hoặc phí broker
đích đã xác minh. Giá từ nguồn nghiên cứu và phí khai báo vẫn được ghi rõ.

| Trường hợp | Bằng chứng hiện có | Việc có ích tiếp theo |
|---|---|---|
| Giá đã bất lợi trước phí | R087 năm2022: midpoint−676,615JPY/unit trên phần biết được | Gác exact recipe; giảm phí đơn thuần không làm phần price PnL dương. Không suy cả họ chiến lược vô dụng hoặc tự đảo BUY/SELL |
| Giá có lời nhưng chi phí ăn hết | R087 năm2019: midpoint+781,824 nhưng spread1.170,026JPY/unit; R086 stress âm vì funding chiếm93,98%/95,33% cost pool | Xác minh đúng khoản phí/spec còn thiếu trước; chỉ tiếp nếu có cơ chế và điều kiện thực tế mới, không đặt phí0 hoặc tối ưu mọi loser |
| Sau phí có lời nhưng chưa chứng minh chọn đúng cơ hội | R088: stress+1.013/+545USD mỗi cohort8events; matchedweek+718/+2.441. Event increment2022 âm | Ưu tiên kiểm giả thuyết/chọn cơ hội, độ bền và risk fit; không gọi cost optimization là phần còn thiếu duy nhất |
| Price component dương nhưng wrapper yếu | R021 price sleeve dương nhiều năm; parentexit làm giảm kết quả, weights giúp trên commonmask; R056 net13năm dương nhưng2/4stressblocks âm | Đọc stop/sizing/path risk cùng nhau; không bỏSL hoặc nớiSL giữ lot cũ để lấy lại phần lời giả định |
| Thiếu nguồn/spec/coverage | R087 có66eligible sessions unknown; cached FTMO spec chỉ EURUSD, không đủ XAU/US500 | Giữ unknown/N/A; admission dữ liệu/contract trước tính lại, không quy mọi thiếu sót thành signal hay phí |

Các đơn vị USD/researchunit, JPY/unit và USD/account khác nhau, không cộng hoặc
xếp hạng bằng số tiền tuyệt đối. Gross dương chưa chứng minh expected edge.
Với Bid/Ask gross, spread đã nằm trong giá; diagnostic chuyển về midpoint
benchmark rồi tách spread để đối soát, **không trừ lần hai**. Midpoint riêng
hai side M1 không là giá chắc chắn khớp được. Phân rã là kế toán, chưa đo
implementation shortfall/market impact thực khi thiếu order/fill evidence.

### Những tối ưu có thể tận dụng, đúng thứ tự

1. **Đúng dữ liệu và phí:** giữ observed/declared/unknown, đơn vị, commission
   mỗi chiều hay khứ hồi, rollover/multiplier và funding debit/credit. Nếu
   phát hiện lỗi material, sửa và chỉ kiểm lại phạm vi bị ảnh hưởng; giữ bản
   cũ. Có contract mới khác giả định cũ thì đó là model revision có lineage,
   không ghi đè lịch sử hoặc chọn contract vì cho PnL đẹp nhất.
2. **Nhắm khoản lớn:** R086 chưa đáng tối ưu commission (đã0 trong model)
   hoặc spread vài USD khi funding hàng trăm USD. Gold funding lớn nhưng
   nhóm giữ lâu cũng có winners; chưa có căn cứ cắt mọi lệnh sau5ngày.
3. **Lọc phí hoặc giảm turnover khi có cơ chế:** spread-at-entry gate, giao
   dịch ít hơn hoặc đổi giờ/holding có thể giảm chi phí, cũng có thể bỏ mất
   cơ hội lời. Phải khóa version mới trước outcome, dùng thông tin có lúc
   quyết định, mô phỏng lại eligibility/sizing/SL/account path và kiểm trên
   dữ liệu phù hợp; không chỉ cộng khoản phí tiết kiệm vào net cũ.
4. **Đo thực thi khi đủ điều kiện:** đối chiếu quote dự kiến với giá fill,
   commission và swap thực tế theo đúng tài khoản/program. Đây là việc sau
   admission/authorization riêng, không tự gọi broker để bổ sung bảng này.
   Không tự đổi quỹ/provider hoặc lấy điều kiện evaluation rẻ hơn áp cho
   funded phase; contract các phase phải được kiểm riêng.

Biên phí hòa vốn lịch sử chỉ trả lời “trên path này còn chịu được bao nhiêu”,
không là mức an toàn tương lai hoặc bằng chứng statistical edge. Tăng lot
không tự sửa expected lợi nhuận trên mỗi đơn vị; lot grid/minimum fee có thể
đổi economics và đồng thời đổi rủi ro, phải mô phỏng đúng.

Phí challenge/reset và tỷ lệ chia payout thuộc bài toán kinh tế toàn chương
trình, không cộng vào commission từng lệnh nếu không có quy tắc phân bổ rõ.
Quota/token AI, CPU, điện là chi phí vận hành riêng; không trộn vào trade PnL.

### Đối chiếu và quyết định của lượt này

Đọc lại [R088](EURUSD-POST-FOMC-RESULTS-20261109.md), [wrapper attribution](PRE-ECB-WRAPPER-ATTRIBUTION-RESULTS-20261108.md),
[path risk](PRE-ECB-PATH-RISK-RESULTS-20261108.md) và [R056](PRE-ECB-SESSION-RISK-RESULTS-20261108.md).
R08802:01→13:59NY khác R02102NY→14Berlin, không gộp PnL/clocks. MAE của
noSLcounterfactual tới5,48R trên observed scope không cho bỏ SL. R056 đã thử
session-volatility stop/risk25USD nhưng không qua frozen block gate; không
đăng ký grid khác chỉ vì cần winner. Chưa có risk hypothesis mới đủ cơ sở
để chạy thêm từ phép đối chiếu này; giữ recipes và phí lịch sử nguyên vẹn.

Đối chiếu lại [AQR — Transactions Costs: Practical Application](https://www.aqr.com/Insights/Research/White-Papers/Transactions-Costs-Practical-Application)
ngày09/11: trang primary hướng dẫn thẩm định chi phí và cảnh báo đơn giản
hóa có thể làm hiểu sai khả năng giao dịch. Đây là phương pháp tham khảo,
không chứng nhận edge hoặc phí FTMO/The5ers. Không đọc lại fullpaper trong
lượt đối chiếu này. Existing qualification skill/reference đã bao phủ workflow;
chưa có lỗi lặp hoặc capability gap cần thêm skill/framework.
