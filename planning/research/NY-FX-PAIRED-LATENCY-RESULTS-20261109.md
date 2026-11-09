# R072/R073: so độ trễ đã chạy, annual PnL vẫn chưa xác định

**Chưa có ứng viên challenge.32books hoàn tất và kiểm chéo, nhưng16nonnull
books giữunknownexposure vì missingheldminute.** Không gọi partialcash là
annualprofit hoặc strategyfail.16nullbooks0lệnh/0PnL/knownflat.

[Protocol](NY-FX-PAIRED-LATENCY-PROTOCOL-20261109.md) `1047a5d` trướcfullsource/
PnL, implementation`56ea354` trước outcomes;7parent+5M1focusedtests đạt.
16synthetic producer/Fractioncases khớp trước actualPnL; v2syntheticreceipt
lặp vì thêm reviewer candidateidentitycheck, không thay chiếnlược hoặc marketfit.

## Những gì đã thực sự biết

| Policy / năm | Lệnh đóng trướcunknown, mỗi cost | FirstunknownUTC | Annualnet |
|---|---:|---|---|
| R072 reversal15min2019 | 207 |20/05/2019,17:54| N/A |
| M1reversal60min2019 |196|20/05/2019,17:54|N/A|
| R073 momentum15min2019 |185|20/05/2019,17:54|N/A|
| M1momentum60min2019 |185|20/05/2019,17:54|N/A|
| R072 reversal15min2022 |3|05/01/2022,18:42|N/A|
| M1reversal60min2022 |27|15/02/2022,18:35|N/A|
| R073 momentum15min2022 |2|05/01/2022,18:42|N/A|
| M1momentum60min2022 |25|15/02/2022,18:35|N/A|

SameMA4/SL1,5TR14/risk25USD/costs; bothlags dùng cùngstrictM1→H1features,
sameM1matching/sizing/cash. Khôngannualdelta để kết luậnlatencyadvantage.15min
cóthểgiữvịthế ởphút mà60minchưavào nên firstunknown khác nhau; khôngbugđã
chứngminh. OldH1R070/R071negative giữ nguyên vàkhông thay bằngM1numbers.

FullreviewFraction riêng dựng H1source,4priceMA/TR/signals,quantity/SL,
M1protectivepaths/costs/cash/unknown/endstate/census cho32books;1.660closedpaths
gồm lặpqua costs.5actualmutations entry/quantity/net/count/authority reject.
Sameagent/provider với implementationkhác,không independenthuman/modelsignoff,
khôngedge/prop/OOS/brokerqualification.

## Chuẩn hóa nguồn: đã hoàn thành gì?

- 4source-onlyexports2019/2022BidAsk,1.460dailyURLs;1.492.264explicitM1bars/
  7.461.320price-volumefields và timestamps raw/canonical/Fractionexact.
  274.370paddingrows bịloại theo sourcemembership,không lọcvolume0 tùyý.
  Common side presence/crossed quality giữtrongreview,khôngsourceimputation.
- Source-onlypricefidelity không là fullcontinuousquotehistory.52emptydays/
  side2019,53/side2022 giữ đúngemptyraw,khônggắnnhãnfeedoutage hoặcmarketclosed.
- Reviewer v1 lỗi khi đọc baseprice`null` trước khi xử lý rawarraysrỗng.
  Giữ`review-v1-failure.json`/oldcode. Reviewerv2/isolatedoracle mới xử lýempty
  nhưcanonical đã có; malformedempty vẫnreject. Raw/producersnapshot/output
  khôngđổi,khôngdownloadlại. Đây là reviewerfix,không strategy/datarepair.
- Additionaldayscope review kiểmđúng1.460URLs/year/side/rawdayanchor/lasttime;
  year/side/timestampmutationsreject. Không sửa oldsealed pins để reuse.
- Native source/policy/contracts,unitsUTCms/minutestart/closeknownafter+1min/
  grid0,00001/sourcehash/protocol/codeversions đềuđược giữ; không thêm DB/RAG.

## Đã điều tra10phút thiếu bằng nguồn tick

[Tickprotocol](NY-FX-M1-GAP-TICK-PROTOCOL-20261109.md)`cd39fe1` trước fetch.
Source-onlycensus chọnmọiweekday cócausalfeature-readydecision vàpotential
heldwindow, khôngchọntheoPnL/side/trade.10missingminutes/10days/10hours,
không chỉ3firstunknowns củaannualbooks.

10tickhours đãraw/Fractionreview:15.379jointticks/76.895fields,1.180commonM1
sidebars/4.720OHLCfields exact,0conflict;price/time/order/hash/authoritymutations
reject. **Cả10phút thiếuM1 cũngkhôngcótick trongarchiveđãđọc.** Maxsourcegap
trongcáchours61,538→134,405s. Không có nguồnpriceđểpatch; proposedpatchesempty,
admissionfalse. Không chứngminh broker/thịtrườngkhôngcóquote hoặcgiáđứngim.
Khôngclearunknown hoặcrerunnumeric sau tickreview này.

