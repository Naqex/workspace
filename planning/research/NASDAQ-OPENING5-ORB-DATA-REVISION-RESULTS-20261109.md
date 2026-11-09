# Opening5: năm2022 đã đủ sổ;2019 vẫnunknown

Rà09/11, campaign08/11. Tiếp [interimv1](NASDAQ-OPENING5-ORB-INTERIM-20261108.md)
và [derivedsourceprotocol](NASDAQ-TICK-DERIVED-HOUR-PROTOCOL-20261108.md).
Giữ exactR065code d5aad5b/risk25USD/TP10R/latency/costs, không strategyretune.
**Chưa đạt two-yeargate, chưa challengecandidate hoặc cleanOOS.**

## Nguồn mới có scope và semantics rõ

Whole15UTC18Oct2022 được dựng từ34.353rawjointticks:60minutes/120sidebars,
480OHLCfields khớp separateFraction rawaggregation; first/lasttick ordinal,
volume exactreceipt/float conversionerror0 được kiểm. Mọi field ngoàihour giữ
exact; tronghour thêm7minutes và đổi2Openfields15:31 theo firstjointtick.
OldOpen có observedvalue trongminute nhưng không phảifirsttick, không gọi
stalepricebug/decoderbug đã chứng minh. Oldmissing-onlypatchgate vẫnfalse.

Sourceview admission riêng đã đạt,8mutations reject.2mixed2022books mỗi bên
342.783rows, parent342.776; không overwriteoldraw/books/pins. Có perminute
rawhash/ticktimes/volumeunits/known-at và old→newdeltas; source kiểu mixedM1,
không giả oldexplicit-M1proof áp cho quote-derived rows mới. Không fetch lại.

## Sổ tiền sau replay affectedyear

Initial10.000USD, planned25USD/entry, không compound. One researchunit worth
1USD/point, sourceBidAsk/declaredslips0,25/0,75,commission0; chưa targetbroker.

| Năm | Lệnh đóng | Phí chuẩn,USD | Phí cao,USD | Trạng thái |
|---|---:|---:|---:|---|
|2019|16trướcgap|+186,21partial|+136,98partial|AnnualequityN/A, giữunknown|
|2022|243|+714,71(+7,1471%)|+568,12(+5,6812%)|Fullmodeledbook knownflat|

V2reuse4case2019 exactbytes/review cũ; không rerun, clearstate hoặc bỏyear.
2022replay4cost/controlbooks, sourcecalendar/rules/financialcode giữnguyên.
191closedtrades trước affectedposition và mọiearliersessionrow exactv1;
nullfullfinancialstate exact. Suffix được replay đầy đủ, không sửa PnL bằng tay.
4newbooks qua same frozen Fraction firsthit/size/ledger oracle;3suffix/
authority mutations reject.8bookcensus giữ đủ, gate2019inconclusive/2022pass
cho furtherresearch **trong yearscope**; overallretained vẫnfalse như protocol.

## Time-fit và concentration diagnostic, không proppass

Đăng ký read-onlydiagnostic sau annualnetđãexposed, không blindtrial mới.
Mỗi dòng là prefix cùngJan1-start account, không resets hoặc actualphase2.

| Prefix | Closedcashnet chuẩn,USD | Closedcashnet cao,USD | Closedtrades |
|---|---:|---:|---:|
|3tháng|+109,97|+83,15|59|
|6tháng|+464,21|+395,47|117|
|12tháng|+714,71|+568,12|243|

63wins/180losses, winrate25,93%, longestlosingstreak13 ởcảcosts. Mean returns
không là winrate hoặc probabilitypass.5lệnh dương lớn nhất chiếm23,05%/22,85%
tổng positivecontribution. MaxclosedbalanceDD595,35/595,93USD, **không** là
intrabar equitydrawdown hoặc daily/overallfirmbreachproof.

Maxclosedprofit+1.116,09/+981,44USD; reference chạm đường+1.000USD ngày01Nov,
stress chưa chạm. Đây là tiền đã đóng của một modeledaccount, không actual
challengepass hoặc phép chứng minhphase2. Không tăng risk để vượt vạch.
Fractionchronologicalcash/Decimalprefix checks khớp, không closureinterval
cắt các3/6/12monthboundaries. Source/account/policy dùng lại, không simulatorrerun.

## Engineering và audit locators

| Lát | Walltime |
|---|---:|
|Buildnewsourcehour/mixedyearviews|11,265s|
|Fullnewsource review|4,221s|
|2022affectedreplay +reuse2019|7,777s|
|2022Fractionaccount review|5,544s|

Không speedupclaim vì khác workload. Source correction đã có version/fidelity
proof; khôngcần thêm framework/GPU/cleanup.12unit/22Fractionwirefixtures đã
đạt trướcv1numeric, sourceview8mutations và newaccount3mutations dùng lạiexact
kernel; không chạy lại unchangedtest/simulation chỉ để tăngcounts. No native
product/runtime/globalconfig/skills/provider/account/broker/holdout mutation.

Privatecampaignroot: `nasdaq-tick-derived-hour-v1` resultSHA
`fcb1698e819f980c7ceee4b77756955a2b031ce4d42ba941325f0287e7758236`;
reviewreceiptSHA`f2feb2767dc5029854100d4ed62597b207adc7c710b629714288cf69045b4b67`.
`nasdaq-opening5-orb-v2` resultSHA
`966d29d2899bde62c0ee43451bb3ccb6b66d61a7c53b72fa5102398f0ef0365a`;
reviewer codeSHA`d782655d23e453905fd8ede5d73cd8ef94aca12a492947202238a034b60c0860`.
`nasdaq-opening5-2022-cash-diagnostics-v1` giữ registration/prefix/cash results.
PIDs25656/7808 vàreviewers terminal0; không worker chờ.

**Tiếp:** source admission của alternateofficialarchive transport cho đúng2019
firstgap trước khi kết luận không thể khôi phục. Cần primaryURL/format/pin và
boundedfixture trước fetch/decoder; không research lại toàn literature, không
quote-interpolate hoặc đổi strictunknownpolicy sau outcome. Nếu archive cũng
thiếu, giữ2019inconclusive và đánh giá phương pháp/data path tiếp có ghi lý do,
không loại năm này để tựpass. CleanOOS/prop/forward/handover còn mở.
