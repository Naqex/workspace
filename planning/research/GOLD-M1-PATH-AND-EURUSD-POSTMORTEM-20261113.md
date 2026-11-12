# R043: đã đo M1 có điều kiện; EURUSD cần alpha đủ trả chi phí

13/11/2026 (Asia/Saigon); measurements12/11UTC. Theo chỉ thị owner sau
[PR67](https://github.com/Naqex/workspace/pull/67), giữ220lệnh đóng và5vị thế
cuối15sổ50k của R0432010–2024, không ép H4 thành intraday, không bỏShort hoặc
đổi rules/SL. EURUSD chỉ đọc sổ Catalogue13; không study chiến lược mới.
**Không mở giá2025–2026 hoặc gọi broker.** [JSON có số liệu và coverage từng vị thế](GOLD-M1-PATH-AND-EURUSD-POSTMORTEM-20261113.json).

**Quyết định:** Gold vẫn research survivor, chưa candidate challenge. Ở0,25%,
bao biên M1 quan sát cho Daily Loss0,4926%, peak-to-trough equityDD4,20428%,
lỗ equity so initial3,8812%.0,40% còn dưới internal3%/6,5% nếu6,5% là
**static initial loss**, nhưng vượt6,5% nếu dùng **peak-to-trough DD**.
0,50% vượt cả hai cách áp6,5%. Chưa có mức nào được chứng nhận safe toàn path.
0/15sổ chạm10% tiền lãi đã đóng ở cả9case swap×sizing; chưa giải được time-fit.

## Repo cleanup

PR67 head`60f99d6` merge sau3CIđạt, mergeSHA
`0240424a8e56286a6942456758c51c3cf2d4e305`; localmain fastforward.
Đã xóa local/remote `codex/gold-cost-path-audit`,
`codex/us500-frequency-review`, `codex/us500-ma-reclaim-study` và
`codex/us500-multiframe-study` đúng tips đã đối chiếu với owner.
Annotatedtag **`archive/us500-multiframe-study`** đã push, trỏ commit
`b77fc68639992a0a23d96e15bf005eeabfae9aee`; không rewrite/squash lịch sử.
Hai branch divergent được xóa theo xác nhận trực tiếp; Git refs cập nhật
compare-and-delete exactSHA, không giả chúng là ancestor của main.

8remote-trackingrefs khác là refs local đã stale, không phải8branch remote
còn sống; `git fetch --prune origin` đã dọn. Sau cleanup trước PR báo cáo này,
**GitHub chỉ cònmain**. Local còn `annam024-vi-dubber-ui-proposal` do worktree
chat khác đang dùng, và dirty submodule VI Dubber; giữ nguyên, không nhận là
mọi localcheckout đều clean hoặc xóa WIP để đạt hình thức “chỉmain”.

## 1. Cách đo và phạm vi đúng

Reuse export M1 Bid cũ, SHA`d209df9…471b9`,5.399.878rows gồm warmupNov–Dec2009;
chỉ đánh giá2010–24. Giữ spread Ask mô hình1USD/oz, commission2,50USD/lot/side,
slip0,20USD/oz/side và nguyên fill prices/lot của stress parent.
Một lot vàng100oz; chưa target-spec/account verified.

- Entry và exact-open exits khớp M1Open; SL được định vị tới phút đầu chạm
  trong H1exitinterval đã ghi. Không sửa fillprice/trade selection. Tất cả
 220closed/5open được giữ; không thấy M1Open gap vượt frozenSL trong
  135stopminutes được định vị (khác các gapstop đã exact-open trong parent).
- Giá closeable là Bid choLong, Bid+1 choShort. Equity trừ reserve commission/
  slip hai chiều, financing đến hạn; cash posting lúc đóng như parent.
  Đây là **liquidation-equity convention của mô hình**, chưa actual MT5posting.
- Trong phút SL, chưa biết extrema xảy ra trước hay sau fill. Bao biên cho
  phép toàn High/Low của phút đó và high-before-low để có DD thận trọng trên
  **bars quan sát**; không gọi là actual MAE/tickDD hoặc bound cho phút mất dữ liệu.
- Sổ cũ vẫn trừ funding tới year-end sau quote cuối. Bridge cuối sổ giữ đúng
  tổng+4.035,06USD; mark tại quote cuối được lưu riêng. Không carry-forward
  giá qua gap rồi gọi là quote/equity quan sát mới.

Luật hiện hành đối chiếu [FTMO2-Step objectives](https://ftmo.com/en/trading-objectives/):
Daily Loss so equity với **balance tại00:00CE(S)T**, resetEurope/Prague cóDST;
overall floor là90%initial, không phải highwatermark. Đây là current-rule
counterfactual lên2010–24, không lịch sử điều khoản hãng từng năm.
Swap đúng lúcreset được đặt sau pre-fee balance anchor, thận trọng cho debit.
Opening-equity daily change được lưu riêng, không thay balance anchor của quỹ.

[SwingFAQ](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/)
xác nhận miễn hạn chế news/marketbreak và base leverage1:30, chỉ2-Step.
**Base leverage không là leverage mọi symbol**: public XAUrow08/11 ghiSwing1:15,
xem [snapshot có nguồn](FTMO-SYMBOL-AND-CLOCK-ADMISSION-20261108.md).
Không nâng parentleverage10 thành30 hoặc gọi đã kiểm margin/account đích.
50k là vốn nghiên cứu; availability Swing50k trong ClientArea chưa xác nhận
(owner trước đó thấy10k/25k), không khẳng định mua được cấu hình này.

## 2. Daily/overall equity: kết quả baseline125USD/lệnh

Mỗi sổ bắt đầu lại50k. Mọi tỷ lệ risk/DD chia đúng50k của sổ đó.
Worst daily bao biên **246,30USD /0,4926%** (2019);
worst equity peak-to-trough **2.102,14USD /4,20428%** (2011), so cash
MaxDD cũ **1.930,54USD /3,86108%** (2020). SampledM1Close-only equityDD lớn
nhất2.090,02USD. Lỗ equity sâu nhất soinitial **1.940,60USD /3,8812%** (2020).
Các worst này khác năm, không gom thành một worstday đồng thời.

| Năm | Cash MaxDD USD | Daily Loss bao biên M1 USD | Equity MaxDD bao biên USD | Lỗ tối đa so vốn đầu USD | Coverage phút lịch |
|---|---|---|---|---|---|
| 2010 | 1.118,01 | 163,42 | 1.067,65 | 917,50 | 72,37% |
| 2011 | 771,02 | 144,93 | 2.102,14 | 377,37 | 68,71% |
| 2012 | 1.254,88 | 194,42 | 1.460,93 | 747,34 | 68,98% |
| 2013 | 705,51 | 156,52 | 1.893,27 | 673,90 | 68,20% |
| 2014 | 984,73 | 166,90 | 1.380,67 | 720,55 | 69,62% |
| 2015 | 1.681,50 | 161,93 | 1.865,85 | 1.276,21 | 67,17% |
| 2016 | 625,06 | 158,84 | 1.220,05 | 143,46 | 68,26% |
| 2017 | 528,69 | 126,38 | 1.163,66 | 216,62 | 67,26% |
| 2018 | 1.834,67 | 177,03 | 2.073,42 | 1.838,21 | 66,26% |
| 2019 | 1.082,67 | 246,30 | 1.239,11 | 890,96 | 69,85% |
| 2020 | 1.930,54 | 156,01 | 2.081,17 | 1.940,60 | 64,88% |
| 2021 | 507,94 | 132,32 | 1.227,58 | 140,73 | 67,31% |
| 2022 | 994,48 | 137,20 | 985,04 | 953,24 | 66,75% |
| 2023 | 358,16 | 126,63 | 1.205,47 | 172,41 | 67,32% |
| 2024 | 602,44 | 132,90 | 1.616,42 | 440,75 | 68,27% |

Theo **bars/mô hình đã đo**, dailyroom tới ngưỡng5% còn2.253,70USD;
room tới staticfloor45k còn3.059,40USD. Đây không là chứng nhận toàn path:
missing minutes, targetAsk/spread/delay/holiday/fees và exactstop chưa đóng.
Không dùng2.500 trừ DD của cả năm, không gọi peakDD là FTMOstaticloss.

### Coverage có mẫu số, không che market closures

225positions:2.754.363M1 quan sát /4.040.190phút lịch có thể đang giữ
= **68,1741%**.198positions có phút lịch không quan sát được.
1.285.827phút không quan sát, trong đó1.108.505phút rơi vàoSaturday/Sunday
(86,2095%);177.322phút còn lại có thể gồm dailybreak/holidays/feed gaps,
chưa phân loại thành outage bằng lịch broker lịch sử.

Coverage bên trong **những giờ đã có ít nhất một bar** là98,8939%; mẫu số này
bỏ qua giờ trống hoàn toàn nên không gọi là full-session coverage98,89%.
Gap không quote dài nhất trong exposure275.400giây≈76,5giờ. Giữ gaps và
coverage từngposition trong JSON, không fill/drop/giả rằng chắc chắn đóng cửa.
Vì vậy global worst risk/unknown minutes vẫn chưa được chứng minh, kể cả khi
metric trên observedbars thấp hơn ngưỡng quỹ.

## 3. Swap sensitivity — cùng220lệnh, cùng giá và phí khác

Weekdays22UTC/Wednesday×3 giữ nguyên, không tự đổi clock/rates theo năm.
S1 vàS2 chỉ thay financing trên **stress trade path**; S1 không tái tạo old
reference có219lệnh/spread0,5/slip0,1. Không so chéo hai bảng rồi gọi bug.

| Kịch bản | Long/Short: USD trừ mỗi lot/lần | Tổng financing USD | Tổng net equity USD | Cash MaxDD lớn nhất một sổ USD |
|---|---|---|---|---|
| S1_20_20 | 20 /20 | 4.475,40 | 8.510,46 | 1.846,54 |
| S2_40_40 | 40 /40 | 8.950,80 | 4.035,06 | 1.930,54 |
| S3_declared_45_5 | 45 /5 (giả định) | 6.584,05 | 6.401,81 | 1.824,34 |

Net là tổng terminal equity của15annual-reset books, gồmopenfinancing/floating;
Cash MaxDD là worst một sổ, không DD tài khoản nối15năm.

S3 chọn Longdebit45/Shortdebit5USD/lot/lần: bảo thủ **trong khoảng minh họa
owner đề xuất**, chưa bảo thủ so mọi account hoặc swap lịch sử. Giữ tất cảShort.
Nguồn FTMO hiện hành nhắc [swap thường xuyên đổi, xem từngsymbol](https://ftmo.com/en/blog/trading-updates/trading-update-5-nov-2026/).
Public points thiếu point/mode/conversion đúngaccount nên không suy S3 là
“biểu phí FTMO đã xác minh”. Signedrates/mode cần
[symbolproperties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants),
không dùngsourcegrid0,001 làm targetpoint. Lượt này không gọi MT5.

S3 nâng tổng net2.366,75USD soS2 nhưng vẫn0/15flat checkpoints đạt5% ởbase
risk; không biến Gold thành challengecandidate hoặc chứng minh edge ngoài mẫu.

## 4. Sizing: tách hai nghĩa của overall

Chỉ1×/1,6×/2× đã khóa trước số liệu, tương ứng nominalrisk0,25/0,40/0,50%.
Lot từngposition được floor về0,01; pricecost/funding làm tròn lại theo cent.
Không chỉ nhân số cuối, không tìm thêm mức đẹp sau outcome. Giữ entries/
stops/exitfills, không native margin/risk/signal replay hoặc sizing thật.

| Swap | Risk danh nghĩa | Daily Loss /50k | DD đỉnh–đáy /50k | Lỗ so vốn đầu /50k | Sổ chạm5% khi flat | Sổ chạm10% khi flat |
|---|---|---|---|---|---|---|
| S1_20_20 | 0.25% | 0,493% | 4,188% | 3,713% | 0/15 | 0/15 |
| S1_20_20 | 0.40% | 0,750% | 6,701% | 5,639% | 4/15 | 0/15 |
| S1_20_20 | 0.50% | 0,985% | 8,377% | 7,426% | 5/15 | 0/15 |
| S2_40_40 | 0.25% | 0,493% | 4,204% | 3,881% | 0/15 | 0/15 |
| S2_40_40 | 0.40% | 0,750% | 6,727% | 5,895% | 2/15 | 0/15 |
| S2_40_40 | 0.50% | 0,985% | 8,409% | 7,762% | 4/15 | 0/15 |
| S3_declared_45_5 | 0.25% | 0,493% | 4,208% | 3,669% | 0/15 | 0/15 |
| S3_declared_45_5 | 0.40% | 0,750% | 6,733% | 5,575% | 4/15 | 0/15 |
| S3_declared_45_5 | 0.50% | 0,985% | 8,417% | 7,337% | 5/15 | 0/15 |

“Chạm5%/10%” là từng sổ từng có **cash sau đóng, flat**, đạt2.500/5.000USD.
Không forceclose; không actualphase2/minimumdays/reset/rolling-start/passrate.
Ví dụ S2/0,50%:4sổ từngflat≥2.500, nhưng chỉ3sổ cuối năm equity≥2.500;
không dùng hai định nghĩa lẫn nhau. S3/0,50% lần lượt5sổ/4sổ.

**Theo cap nội bộ peakDD<6,5% đã khóa trong diagnostic:** chỉ0,25% trong ba
mức được thử còn đạt;0,40%≈6,70–6,73%,0,50%≈8,38–8,42%. Daily đều<3% trên
bao biên quan sát. **Nếu6,5% được dùng cho staticloss giống nghĩa luật FTMO**,
0,40% vẫn đạt observed3%/6,5% ở cả3swapcases (S2static5,89542%,S3static5,57482%).
Đây là hai contract khác nhau, không đổi metric sau outcome để tự pass.

Khuyến nghị: **chưa nâng sizing chạy thật**;0,40% có thể là đối tượng kiểm
định tiếp khi targetcost/data/nativepath đủ, không là mức đã certifiedsafe.
0,50% không đạt cả capstatic6,5% lẫn peak6,5% trong dữ liệu quan sát. Quan trọng
hơn: cả9cases vẫn0/15flat10%touch, nên sizing alone chưa giải quyết time-fit.
Giữ Gold multi-day/Swing research, không ép intraday/long-only hoặc quét exits.

## 5. EURUSD Catalogue13 — đã thử gì, vì sao âm?

Reuse [624case results](EURUSD-CATALOGUE13-RESULTS-20261108.md) và13sealed
annualresults2010–2022, mỗi sổ10k/risk25USD.24versions, **8H4 +16H1**;
đây là standalone H1/H4 strategies, không một pipeline H1bias→M15entry.

| Nhóm logic | Số versions | Khung | Cách giữ/thoát chính |
|---|---|---|---|
| Trend/MA/pullback/compression | 5 | 4H4 +1H1 | Donchian/SMA/pullback H4 theo hướng; compression có trần6nến; pullback H1 trần24nến |
| Breakout theo phiên/vùng | 5 | 1H4 +4H1 | Phá range UTC/ngày trước hoặc ORB London/NewYork/Asia→London; đóng theo giờ phiên |
| Quay về trung bình giá | 5 | 1H4 +4H1 | Z-score H4 trần6nến; RSI/shock/BB/BBflat H1 thoát hồi về mức giữa hoặc12nến |
| Phá giả/quay lại vùng | 3 | 2H4 +1H1 | Failed20 H4 trần6nến; UTC rangefade và prior-day fade có giờ đóng |
| Theo giờ phiên/fixing proxy | 6 | H1 | EuropeAM, LondonPM, preECB, postLondon, preTokyo, composite; median thực tế3–5giờ |

Horizon12/24/6nến là completed observations; weekends/gaps có thể kéo dài
ngày lịch. TrendH4 có median≈4–4,5ngày/p90≈11–28ngày; session/fixing thường
median3–8giờ; mean-reversion H1 thường1–7giờ, H4time6≈24giờ median.
Holding dưới đây là closedtrades/earliestexit, không gồm terminalopens.

**Không phải cả24 âm mọi kịch bản:**6/24net chuẩn dương;0/24stress dương.
Phân rã cùng stresspath, gồmterminalfloating/costreserves để khớp equity:

| Lớp thất bại theo sổ | Versions | Diễn giải đúng |
|---|---:|---|
|Gross Bid/Ask đã không dương|9|Không đủ bù spread ngay trước commission/slip/swap; chưa tách được pure pre-spread markout|
|Gross Bid/Ask dương nhưng sau commission+slip đã âm|13|Lãi mỗi cơ hội quá mỏng so ma sát, swap có thể làm tệ thêm|
|Sau spread+commission+slip còn dương, swap đẩy âm|2|SMA H4 và pullback H4; không đại diện mọi intradayversion|

Ví dụ prior-day-break: gross sau spread+1.230,27 −commission1.125,25
−slip900,20 −swap0 = **−795,18USD**. Londonpostfix: gross+1.558,50
−commission1.479,35 −slip1.183,48 −swap0 = **−1.104,33USD**.
Vì vậy đóng trong ngày không tự sửa được edge quá mỏng sau chi phí.
SMAH4: gross232,72 −commission37,90 −slip30,32=164,50 trướcswap,
trừfinancing1.455,20→ **−1.290,70USD**; đây mới là ví dụ swap chi phối rõ.

**Gross trong bảng đã chứa historical Bid/Ask spread**; không giả đó là
markout trước mọi loại phí. Muốn phân biệt alpha-price trước spread với
spreaddrag riêng cần quote benchmark có căn cứ; lượt quickpostmortem không
đọc lại325triệu ticks để dựng counterfactual hoặc kết luận spread gây X%.
Tần suất cao không tự là lỗi: cần kỳ vọng mỗi trade đủ lớn sau tổngchi phí.
Versions overlap/cùngmarket, không cộng thành portfolio hoặc24edge độc lập.

| Version rút gọn | Lệnh/13sổ | Giữ median /p90 giờ | Gross sau spread USD | Commission USD | Slip USD | Swap USD | Net stress USD |
|---|---|---|---|---|---|---|---|
| h4-donchian20-10-atr14 | 640 | 92,0 /268,4 | -482,21 | 103,65 | 82,92 | 1.956,80 | -2.625,58 |
| h4-sma20-80-atr14 | 224 | 107,5 /666,8 | 232,72 | 37,90 | 30,32 | 1.455,20 | -1.290,70 |
| h4-z20-2-atr14-time6 | 1403 | 24,0 /76,0 | -500,00 | 227,75 | 182,20 | 1.117,60 | -2.027,55 |
| h4-pullback20-80-atr14 | 301 | 107,0 /560,0 | 532,98 | 51,85 | 41,48 | 2.029,80 | -1.590,15 |
| h4-utc-range00-08-atr14 | 2637 | 8,0 /8,0 | -355,52 | 434,65 | 347,72 | 0,80 | -1.138,69 |
| h4-failed20-atr14-time6 | 1353 | 24,0 /76,0 | 221,23 | 223,15 | 178,52 | 1.012,60 | -1.193,04 |
| h4-compression6-24-atr14-time6 | 1513 | 24,0 /70,0 | -919,15 | 251,20 | 200,96 | 1.120,60 | -2.491,91 |
| h4-utc-range-fade-atr14 | 1537 | 8,0 /8,0 | -110,82 | 255,25 | 204,20 | 1,00 | -571,27 |
| h1-rsi14-reentry-atr14x1p5-time12 | 2195 | 7,0 /12,0 | -2.804,00 | 1.009,45 | 807,56 | 1.833,80 | -6.454,81 |
| h1-shock2-reclaim-atr14x1p5-time12 | 322 | 1,0 /9,0 | 203,71 | 143,75 | 115,00 | 104,40 | -159,44 |
| h1-prior-day-break-atr14x1p5-close20 | 2249 | 5,0 /12,0 | 1.230,27 | 1.125,25 | 900,20 | 0,00 | -795,18 |
| h1-prior-day-fade-atr14x1p5-close20 | 1883 | 3,0 /9,0 | 176,18 | 947,95 | 758,36 | 0,00 | -1.530,13 |
| h1-bb20-reentry-atr14x1p5-time12 | 3157 | 4,0 /12,0 | 1.265,48 | 1.515,30 | 1.212,24 | 2.298,20 | -3.760,26 |
| h1-pullback20-80-atr14x1p5-time24 | 2646 | 10,0 /24,0 | -258,73 | 1.345,15 | 1.076,12 | 3.551,80 | -6.231,80 |
| h1-europe-am-short-atr14x1p5-close13 | 3383 | 5,0 /5,0 | 1.540,89 | 1.973,50 | 1.578,80 | 23,60 | -2.035,01 |
| h1-london-postfix16-20-atr14x1p5 | 3376 | 4,0 /4,0 | 1.558,50 | 1.479,35 | 1.183,48 | 0,00 | -1.104,33 |
| h1-pre-ecb02ny-14berlin-atr14x1p5 | 3383 | 5,0 /6,0 | 2.846,03 | 1.972,80 | 1.578,24 | 23,60 | -728,61 |
| h1-post-london16-16ny-atr14x1p5 | 3376 | 5,0 /5,0 | 2.423,12 | 1.479,35 | 1.183,48 | 0,00 | -239,71 |
| h1-pre-tokyo18ny-10tokyo-atr14x1p5 | 2705 | 3,0 /3,0 | -1.759,95 | 1.340,85 | 1.072,68 | 0,00 | -4.173,48 |
| h1-fixing-composite-atr14x1p5 | 9461 | 3,0 /6,0 | 3.487,20 | 4.790,90 | 3.832,72 | 23,60 | -5.160,02 |
| h1-london-orb08-09-atr14x1p5 | 2497 | 4,0 /6,0 | 791,81 | 1.287,35 | 1.029,88 | 0,00 | -1.525,42 |
| h1-ny-orb08-09-atr14x1p5 | 2760 | 5,0 /6,0 | -889,05 | 1.236,50 | 989,20 | 0,00 | -3.114,75 |
| h1-asia09-15tokyo-london-break-atr14x1p5 | 2939 | 5,0 /8,0 | 671,60 | 1.609,25 | 1.287,40 | 0,00 | -2.225,05 |
| h1-bb20-reentry-flat80-atr14x1p5-time12 | 471 | 4,0 /12,0 | 30,87 | 223,95 | 179,16 | 360,20 | -732,44 |

## Kiểm chứng, thời gian và cách tiếp tục

- Gold:18bindings giữ nguyên;rawschema/order/OHLC/grid/date kiểm;15sổbaseline
  cash/equity và mọi oldclosedcheckpoint khớp.225positionidentities/fillprices giữ nguyên.
  Integer cent/tick half-up; syntheticlossanchor/DST March/October/reset-order
  checks chạy trước scan. Không dùng pandasdefault time unit một cách ngầm định.
- Reviewer scalarDecimal riêng, không importproducer:44M1witnessbars,
  15dailyanchors/15peak-troughpairs/cashendpoints khớp;3mutations daily/DD/cash
  cộng1cent đều reject. Không claim độc lập scan lại toàn bộglobalmax hoặc
  independenthuman/model/feed. Negative history giữ nguyên.
- EURUSD:624uniquecases/13completedseals/config và mọi financialbridge khớp,
  không replayprices. Gross và vốn/mẫu số đúng mỗi sổ, không nốiannuals.
- SuccessfulGoldscan135cases wall **16,048s**, CPU15,953s;
  scalarreview5,437s; EURUSDpostmortem3,995s.
  Không là totalagent/Git/webtime, không so như speedup với native tickbacktest.
- Hai lỗi diagnostic bị chặn trước report: pandas3 giữ ms/us thay defaultns
  (DSTfixture bắt trước mởraw); terminalfee sau lastquote (cashbridge bắt).
  Sửa explicitunits/terminalbridge, giữ failureattempts; không sửa oldengine,
  fill hoặc kết quả cũ. Rerun đúng diagnostic sau sửa, không alpha retune.

Private evidence: `execution-v1/gold-m1-path-review-20261112-v1/` dưới campaign
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/` giữ
`protocol.md`, `review.py`, `result.json`, `verify_points.py`, `verification.json`,
`eurusd_postmortem.py`, `eurusd-postmortem.json`, cleanup/failure receipts.
Input/output/script hashes có trong JSON; sourceCSV/quoteprices không commit.

**Tiếp theo đề xuất:** đúng accountcost/Swapmode/calendar và sourcegap admission,
rồi boundednativeGoldfixture nếu feasibility còn hợp mục tiêu. EURUSDintraday
mới cần hypothesis khác có lý do tạo lợi nhuận đủ trả ma sát, freeze
H1bias→M15zone/setup→entry/exit-before-rollover và count-only trước PnL.
Chưa mở study/2025–26, không bỏShort, không tối ưu thêm grid; US500overlay
Bước3–4 vẫnpaused. Existingqualification/evidence skills đủ dùng; không thêm
manager/runner/skill trùng chỉ để thực hiện một diagnostic.
