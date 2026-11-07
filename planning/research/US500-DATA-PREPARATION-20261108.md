# US500 development2022 — data preparation sau bounded fixture

Kế thừa [Discovery14 fixture](INDICES-DISCOVERY14-PREPARATION-20261108.md),
không numericalstrategyoutcomes. Mục tiêu chuẩn bị một năm development cho
nghiên cứu equityintradayprice-onlynoisebands; không cố cứu24FXversions vừa
không đạt. SPYpaper chỉgợi ý cơchế; adaptationUS500CFD phải cóspec riêng.

## Exact read-only provider requests

- Chỉ `usa500idxusd`, M1Bid vàAsk,UTC01/01/2022→01/01/2023exclusive,chia
 4quarters×2sides=8requests. ExistingpublicDukascopy+installedpinnedpackage
 1.51.1/lock/SRI/review,khôngQDMsymbolchange/fullhistoryupdate,newaccount/key,
 browserrecovery/auth/token hoặcpaidprovider. Không2025+.
- Mỗiquarterrequest dùngbatch2,interval/pause300ms,retry0,WAFOFF/tokenfalse.
 403/timeout/empty dừng;khôngbypass hoặc tự đổi source. Totaldeadline1200s;
 fileCANCEL kiểm giữarequests. Mộtwriter vớiPID/status/log/manifest; giữ
 quarterlyraw/checksums đã xong,khôngoverwrite hoặc autoretry lỗi.
- Giữ raworder/UTC/minutegrid/sideOHLC/volume/gaps. Đầu tiên hash/schema/date
 scope,sidealignment,positivefinite/sourcegrid0,001 vàcashsessioncoverage.
 Khôngsort,dedup,gapfill hoặc suy midhigh/low từsideextrema. Tick/realvolume,
 USexchangevolume,holiday/halfdaycalendar vàtargetbrokercontract vẫn unknown
 nếu chưa có nguồnriêng. Không tính VWAPexchange từ CFDquotevolume.

## Điều kiện chuyển bước

Fixture03/01/2023 đã390/390cashminutes09:30–16:00NY cảSPYvàUS500,hai side
aligned;chỉmột ngày,khôngchứngminh2022coverage. Năm2022 làdevelopment giá mới
đượcthutoàn bộtheoscope này,khôngholdout. Phảifreeze exactnoisebandentry/exit/
hardSL/lot/cost/DST/holidays vàsyntheticfixtures trước bấtkỳPnL. Reuseexecution/
cost primitives hiệncó,không giả indexlàEURUSD hoặc bỏ nativeFXaccountguard.
Không OrderCheck/OrderSend hoặcmua challenge; C1/C2campaign chưađạt.

## Kết quả tải và kiểm dữ liệu — 08/11, sau 06:00 Việt Nam

Download completed 319,701s,8/8quarter-side seals;341.682rows mỗi side.
Private `execution-v1/us500-development2022-v1/result.json` giữ hashes/rowcounts;
controller12304 đã kết thúc và lock đã gỡ. Không strategy/broker/model calls.

`tooling/ai-engines/sealed_m1_review.py` kiểm lại raw hashes, seal metadata,
request/year/side binding, grid0,001, finite/OHLC/volume/order và timestamp pairs.
Review thực tế3,63s;4focusedtests đạt, gồm calendar/DST, lỗi giá/thời gian,
side alignment, sửa raw/seal và giữ gaps. Không fill/sort/dedup raw input.
Artifact `calendar-quality-review-v1.json` giữ source/calendar/reviewerhash.

| Phần | Kết quả |
|---|---|
| Phiên NYSE2022 | 251phiên:250×390phút +25/11×210phút |
| Cash phút có/dự kiến | 97.698/97.710; thiếu12phút ở4ngày |
| 01/03 | 17:58–18:01UTC,4phút |
| 29/03 | 16:59UTC,1phút |
| 18/10 | 15:24UTC,1phút |
| 14/11 | 16:50–16:55UTC,6phút |
| Ask−Bid tại M1open/close toàn file | median0,525/max7,295indexpoints; không tickspread đồng bộ |

[NYSE/ICE announcement27/12/2021](https://ir.theice.com/press/news-details/2021/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar/default.aspx)
được đọc08/11, bao gồm Juneteenth20/06 và đóng13:00NY25/11. Frozen calendar
ở `tooling/ai-engines/fixtures/nyse-2022.json`; không suy brokerCFDhours từNYSE.
M1 side extrema/endpoints không chứng minh synchronous mid/high/low/spread.

**Bước tiếp:** freeze riêng adaptation/noiseband, timing, hardstop/sizing/cost
và causal gap policy trước PnL. Không xoá cả ngày chỉ vì nhìn thấy gap cuối
ngày; missinghistoryslot không được thay bằng futuredata hoặc backfill giá.
Tick review phải giải quyết ảnh hưởng gap khi có exposure. Chưa nativeindex
execution/propDD; researchdata usable with gaps, không gọi fullcleancoverage.
