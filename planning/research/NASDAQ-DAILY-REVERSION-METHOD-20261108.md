# NASDAQ daily reversion: phương pháp và hai source fixtures, chưa PnL

Tiếp sau [R062](FOMC-NASDAQ-COMPONENT-RESULTS-20261108.md), không dịch event
window để cứu kết quả. Question mới: data/code hiện có có đủ để kiểm một
daily-reversion adaptation có basis/clock đúng trước khi mở history không?

## Method và novelty, trước recipe

[Pagonidis: The IBS Effect](https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf)
đã đọc08/11 phầnData/Methodology/IBSasFilter, pp2–7. Paper dùng dailyETFCSI,
có QQQ; chỉ báo vị tríclose trongrange. Phần minh họa kết hợp CutlerRSI3 với
IBSfilter, giữ ởclose; fees/closingexecution và volume có ý nghĩa. Không có
nghĩa sourceCFD làETF, quotevolume làexchangevolume hoặc publication còn
hiệu quả sau sample. Không importcode/data hoặc claim fullreplication.

Parent ý tưởng có thể làR050(US500RSI3+IBS05), không làmethod chưa từngthử.
US500 source-only long đã không đạt; đọc
[correctedresults](INDEX-LONG-EXPLICIT-RESULTS-20261108.md) trước code. Nasdaq
asset adaptation là trialrelated, không independentedge. KhácSMA/R061 ở
meanreversiondaily, kháceventfixedclockR062; chưa khóa candidate/thresholds/
cost/riskwrapper ởlát source này, không accountpolicy mới.

**Không dựng cashbar09:30NY từsourceH1bar09:00–10:00** rồi gọi exactcash.
Tương tự không dùngmeanBidAskextrema làobservedmid. Có thể reuse M1source-only
và same-side OHLC; completecashbar chỉ known16NY, nên orderclose16:00fill
ngaygiáđãbiết là chưa causal. Một recipe sau này phải chốt delayedfill riêng.
ClosingauctionETF vàCFDaftercashquotes không là cùng execution/cost.

## Registered source fixtures, không indicator/outcome

Reuse đúng **02/01/2019 và01/07/2022** Bid/AskM1 từ NASDAQpilot đãsource-review.
Hai ngày kế thừa nguyên fixture winter/summer trước đó, không chọn theo giá.
SourcepilotresultSHA`f4f92c4de46263ab6ddf4afeb3dbc3295c812b6a3c724d1d9d0f023fed9987ba`,
reviewreceiptSHA`9b2904e98401d7e9bb654c51649a7459ca313f8e6be5eb32d6f2b52bc95f4f09`
đã rehash trước đăng ký; không nhầm reviewer-sourcehash với receipt. Parentreport
[source results](NASDAQ100-SOURCE-RESULTS-20261108.md) giữ exactbindings.

Chỉ census09:30<=M1timestamp<16:00America/New_York,390expectedminutes/side/day;
missing/duplicate/crossedOpenClose giữrõ. Check16:01sourceM1Openavailability,
không pricecalculation/PnL/IBS/RSI/selection. ValidateUTC/ms/grid0.001/OHLC/
explicitvolume0/priceunits và roles/known-at; source/side proofhash từparent.
Winter14:30UTC→21:00,summer13:30→20:00. QuoteOpen16:01 làintervalproxy;
khôngchứngminh actualfill/tick/lot/margin/swaps/historicaldividends.

[Nasdaq technical reference](https://www.nasdaqtrader.com/content/technicalsupport/specifications/TradingProducts/fixactspec.pdf)
và [historical regularhours rule](https://www.sec.gov/files/rules/other/nasdaqllcf1a4_5/nasdaqllcamendrules4000.pdf)
đọc08/11 hỗ trợ regular09:30–16:00ET. Đây không current/historical CFDsession
calendar; halfdays/holidays phải được xác định trước fullhistory hay returns.

Lưu nhỏ `execution-v1/nasdaq-cash-session-fixture-v1` dướiprivatecampaignroot,
producer/reviewer/protocol/source/sampledclock hashes,events/progress/timing,
1writer,deadline30s/no network/no2025+/no broker. Admission chỉ source đúng
trong2days, không wholehistory. Không tính signal hoặc returns để đổi window.

Nếu đủ, nextslice đăng ký marketcalendar/holiday/earlyclose và source-onlyM1
history cho exacteconomicquestion; không tải toànhistory vì muốn “códata”.
Không épregular390minutes vàohalfday, không impute sourcegaps hoặcvolume0drop.
Nếu thiếu16:01/cashminutes thì ghi gap, không tự đổi clock/asof/filter khi đã
thấy data. Existing research/source/qualification/continuity skills đủ.


## Source fixture results — sau đăng kýbf2af55

Đãterminal/reviewed:02Jan2019 và01Jul2022 mỗi ngày390/390Bid và390/390Ask
sourceM1minutes,crossedOpenClose0,16:01quote cócả2sides.780minute-presence/
clockchecks và4mutations clock/missingminute/presence/falseauthority reject.
Canonical fullsourcepricefidelity của parentpilot được reuse, không claim
fresh independentdecode mọigiá; không tính dailybarindicator/returns hoặcPnL.

Private`execution-v1/nasdaq-cash-session-fixture-v1` tại campaignroot giữ
result/review/manifest/source-snapshot/status. ResultSHA
`fb847d6a2b6b87466ab5dec65a88bff83c6e52b2a5c43cc7e2d204c60ea4bdeb`;
reviewerSHA`d6b0dc20745c4129ebb7b81ad926f4ceab567cb37ec8a88fe4ffcb3bc2126af2`.
PID29228 và reviewerterminal0,0network/broker/holdoutcalls. Source admission
2days không wholehistory hoặc targetfills. Producer/reviewer timings trong
artifacts;0,072sreview, không wholeworkflow/benchmarkclaim.

**Next:** đăngký source-onlyM1history theo cashcalendar/earlyclose trước data
fetch và economicrecipe. Không cần tải/giải mã lại pilot khi bindings cònđúng.
Không thêmR063/implementationcount chỉ vìmethod/source2daysđạt. Giữ negatives
R049/R050US500 và declaredfunding/geometry; Nasdaq không renameUS500đểvượtguard.
