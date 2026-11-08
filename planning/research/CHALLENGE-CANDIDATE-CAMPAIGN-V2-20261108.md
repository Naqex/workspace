# Chiến dịch tìm ứng viên challenge — Goal mới, 08/11/2026

**Đang thực hiện.** Owner giao mở rộng phương pháp, tìm ứng viên đủ bằng chứng
cho challenge, đồng thời sửa correctness, cải tiến performance và dữ liệu khi
có nhu cầu thực. Goal mới đã active. Quyết định dừng B ở
[campaign trước](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) là lịch sử, không là
điều kiện tự hoàn tất Goal này. Giữ nguyên tài liệu/pins của các đợt đã freeze.

## Checkpoint hiện hành — 09/11/2026

[R076/R077 rest-of-day review](INDEX-REST-OF-DAY-RESULTS-20261109.md) đã xong:
1.006 cashday rows /995 resolved asset-days, primary stress không dương cả
hai năm. US5002019 giữ missing-entry unknown, không gọi known sum là full net.
NASDAQ2022 chỉ phí chuẩn dương. Gác exact components; catalogue 77 /58 /
25 native /9 controls, chưa challenge. Goal vẫn active.

8 tests mới +11 regressions, 28 synthetic cases và full Fraction/cost/census
review; 18 mutations bị reject. Shared primitives giữ 1.006 old rows/summaries
exact. Producer 19,237 s /review 14,132 s, chưa compute bottleneck đáng thêm
GPU/Rust. Tiếp [registered closing-tick calibration](INDEX-CLOSING-TICK-CALIBRATION-PROTOCOL-20261109.md):
8 source hours, chưa PnL. Không mass-filter/tune trên delay proxy chưa đo hoặc
promote controls. [R075/frozen source](US500-OVERNIGHT-REVERSAL-RESULTS-20261109.md)
và [strict FX N/A](NY-FX-PAIRED-LATENCY-RESULTS-20261109.md) giữ scope riêng.
Không repeat unchanged books, repin old manifests, own2025+ hoặc broker.

## Đích và cách biết đã đạt

Kế thừa **C1/C2** của campaign trước: ứng viên có lợi thế sau phí và đủ bằng
chứng cho đúng bước challenge; quá trình có protocol, causal inputs, kiểm
chéo số học/nguồn, trial history, prop equity/time-fit, prospective
reconciliation và bàn giao owner. Không hạ ngưỡng để tạo winner hoặc coi một
batch/admission hoàn tất là đạt mục tiêu. Không bảo đảm thị trường có edge.

FTMO/The5ers phải đánh giá riêng theo program và điều kiện hiện hành. Profile
10k/25USD mỗi lệnh và mốc so sánh 3/6/12 tháng kế thừa để nghiên cứu; chưa là
đề nghị mua challenge hay deadline cá nhân. Holdout 2025+, broker sends,
tài khoản/provider mới, trả phí và production vẫn có gate riêng.

## Baseline và các lát kế tiếp

Baseline: 53 hồ sơ/41 policy versions, chưa challenge-qualified. Giữ negatives
và [owner report](OWNER-EVIDENCE-REPORT-20261108.md), không chạy lại 624 cases
FX không đổi. Gold SMA50k là research survivor, chưa đủ time-fit/realism/OOS.

| Lát | Câu hỏi sẽ giải quyết | Đầu ra cần |
|---|---|---|
| Chuẩn hóa đầu vào đang dùng | Một file có hash có thật là đúng loại giá, giờ, side và nguồn không? | Reuse validators, metadata có version, hash/lineage, exposure, units và quality; áp fixture thật, kiểm mutation; không migration/raw rewrite |
| R026 hedge cổ phiếu cuối tháng | Có thể tạo tín hiệu tương đối EUR/US causal bằng proxy đang có không? | Source/clock/mapping admission trước outcome; ghi rõ proxy khác paper, dividend/adjustment unknown; không gọi Total Market là total return |
| Component trước bot | Với recipe được khóa, tín hiệu có giữ economics sau phí qua hai giai đoạn không? | Protocol trước outcome, các ngày thiếu vẫn có mặt, baseline/control và uncertainty; không claim account PnL từ price component |
| Qualification | Survivors có giữ được sau causal fill, prop equity path và dữ liệu chưa dùng không? | Exact C1/C2 review, chỉ affected reruns, đúng permissions; owner handover dễ hiểu |

