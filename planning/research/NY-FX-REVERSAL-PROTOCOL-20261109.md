# R070/R071: EURUSD đảo chiều MA4 trong phiên New York

Đăng ký trước new source fetch/quotes, signals và PnL. GoalC1/C2 vẫn active;
đây là early economic triage, chưa challenge/broker permission.

## Cơ chế và phép chuyển có chủ đích

LeBaron/Zhao, *Foreign Exchange Reversals in New York Time* (September2008),
[authorPDF](https://people.brandeis.edu/~blebaron/wps/fxnyc.pdf), đọc09Nov §§2–4
và Table3/7: contrarian hourly price-versus-MA trong coreNYhours; paper có
sample EBS2003–06 và cảnh báo suy yếu. Không lấy reported returns làm bằng
chứng hiện tại. Không code/data import từ paper, chỉ implement ý tưởng riêng.

PDF445.817bytes/SHA`fe23d8cdb011b927a7a4ddc93d2257fb075498d4a3756ab9e88893889305f2bd`;
private`ny-fx-reversal-method-source-v1/fxnyc-system-trust-v2.pdf`. Webtimeout,
Pythoncertificatefailure và curlpartial215.919bytes được giữ; complete download
qua Windows systemtrust, không disableTLS. Không gọi partialfile là fullpaper.

Paper MA4–12 bao gồm current sampled price, contra direction; không biết
source-side sample/lifecycle code, EST/DST treatment chưa certified. Project
chỉ chọn **MA4**, shortest window trong paper, trước newoutcome; không grid
hoặc chọn bestpaperrow. Chọn EURUSD cùngcurrency được khảo sát, không chuyển
GBP/AUD/JPY chỉ vì đã có outcomes đẹp. Khác oldZ20±2/holdtime: MA4 sign, stateful
same-side hold/flip, NYsession only, no z-threshold. R071 opposite momentum là
registered diagnostic control, không winner để promote sau khi xem kết quả.

## Nguồn, clocks và causal inputs

- Existing Dukascopy/pinned1.51.1, EURUSD Bid/Ask explicit H1:2019 và2022,
  4exports/48months. Các năm đã exposed; không cleanOOS. Fullsource fixture
  review bằng raw/canonical/Fraction trước economicrun. Reuse native H1cache,
  ignoreFlatsfalse/source-only,volume rounding metadata, noM1/tickfillclaim.
  Own2025+đóng; không tải warmupyear vì15hours prior firstdecision nằm cùngJan1.
- Mọi weekday trong hai năm là expecteddate; không loại holidays vì missing
  hoặc performance. Quyết định10/11/12/13 **America/New_York với DST**, action
  đúng H1Open một giờ sau11/12/13/14NY; scheduledflat15NY. SourceH1Open là
  separate-side interval proxy[hour,hour+1), không exact executable jointquote.
  Đây là **onehour latency adaptation**, không replication paper15mincheck.
- Decisiont dùng15exact consecutive BidH1 đã đóng (t−15h…t−1h), AskClose ở
 4lasthours để midpoint closes; mỗibarClose knownafter+1h. P=current midpoint,
  MA4=mean4; P<MA4BUY, P>MA4SELL, equality targetflat. Missing/crossedfeature
  ghi unavailable, không backfill/asof/drop expectedrow; unavailable không
  ép exit, giữ existingposition vớiSL/scheduledexit. R071 đảo BUY/SELL.
- TR14=mean14 max(high−low,abs(high−previousClose),abs(low−previousClose)) từ
 15pastBidbars. Distance1,5TR14. Không future price/quality làm entryfilter.
  OpenBid/Ask check chỉ hiện tạiOpen; không dùng futureClose để skipentry.

## Account/path rules cố định

Initial10kUSD/year/fixed25USDplannedrisk, max1position, EURUSDcontract100k,
tick0,00001/minstep0,01/max50/leverage30; declared research geometry. Costs
commission2,5USD/lot/side,observedspread,slippage0reference/0,00002stress/side,
intradayfunding0. Không targetbrokerhistoricalcost/spec certification.

- Actionhour: priorposition open-gapSL trước queuedintent; scheduled15NYclose
  trước intrabar. Intents lấy đúng previousdecision, không recompute bằng
  entryhourfuture. Same-side giữsize/SL, opposite/flat đóngởOpen rồi mới mở
  opposite nếu financeable. Closedcosts/cash xong mới xét margin/risk cho newentry.
- BUYAsk/SELLBid; SLentryquote±distance floorBUY/ceilSELL; sizing reuse native
  stop-cost+tickreserve, rounddown0,01; actualplannedrisk≤25,margin≤cash,cash≥25.
  ProtectiveBUYBid/SELLAsk, gapfillatOpen; intrabarSL theo nativeOHLCstopmodel,
  noTP/trailing. Re-entry sauSL chỉ theo nextactionintent, không withinhour.
- Tối đa4entryintents/day; actionflat hoặc rejection vẫn giữcensus. Missing/
  crossedOpen lúcflat ghi unavailableentry,không inventedfill. Missing held
  bar/exit hoặc crossed heldOpen/Close là unknownexposure, freeze annualbook,
  netN/A; không droptrade hoặc tựclose. Sourcegap không được nhìn trước để
  skipentry. H1OHLC không intrabar ordering/propDD hoặc brokerrejectionproof.
- Nullbook same decisions/source nhưng noentry/cash0.2years×2directions×2costs
  ×2null=16books. Separate inputquality census không được dùng futureexit
  validity làm eligibilityfilter. Không compoundrisk hoặc scaleup để ép target.

## Gate/review/thời gian

Chỉ R070 là candidate: cảhai stressyears knownflat/net>0 và≥100closedtrades
để ưu tiên further research. Gate là triage, không statistical edge/prop proof;
không tune sau outcomes, không promote oppositecontrol. Preserve allnegatives.
Nếu fail thì gác exactrecipe; nếu unknown thì giữ unknown và xem impact nhỏ
trước longfullrun. Không gọi uncertainty là economicloss đã xác minh.

Trước numeric: tests decisioncausality/futuremutation/equality/DST/knownbar,
same-side/flip/SLgap/timeexit/cost/sizing/margin/missingfreeze/entryOpen-only.
ManualFraction BUY/SELL×cost fixtures. Full reviewer riêng Fraction signal/
TR/sizing/financialpath/cash/selectedsource and allbooks; mutation falsecounts/
prices/cost/authority phải reject. Sameagent/provider vẫn chưa independent
human/modelcertification. No accountwide prop/native tick/forward/OOSpromotion.

Source`execution-v1/ny-fx-reversal-source-v1`,numerics`ny-fx-reversal-v1` tại
campaignprivate. Onewriter/CANCEL/status/events/pins/snapshots/deadline180s mỗi
phase. Source4books/48months,retry0/cumulativefailurecap1,WAF/token-cacheoff.
Không newprovider/account/key/service/runtime/globalconfig. Giữfailedattempts;
không restart job chỉ vì observer timeout. Đo wall/CPU/prep/compute/review;
reuse đúng seals, không rerun unchanged. Existing skills đủ, không framework mới.
