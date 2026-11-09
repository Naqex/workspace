# WTI: tick archive cũng thiếu ở cả sáu phút mẫu

10/11/2026. [Protocol](WTI-GAP-TICK-PROTOCOL-20261110.md) freeze`047cbdf`
trước6GET. Kế thừa [oldsourcefixture](WTI-SESSION-SOURCE-RESULTS-20261109.md)
và42missingroles, không sửa98%gate/oldreview. Không financialtrial/R092 mới.

## Kết quả

| Missing role UTC | Tick tại phút thiếu | Tick tại phút đối chiếu đã khóa | Common M1–tick conflict trong cả giờ |
|---|---:|---:|---:|
|2019-02-04 00:40|0|6|0|
|2019-02-04 21:40|0|3|0|
|2019-02-04 23:20|0|3|0|
|2019-02-05 21:05|0|4|0|
|2019-07-01 22:55|0|2|0|
|2019-07-02 04:15|0|2|0|

1.996jointticks trong6fullhours;9.980rawtimestamp/BidAsk/volume fields khớp
native/integercompact/separateFraction decoder. Toàn548explicitM1sidebars
trong6hours có tick, cả4OHLCfields khớp; không chỉ so6controls hoặc chỉOpen.
Same-msordinal giữ, không ghép nextminute/lastquote. Không đồng nhất tickvolume
với exchangevolume hoặc M1volumesum.6missingminutes khôngquote trong chính
archive này; **không chứng minh market/broker thực tế không có quote**.

Đây là evidence chống giả thuyết sửa riêng M1decoder sẽ lấp các sampledholes,
không chứng minh mọi42holes cùng nguyên nhân hoặc provider không bao giờ lỗi.
Không cần thu36phút còn lại vì registeredpilot không đủ điều kiện mở rộng.
Old1.614/1.656sourceadmissionfalse giữ; không patch/padding/relaxgate.

## Kiểm chứng, hiệu năng và dấu vết

9syntheticchecks trước requests: match/absence/holewithquote/conflict/
nextminute/same-ms/crossed/offgrid/nonfinite.3actualmutations price/time/count
bịreject sau fullsourcecheck. Reuse `index_tick_review.py` đúng0,001format,
không áp indexcontract cho dầu. SeparateFraction decoder được pin từ
`review-nasdaq-M1-gap-ticks-v1.py`; arithmetic khác nhưng cùngagent/provider.
Không independentfeed, executablefill/brokerliquidity hoặc futureedge proof.

| Phase thực đo | Wall | CPU |
|---|---:|---:|
|6sourcehours /6GET /0reuse|4,124s|0,453s|
|Fullreview và minute bridge|0,344s|0,344s|
|Tổng hai phase|4,468s|0,797s|

Không gồm thời gian research/code/Git.6GET hoàn tất, controllerlock đã gỡ,
collectorreviewerexit0, khôngjobnền.0features/returns/PnL/broker/model/2025+.
Manifest giữprotocol/census/parents/rawbindings/scripts/helpers/native/lock/
config/snapshots; everyexport/finalpins,seals/PID/progress/events/CANCEL,
retry0/WAFoff/cumulativefailurecap1/deadline180s/nooverwrite.

Privatebase campaign, `execution-v1/wti-gap-tick-source-v1/` giữcache/native/
seals/proofs/manifest/snapshots/result/review/conflicts/progress/events.
Scripts `register-wti-gap-tick-census-v1.py`, `prepare-wti-gap-ticks-v1.cjs`,
`review-wti-gap-ticks-v1.py`; censusSHA trongprotocol. ResultSHA
`c2cb8ddbe0a56bc9d6daf67acf234c8799ef5acf695251b3ff2cbce9cfe78db5`.
ReviewSHA`cb2fd88d79f7748c46ce2437ea83aa68b9fbb7463df2edd576838b7861e2fc8c`.
Không dùng reviewer-codeSHA thay reviewartifactSHA. Khôngnewcandidate hoặc
đổi91records/58policyversions.

## Quyết định tiếp

Gác đường fullsession WTI source hiện tại; không retry unchanged6hours hoặc
20day-sideexports. Chỉ mở lại khi có nguồn mới giải quyết đúng roles hoặc
semantics mới có căn cứ trước economicoutcome, chưa có trong lượt này.
Chưa kết luận WTIexpansion lỗ; sourcegap không là economicnegative.

Hậu kiểm: nhỏ/nhanh, giữ nguồnđối chiếu và nguyênnhânunknown; không phát hiện
bug/nút thắt cần sửa sharedengine/GPU/Rust hoặc thêm skillmanager. Quay lại
[index-pair admission](INDEX-PAIR-METHOD-ADMISSION-20261110.md), không cứu
oldrecipes bằng cost/clock/holdinggrid. C1/C2 chưa đạt, Goalactive.
