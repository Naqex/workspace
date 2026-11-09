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
