# ECB conference pilot: 3/4 ngày đạt, chưa đủ để mở financial trial

10/11/2026. [Protocol](ECB-CONFERENCE-SOURCE-PROTOCOL-20261110.md) freeze
`d552f3e` trước9GET, [method](ECB-POSTDRIFT-METHOD-ADMISSION-20261110.md).
EUS.IDX-EUR làCFD50stocks, khôngbroadEUROSTOXX hoặcexactbrokerquỹ.

| Event date | Pre quote/minutes/maxgap | Post quote/minutes/maxgap | Có locator sau60s? | Source gate |
|---|---|---|---|---|
|2019-01-24|43 /8of10 /121,901s|113 /10of10 /49,194s|Có|Không đạt|
|2019-09-12|1.082 /10of10 /11,048s|1.949 /10of10 /8,153s|Có|Đạt riêng ngày|
|2022-02-03|207 /10of10 /53,229s|1.067 /10of10 /6,045s|Có|Đạt riêng ngày|
|2022-09-08|206 /10of10 /36,181s|392 /10of10 /15,097s|Có|Đạt riêng ngày|

7/8windows đạt. Gate≥9populatedminutes vàmaxgap≤120s đãkhóa, không đổi thành
122s hoặc chỉgiữ3ngàyđẹp. Hai phútkhôngtick trongpre2019giữunknown; archive
khôngquote khôngchứngminh marketclosed/marketliquidity hoặcproviderbug.
Không tínhmedianchange/signal/tradingPnL hoặcfullcalendarbulk trongpilot.
Giữ nhữngquoteđãcó đểreview, khônggọingày2019“sai dữ liệu” chỉvìthưaquotes.

## Correctness và hiệu năng

- 29.337jointticks/146.685timestamp,BidAsk,volumefields khớpnative/integer
  0,001/separateFractiondelta. Full9hours, khôngquotesfilter/forwardfill;
  same-msordinal/order/year/UTC/grid/noncrossed/finite/volume/rawseals kiểm.
- Calendaroracle dùng explicitUTC cho4dates soBerlinhistoricalconversion;
  pre/posthalfopen, straddle13/14UTC tháng09/2022 vàentryexpiryinclusive
  khớpmọiavailabilityfield. Đã xửlýclock21/07/2022, khôngfixUTC+1quanh năm.
-4focusedtests đạt trướcrequests (0,001stestbody); actualprice/time/count/
  falseauthority/hashmutations reject. Arithmeticriêngnhưngsameagent/provider,
  khôngindependentfeed/brokercertification hoặcC1/C2fullacceptance.

| Phase thực đo | Wall | CPU |
|---|---:|---:|
|9sourceGET /0reuse|6,430s|0,656s|
|Fullraw/role review|1,070s|1,063s|
|Tổng hai phase|7,500s|1,719s|

Không gồm research/code/Git hoặcactualbrokerlatency. Collector/reviewerexit0,
lockgỡ/khôngjobnền; `admitted:false` là gateoutcome, khôngcrash.
0ownfeatures/returns/PnL/broker/model/2025+, catalogue92/58giữ.

Privatecampaignbase `execution-v1/ecb-conference-source-pilot-v1/` giữ
config/roles/metadata/rawcache/nativeexports/proofs/seals/manifest/snapshots/
events/progress/result/review/PID; `ecb-conference-calendar-v1.json`, saved
`prepare-ecb-conference-source-v1.cjs`, `review-ecb-conference-source-v1.py`.
ResultSHA`f5f6c1c6555443ae332bd0b70bc437e9236bfa41dc3289376e04b449ae471aae`;
reviewSHA`86fb22de2d4520ffd846eebd70b77faabda2ffb4876c3b51f062518cb32b27c1`.

## Quyết định

Chưa admit sourcepilot đểthiết kếfeaturetrial. KhôngtựtínhPnLtrên3ngày,
rerun9unchangedhours hoặcrelaxgate đểpass. GiảthuyếtpostECBchưa bịbácbỏ
vìchưađotínhiệu/lợinhuận;sourcegap khácstrategynegative.

Đã tìm được authorarchivedEA-MPD tạiGitcommit15dd019 (04/2025, mô tảupdate
tới12/2024), cósourceworkbook vàlicenseREADME. Chỉnhận
[sourceauditriêng](ECB-ARCHIVED-SURPRISE-SOURCE-PROTOCOL-20261110.md) đểxem
semantics/clock/availability, khôngdùngprocessedserieslấpbrokerquotes hoặc
admitlivefeatures. Officialappendix cócenteredcleaning/same-msmedian/minute
carryforward; đây khôngphépxửlýcausalđượcchứngminh tạifixedendwindow.
Giữoriginalpilotfalse; khôngmượnsourcekhácđểđổikếtluậnrawviewnày.

Hậu kiểm: nguồn được kiểmtrướccost/holding, chưa materialbug hoặcbottleneck
cầnengine/GPU/framework/skillmanager. ChưaGold/R092reopen/C1/C2 hoặcbroker.
