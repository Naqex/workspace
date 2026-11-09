# R082 — WTI Wednesday reaction/late-session diagnostic component

Freeze09/11 trước new history/returns. Own transfer từ cơ chế thông tin sau
inventory announcements, không clone EA, không replication USO hoặc causal
policy. [Role-source protocol](OIL-EIA-ROLE-SOURCE-PROTOCOL-20261109.md) giữ
oldETF gate: USO2019 thiếu5holdingminutes, tổng4asset-day admissionfalse;
WTI hai date riêng đủ60roleminutes. Không sửa oldresult hoặc dropUSO vì lỗ.

## Vì sao kiểm trước khi đầu tư full calendar/ETF transfer?

Primary [Wen et al.](https://digital.library.adelaide.edu.au/server/api/core/bitstreams/aee73b81-111e-4bef-9e0e-7b1164f368a1/content)
§2.2/footnote6 chỉ dùng Wednesday releases cho EIA subgroup. New archived
EIA PDFs mô tả normal10:30tables/13hfullreport; chưa actualms/PITallcalendar.
Câu hỏi diagnostic: trên cohort **retrospectively labelled** Wednesday release
trong2019/2022, price-reaction sign có giữ net association cuối phiên trên
WTIquote proxy sau modeledcosts không? Nếu đã yếu trong điều kiện thuận lợi
về labels thì gác recipe, tránh chi phí làm calendar/forward cho bản yếu.
Nếu mạnh thì chỉ ưu tiên xác minh PIT/calendar/fees/transfer tiếp, chưa edge.
Không đánh tráo date labels ex-post thành lịch đã biết khi quyết định trade.

Cohort88date =44/year, từ existing103event archive census, SHA
`36aa7870ba27016a4d68fbbe84464cea7eca908c2e860f577f6b661950b204f9`.
Không Thursday/Friday, không nhân đôi29Jun2022; không lọc theo giá/kết quả.
Đây là cơ chế liên quan R027/eventmomentum, không independentedge chứng minh.
2022beyond paper sample vẫn **không cleanOOS** cho campaign đã xem data đó.

## Nguồn và geometry

ExistingDukascopy1.51.1 `lightcmdusd`, fullUTCdayM1 Bid/Ask cho88dates =176
rawday-sideURL tối đa, sourcegrid0.001, native millions/ignoreFlatsfalse.
Reuse4oldWTIraw bằng copy bytes vào cache mới, không thêm file vào oldsealed
cache. NoWAF/auth/retry/newprovider, cumulativefailurecap1,deadline300s,
CANCEL/onewriter/status/events/pins/attempt; no2025+, broker/modelcalls0.
Các exportsnativefull vàraw giữ; explicit rows decode riêng, padding khôngquote.
Source-only role coverage10:30–11:00inclusive31minutes,15:31–15:59inclusive29.
Full raw/native/clock/grid/seal và FractionOHLCV reviewer trước economics.
Thiếu/crossedrole ghi unknown trong expecteddate, không loại hàng để đẹp PnL.
Noquote khôngsuygiá khôngđổi/marketclosed. Không futurequality làm tradefilter.

## Own diagnostic rules, không account strategy

- Source Opens10:30 và11:00America/New_York với DST, side-midpoint. Chỉ sau
  11:01 mới known feature; sign(mid11−mid10:30) là direction cho slot15:31.
  Equal → noentry. Không thresholds/volumefilters/parametergrid hoặc tối ưuSL.
- Entry15:31sourceOpen, exit15:59sourceOpen trước ETFclosingminute; giá trong
  interval[minute,minute+1), chưa executablejointtick. WTI khác USO; own timing
  adaptation không hứa giữ economics của paper. Cố định1research barrel/unit,
  priceUSDperbarrel, không lot/balance/leverage/SL/prop-equity hoặc OrderSend.
- BUY vàoAsk, raBid; SELL vàoBid, raAsk. Net=executable-side proxy move −
  modeledextraRTcost **0.05USD/unit reference /0.10USD/unit stress**, gồm
  commission/slip/implementation shortfall allowance giả định. Spread đã có
  trong entry/exit sides, không trừ lần nữa. Chưa actualbrokerfee/history.
  Intradayslot funding0declared, không swap-free evaluation claim.
- Controls: opposite-direction, always-long, always-short, flat null trên
  cùng88plannedrows/costscenarios. Không promote control thắng sau outcome.
- Report mỗi năm: expected/resolved/unknown/flat/trades; known-subset gross/
  spread/extra/net decomposition; strictannualnet=N/A nếu bất kỳ selectedday
  unknown. Không chuyển giá thiếu thành0, không projectedaccountPnL/passrate.

## Gate, tests và output

20books =2years×5rules×2costs. Next-stage research priority chỉ khi primary
strict cả2stressyears known/net>0, >=35trades/year, không source/materialbug;
không p-value/edge/propcertificate. Khônghạgate hoặc tune khi fail; knownnet
âm chỉ loại conditionalrecipe, unknown giữ nguyên. C1/C2 tổng chưa tự đạt.

Synthetic BUY/SELL/zero/cost/decomposition/missing/future-feature mutation và
DST/entryafterfeature; separate Fraction rawdecode/decision/net/count theo
allplannedrows, mutations source/row/count/fees/authority phải bịchặn. Pure
pricecomponent không là brokercheck; không ép vào existing nativefixture.

Private `execution-v1/wti-wednesday-source-v1/` và `wti-wednesday-component-v1/`
trong campaignroot. Failedattempts giữ; cache/sealedprefix reuse khi bindings
khớp, khôngrestart merelyobserver timeout. Source/review/compute timing tách
research/code wall; code/protocol/config/snapshot freeze trước requests.
No money/account/provider/service/globalconfig. Giữ quyềnholdout/broker riêng.
