# R090 dự kiến: tiếp diễn sau first observed hourly shock, trước outcome

09/11/2026, tiếp [R089 temporal không đạt](FX-ABNORMAL-DAY-TEMPORAL-RESULTS-20261109.md).
Đây là **recipe khác**: tiếp diễn trong cùng ngày, không đảo side của trade
R089 hoặc chọn control dương thành winner. RelatedR007/R089, chưa independent
edge. Component `eurusd-first-hourly-shock-continuation-utc-v1`, ID R090 chỉ
ghi catalogue khi có implementation/outcome; hiện89records/58accountversions.

## Nguồn phương pháp và phép chuyển

[Caporale/Plastun primary PDF](https://bura.brunel.ac.uk/bitstream/2438/20567/5/FullText.pdf)
§§3–4/eq1–8/Tables1–5 đã đọc và kiểm lại09/11, sourcePDF/visual/hash ở
[method admission trước](FX-ABNORMAL-DAY-METHOD-ADMISSION-20261109.md).
Nhánh Strategy1 cùng hướng trong ngày khác Strategy2 ngày sau. Không chép
giờ19/17server không rõ thành UTC, không dùng mean/CAR toànsample để chọn
entry, không gọi việc bỏcosts hoặc winrate≥50% là đủ lợi nhuận. CC BY4paper,
owncode không import dữ liệu hoặc code của tác giả.

Ownadaptation dùng currenthour change đã biết, chỉ **first observed hourly
threshold crossing**, nhận tin h:01 và entryh+1UTC; một độ trễ giờ có chủ đích
để không giả khớp vào chính quote phát tín hiệu. Đây chưa firsttickcrossing/
exactpaperreplication. Hypothesis có thể mất continuation trong độ trễ này;
không được đổi sang instantfill sau khi thấy PnL âm rồi giữ cùngversion.

## Quy tắc khóa trước nguồn thật

- Evaluation toànweekdays2019/2022:261+260=521rows. Hai năm exposed; không
  cleanOOS hoặc sampleđộc lập sau89hồsơ. Khôngown2025+. Mọi weekday được giữ,
  không loại holiday hoặc Monday theo lợi nhuận sau khi chạy.
- Dailybase là first-after00UTC. Calibration20weekdays ngay trước currentday,
  mỗi ngày dùng midpointfirst-after00→20UTC; return=end/start−1, samplevariance
  ddof1, k2strict. Currentday không vào calibration. Missing/late bất kỳ prior
  slot →unavailablehistory, không lấy ngày xa hơn; variance0→unavailable.
- Observe giờh=1..18UTC theo thứ tự. So `mid_h/mid_00−1` với mean±2std prior
 20returns. Positive shock đòi currentreturn>0 và delta>0;negative ngược lại;
  equality khôngshock. Không dùng current20UTC/futureClose xác nhận signal.
- **Chỉ crossing đầu tiên** ở các giờ đã quan sát hợp lệ; không phải first
  intrahourtickcrossing. Mỗi quote first-aftertargetlag≤60s, known-at≤h:01,
  decision=h:01. Nếu prefix0..h thiếu trước crossing →unavailableprefix,
  không tìm crossing ở giờ sau. Nếu đãcrossing, latermissing/futureprice
  không đổi selection/side hoặc đẩy crossing sang một thời điểm thuận hơn.
- Entrytargeth+1UTC, exitdecision19:59/exit20UTC cùngngày, quote lag≤60s.
  Khôngretry entry ở giờsau, không lấy futuremissingentry/exit để bỏ signal;
  selectedunknown giữ financialunknown. Max1signal/ngày/khôngreverse.
- Primary cùnghướngshock (positiveBUY/negativeSELL); oppositecontrol cùng
  timestamp/mask, null0. Khôngpromotecontrol dựa outcome.
- Một researchunit=100.000EURnotional, USD;sourcejointBidAsk, commission5USD
  roundtrip, referenceextraslip0, stressextraslip0,4pipRT=4USD. Reuse native
  costcore; funding0 chỉ vìentry02..19→20UTC khôngqua declared17NYrollover.
  Chưa SL/TP/lotgrid/account/margin/equity/path/prop hoặctargetbrokerfees/fills.

## Source admission trước financials

Pilot calendar-only: firstTuesdayFebruary2019/2022,05Feb2019/01Feb2022.
20priorweekdays×2slots +current0..20UTC=61targets/date,**122slots** tổng.
Khôngrealfeatures/PnL trongpilot. Reuse sealed `fx-abnormal-day-temporal-source-v1`
packet khi đúngtarget; thiếuhourroles phải lấy từregisteredraw/cache2019/22,
không reuse20UTC nhưquote giờkhác. Native/Fraction/predecessor/referencecache
review nhưR089; oldproducer/currentconsumer runtime giữ riêng, không ép cache.

Pilotđủ122slots/tronglag vàcomparators/mutationsđạt mới fullsource4partitions:
2018=40warmup,2019=5.481,2021=40warmup,2022=5.460;**11.021targets**.
Source-calendar phải dựng riêng vàsođủ, không copy122 thànhfullhistory.
Fullcensus chấp nhận explicitmissing, không phải mọiquoteavailable; current
signalprefix theo rule ở trên. Missing khôngPnL0, noffill/nohiddenGET/rebuild.
Bind parentseals/rawSHA/cachepayload/code/runtime/targets/output; nooverwrite,
PID/events/progress/timers/deadline300sperphase/CANCEL, mộtwriter,0broker/GET.

## Frozenpriority và kiểm

12books/3.126financialcases, không3.126trades. Giữ reference/stress/primary/
opposite/null và unavailable/normal/selected toànrows. Chỉgiữđểkiểmđộbền nếu
cả2years:≥8selected, mỗi năm≥80%weekdays cófeatuređủ (`normal+shock`),
allselectedendpointsresolved, strictstressnet>0. Thiếucoverage/sample/selected
quotes→inconclusive; đủnguồn/mẫu nhưngnet≤0→gác exactversion. Heuristic ưu tiên
công việc, không thống kê chứng minh edge hoặc xác suất đạtquỹ.

Synthetic trước nguồn: priorwindow/sign/equality/crossingfirst/futureinvariance/
prefixmissing/decisionknown-at/no-retryselectedunknown/weekday/pricegrid,
BUY/SELLfees/null/unit. Reviewer tựtính varianceidentity khác vàfullsignal
hourlyprefix, clocks/order/sourceavailability, costs/census/sums/gate; không
importproducerfeature/costhelper chooracle. Actualmutations price/time/feature/
side/net/commission/dropday/unknown/authority/gate phải bịreject đúngscope;
unknown cóthể synthetic nếu actual không có. Sameagent khônghuman/feedreview.

Source/correctness/PnL/risk/prop/authority tách riêng. Khôngholdout/account/
providertrảphí/broker/runtime/muachallenge. Nếu retained, freeze temporalextension
trước riskwrapper nhưR089; nếu thấtbại khôngentrylag/hour/k/feegrid cứu recipe.
