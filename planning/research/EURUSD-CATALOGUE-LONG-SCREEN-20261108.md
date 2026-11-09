# Discovery13 — sàng lọc catalogue cố định trên cache Bid/Ask2010–2022

Đăng ký trước outcomes của22policies còn lại. [Discovery12](EURUSD-OBSERVED-HISTORY-20261108.md)
đang chuẩn bị observedH1cache và kiểm hai policies. Không sửa kernel/source/
protocol của job đó; bài này chỉ đọc dataset đã sealed, reuse kết quả hai
policies đã chạy và tính22bản khác. [Campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md)
vẫn chưa đạt. Đây là mở rộng development, không biến data được xem thành OOS.

## Frozen universe

24versionFX nativeoffline hiện có, exactIDs trong config từ `ALL_STUDY_CANDIDATES`
ở Trader9fd6cd00:8H4 (Donchian/SMA/Z/Pullback/UTC range/failed20/compression/
rangefade) và16H1 (RSI/shock/prior-day break/fade/BB/pullback/EuropeAM/LondonPM/
fixing variants/ORB/BBflat). Không thêm parameter/hours/TP/risk grid hoặc ML/
metal policies vào bài này. Các versions cùng family/asset không độc lập.

London16–20 và Asia→London exact52rows từDiscovery12, source/runtime/input/
cost vàcash/count/proof phải khớp; không numerical rerun. Những22policies khác
chạy13years×2costs=572newrows, tổng624rows. Flatcash baseline0 đã định, không
đếm thành strategy có thể passchallenge. Giữ negatives, không bỏ0tradecases.

## Data/semantics và khả năng tái sử dụng

- Chỉ source-bound observedBid/AskH1cache2010–2022, causal warmupNov–Decnăm
  trước từDiscovery12. Chờ năm đó completedseal; không đọc file đang được ghi.
  Rehash raw/cache, kiểm runtime/schema/grid/order và exactprovider/cutoffs.
- H1signals dùng100warmupH1; H4signals dùng H4builder từ observedhours,
  ≥81completeH4, không dựng nến thiếu. Same annualinitial10k/planned25USD,
  minstep0,01/oneposition/noforceclose. KhôngportfolioCAGR hoặc resettuỳ ý.
- Same2costs: embeddedhistoricalspread, commission2,50USD/lot/side,
  slippage0/0,00002; financingBUY9,30/SELL−0,31reference,20/20stress,
  Wed×3/22UTC. Historicalbroker/accountspec vẫn declaredcounterfactual.
- Reuse `simulate_coarse` và `h4_from_hours`, không engine/riskowner thứ hai.
  CoarseSLlevel/hourOpengap vẫn approximation; không fulltickDD/internalbrakes/
  propcertification hoặc brokerpermission. Sốsource ticks không là executions.

## Quyết định khóa trước outcome

Primary: netequity sauphí theoannual/cost,ba bands2010–14/2015–19/2020–22 và
stressyear dispersion. Heuristicretention nhưDiscovery12: totalnet dương cả
hai costs,≥9/13stressyears dương,cả3bands stressnetdương. Không có thì giữ
`no_retention_under_declared_heuristic`,không hạ ngưỡng hoặc tăngrisk để cứu.

Rank những bản đạt bằng weakestbandnet tínhUSD/year (3-yearband chia3,
5-yearbands chia5),tie totalstressnet; chỉ max2versions từfamily khác nhau
được **đề xuất** kiểm tick tiếp. Không dùng ranking làm authority hoặc proofedge.
Cảheuristic/rank chỉ workloadtriage, không xác suất pass, FDR hoặc ngưỡng loại
cứng cảfamily. Nếu bản gầnngưỡng có cơ chế đáng nghiên cứu, đăng ký câu hỏi mới
và giữ việc đó là trialmới, không gọi eligible trong study này.

Phải đọc uncertainty/trialcount/selection/concentration và gaps. Không chọn
điểm tốt rồi tự mở2025+hoặc gọi tất cảpriceperiods là cleanOOS. C1cần exacttick/
risk/prop+freshfrozen/forward theo gate; C2cần quá trìnhđúng trong scope đã kiểm.

## Execution hữu hạn và quan sát

Một numericalwriter trênCPU, chờ datasetcompleted trongDiscovery12 và đọc
readonly,khôngQDMexport/provider/broker/modelcalls. Totaldeadline7200s kể cả
wait,peryear600s; cachecompleteyears/rows/checksummanifest giữ trongprivate
`eurusd-catalogue13-v1/`. StatusJSON/PROGRESS.md ghi waitingdataset/loadcache/
compute/validate/summary,candidate/cost/year/counters/wallCPU. FileCANCEL dừng
trước lượtcompute tiếp,khôngauto retry/overwrite completed evidence. Dữ liệu
chuẩn bị dùng lại; lần này không hash/parsehundredsmillionticks cho từngstrategy.

Correctness trước timing: explicit source/runtime/config pins, perrowcash/
floating/count checks, replaycounts và bytes của52parentrows khi reuse. Kết
thúc kiểm52+572=624uniquecases,13years×24versions×2costs; không nhận exit0 thiếu
rows. Sau đó hậu kiểm engineering và qualification riêng; không autoreject/
promote. Đừng rerun nguyênbatch chỉ vì cần sửa report/interpretation.
