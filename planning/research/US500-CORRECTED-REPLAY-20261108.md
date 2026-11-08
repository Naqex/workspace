# US500 sau sửa loader — kết quả hiện hành

**RSI3+IBS được ưu tiên nghiên cứu sâu hơn; chưa đủ đề xuất challenge.**
[Correction](INDEX-UNFILTERED-SOURCE-CORRECTION-20261108.md) giữ nguyên
[noise14 rules](US500-NOISE-STUDY-20261108.md), [daily rules](US500-DAILY-REVERSION-20261108.md),
risk và costs; chỉ sửa materialinputfilter. Bảngfilteredcũ giữhistory.

| Policy | Năm | Net chuẩn / stress USD trên10k | Entries /scenario | Vị thế cuối |
|---|---|---:|---:|---|
|Noise14|2022|+181,19 / +117,61|156|0|
|Noise14|2023|−158,16 / −250,70|153|0|
|Noise14|2024|−156,91 / −239,22|147|0|
|IBS02hold|2022|+68,82 / +43,33|44|0|
|IBS02hold|2023|−51,24 / −87,02|39|0|
|IBS02hold|2024|+102,44 / +71,15|38|0|
|CutlerRSI3+IBS05|2022|+38,25 / +21,09|25|0|
|CutlerRSI3+IBS05|2023|+25,72 / +6,43|17|0|
|CutlerRSI3+IBS05|2024|+93,92 / +77,77|17|1, gồmfloating|

Đây làannualbooksriêng,khôngcontinuousaccount/CAGR/certifiedpropDD. RSIstress
tổng+105,29USD trên3books10k,không+105,29USD/năm. 59entries/58closed/1open
perscenario là mẫu nhỏ; selection/trials/cost/funding/nativebroker/prop/forward
cònthiếu. Khôngtăngrisk hoặc mua challenge. Noise14/IBSkhôngretained;không
hardrejectfamily vì3năm. Mọioutcomeâm/dương đượcgiữ.

## Dữ liệu và kiểm chứng

Canonicaldecode24quarter-sides từsamecache/package1.51.1,explicitignoreFlatsfalse,
networkdenied/0calls,9,687s; source-responsehashes/parentmanifest giữ ngoài repo.

| Năm | M1 rows/side cũ → mới | Cashphút có/dựkiến |
|---|---:|---:|
|2022|341.682 →435.596|97.710/97.710|
|2023|332.236 →434.687|97.094/97.140|
|2024|335.016 →439.334|97.740/97.740|

2023còn46missingcashminutes cuối halfday24/11,khôngtựfill. Gaps12/108/62
trước đây phầnlớn làloaderfilter,khôngfeedoutageđãxácminh. Volume0khôngchứng
minhquote/tradefillable; giữproviderbarsvàchỉclaimmodeledM1. Reviewergiờreject
missing/trueignoreFlatsmanifest trước nhậninput. Guardkhôngtựinvalidate QDM/
ticks khôngdùnglibraryM1default này. UpstreamH1/D1rangekhôngchứaticks làissue
riêng: [oracle](INDEX-DAILY-RANGE-ORACLE-20261108.md), chưađượcnhậnchoPnL.

9books×2costs+9nullcontrols122,391s gồmquality/load/results. Cả9children đã
qua checkerDecimal riêng:cost/funding/mark/quantity/SL/quotes/cash/source/raw
snapshots/seals khớp;nullcontrols0. Sameagentimplementationreview,khôngđộc lập
human/modelsignoff hoặcwholeproductacceptance. Oldattempt/protocol/source giữ
nguyên,khôngrewritegiá/rules/ngàyoutcome. Private`execution-v1/us500-unfiltered-m1-v1`
và`us500-corrected-replay-v1` giữcanonicalinputs/results/reviews/events/progress.

`zero-volume-fill-review-v1.json` kiểm cácentry/exittrongstresscả9books:
**0entry/exit cócảhai sidevolume0**. Dođó correctedfillsetnày không bịđổi sang
khớplệnhtrênplaceholderbarhai side0. Khôngchứngminh từngM1filllàobservedtick;
volume0bartronghistoryvẫncầnrõsource/quotevsvolume semanticschoextensions.

## Tiếp tục

RSI3+IBS05frozen chuyểnhistoricalextension/uncertainty/selectionreview;chỉkhi
đủmới đăngkýnative/tick/prop/time-fit/forward. [LongM1V5](INDEX-HISTORY-PER-REQUEST-RECOVERY-20261108.md)
tiếp dữliệu đãcache bằngnativecomponents vàboundedper-requestrecovery;không
shortcutupstreamD1range để épnhanh. Exacthypotheses dài hơn phảifreeze trước
PnL. C1/C2chưađạt,checkpointkhông làdừngcampaign.2025+closed,zeroorders/models.
