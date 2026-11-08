# NASDAQ M1 gap: tám tick-hour source fixtures, không strategy tuning

Đăng ký sau [R065inconclusive](NASDAQ-OPENING5-ORB-INTERIM-20261108.md), trước
sourcefetch. Lý do là missingM1 khi holding làm accountunknown, không vì muốn
sửa outcome dương/âm. Source audit xử lý mọi missingcashminute trong hai dev
years đã khóa, kể cả ngày không ảnh hưởng R065, không chọn từng trade thuận lợi.

## Frozen source-only census

`nasdaq-M1-gap-census-v1.json` tại existingprivatecampaignroot được dựng chỉ
từ source timestamp/calendar:22missingminutes,6days,8distincttickhoursUTC:

| Ngày | Tick hours bắt đầu UTC | Missing M1 |
|---|---|---:|
|2019-01-25|14:00,16:00|8|
|2019-10-02|16:00|1|
|2022-01-26|15:00|1|
|2022-03-01|17:00,18:00|4|
|2022-03-29|16:00|1|
|2022-10-18|15:00|7|

WarmupDec2021gap không numericinput của R065 nên không thêm. Parent source
result3058b26d…06e7/review8b0bced9…9703 và cashqualityhash trong census phải
rehash. ExistingDukascopy `usatechidxusd`, tickjointBidAsk nativeJSONdelta;
installeddukascopy-node1.51.1/package-lock giữ pin. Không newprovider/account/
auth/paidservice/package/2025+ hoặc broker/modelcalls.

Reuse nativeBufferFetcher/CacheManager và existingrequestWithRecovery,
formatjson/volumemillions, nohiddenretry/WAF. Một URL/hour, tuần tự8requests,
300ms giữa noncachedrequests,3attempts/request/cumulative6transientfailure,
timeout/deadline180s/CANCEL. Auth/403/429/schemafail khôngretry/bypass. Validempty
rawsource giữempty, khônginventquote. Reusecache nếu exactbinding, nooverwrite.

## Fidelity, quality và giới hạn admission

Trước strategyPnL: native tickexport toàn8hours so separateFraction rawdelta
time/Bid/Ask/volume/order/grid, preserve same-ms ordinal, exactrawhash/URL/hour/
instrument/priceunits. Quote-bar oracle aggregate every populatedminute,
separate sides. Common explicitM1 phải OHLCexact với observedtickaggregation;
reportmissingminutes có/không actualticks, gaps/firstlast/maxgap, sourceempty.

Chỉ đề xuất patch cho phút M1 vốn thiếu **và có actualjointticks đãreview**;
không carryclose/zero-volume/padding/điềnphút từ neighboringprice. Giữ source
M1 hiện có và comparecommons, không overwritebar conflict. Tick absence vẫn
unknown, không gọi là proof no-trade/continuousquotes. All8rawtransforms và
commonOHLCchecks phải khớp; fail thì không economic rerun hoặc clearstate.

Output mới`execution-v1/nasdaq-M1-gap-ticks-v1`: pins/snapshots/config/tickrows/
proof/rawbindings/quality/result/review,1writer/PID/progress/events/failure.
Mutations wrongtickprice/time/order/sourcehash/falseauthority reject. Reuse
`quote_bar_oracle` và pinned native components; không source/strategyengine mới.

Nếu đạt: đăng ký derivedM1view với perpatchticklineage và explicitvolumeunits,
giữ originalraw/book/attempt. Datarev mới không là strategyretune. Rerun chỉ
affected annualbooks vì unknownstate làm đổi suffix; oldcase results không
được chỉnh tay. Nếu phút unknown vẫn không có ticks, báo inconclusive và
chọn bước data/method tiếp bằng evidence, không hạ nguồn/selectiongate.
