# Tick-derived M1 hour: data revision riêng, không nới missing-only patch gate

Đăng ký sau [source review gatefail](NASDAQ-M1-GAP-TICK-RESULTS-20261108.md),
trước dựng view và rerun. Câu hỏi mới về data semantics: có thể dựng toàn
60M1 Bid/Ask từ jointticks của hour15UTC18Oct2022 một cách faithful không?
Giữ oldmissing-onlyadmissionfalse, không sửa nó thành pass sau outcome.

## Nguồn và phép biến đổi mới

Only existing `2022-10-18-15.json` + rawsourceproof, native/rawfullFraction
review tại `nasdaq-M1-gap-ticks-v1`. Rehash result/review/raw/export và
post-gap diagnostic. No newfetch/account/provider/2025+/broker/modelcalls.

- Build đủ60minute buckets theoUTCms. Open/Close là first/last jointtick
  theo originalordinal, giữ same-ms order; High/Low min/max riêng từngside.
  Mỗi phút phải cótick, mọiOHLC positive/grid0.001 và observedprice. No carry/
  padding/interpolation; first/last actualticktimes và counts giữ tronglineage.
- Nativequote-bar helper và separate Fraction aggregation phải exact cả
  120sidebars/480pricefields. Volume làsum provider-side quotevolumes ở đơn vị
  millions, không exchangevolume. Giữ exact rational volume trong receipt;
  nếu normal JSONfloat cần rounding thì report conversionerror, không giấu
  zero hoặc gọi losslessvolume khi khôngexact. Policy không dùng volume.
- So với oldM1 cảhour: census đã có106common sidebars và14new sidebars
  (53oldminutes/7missing).
  Phải đo120newsidebars,480pricefields; oldcommon H/L/C exact, chỉ2Openfields
  15:31UTC được phép khác theo source review đã xem. Bất kỳdelta khác dừng.
  OldOpen là intervalproxy có observedvalue trongminute; không claim decoder
  bug/firsttick cũ, không sửa historicalsource/proof.

Output mới`execution-v1/nasdaq-tick-derived-hour-v1`: price/volume/timeprovenance,
old/newdeltas,source snapshots/pins/result/review/progress/events. One writer,
CANCEL/deadline120s. Mutations price/count/time/order/rawhash/authority reject.
Source admission chỉ đúng120sidebars, không fulltickhistory/targetbroker.

## Derived2022book và affected strategy replay

Nếu60-minute sourceview đạt: newBid/Ask2022books=oldsealedbook với exactly
onehour replaced bằng tickderived rows. Giá/volume/timestamps ngoài hour giữ
exact;7newminutes,2changedOpenfields có provenance rõ. Mọi oldraw/book/results
và R065v1unknownstate immutable. Calendar và allprices ngoàihour không đổi.
Dataset contract phải ghi mixedM1source/provenance và Openfirsttick củahour
mới, không giả old`explicit-source-M1-v1`proof cho toàn mixedview.

Rerun2022 reference/stress với same R065 candidate/code/risk25/TP10R/fees/
unknownfreeze; có thể chạy samebatch nullcontrols để kiểm inputchange nhưng
nullfinancialstate phải exactold. Reuse2019books/reviews unchanged, giữyeargate
inconclusive; không serialize2019null/equityunknown thành0 hoặc bỏ khỏicensus.
Audit first5plans/quantities/trades trước affectedhour phải exact. Fullsuffix
được replay vì unknownstate trước đây chặn entries, không sửa hậu tố bằng tay.
SeparateFraction oracle trên newinput/accounting trước đưa verdict mới.

Không relax two-stress-year qualification hoặc promote partial2022 chỉ vì
dương; R065 còn data/OOS/prop/forward/handover gaps. Đây là datarevision có
scope/semantics được ghi trước rerun, không là rescue bằng sửa strategy.
