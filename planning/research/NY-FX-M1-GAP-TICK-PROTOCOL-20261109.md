# NYFX: kiểm nguồn tick cho10phút M1 chưa rõ

Đăng ký trước tickfetch/inspection, không economic rerun. [Pairedstudy](NY-FX-PAIRED-LATENCY-PROTOCOL-20261109.md)
đã chạy32books/review nhưng mọi nonnullannualbook vẫnunknownexposure khi
thiếuphút giữvịthế. Không biến partialcash thành fullannualPNL hoặc gọi strategy
failvìsourcegap. ParentH1negative vẫn giữ; chưa challengecandidate.

Source-onlycensusprivate`ny-fx-M1-gap-census-v1.json` đã ghi bindings/selection:
mọi weekday2019/2022 có ít nhất một causalfeature-readydecision, từ earliest
possible15minentry đến15NY. Không chọn theo entryside/PnL/tradeoutcome. Có
10minutes/10days/10distincthoursUTC, không cherry-pick3firstunknowns:

| Ngày | TickhourUTC |
|---|---|
|2019-05-20|17:00|
|2019-05-27|18:00|
|2019-07-04|17:00|
|2019-09-02|18:00|
|2022-01-05|18:00|
|2022-02-15|18:00|
|2022-03-29|16:00|
|2022-04-15|15:00|
|2022-06-20|17:00|
|2022-09-05|17:00|

ExistingDukascopy EURUSD/pinned1.51.1, jointtickJSONdelta/tick0,00001/volume
native millions, preserve same-msorder.10requests/1URLperhour, sequential,
cacheexisting`source-hour-cache-v1`,retry0/cumulativefailurecap1/deadline180s/
CANCEL/WAF-tokenoff. No rawoverwrite/auth/newprovider/account/paid/2025+/
broker/modelcalls. Reuse nativefetcher/cache/decoder vàFractionreview pattern,
không thêm downloader/framework. Sourcepins/snapshots/seals/events/timing.

Full10rawhours so Fractiontime/price/volume/order/grid; sourceURL/instrument/
hour/hash phảiđúng. Aggregate ticks→M1OHLC riêngBid/Ask; compare mọi commonM1
field/side/census. Missingminute cótick mới có thể đềxuất derivedsourcepatch;
commonmismatch giữ conflict, khôngoverwriteđểbridgepass. Noquote tickminute
giữnguyênunknown, không chứngminhthịtrường/brokerkhôngcóquote hoặcgiábấtbiến.

Output `execution-v1/ny-fx-M1-gap-ticks-v1`,onewriter. Price/time/order/hash/
authority mutations bịreject trướcnguồnđược admit. Giữ sourcegap vànewsource
revisions; proposedpatch khôngclearaccount hoặcpermissionrerun. Patch/view
recipe phảiđăngkýriêng saureview; unchangedrules/costs/SL/risk, affectedbooks
rerun từ đủstate vìsource/gap làmđổisuffix. Không sửasealedresult hiện có.
Nếukhôngđủnguồn, reviewimpact/sensitivity riêng hoặcgác exactversion với
inconclusive rõ;không tảilạiunchangedannualhistory vàkhôngclaimedge/prop/OOS.
