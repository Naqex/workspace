# FTMO: đã đọc đúng symbol rows; chưa đủ để coi là hợp đồng tài khoản

**Đã giải quyết gap đọc trang:** browser render được XAU/USD, US500.cash và
EUR/USD của regionGlobal, không login/account mới. Public facts lưu trong
[observation JSON](FTMO-PUBLIC-SYMBOLS-20261108.json), không là runtime config.
Chưa gắn `broker_spec_verified=True`, sửa oldcost hoặc rerun strategy.

## Đã thấy gì ngày08/11/2026?

Nguồn chính thức: [Symbols](https://ftmo.com/en/symbols/), chọn MetalsCFD,
CashCFD, Forex. Browser DOM có bảng sau khi JS load; textfetch thiếu rows
không có nghĩa hãng không công bố. Search-index copy còn GMT+3/swap khác;
dùng renderedobservation mới và ghi ngày, không trộn hai snapshots.

| Public row | Contractsize | LeverageSwing | Commission hiển thị | Swaplong/short hiển thị |
|---|---:|---:|---|---:|
|XAU/USD|100|1:15|0,0014PERCENT/VOLUME|−59,58/−4,2points|
|US500.cash|1|1:15|0|−180,08/+4,46points|
|EUR/USD|100.000|1:30|5USD/LOT|−9,5/+0,36points|

Marginpercent2/2/1 trên row đi với leverageStandard1:50/1:50/1:100; **không**
lấy marginStandard đó làm marginSwing. Tại snapshotGMT+2: XAU/US500 Mon–Fri
01:05–23:50, EURUSD00:05–23:55; weekendclosed. Đây là giờ công bố tiêu chuẩn,
chưa gồm holiday/maintenance/changedhours và chưa chứng minh quote thực thi.
Không lấy staleSundayticker để đặt spread hoặc suy đang tradeable.

### Hai bẫy về tiền và giờ

**Points khác USD và cũng không tự là minimumtrade tick.** [FTMO points/pips/ticks](https://ftmo.com/en/blog/points-pips-and-ticks/)
phân biệt technicalpoint theo digits với tickstep. [FTMO swap explanation](https://ftmo.com/en/blog/what-is-a-swap-and-for-whom-is-it-important/)
nêu points/lot; [MetaQuotes symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants)
và [swap modes](https://www.mql5.com/en/book/automation/symbols/symbols_swaps)
tách SYMBOL_POINT, TRADE_TICK_SIZE/VALUE, SWAP_MODE và ROLLOVER3DAYS.
Publicrows không trả đủ các field này; QDM/Dukascopygrid không thay targetpoint.

Ví dụ **điều kiện minh họa**, chưa là FTMOcashswap: nếu XAUcontract100 và
1point=0,01USDprice thì−59,58points tương ứng−59,58USD/lot; nếu point=0,001
thì−5,958USD/lot trước rounding/multiplier/conversion. Vì thế không chọn một
pointvalue để model “đẹp” hoặc gọi declared20/40USD là conservativebaoquát.
Giữ cashswap unknown tới khi đúng point/mode/units/multiplier được xác minh.

**Giờ MetaTrader và resetdaily loss là hai đồng hồ.** [FTMO05/03/2026](https://ftmo.com/en/blog/trading-updates/trading-update-5-mar-2026/)
ghi server chuyển GMT+2→GMT+3 theo US DST, trong khi riskreset theo Prague.
[29/10/2026](https://ftmo.com/en/blog/trading-updates/trading-update-29-oct-2026/)
xác nhận swaps/dailyreports chuyển00:00GMT+3→00:00GMT+2; Prague reset không
chuyển theo server. Không dùng một fixedUTC hoặc Europe/Prague cho cả hai.

Ví dụ calendar2026 (UTC instants trước localmidnight của ngày ghi):

| Localmidnight date | Serveroffset có nguồn | SwapmidnightUTC suy ra | Prague00:00UTC | Chênh |
|---|---:|---|---|---:|
|06/03/2026|+2|05/03 22:00|05/03 23:00|1giờ|
|15/03/2026|+3|14/03 21:00|14/03 23:00|2giờ|
|15/07/2026|+3|14/07 21:00|14/07 22:00|1giờ|
|08/11/2026|+2|07/11 22:00|07/11 23:00|1giờ|

Calendar table là phép quy đổi, **không swapcharge trên Sunday hoặc lịch sử
broker2010–24**. Các ngày/rollovers có tính phí, triple/holiday/dividend phải
pin riêng; không suy mọi symbol đều Wednesday×3 từ bài giải thích Forex.

## Chi phí hiện có được phép kết luận gì?

[25/09/2025announcement](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
nêu Metals0,0007%volume/side, Forex2,50USD/lot/side. Publicrow0,0014 và5 phù
hợp tổng hai chiều ở cùng notional, nhưng row không ghi sidebasis riêng.
Với percentagecommission cần tính entrynotional và exitnotional tương ứng;
không thay bằng fixed2,50USD/lot cho mọi giá. Announcement không chứng nhận
rate cho mọi account hiện tại hoặc chi phí lịch sử2010–24.

[InfrastructureFAQ](https://ftmo.com/en/faq/how-does-the-ftmo-technical-infrastructure-work/)
nêu delay tới200ms; đây không measuredlatency của máy/broker và không đảm bảo
khớp tại giá ở200ms. Không đổi modeledM1stop thành actualtickfill theo nhãn.

| Lát | Evidence đã có | Điều vẫn chưa đủ / quyết định |
|---|---|---|
|Gold50k|Publiccontract100,Swingleverage15,percentagefee|Oldmarket100/leverage10/fixedfee2,50 và declaredswap không exactFTMO; giữ originalresults/lowpriority, không rerun để cứu target|
|US500|Publiccontract1,Swing15,commission0|usa500idxusdDukascopy khác feedUS500.cash; grid/minlot/point/swap/dividend/clock unknown. Intradaycommission0 study giữ scopedcostscenario; carrybooks không targetqualified|
|EURUSD|Publiccontract100k,Swing30,publicfee5roundtrip consistent|Swapratepoints snapshot không historicalcash; old9,30/−0,31USD và22UTC vẫn declaredscenario, không currentaccountproof|
|Riskprofile|Existing offlinefixture resetEurope/Prague và balanceanchor đã có|Không cần tạo propengine thứhai. Fees/reset ordering, actualequitypath/spec và accountauthority vẫn riêng|

## Quyết định và bước tiếp

**Sourcegap đã thu hẹp; economic/prop admission chưa đạt.** Lưu nguyên raw
display strings; không tự đổi points→USD, fillunknown→0, suy multiplier/point
từ PnL hoặc nâng publicmetadata thành verifiedaccount. Giữ oldprotocols/
source/results để reviewdelta. Không sửa product/nativeUI, terminal hoặc global
skills; existing research/qualification/continuity workflows đủ cho lượt này.

Không cần chờ có account mới mới làm research: có thể đăng ký declaredcost
scenarios rõ uncertainty để sàng lọc; chỉ exacttargetqualification bị thiếu
accountfields. Không mua challenge, tạoFreeTrial/OAuth hoặc lấy Exnessspec làm
FTMOspec. Không có batch/numeric/brokercalls, không mở2025+; C1/C2 vẫn active.

Tiếp theo chọn boundedhypothesis có inputsđãcó và cơ chế khác trong catalogue,
trước khi code/numeric. Ưu tiên method/data admission củaR024weekendgap hoặc
R019break/retest; không bỏ R026data/calendar gaps hoặc mở grid losers. Protocol
phải nêu targetcost uncertainty, trial/exposure và stopconditions trước outcome.
Research sources/clock calculations không là evidence rằng hypothesis có edge.
