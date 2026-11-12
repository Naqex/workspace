# Tám setup, economic screen có giới hạn, trước outcome mới

12/11/2026. Theo [PLAN/owner grant](US500-RECENT-DISCOVERY-PLAN-20261112.md).
US500/M15, BUY/SELL, source cashNY/DST; đây là screening, không challenge grant.

## Luật khóa và lineage

| Code | Trigger | Parent / lý do |
|---|---|---|
|RS01|FP07 prior20high/low ±0,10closedATR14; một event mỗi episode ngoài kênh|R001/FP07, momentum theo giá mới; giữ tín hiệu đã đo|
|RS02|Sau breakout RS01 đầu10–14NY, freeze channellevel+ATR; bar sau≤60phút/15NY chạm level±0,10ATR rồi close lại phía breakout ngoài đệm; đối hướng hủy|RelatedFP07, kiểm retest sau phá thay vì thêm MA|
|RS03|Close vượt high/low của **phiên thường trước đã đủ dữ liệu**, ±0,10ATR hiện tại,10–15NY|Related prior-day levels/R019, không biết orderflow thật|
|RS04|Close ngoài range09:30–09:45,10–11NY, lấy lần đầu|R094 trigger control; standardized execution khác bản gốc|
|RS05|Sau breakout RS04 đầu, bar M15 sau đóng lại trong range≤11NY, vào ngược|R095 related control; không independent edge|
|RS06|ExactR123/FP05 setup+confirmation, lấy confirm đầu/ngày|Known negative control; standardized time exit khác R123|
|RS07|Prior20close mean/populationSD; bar trước ngoài ±2SD, bar hiện tại trở vào band nhưng chưa vượt mean,10–15NY, BUY từ dưới/SELL từ trên|R003 related price-reversion, exit khi closedSMA20 hồi tới phía vị thế|
|RS08|Openinggap so prior full-session close≥0,25priorM15ATR, firstM15 close đi ngược gap →fade tại09:45|Related overnight/openingreversion, source daily endpoint cần đủ|

Chỉ8thiết kế, không gridlookback/threshold/giờ. RS01/03/07 cập nhật state trên
mọi M15 đã đóng trước giờ entry; prior channel/band không chứa currentbar.
RS03/08 cần prior normal390M1 session không gaps; không dùng current full-day
quality để xóa entry trước missing tương lai. Shortsession không entry. Missing
M15 reset lookbacks; gap đã có chặn ngày. Mỗi recipe chỉ xét trigger đầu/ngày,
quote missing/riskreject/activeposition không chọn trigger sau để bù.

RS01–08 là related hypotheses/controls, không8independentedges. Tất cả phải
giữ trial history; negatives R094/R095/R123 không bị xóa/đổi tên thành mới.
RS04/05/06 economic assumptions khác exit/SL cũ nên không gọi exact rerun.

## Chặng trước khi xem2026 outcomes

1. Cadence cả8 trên2022–24, giữ đủ0/coverage/reasons; historical2016/20/21
   count khi nguồn đã admitted. Không sửa setup theo count vừa thấy.
2. **Chỉ RS01/RS02/RS03/RS07** chạy economic screen2022–24 rồi2025, mỗi năm
   reset10k, reference/stress; có nullcontrol. Chọn trước theo cơ chế rõ và
   bổ sung trigger/reversion, không chọn8bản theo PnL. RS04/05/06 giữ control
   cadence/knownnegative; RS08 chưa ưu tiên economic trước sourceendpoint fit.
3. Khóa tối đa2recipe trước2026 outcomes: sort full-known stress2025net giảm
   dần, tiecode; ưu tiên kết quả stress2022–24sum dương nếu có. Nếu tất cả âm
   vẫn thử2để chẩn đoánrecenttransfer, ghi không đủ điều kiện/promote.
   Recipe unresolved/open/rejected accounting không được chọn bằng modeledPnL;
   nếu dưới2full-known thì chỉ chọn số đủ, không thayunknown bằng0.
4. Hai recipe đó chạy2026Jan1→11NovNY; không đọc outcomes recipes khác2026.
   Historical2016/20/21 cho đúng shortlist là stress phụ, giữ toàn năm/gaps.
   Source2026 ingestion/validation trước đó không đánh giá strategy/outcomes.
5. Không chỉnh luật rồi chạy lại2025/2026 trong study này. Sau scoring2026 đã
   consumed, cần forward/newwindow cho bằng chứng thực sự mới. Owner history
   ngoài project chưa rõ nên không gọi clean/pristineOOS.

## Native economic assumptions

Nautilus1.231.0, reuse existing native orders/matching/SL/cash và independent
Fraction reviewer. Signal tại close →market entry decision+60s, preceding
minute/exactquote phải có. Bid/Ask embedded spread, commission0 declared index
scenario, extraadverse slip0,25/0,75point mỗi fill; chưa measuredFTMOquotes/spec.
SL2×entrydecisionATR (RS06 frozenarmATR); outward tick.001; quantityfloor.01,
min.01/max50, leverage10, plannedstoprisk≤25USD trêninitial10k (khônglivebudget).
Oneposition, firsttrigger/day, không reentry/add-on/martingale.

Exit decision15:30NY/fill15:31, trừ RS07 closedM15 chạm/phía mean20 trước đó
thì exit nextminute. ProtectiveSL ưu tiên theo parentquote model. Không TPfixed,
khôngforceclose cuối mẫu; heldgap/missingexit/unresolved/open cuối →fullnetN/A,
không promote modeledPnL. M1extrema là stop-envelope, chưa exacttickpath.
RS06 dùngtimeexit chuẩn để so, khác nativeR123 còn trend-loss exit: trial mới.

## Scoring, unknown và đề xuất

Safety/correctness gates trước điểm: material bug hoặc accounting/sourcefail
chặn scorekinhtế; unresolved/fullpathunknown giữinconclusive. Không bù bằng
cadence hoặc profit đẹp. Report cả closedDD/endpointDD với scope, không gọi
intraminute-equity/propdaily fit khi chưa mô hình.

Điểm **ưu tiên nghiên cứu /10**, là rubric của project, không xác suất pass:
2correctness/source+cash checked;2development stresssum>0 và≥2/3năm>0;
2recent2025stress>0;2fixed2026stress>0;1cadencefirstday2–5/5phiên;
1historical stress full-known positive≥2/3năm. Mục chưa đo làN/A, báo
`earned / evaluated maximum`, không tự cho0 hoặc chuẩn hóa thành cao.
Economic evidence không đạt vẫn nhận nhãnfail/inconclusive dù có điểm kỹ thuật.
Khôngstrategy nào được gọi challenge-ready chỉ bằng điểm này; targetterms/
news/inactivity/actualcost/equity/forward/ownerhandover còn gates riêng.

Prioritize recent:2025+2026tối đa4điểmkinhtế, dev2, old1; olddata gaps không
tự thành economicfail. Cần báo net/risk/R, count, coststress, concentration,
monthly distribution và uncertainty/dependence; không ép pvalue/Sharpe pass.

Mộtwriter, source/protocol/tests/pins và code checkpoint trước numeric,
progress/CANCEL/deadline/immutable outputs; reuse completed books đúng bindings
nếu có. Không tự sửa scope khi fail; giữ mọi lỗi và subsequent amendments.