Mỗi lát có phạm vi hữu hạn; kết quả âm dẫn tới hypothesis mới có lý do, không
đóng Goal mới bằng kết luận B của đợt cũ. Lưu timing/status/log/attempt và
quyết định trước/sau tại artifact/protocol owner. Sau batch có kết quả mới,
hậu kiểm gọn; chỉ profile hoặc dọn khi có bottleneck/phần thừa đã xác minh.
Không xóa evidence, không thêm dashboard/ledger cạnh tranh Paperclip.

## Lát đang triển khai

[R026 continuation](R026-RELATIVE-EQUITY-CONTINUATION-RESULTS-20261108.md)
đã terminal/reviewed:3/4năm mới âm, không đạt; gác exactpriceproxy, không
rescue bằngSL/clock/side. [R010 source results](MULTI-ASSET-TREND-DATA-RESULTS-20261108.md)
đã phân rã data blockers:monthlyhistory84/84 từ2018, ATRfullsessions chỉ32;
asofcap120s không tăng140/144endpoints. [Monthly results](MULTI-ASSET-TREND-RESULTS-20261108.md)
đã hoàn tất4books/review:primaryreference−1.138,18/stress−3.519,01USD trên10kproxy,
khôngretained. Dataset864records cósource/clockreview và tái sử dụng cho numeric
1,416s; không hạ phí hoặc tăngleverage cứu outcome. Bước tiếp: cơ chế holding
ngắn có data/method rõ và khác các exactversions đã gác, freeze trước số mới.
Dùng repo skills hiện có; không tạo một skill quản lý toàn bộ khác.
[Gold session results](GOLD-SESSION-COMPONENT-RESULTS-20261108.md) thêmR054/R055:
cả2negative saufees/0of15stressyears dương, khôngretained. Catalogue hiện55hồ
sơ nhưng vẫn41accountpolicies; không tăngcount bằngpricecomponents. Lát tiếp
ưu tiên full-historyPreECBprice robustness trước thiết kế riskwrapper khác.
[PreECB long results](PRE-ECB-LONG-PRICE-RESULTS-20261108.md):đã terminal/reviewed,
stress12/13years dương/cả4blocks dương; đủ ưu tiên đăng ký1wrapper theo scale
holding-session nhưng chưaSL/account/prop/OOS. Giữ risk25USD,không grid/giữlot
khi nớiSL; xem kết quả này để tiếp, không khởi động lại monthly/gold negatives.
[Recent continuation](PRE-ECB-RECENT-PRICE-RESULTS-20261108.md) đã thêm2023/24
same-clock/cost explicitrawmode:+187,1/+184,9stresspip. Combined14/15positive
years/cả4blocks dương; đủ ưu tiên1riskwrapper, chưaaccount/SL/prop/OOS.
[R056riskresults](PRE-ECB-SESSION-RISK-RESULTS-20261108.md) đã chạy1wrapper
theoholding-sessionRMS20x2/risk25:3.171trades/cost,+1.535,95/+1.078,12USD
nhưng2/4stressblocksâm,khôngretained. Khônghạgate/SLgrid;catalogue56records/
42researchpolicyversions. Lát tiếp sourceadmissionGBPUSD/AUDUSDH1 với
USDquote/existingDukascopy trước cơchế/portfoliobudgetchung,khôngbroker/holdout.
[H1sourcepilot](FX-H1-SOURCE-RESULTS-20261108.md) đãđạt144bars/720Fraction
checks/bridgeEURUSD7.971ticks;chưahistory/PnL. Bướctiếp đăngkýsourcehistory
2010–24GBPUSD/AUDUSD trước numeric,không sourcepadding/nativefillclaim.
[H1historyresults](FX-H1-HISTORY-RESULTS-20261108.md) đãreview60books/
373.652bars/1.868.260checks;719/720months/30crossedhours,fulljointadmission
inconclusive. Recoveryreuse15books vàvolume-roundingmetadata giữrõ. Tiếp
registeredendpointcomponents trênOpenroleshợplệ,giữmissing/crossedrows;
chưaeconomicoutcomes,khôngtrade/newprovider/holdout hoặcR056retuning.
[TwoFXresults](TWO-FX-PRE-ECB-COMPONENT-RESULTS-20261108.md) đãterminal/reviewed:
R057GBPUSDkhôngđạtblock/yearretention dùstresssumdương,R058AUDUSDâmrõ.
Catalogue58records/42researchpolicyversions,khôngtăngpolicycount vìcomponents.
Lát tiếp methodadmissionkhácprefixUSDshort;khôngcontrolsrescue/SLgrid hoặc
tảidata/thêmengine khôngcâuhỏi. GoalC1/C2active,chưachallengecandidate.

