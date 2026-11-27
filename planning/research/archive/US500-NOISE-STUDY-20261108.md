# US500 noise band v1 — đăng ký development trước PnL

Đây là một hypothesis mới trong [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md),
không replication SPY hoặc ứng viên đã qualified. Frozen trước mọi numeric PnL:
US500 CFD sourceDukascopy2022, [data/quality](US500-DATA-PREPARATION-20261108.md).
Không mở2025+, không broker calls. Một version, hai declaredcostscenarios;
không gridsearch lookback/giờ/exit sau outcome để giữ cùng trial identity.

## Cơ chế và quy tắc

- Candidate `us500-m1-noise14-opposite-hardstop-r025-v1`.
  Hypothesis: chuyển động vượt biên độ thường thấy cùng giờ14cashsessions
  trước có thể tiếp diễn trong phiên. [Paper tác giả](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf),
  version22/09/2025, là cơ chế tham khảo; paperSPY/IQFeed không là evidenceCFD.
- Clock `America/New_York`, frozenNYSE2022calendar,09:30–16:00;25/11 đóng13:00.
  Cashsession tham chiếu tín hiệu, không hợp đồng giờ giao dịch broker.
- Chỉ dùng midpoint của **M1open vàM1close**; không tạo midhigh/midlow từ
  sideextrema. Quyết định10:00,10:30,…,15:30 (halfday tới12:30) từ close của
  phút đã kết thúc trước boundary; ví dụ10:00 dùng09:59close.
- Sigma=mean(abs(close_same_slot/open_cash−1)) của đúng14cashsessions trước;
  missing slot hoặc open/history chưa đủ thì không có decision tại slot đó.
  Không lùi xa hơn để lựa14ngày đẹp. Previouscashclose bắt buộc là close phút
  cuối của đúngcashsession trước (kể cảhalfday), không extendedsessionclose.
- Upper=max(todaycashopen,previouscashclose)×(1+sigma);
  Lower=min(todaycashopen,previouscashclose)×(1−sigma).
  Currentclose>upper→BUY; <lower→SELL; bên trong giữ position nếu có,khôngentry.
  Opposite signal đóng/rồi đảo chiều nếu risk/margin hợp lệ; cùngside khôngadd.
  Không VWAP vì sourcevolume chưaexchangeverified.
- Adaptationprop: thêm hardSL cố định tại **oppositeband của decision**,
  khôngTP/trailing; khác stopsemi-hourly/capitalallocation của paper. Theo dõi
  stop bằng closing-sideM1extrema; gapopen fill adverseopen, intrabar modeled
  stop level, dùng `protective_exit_for_bar`. Không tự gọi firstcrossingtick.
- Fill entry/strategyexit tại open phút **sau decision1phút**, không sameclose.
  Ví dụ decision10:00→fill10:01. Pending hết hạn nếu phútfill thiếu; không
  fill lại ở tương lai tuỳ ý. Margin/sizing từ quoteopen đã đến lúcfill.
- Scheduledflat tại open của phút cuối cashsession (15:59 hoặc12:59),
  nhằm chừa1phút trước referenceclose. Không forceclose cuối sample. Missing
  scheduledflat quote giữ exposure/đánh dấu unresolved, không giảfill.

## Declared market và costs — chưa broker verified

USDaccount10.000,1USD/indexpoint/lot,sourcegrid0,001;min/step0,01lot;
max50lot,leverage10,plannedrisk25USD/trade gồmcommission/slippage/gridreserve.
Reuse `InstrumentSpec`, `CostModel`, `size_for_market_stop` và
`calculate_round_trip_cost`; không nới `ForexPilotSnapshot` EURUSDguard.
Commission0,50USD/lot/side ở cảscenarios; slippage0,25point/side(reference),
0,75point/side(stress); sourceBid/Ask embedded. Đây là assumptions trướcoutcome,
không historicalfee/targetbrokercontract. Intraday không scheduledfinancing;
overnightexposure nếu thiếuflat/gap khiến kết quả không đủ qualify.

## Gaps, risk và qualification

12missingcashminutes giữ nguyên. Không loại cảngày bằng hindsight hoặc fill
giá. Trong exposure, gap đánh dấu `path_unresolved`; nextquote có thể mark/
modeledstop nhưng không chứngminh pathSL/equityDD. Missinghistoryslot chỉ làm
unavailable nhữngdecision cầnslot đó, kể từthờiđiểm biếtgap. Không dùng việc
ngày mai thiếugiá để ngừngtrade hômnay. Cash daily/overall/internalbrakes chưa
native evaluated; không côngbố compliance/targetpass từ coarseM1 study.

Trước PnL: synthetic band arithmetic, exact14past/historygap, futureprefix
invariance, minlot/riskcost/margin, pendingexpiry, stopgap vàscheduledexit được
kiểm. Nullsignal control phảiflat/0PnL. Source/inputs/calendar/protocol/costhash
freeze trongattempt mới; khôngoverwrite hoặc autoretune. Dossier giữ toàn bộ
trades/decisions/gapflags/cashreconcile và thời gian.

Đánh giá: năm2022 chỉdevelopment/sanity; báonet/trades/R/costs/opengaplimits.
Nếu cả2scenarios dương vàkhôngmaterialdefect→chỉ eligible để đăngký exposed
2023/2024robustness/tickcheck mới, **không C1**. Nếuâm, giữnegativeversion.
Không tune năm2022 rồi gọi cùngversionvalidated; trialcountbao gồmvariants.
