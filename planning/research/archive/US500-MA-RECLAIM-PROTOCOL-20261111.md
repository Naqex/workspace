# US500: hồi về MA rồi đóng trở lại theo hướng xu hướng

11/11/2026. Owner đồng ý tiếp giả thuyết mới sau
[frequency audit](US500-FREQUENCY-AUDIT-RESULTS-20261111.md). Đây là thay luật
confirmation có chủ đích, không sửa bug hoặc hạ floor để cứu FP04. FP04/158
signals vẫn giữ nguyên. Một phiên bản mới, không grid MA/SL/TP/giờ.

## Ý tưởng và khác biệt khóa trước kết quả

FP02 trước có396setup nhưng chỉ93confirm khi yêu cầu vượt armbar. Một pullback
đóng qua MA có thể hồi phục theo xu hướng trước khi vượt toàn bộ nến arm.
Giả thuyết mới: closed-price recovery qua fastMA cộng đệm là tín hiệu tiếp diễn
có thể kiểm được, đủ mẫu hơn và có thể bù costs. Tăng tần suất **không** chứng
minh lợi nhuận; cần kiểm native nếu qua bước ưu tiên nghiên cứu.

**Chọn FP02 làm parent về setup**, không FP04 wick-touch: phải có close đã
quay sang phía pullback để chữ “đóng trở lại” có nghĩa. Chỉ đổi confirmation
từ armhigh/low sang fastMA tại nến confirmation vừa đóng. HọR004/R098/FP02,
một frequency-only design FP05; nếu chạy tài chính là R123, không edge độc lập.

## Luật duy nhất

| Phần | BUY | SELL |
|---|---|---|
| Hướng ở M15 trước và hiện tại |SMA20>SMA80|SMA20<SMA80|
| Close trước setup |trên SMA20 trước|dưới SMA20 trước|
| Close nến setup |<=SMA20 hiện tại|>=SMA20 hiện tại|
| Confirmation ở M15 **sau** setup |Close>SMA20 của nến vừa đóng +0,10×ATR arm|Close<SMA20 vừa đóng −0,10×ATR arm|

MA confirmation cập nhật bằng đúng nến vừa đóng, không nến đang hình thành;
ATR14 Wilder lưu từ arm không đổi. Threshold so Fraction trên frozen Decimal
inputs, equality không đủ. Không yêu cầu confirmation vượt armbarhigh/low.

Arm M15 closes10:00–14:00 New York; current/previous phải cùng session. Đủ
SMA80 hiện tại/trước sau reset (81M15), không H1 gate/common161. Full cash
session chuẩn09:30–16:00, NY/DST; shortsession indicator history giữ nhưng
không trade. MissingM15 reset readiness/block ngày causal; không nhìn full-day
coverage để xóa entry trước đó. Đúng accepted paired M1 proofs2022–24 của parent,
không2021warmup,2025+,fetch hoặc rawdecoder mới.

Một arm attempt/ngày kể cả cancel/expiry/riskreject. Confirm trong60phút từ
arm và không quá15:00NY; final expiry bar được xét, cancellation khi M15 mất
hướng ưu tiên trước confirmation. Không same-bar entry/rearm/add-on/reversal.

## Hai chặng và stop rule

1. Frequency-only trên3năm; timestamp/side arm phải khớp saved FP02. Chỉ
   confirmation được đổi. >=200exact-open-available signals tổng,>=50/năm
   mới chạy native ở chặng2. Đây là research-priority floor, không statistical
   minimum hoặc bác bỏ edge nếu ít mẫu. Giữ FP05 kể cả không qua.
2. Nếu qua: **R123 duy nhất**,3annual-resetbooks×reference/stress=6financial
   books và3nullcontrols(reference,noentry). Không chạy lại27cấu hình cũ hoặc
   chọn sau PnL. Code/protocol/tests phải commit trước chặng1 và mọi outcome.

## Native execution và tiền

Reuse Nautilus1.231.0 CfdINDEX/QuoteTick/order/stop/accounting của parent,
chỉ inject offline policy mới. Không fake PnL từ vector signals. Starting10kUSD
mỗi annualbook, plannedstoprisk<=25USD, declared1USD/point/lot, tick.001,
min/step.01,max50,leverage10. BUY ask+slip,SELL bid−slip,exactdecision+60sec
M1open. Missing exactfill hoặc precedingminute rejectentry, không latefill.

SL2×frozen armATR từ actual modeled entryfill, outward rounding; qty floor
và include adverse exit slip trong risk. Không TP/trailing/breakeven. Native
stop luôn active khi chờ exit. Gap qua SL khớp rawopen±slip, intraminute touch
dùng same-side M1extreme envelope→stop±slip. Envelope không là observed tick
hoặc synchronous spread; không đổi legacy bar model.

Exit khi M15 fast/slow direction mất; nếu không, **decision15:30NY/fill15:31**.
Không giữ noonexit cho late-entry. Stops vẫn có ưu tiên tại exitopen, không
forceclose cuối mẫu. Missing held path/exit/unclosed cuối =>fullnetN/A, giữ
modeled/knownclosed riêng. Native cent rounding và independent Decimal cash
giữ semantics đã kiểm của parent. No overnight funding được gọi known khi
carry do gap vẫn unresolved. News/closure/targetfeed/targetspec chưa certified.

Commission0 scenario, paired Bid/Ask embeddedspread, adverse slip.25/.75point
mỗi fill; không doublecharge. Sizing/SL có thể khác giữa costs; không coi
stress-reference là phí tăng trên cùng lot cố định. Parent risk chỉ offline,
không quyết định risk tài khoản thật.

## Kiểm đúng, kết luận và vận hành

Fixtures BUY/SELL, strict equality/dynamicclosedMA/frozenATR/no samebar,
trendcancel/expiry/lateclock, nextminute entry,15:31exit,stop/gap/missingpath,
null và mutations sai clock/condition/cash. Reuse financial Fraction reviewer;
review riêng arm/firstconfirmation/earliestexit clocks. Đổi optional policy
injection phải giữ legacy default behavior ở focused tests; không rerun
unchanged27study. Parent R098/R120 và FP02 traces còn dùng làm đối chiếu.

Kết quả: frequency, fills/rejects/unknown, BUY/SELL/combined, net/cost/R,
endpointDD và reason/annual counts; fullintraminute equityDD vẫn unknown.
Không tự promote theo PnL dương, winrate hoặc>=200trades. Theo dõi cost
sensitivity/annual stability/concentration; thiếu cleanOOS/targetprop/forward
giữ inconclusive. Nếu không ổn thì giữ negative, không retune trong lượt này.

Một writer, source/input/protocol/test hashes và snapshots; atomic books/seals,
progress JSON/Markdown/events, CANCEL,600s deadline. Reuse source/preparation
mỗi năm giữa hai chặng, không phải state-resume. No automatic retry/sends.
Giữ failure và frozenattempt nếu có lỗi; source không đổi khi job đang chạy.