Điềunày phânbiệt **source không có priceevent** với decoderlàm mất bar. Trong
modelstrict hiện tại, thiếuheldminute vẫnfreeze nhưprotocolđãkhóa. Nếu thử
observed-event model (không inventbar/fill/mark lúc khôngquote,protectivefill ở
nextobservedquote), phải đăngký modelassumptions riêng và giữ strictunknown.
[Nautilusbacktesting](https://nautilustrader.io/docs/latest/concepts/backtesting/)
mô tả xử lýhistoricaleventstream; không chứngnhận observed-feed silence là
fullmarketcontinuity. Đây mới là hướng cần methodreview, chưa implementation,
outcome,permission hoặc workaround để tạo winner. Không đổi mãđangpin.

## Thời gian và hậu kiểm

| Lát | Wall / CPU | Quyết định |
|---|---|---|
| NewM1history1.460URLs |569,796s /15,999s|12hits/1.448misses/0unknowncache; network là chính; nguồn đã giữ để reuse|
| Sourcev2raw/Fractionreview |107,776s /107,328s|7,46triệufields;khôngrerun khihash/code/scopenguyên|
| ExactdailyURLscope |1,378s /1,359s|1.460rawdaysvà3mutations|
| Numeric32books |22,167s /21,781s|Không cần GPU/Rustrewrite;affectedbooks unknown giữ nguyên|
| FinancialFractionreview |31,923s /31,781s|Khôngsimulationrerun|
| Source-onlygapcensus |8,573s /chưaghi|Dùngsourcefeatureavailability,khôngPnLselection|
| Tick10hours |17,015s /xemsource result|Khôngannualdownloadlại|
| TickFraction/M1bridge |3,996s /chưaghi|Khôngsourcepatchapproved|

Không cộng research/authoring/v1failure/review vào một end-to-endbenchmark;
phần chưađo ghiunknown. Không so22s vớioldfulltick53phútvìkhác workload và
realism. Hậu kiểm củng cốempty-sourcehandling/sourceclock,không bỏquality
đểtăngtốc. Không jobcònsống saulượt này;source/numeric/reviewer đềuterminal.

## Artifacts và đường tiếp

Privatebase`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.

| Locator | SHA256 |
|---|---|
| `execution-v1/ny-fx-timing-M1-history-v1/result.json` |`a303848a913bf523aaee8320f07ac6bcadad5d52423d7a57c2277ae1c5469538`|
| Source `review.json` |`7a83b1098263b54ec87c27671bfda02d19ba6a93d523e8f53ba7465fa18b04cb`|
| `execution-v1/ny-fx-paired-latency-v1/result.json` |`3c8779dc563e1c476b8ca32f70a62f0aba2377c7dddac3ac885c448e930751f6`|
| Numeric `review.json` |`44f3901c37eb81e70ddc9cf7df899929e5cc382deb30342f8139e7431b86d128`|
| `execution-v1/ny-fx-M1-gap-ticks-v1/result.json` |`0052666c3ec17c9e68e3b9f4bb1b3e15f02850e227e6d8f117acfd671753159a`|
| Tick `review.json` |`e0243ee2e3d03cd3d09753f7779b57ef2ff387cf91339ab2146a18b6ca8ce76e`|

Đúngsource reviewer là`check-ny-fx-timing-M1-history-v2.py` với
`ny-fx-timing-full-source-oracle-v2.py`;additionaldayreview vàemptyfixture trong
sourcefolder. Driver`run-ny-fx-paired-latency-v1.py`,reviewer cùngprefix;fullpins/
snapshots/status/events/books vàcensusgiữ riêng. Không gọisourceproducerv1pin
oldreviewer nghĩa v1review đãpass; v2receipt giữ exactcurrentreviewerhash.

**Tiếp:** method admission observed-event/uncertainty model riêng: còn thiếu
quote khôngđồngnghĩagiákhôngđổi; khôngsửafrozenstrictmodel,khôngmởnewyears hoặc
tảilạiannualhistory. Nếu khôngbiệnminhđượcsource/gapassumptions thìgác version
inconclusive vàchọncơchếkhác. C1/C2Goalactive,chưachallenge. Catalogue73records/
54policyversions/25native/7controls: thêm2lag15policies và2lag60M1source-model
versions củaR070/R071,không54edgesđộc lập. No brokerage/holdout2025+/runtime/
MT5/globalconfig/skill/database mutation. Existing skillsđủ,khôngtạoskillchomộtcase.
