# RSI3+IBS trước giờ đóng cửa — sửa độ phù hợp vận hành bằng một phiên bản mới

Candidate `us500-cash-preclose2-cutler3-10-40-ibs05-atr14x1p5-r025-v1`, parent
R050. Đây là clock adaptation mới, không sửa ngầm bản close→16:01 cũ.

Lý do đã quan sát trước outcomes mới: năm2016 có13BUYsignals nhưng0fills;
phút16:01NY đã chọn thường không có quote trong sourceCFD. Các lệnh chờ hết
hạn được giữ;không gọi năm này có0PnL làbằngchứngeconomic/edge. PaperPagonidis
dùngETF/closingprices,không bảo đảm CFD nhận lệnh saucashclose. Bản mới thử
thao tác trướcclose,không tăngrisk/đổithreshold để cứuPnL.

## Quy tắc chốt trước thử nghiệm

- Giữ CutlerRSI3<10 +IBS≤0,5 choBUY;EXIT nếu RSI>40 **hoặc** IBS>0,5;
  từng điều kiện exit độc lập khả dụng. Khôngpyramid/TP/trailing.
- Decision 2phút trước referencecashclose:15:58NY hoặc12:58halfday. Chỉ dùng
  các M1bars đã kết thúc đến15:58 (lastbar15:57), không nhìn15:58/15:59.
  Fillopen15:59 hoặc12:59,one-minute delay saudecision;missingminuteexpire.
- CurrentIBS dùng Bid high/low/close của phầncashday đãquan sát đếncutoff.
  RSI dùng currentpartialclose và3fullcashcloses trước. Stopdistance1,5×mean
  14TR:13pastfullcashTR +currentpartialTR theo exactconsecutivesessions.
  Thiếu currentprefix bar→safetyEXIT;missinghistory không tạoBUY. Fullcashbar
  ngày hiện tại chỉ được cập nhật vào history **sau** khi chốt currentdecision.
- Dailyhistory/NYcalendar/DST, oneposition/lot/margin/SL/cost/funding/openmark
  giữexactprimitives của source82f5ed9. Vốn10k/planned25USD,marketgeometry,
  fee0,5/lot/side,slippage0,25/0,75;funding1/2USD/lot/calendar-day declared.
  Overnight/weekendgap/slippage/funding cóthể làm lỗ vượtplanned25;khôngcaplỗ.

## Kiểm và đánh giá

CanonicalsealedM1/data2022–24,cùngsourcecache,khôngdownload/broker/modelcalls.
3annualbooks×2costs+3nullcontrols;chỉ development/exposedrobustness,khôngOOS.
Kiểm cutoff/halfday/futureprefix/gaps/ATR/ORconditions trướcPnL;independent
Fractionoracle đánhgiá rule và distance trên partialbar trong mỗi simulation.
Giữoriginalcomparison/negativecases,cost/risk unchanged,outputmới/sourcepins.

Ưu tiên historicalextension nếu mọiannualyearpositive cảcosts và material
implementation checks đạt;không đủ C1/prop. Báo tradecounts/fillavailability/
funding/marks/gaps,không đếm oldmissedentry thành thua hoặc chọn lại history.
Nếu không đạt thì giữ version, không thử cutoffs1/3/5phút thành grid để kiếm
winner. Thay đổi clock được tính vào trialhistory và selection uncertainty.
