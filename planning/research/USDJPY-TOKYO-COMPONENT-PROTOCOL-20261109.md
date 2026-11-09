# R084 — USDJPY trước Tokyo fix: protocol khóa trước outcomes

09/11/2026; tiếp [method](TOKYO-FIX-METHOD-ADMISSION-20261109.md) và
[source pilot](USDJPY-TOKYO-SOURCE-RESULTS-20261109.md). Liên quan họ fixing
R020/R021, không cơ hội độc lập được chứng minh hoặc replication NBER/BoC.
Mục đích: hỏi một own price component ngắn có sống sau phí không trước khi
đầu tư SL/account/prop. Không paper returns/retail bank-rate arbitrage.

## Cohort và hai cách dùng lịch

2019 và2022; chỉ nominal pay dates ngày5,10,15,20,25,30 của mỗi tháng nếu tồn
 tại trong tháng. Không thêm lastbusinessday31/EOM hoặc calendar threshold.
Official Cabinet CSV cp932 đã lưu SHA
`cec37a743c96995cdb9cb52b685c9003634682a9b0e1a640a6b9b96881fe964a`.
Businessdaymodel: Monday–Friday, loại national/substitute holidays trong CSV,
Jan1–3 vàDec31. [BankingOrderArticle5](https://www.japaneselawtranslation.go.jp/en/laws/download/3602/09/s57Bc000400304en14.0_r01C139.pdf)
và [JBA2019GoldenWeek](https://www.zenginkyo.or.jp/topic/era/) hỗ trợ bankclosure,
không xác minh mọi ngân hàng/actual published fix/PIT snapshot của từng ngày.

- **Primary nominal_business**: nominal paydate không business → noentry;
  không âm thầm chuyển ngày. Lịch giữ cả skipped dates và lý do.
- **Sensitivity previous_business**: mỗi nominal date chuyển về businessday
  gần nhất không muộn hơn nominal date; deduplicate khi nhiều targets về cùng
  ngày, giữ mapping. Đây là model riêng, không quy luật thanh toán đã verified.
  Không so kết quả rồi tự thay sensitivity thành primary/winner.
- Cả hai loại ChristmasDec25 theo treatment của NBERdata, không phụ thuộc
  quotes; primary holiday25Dec không bị đẩy về24Dec. Không xét nominal của
  năm2020/2023 trôi về nămtrước; model targetyear scope phải rõ. Nếu có mapping
  ra ngoài2019/2022 thì dừng registration, không tự mở sourceyear.
- Tất cả dates được freeze/machine+calendar-oracle review trước quote fetch.
  Nguồn holiday hiện tại không tự là cleanPIT; output là declaredcalendar
  scenario, không chứng nhận historicalauthority hoặc realizedpaymentflow.

## Rules và source

Chỉ USDJPY existingDukascopy1.51.1, rawM1 Bid/Ask, UTCday cho unionactualdates,
max300rawday-sideURLs; noauth/WAF/retry, cumulativefailurecap1/deadline300s,
CANCEL/onewriter/nooverwrite. Copy4oldpilotraw sangcachemới đểreuse nếu thuộc
union; khôngghi thêmcachecũ. Source-onlyexplicit/padding phânbiệt, grid0.001,
pip0.01. No2025+/newprovider/account/service/paid/model/broker calls.

- **Primary prefix BUY**: lịch biết trước, scheduledentry09:25JST,
  modeledentry09:26M1Open; scheduledexit09:53, modeledexit09:54M1Open.
  Cửa ngắn28phút từ gợi ý pre-hedge30phút của NBER; riêng project, không
  code/preset hãng. Không cố fill đúng09:55spike hoặc bankTTM.
- Diagnostic prefix SELL cùng slot, **postfix SELL**09:56→10:24JST riêng và
  flatnull. Postfix không dùng kết quảprefix để chọn hướng/ngày hoặc ghép lãi
  hindsight. Bốn rules×2calendarmodels×2years×2costs=32books, không32edges.
- Strict role:29minutes09:26–09:54 hoặc09:56–10:24inclusive, bothsides.
  Missing/crossedholding quote → unknownplannedrow; không dùng futurequality
  làm eligibilityfilter. NoSL/equity/accountpath, không inventedfills/returns.
- BUY entryAsk/exitBid, SELL entryBid/exitAsk. Mid endpoint spread decomposition
  chỉ separate-sideproxy; firstquoteinminute không exactjointtimestamp/fill.
  SourceM1interval là approximation, không guaranteed latency hoặc benchmark.

## Đơn vị, chi phí và phép tính phải đối soát

Giá JPY/USD, pip0.01JPY/USD; fixed researchnotional100.000USD (đơn vị một FX
standardlot), **không leverage/account simulation hoặc riskbudget**.
Commission5USD/100k roundtrip declared; giữ reference slip0, stress0.4pip
roundtrip. Spread đã trả bằng Ask/Bid, không trừ hai lần; intradayfunding0.
Không actual targetbrokerfees, historicalcommission/currencyconversioncert.

PricePnLJPY=100k×sidefilldifference; slippageJPY=100k×0.01×slippips.
NetUSD=(PricePnLJPY−slippageJPY)/exitmid−commissionUSD.
Netpips=PricePnLJPY/(100k×0.01)−slippips−commissionUSD×exitmid/(100k×0.01).
Exitmid dùng quy đổi tiền đã realized, không làm tín hiệu/sizing/calendar.
Cashconversion tại mid là declaredapproximation, không actual brokerUSDconversion;
stress chỉ allowance, không đo actualslippage. SumUSD và sumpips là hai
mẫu số khác nhau; đối soát từngrow, không đổi aggregatepip bằng meanFXrate.

Report gross/spread/commission/slippage/net từngyear/rule/model, planned,
resolved/unknown/noentry và contributions/outliers. StrictannualN/A nếu có
selectedunknown; knownsubset không annualtotal. Null0financialPnl do không
exposure, nhưng giữ sourcequalitydiagnostic chứ không bảo null thiếu giá bịlỗ.

## Frozen gate / review / giới hạn

Primary nominal_business BUY được ưu tiên nextresearchstage khi cảhai stress
years strictknown/netUSD>0, >=35trades/year, không lỗi material; đây là triage,
không statisticaledge/prop chứng nhận. Sensitivitypositive chỉ là followupflag,
không passprimary. Không promote opposite/postfix hoặc retune clock/fees/calendar.

Sourcefullraw/native/Fraction review trước quyết định; synthetic currencies,
BUY/SELL, commissionconversion (110JPY/USD:5USD=0.55pip), actualdate vsnominal,
GoldenWeek2019May5previousApr26,duplicates/weekends,TokyoUTC, missingrole và
future-exitprice thay chỉPnL không quyếtđịnh. Separate financialoracle rebuild
32books, mutateprice/calendar/fees/count/authority/promotion đểreject.

Private `execution-v1/jpy-tokyo-calendar-v1/`, `jpy-tokyo-source-v1/`,
`jpy-tokyo-component-v1/`. Pins/protocol/code/config/raw/seals/rows/progress/
events/result/review/timings. Logs printboundedcounters, no secrets/tickspam.
Failedprefix giữ, khôngrestart chỉ vìobserver timeout; no migration/raw rewrite.
Source+compute/review timers riêng; existinghelpers, không engine/framework mới.
C1/C2 còn mở; có lợi nhuận ở component này vẫn cần risk/path/OOS/prop/forward.
