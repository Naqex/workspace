# Chẩn đoán sâu có chọn lọc: thiết kế trước số liệu mới

Owner giao09/11: tìm nguyên nhân lỗ và tỷ trọng, chỉ đầu tư sâu cho ứng viên
có cơ sở. Bổ sung vào [mechanism plan](MECHANISM-FIRST-EXECUTION-20261109.md),
không tạo engine/tracker hay tự mở lại tham số đã gác.

## Cửa chọn trước phân tích

| Cửa | Việc thực hiện | Quyết định |
|---|---|---|
|D0, đọc sổ đã có|Tách gross/net, costs, coverage, lỗi material và verdict cũ; không rerun/fetch|Negative rõ và không mechanism mới→gác exact; thiếu dữ liệu→inconclusive; materialbug→sửa bất kể profitability|
|D1, chẩn đoán sâu|Một ứng viên từng retained hoặc near-miss có mechanism/data và câu hỏi cụ thể có thể trả lời|Ghi baseline/assumptions/giới hạn trước số mới; không loại bằng ngưỡng arbitrary mới|
|D2, cải tiến|Tìm nguyên nhân có thể tác động thực tế, không bỏ các lệnh thua hồi tố|Giả thuyết/version mới, một thay đổi có căn cứ; đăng ký lại và kiểm selection/OOS/cost/prop theo stage|

**Chọn Gold SMA50k R043**, exact `xauusd-h4-sma20-80-atr14-r025-v1`, vì từng
qua frozen screen và [review](GOLD-SMA50K-REVIEW-20261108.md), còn time-fit và
funding/concentration gaps. Không chọn vì biết tỷ trọng mới. Giữ status research
survivor/deprioritized challenge. R080/R081 knownsubset gross/net yếu→không
phân tích thêm regimes hoặc tối ưu tham số. R056 đã có attribution/pathreview,
reuse thay nghiên cứu lại. Đây là selection cho công việc, không chứng nhận edge.

## Mẫu và accounting khóa trước

30 sổ Gold 50k:15năm2010–2024×2costs, annualresets độc lập; mỗi cost không
là mẫu độc lập, không cộng thành CAGR hoặc một portfolio liên tục. Reuse sealed
books/result/old review; không đọc lại5,4triệu rawM1, không simulator/import
product mới hoặc giá/holdout2025+. Giữ 125USDplannedrisk/oldfees/swap.

Primary attribution trên **lệnh đã đóng**, reference/stress tách riêng:
mid-gross thắng, mid-gross thua; embeddedspread theo declaredconstantAsk;
commission, slippage, fundingdebit/credit và roundingresidual. Midbenchmark
định giá lại cùng fillpath, không giả xóa spread sẽ giữ signals/SL/lot. Spread
đãtrongBidAsk gross không trừ hai lần. Không gọi zero cost là thực thi được.

Mẫu số tỷ trọng = tổng các khoản bất lợi không âm (mid-gross thua + spread +
commission + slippage + fundingdebit + roundingdebit). Báo riêng tiền thắng/
fundingcredit và net; không gọi là % causal lỗi hoặc % netloss. Mẫu số0→N/A.
Sổ tổng dương không có %củalỗròng; contribution có thể bị winners bù. Không
gộp %exitreason với %cost vào một pie vì overlap. Group BUY/SELL,exitreason,
holdingdays vànăm chỉdiagnostic, không chọn cohort đểtrade sau khi xem PnL.

Reconcile từng sổ:closednet −openfunding +terminalfloating = netequity.
Floating/openmarks giữ nguyên, không forceclose. Funding/openvaluation chưa
verifiedtargetbroker; không lấy modeldeclared rates làm savings chắc chắn.

## Quyết định sau phân tích

Xếp nút thắt theo tiền tác động, mức chắc của evidence, khả năng sửa thật và
công sức. Giảm cost có thể đổi fills/eligibility; không cộng hypothetical
savings vào baseline và gọi qualified. Nếu cost/specunknown là blocker lớn,
ưu tiên xác minh contract trước tuning SL/hold/side. Nếu sửa rule mới thì
freeze trial khác, không overwrite historical books, gate hoặc manifests.

Reuse `forex_screen_diagnostics.py` cho số học Decimal/money và một hàm
adversebudget generic, giữ EURUSD guard nguyên. Preflight 0/credit/nonfinite/
reconciliation/doublecount; reviewer Fraction riêng từ sealedbooks kiểm full
30sổ/tradecohorts/percent và actualmutations. One writer/nooverwrite/deadline180s/
CANCEL/PID/progress/events/phase timing. Outputprivate `gold-selective-loss-v1/`.
Existing skills được bổ sung branch này; negative routing là R081 và materialbug.

## Nguồn phương pháp đọc09/11

- [AQR2018](https://www.aqr.com/Insights/Research/White-Papers/Transactions-Costs-Practical-Application):
  costanalysis quá giản lược có thể dẫn tới đánh giá sai; không cung cấp ngưỡng D1.
- [CFM2018](https://www.cfm.com/wp-content/uploads/2022/12/168-2018-Improving-Trade-Execution-Systematically.pdf):
  decision→execution shortfall có fees/spread/impact và nhiễu; kết quả một lần
  chưa là tiết kiệm bền vững. Chưa có benchmark/arrival/tickdata đểclaim IS thật.
- [CME/FIA2011](https://www.cmegroup.com/education/files/TCA-4.pdf):
  execution tối ưu cách khớp để giữ alpha, không tự tạo quyết định cóalpha.

Taxonomy D0/D1/D2 là thiết kế của project, không chứng nhận chuẩn ngành hay
phép chứng minh hệ thống không bỏ sót. Chưa có enginewide false-negative rate.