[Local-flow hai FX](LOCAL-FLOW-TWO-FX-RESULTS-20261108.md): R059/R060 đã terminal và review, cả hai không đạt frozen retention. Catalogue60/42; Goal vẫn active, chưa challenge candidate. Không thêm wrapper cho hai exact recipes. Lát tiếp admission relative/cross-market signal khác fixed-hour unconditional flow, reuse nguồn hiện có và giữ costs/funding trước PnL.

[R033 pilot](FX-CROSS-SECTION-PILOT-RESULTS-20261108.md) đã terminal/review:132monthlycontributions×4books, gross/net negative, không retained. 864rows chuẩn hóa role/known-at/source/units, giữ2missing panel rows ngoài window đã đăng ký; chưa account/prop/OOS. Catalogue60/42. Bước tiếp admission R019 stateful break→retest có expiry/invalidation so parent R015; không tune universe/funding/control để cứu R033. Goal vẫn active.

[R019 retest](PRIOR-DAY-RETEST-RESULTS-20261108.md) đã native implementation Trader83731fc8 và terminal paired stage1:8books, stress2019−5,16/2022−452,64USD, không giữ. Parent4books exact, preflight đầy đủ trước outcomes,1.268decisions/876trades kiểm lại. Catalogue60/43/25native; Goal active/chưa challenge. Lát tiếp NASDAQ100 method/source/cost admission trên existing provider, fixture nhỏ trước history/numeric; không hạ fees hoặc tune retest3 rescue.

[NASDAQ100 source/history](NASDAQ100-HISTORY-RESULTS-20261108.md) đã terminal/reviewed:56sources/8books/27.512bars,137.560checks, không strategy PnL. Catalogue61records vẫn43versions/25native, R061hypothesis chưa code. Tiếp exact economic/market/cost/funding/gap contract và fixtures trước numeric2019/2022; source admission không thay target broker specs, cleanOOS hoặc C1/C2.

[NASDAQ H4SMA results](NASDAQ100-H4-SMA-RESULTS-20261108.md): R061toolingprototype/13fixtures,4books/5.124decisions/42trades/5mutations reviewed; notretained (2019stress+240,59USD,2022−77,36,7/14closed). Gaps and targetcosts unverified; không challenge. Catalogue61records/44versions/25native. Next distinct-mechanism admission before outcomes, không SMA/ATR/costgrid hoặc épwinner. V1wronghash preflight preserved,0numeric;v2terminal0.

