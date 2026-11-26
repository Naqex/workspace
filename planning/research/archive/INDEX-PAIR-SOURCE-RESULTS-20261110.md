# S&P–Nasdaq: đủ 503 ngày mẫu cho bước kiểm quan hệ

10/11/2026. [Protocol](INDEX-PAIR-SOURCE-PROTOCOL-20261110.md) freeze`54c6818`
trước history; [method](INDEX-PAIR-METHOD-ADMISSION-20261110.md). Source-only,
chưa thống kê hoặcPnL. Hai CFDproxy, không futures/ETF/targetbroker execution.

| Formation year / asset | Explicit H1 mỗi side | Bid-only/Ask-only/crossed O-C | Planned sample |
|---|---:|---|---|
|2018 USA500|5.250|0/0/0|251/251fourroles|
|2018 USATECH|5.249|0/0/0|251/251fourroles|
|2021 USA500|5.923|0/0/0|252/252fourroles|
|2021 USATECH|5.923|0/0/0|252/252fourroles|

Sample16UTCH1Close/known17UTC theo503businessdates đãkhóa, không bỏ ngày.
Year-sourcejointpresence chưa chứng minh everydesiredminute/calendartrading,
simultaneousBidAsk hoặc executablefills. Onehour2018 khác presence giữa hai
assets ngoài sample; không ép bằng padding. Cảhai samples admitted cho bước
**đăng ký statisticalprotocol**, không account/edge/prop hoặcPnL.

96rawmonthsideinputs/8books,44.690explicitbars và223.450OHLCVfields khớp
canonicalDecimal/separateFractiondelta.24.894nativepaddingrows bị loại;
explicitvolume0 vẫngiữ. Fullmonthyear/instrument/side/overlap/proof/seal/
grid0,001/OHLC/timeorder/bounds/rawhash/finalpins kiểm, source không bịrewrite.
8oldNASDAQNovDecraws exactseed/cachehit,88GET mới; không đếm olddata làsource
mới hoặcnewindependentobservations.

8syntheticsamplechecks vàactualacceptedH1fixture/offgridnegative trước fetch;
5actualmutations price/time/count/hash/falseauthority bịreject sau source.
Reviewer arithmetic độc lập nhưngsameagent/feed; khôngindependentfeed hoặc
statisticalcertification. No-gap sample không làm actualbrokerterms known.

| Phase | Wall | CPU |
|---|---:|---:|
|Collect96rawsources (88new/8reuse)|43,713s|1,391s|
|Full source/sample review|3,660s|3,609s|
|Tổng hai phase|47,373s|5,000s|

Không research/code/Gitwalltime. Collector/reviewerexit0 vàterminal,lockgỡ,
0strategy/returns/PnL/broker/model/2025+; khôngjobnền. Catalogue91/58 giữ.
Privatecampaignbase, `execution-v1/index-pair-history-v1/`:config/seeds/raw/
nativeexports/proofs/seals/manifest/snapshots/result/review/quality/samples/
rawbindings/events/progress; saved `prepare-index-pair-history-v1.cjs`,
`review-index-pair-history-v1.py`, `index-pair-source-preflight-v1.json`.
ResultSHA`30971fc426846424bcda77db81b3bc57b80962057b2f418f5aa1a291de7a1c9e`;
reviewSHA`5b52988a913b4c1056c2b557d837aafe70947d5580fa34a908edc392b2670421`.

**Tiếp:** [fixedformationprotocol](INDEX-PAIR-FORMATION-PROTOCOL-20261110.md)
trước diagnostics. Không thửnhiềuhours/pairs hoặc giữratio0,72 của futurespaper
cho CFD. Hậu kiểm không có source/costbug hoặc performancebottleneck đáng
thêmengine/dependency/skillmanager; reuse code/currentisolatedruntime đủ.
