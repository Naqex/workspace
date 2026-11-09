# M1 timing fixture đạt trong4ngày, chưa phải backtest mới

Theo [protocol](NY-FX-TIMING-SOURCE-PROTOCOL-20261109.md) commit`9ed63a1`,
đã fetch12URLs cho Jan6–8/Mar10–12,2019. Targetweekdays Jan7/8 vàMar11/12
được chọn trước nguồn theo winter/DST; Sundays chỉpastwarmup. Không chọn theo
kết quả, không tính returns/PNL hoặc sửaR070/R071negative.

| Kiểm | Kết quả |
|---|---|
| Nativeexpanded /explicit /padding rows | 17.280 /12.118 /5.162 |
| Raw/canonical/Fraction price-volume fields | 60.590khớp, timestamps/census/grid/source hasheskhớp |
| Target action/exitminutes | 9/9mỗi ngày, cảBid/Ask; tổng36targettimestamps |
| Heldminute presence10:15→15:00NY | 286/286mỗi ngày/cả2sides; khôngcrossedOpenClose |
| Featurehour coverage | 144side-hours đều60explicitminutes, khôngpad/asof |
| M1OHLCaggregate so parentH1 | 144side-hours/576fields exact,0discrepancy |
| Mutation rejects | price/clock/count/hash/authority |

Source2,230s;fullreview0,906s/CPU0,906s. OnewriterPID1692terminal0; không job
đangchờ, không retries/source-auth/provider mới. Source-grade pricepresence
không actual jointquote/fillability/wholehistory/PIT/feedrevisioncertificate.
4targetdays khôngđủedge/screening/prop inference. Quotevolumekhôngorderflow.

Source/private tree`execution-v1/ny-fx-timing-source-fixture-v1` trong
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
producer`prepare-ny-fx-timing-source-fixture-v1.cjs`, reviewer
`check-ny-fx-timing-source-fixture-v1.py`. Có12seals/rawcache,config/manifest/
snapshots/progress/events/quality/H1comparison/result/review.

ResultSHA`8918dc6ba3a1b68479c703323ad0ee0ad1a7baffe78502676f1f2b4ae3fdd65e`;
reviewSHA`c41567fc0bbb10e0911aca43d629c834576fc664d230d8772a714598034cb4ce`;
reviewerSHA`5eb17546a18c6c3a975defc514d37195bcc0ba7a32d00397937a7bd66990737f`.
Fullcanonical/native reviewer reuse hiện có, Fractiondecoder riêng; sameagent/
provider, chưa independenthuman/modelsignoff. No strategy/model/broker/holdoutcalls.

**Decisiondelta:** timing-source fixture từpending→admittedforregistration,
chưa admit fullhistory hoặc policy. Bước tiếp khóa pairedM1source/history và
32book experiment trước newPNL; cùngMA4/SL/risk/cost/signals, khác lag15/60,
không quy M1/H1resolutiondelta cho latency. Catalogue vẫn71/50/25native.
Không bottleneck CPU cầnprofile/GPU/framework/skill mới; không xóa dữ liệu.
