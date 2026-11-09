# PreECB: kiểm thêm 2023–2024 trước khi phát triển risk wrapper

Đăng ký sau [13-year results](PRE-ECB-LONG-PRICE-RESULTS-20261108.md), trước
outcomes2023/2024 của exact endpoint component. Source hai năm đã consumed
trong các studies trước, không clean OOS. Không mở2025+.

Lý do: positive2010–2022 chưa trả lời mức chuyển giao ở hai năm gần hơn hiện
có. Dùng same SELL02NY→14Berlin, oppositeBUY, observedBidAsk và phí5USD/lot
roundtrip,slip0/0,00002mỗi side. Không đổi stop/lot hoặc gọi component là bot.
Giữ all weekdays, firstobservedquote≥target≤60s và unresolved/late explicit.

Input và code reuse:

- Rawlocators/SHA/count của2023/24 từ monthly-input config đã review, source
  metadata pins và rawproof giữ nguyên. H1cache producer hai năm này cũ khác
  currentguard; **không rebind hoặc ép nativecache pass**. Dùng existing
  `fixing_clock_probe.scan_targets` explicit raw mode, fullrawhash/count/order.
- Scanner cũng xuất14:15 sourcequote theo contract cũ; chỉ entry/14:00 dùng
  numeric.14:15 không thành outcome/variant hoặc thay exit khi có missing.
-13yearresults/summary/review giữ nguyên SHA, chỉ đọc lại để combinedreport.
  Các helpers và source snapshot pin trước compute; reuseguard đọc strict
  originalreceipt hashes, không fallback expected=current.

Tiêu chí trước số mới: xem là còn đáng đăng ký riskwrapper nếu primary
2023+2024 stresssum>0, mỗi năm≥200resolved; đồng thời combined15years≥10năm
stressdương,tổngstress>0 và các blocks2010–12/13–15/16–18/19–24dương. Không
bắt cả hai năm dương hoặc chọn tiêu chí sau outcome. Đây là triage heuristic,
không adjusted probability/prop hoặc quyền mở holdout.

Báo annual/combined sums,denominators/min/max/mean/concentration như parent,
giữ reference/opposite và missing. Không tính13+2thành hai independentstudies.
Một writer/root mới, deadline180s,peryearseal/status/events/PID/failure/CANCEL.
Runtime fixture dùng helpers hiện hành không đổi; source/control sanity trước
PnL, samefees/no22UTCfunding.0broker/model/network calls trong numeric.

Separate reviewer cùng agent: independent clock/Fraction economics/summaries,
strictdataset/outcome/receipt pins; firstquote và predecessor proofs cho mọi
target, đối chiếu frozenH1firstquotes làm read-onlyoracle cho cả hai endpoints
mọi resolved event, không executeoldcacheproducer. Mutation price/time/net/
missing/authority. Không gọi fullrawcodepath hoặc H1oracle là independentfeed.
Nếu đạt, chuyển1wrapper theoholding-sessionvolatility đã định hướng, không
chạy thêm clock/sidegrid hoặc sửa cost assumptions từ kết quả mới.
