# WTI: kiểm tick gốc tại phút thiếu, trước khi gác source path

10/11/2026. Source-only follow-up của [fixture](WTI-SESSION-SOURCE-RESULTS-20261109.md),
không sửa frozen98%gate hoặc oldreview. Old6sessions chưa qua sourceadmission;
không xem economics, không recipe/R092 mới. Mục đích: phân biệt absence của
archiveM1 với absence của tickarchive, rồi quyết định có đáng kiểm đủ42roles.

## Chọn mẫu trước requests

Mỗi phiên2019 thất bại lấy **phút thiếu đầu tiên và cuối cùng**, mỗi phút ghép
với sampledrole đã có Bid/Ask gần nhất trước nó trong cùng session. Selection
chỉ đọc timestamp/census đãreviewed, không dùng price/returns. Giữ6pairs,
6missingminutes và6controls, không loại/reselect khi tick rỗng hoặc mismatch.

| UTC date | Tick hour | Missing role | Control role |
|---|---|---|---|
|2019-02-04|00|00:40|00:35|
|2019-02-04|21|21:40|21:35|
|2019-02-04|23|23:20|23:15|
|2019-02-05|21|21:05|21:00|
|2019-07-01|22|22:55|22:50|
|2019-07-02|04|04:15|04:00|

Private `wti-gap-tick-census-v1.json` SHA
`27e6e0c96843c6518c7840663e40305f40a65f982cc5d9352c341223e6ba1079`:
deterministic selection/sources/hours, generator saved trước fetch. Recheck
parentresult/review/rawbindings, frozenhelper và census trước source.

## Source và kiểm chứng

Sameinstalleddukascopy-node1.51.1/LIGHT.CMD/USD,6fullUTCtickhours, jointBidAsk,
pricegrid0,001/volumesmillions; nofilter/noinventedquotes. Cache mới dưới
`execution-v1/wti-gap-tick-source-v1/`, không seed hoặc sửa oldsourcecache.
6GETtối đa, tuần tự300ms/retry0/WAFoff/cumulativefailurecap1/deadline180s;
PID/lock/progress/events/CANCEL/nooverwrite, pin config/scripts/helpers/native/
lock/protocol/census/parents trước request và final, seals/fullrawsnapshots.

Reuse `index_tick_review.py` vì integer0,001format giống, không coi WTI là
indexcontract. Đối chiếu native/fullraw timestamps/BidAsk/volumes bằng
separateFraction decoder cũ đãpin; sameagent/feed, không independentfeed.
Trước requests: synthetic missing/observed/controlconflict, scope/order/grid/
same-ms/empty cases. Sau requests: actualprice/time/count mutations reject.

Giữsame-ms ordinal. Minute tickOHLC chỉ tổng hợp ticks timestamp thuộc
[minute,minute+60s), không carry lastquote hoặc nextminute. Với **mọi explicit
M1sidebar** thuộc6hours: so Open/High/Low/Close với tickOHLC, ghi từng delta và
side; M1volume không giả bằng sumtickvolumes hoặc exchangevolume. Missingminute
khôngquote là unresolvedsourceabsence, không thị trường đóng đã xác minh.
Tickextrema ngoài candle là material conflict cho việc trộn hai transports.

## Quyết định khóa trước outcome

- 6holes cótick + mọicommonM1OHLCexact +6controls cójointticks: chỉ eligible
  để đăng ký full42missingrole audit, chưa cho patch hoặc fullhistory/PnL.
- Có commonOHLCconflict: không mixedpatch; muốn whole-session tick-derivedview
  phải đăng ký source semantics riêng và kiểm đủ scope trước economics.
- Có missingrole khôngtick: giữ nóunknown, không giảm gate/agecap để cứu.
  Không retry samehourunchanged. Nếu chưa có phương án source đủ thì gác path
  WTI này và quay lại source-supported cơchếkhác/materialsurvivorblocker.

0financialfeatures/returns/PnL/broker/model/2025+, catalogue91/58 giữ nguyên.
Review/result giữ quote/sourcecounts/coverage/conflicts/phasesCPUwall và
nextdecision; collectorpendingreview không là pass. Khôngđổi targetfunding,
quỹ/program/cost/risk, không update product/runtime hoặc thêm skillframework.