[R035 formation](FX-PAIR-FORMATION-RESULTS-20261108.md) terminal/reviewed:8sourcebooks/519calendarrows đủ nhưng fixedcointegrationp2018=0,2358/2021=0,2696; không giữ để economicdesign, không accountpolicy/PnL mới. Decimal80log/OLS/residualADFt/5mutations reviewed; inferencecurves cùnglibrary. Literature overnightdrift update và sources/supply-chain ghi ởmethodreport; isolatedstatvenv không productmutation. Tiếp scheduledmacro-event primarymethod/calendar admission, không pairgrid. Catalogue61/44, Goal C1/C2 active.

[R062FOMCcomponent](FOMC-NASDAQ-COMPONENT-RESULTS-20261108.md) đãterminal/reviewed16events/32windows/64costcases, khôngretained vì2019stress−0,12USD/unit vàdelta−103,00, dù2022dương. Noaccountpolicy/newtradeauthority;catalogue62/44. [Cashsessionfixture](NASDAQ-DAILY-REVERSION-METHOD-20261108.md) reuse2pilotM1days, đủ390minutes/side/day+16:01endpoint,780presencechecks/4mutations;chưaindicator/PnL/fullhistory. Tiếp Nasdaqdailyreversion method/holiday/earlyclose/M1history admission, không H1cash09:30 approximation hoặcR062clockrescue. Goal C1/C2active.


[NASDAQ M1 source](NASDAQ-M1-HISTORY-RESULTS-20261108.md) đã terminal/reviewed8books/1.704rawdays/7.980.630checks, đủ economic registration. [R063cashRSI](NASDAQ-CASH-RSI-COMPONENT-RESULTS-20261108.md)8cases reviewed, stress2019−2,97/2022−486,42USD/unit, không retained; noSL/account/prop/OOS. Batchvalidate reuse giữ exact8case outputs, compute46,617→12,364s,12tests; không rule/cost/verdict đổi. Catalogue63/44/25native, Goal active. [Next method](NASDAQ-INTRADAY-MOMENTUM-METHOD-20261108.md) reuse source, first→last-half daily momentum khác R063, chưa newoutcomes. Không tải history lại hoặc retune RSI để cứu negative.


[R064 first→last-half](NASDAQ-INTRADAY-MOMENTUM-RESULTS-20261108.md) đã terminal/reviewed503rows/413signaldaypairs/1.652costcases; primary stress2019−481,64/2022−1.969,99USD/unit và kém longcontrol, khôngretained/noaccountpolicy. Source reuse không download;9tests+6helperregressions/6mutations đạt, producer9,756s/review9,992s. Catalogue64/44/25native, Goal C1/C2 active. Tiếp [QQQ opening5 method](NASDAQ-OPENING5-ORB-METHOD-20261108.md): authorPDF có exact first5direction/SL/10RTP, adaptation riêng cần freeze risk25USD/clock/halfday/ambiguity/unknownstate trước outcomes; không đảo R064 hoặc copy1%risk/no-slip.


[R065/datarevision09Nov](NASDAQ-OPENING5-ORB-DATA-REVISION-RESULTS-20261109.md) thêm1modeledpolicy từprimaryopening5rule:source-onlyM1v1 dừngunknown2019/2022,12tests/22Fractionfixtures/full8bookreview.8rawtickhours so1.028.380fields cho22missingminutes,15noquote/7cóquote nhưng2commonOpenmismatch nênoriginalpatchgatefalse. Newregisteredwholehourview raw/Fraction480fields đạt,sourceoutsideexact;replay2022 vàreuse2019 cho243closed/+714,71reference/+568,12stressUSD,2019vẫnunknown.191tradeprefix/nullstateexact, twoyeargate khôngrelax. Catalogue65/45/25native;Goalactive/chưachallengecandidate. Tiếp alternateofficialarchive sourceadmission2019firstgap, không tweak risk/TP/cost hoặc own2025+exposure.
