# WTI session source fixture — khóa trước requests/coverage

09/11/2026. [Method](WTI-OPEN-EXPANSION-METHOD-20261109.md) mới có đường causal
để nghiên cứu, chưa strategy specification/PnL. Mục tiêu hữu hạn: kiểm source
LIGHT.CMD/USD M1 Bid/Ask cho overnight session, gồm Sunday và DST; không dùng
price outcomes để chọn giờ. Catalogue91/58 giữ, không account policy mới.

## Calendar và roles đã khóa

- 6session labels:2019-02-04/05,2019-07-02,2022-02-07/08,2022-07-05.
  Hai ngày đầu mỗi năm là firstMonday/TuesdayFebruary, ngày hè firstTuesdayJuly;
  selection theo lịch, không PnL. Không tự bỏ holiday vì thiếu/giá xấu.
- Ownsession: start18:00America/New_York ngày lịch liền trước → end16:55NY
  ngày ghi nhãn. Monday dùng Sundayopen, không Friday/previousweekday shortcut.
  Sample exact M1Open tại mỗi5phút gồm hai đầu:276slots/session,1.656pairedslots.
  M1Open là intervalproxy/known-at upper+60s, không actualexecutablejointtick.
- 10UTCsource dates:2019-02-03/04/05,2019-07-01/02,
  2022-02-06/07/08,2022-07-04/05. Bid/Ask mỗi ngày→20raw requests tối đa.
  Không2025+, statisticalfeatures/returns/PnL/entry/exit/risk/broker calls.

## Nguồn, guard và kiểm chứng

Reuse dukascopy-node1.51.1/.runtime/research-data lock và `dukascopy_cached_m1.cjs`;
same existing provider/instrument. M1 UTC, unfilterednative/fullsource exports,
volumesmillions, ignoreFlatsfalse. Cache mới dưới attempt; không sửa old caches.
Chỉ seed exact oldraw khi manifest/hash/URL/date/side phù hợp, không giả reuse
nếu sourcefile chưa có. Singlewriter, request tuần tự300ms/retry0/WAFoff,
cumulativefailurecap1,deadline180s,CANCEL/progress/events/PID/nooverwrite.

Bind protocol/helper/native/lock/scripts/config trước requests, recheck trước
mỗi request và final; rawresponses,exports,seals/snapshots giữđủ. Fullraw
integer/FractionOHLCV decoder độc lập đối chiếu existing native expansion/
explicit-source provenance; native padding không là source quote, không tự
fillgaps hoặc suy no-price-change từ zero volume. Sourcegrid0,001 phải khớp.

Review từng source field/time/order/OHLC/grid/volume và mọi pairedslot. Với
separate side bars, chỉ đối chiếu Bid≤Ask tại Open/Close; extrema hai side
không là simultaneousquotes. Rolecoverage giữ numerator/denominator đúng
6sessions, exactopen và exactclose bắt buộc; ≥98%276slots/session. Thiếu role
đầu/đuôi không nextquote/lastbar substitution. Fullslot census độc lập với
producer date arithmetic, có winter/summer/Sunday/midnight fixtures trước fetch.

Syntheticnegative missing side/missingopen/crossed/schema/futuredate trước
collect; actualmutations price/time/count/padding tối thiểu4 bịreject sau
review. Không đổi threshold hoặc timegrid để cho sourcepass. Data-admission
false khác economicnegative, không xem full-session quality trước rồi chọn
trades đẹp. Nếu unavailable, lưu sourcegap và quyết định semantics riêng
trước bất kỳ new financial trial nào; không sửa protocol/result này.

## Output và bước tiếp

Private `execution-v1/wti-session-source-pilot-v1/`; resultcollector chỉ
`pending_review`, reviewer bind exactbytes/coverage/gaps/units/provenance,
phasewall/CPU, mutationreceipt rồi sourceverdict. Không whole-year history
hoặc candidatecount. Report sourcefixture/nextdecision tại research owner.
Pass cũng chưa chứng minh futures→CFD economics, PITbroker contract, exact
funding/SL/prop/holdout/forward. Existing skills đủ, không thay runtime/AIconfig.
