# Thời gian toàn luồng và cách mở rộng sàng lọc — 07/11/2026

Owner hỏi đã lưu time từ đầu đến cuối chưa, và có nên làm rộng tầng nhanh rồi
chỉ kiểm sâu nhóm nhỏ. Kết luận: đã có wall/CPU/phase của các job số học chính;
chưa có timer đầy đủ cho research, viết code và review thủ công. Nên mở rộng
theo tầng, nhưng probe <1giây hiện tại **chưa đánh giá lợi nhuận**.

Trạng thái: báo cáo/đề xuất; không đăng ký hoặc dispatch thêm chiến lược, không
mở dữ liệu2025+/broker. [Kết quả năm](HISTORICAL-RESULTS-20261107.md) vẫn giữ các
quyết định không promote. Không chạy lại study để đo timing đã có.

## 1. Số đo đang có

Wall time là thời gian phải chờ; CPU time là tổng giây xử lý của worker, có thể
lớn hơn wall khi chạy song song. Cả hai khác quota/token AI. Các job mô phỏng
ghi model_calls=0; agent nghiên cứu/code ngoài job vẫn dùng token của phiên.

| Lát | Đã đo ở đợt vừa rồi | Cách hiểu / tái sử dụng |
|---|---:|---|
| Nghiên cứu, chuẩn hóa ý tưởng, code rules | Chưa có timer trọn vẹn | Không lấy thời điểm commit làm thời điểm bắt đầu. Dự trù mới30–120phút/nhóm rules đơn giản reuse factory, chưa benchmark; data/contract mới cần ước lượng riêng |
| Chuẩn bị Q1raw→quality/H4/tick cache |142,812giây | Một lần cho nhóm cùng input; raw đã có, không bao gồm lần thu/download gốc |
| Chuẩn bị UTC2024/export+quality/cache |670,828giây | Chạy chồng thời gian với discovery, không cộng lần nữa vào critical path |
| Tám feasibility probes |Load/hash0,900giây + compute0,063giây | Dữ liệu một quý, rules đã implemented; chỉ tín hiệu/lot, không PnL/DD/edge |
| Preflight riêng |2,02–2,22giây/bản Q1;5,40–7,18giây/bài năm v2 | Không mô phỏng; không cộng trùng với kiểm cache bên trong batch |
| Discovery tick Q1:4candidates×2costs,4workers |786,39giây =13phút6giây | Sàng lọc kinh tế development, chưa full prop path. Mỗi candidate hai cost hiện chạy lần lượt |
| UTC2024:2costs, full tick prop path |Batch9.458,86giây =2giờ37phút39giây | Reference79phút11giây; stress78phút14giây; không phải thời gian8f924908 sau tối ưu |
| Compression2023:2costs, full tick prop path |Batch8.512,56giây =2giờ21phút53giây | Reference71phút; stress70phút35giây; chạy song song UTC |
| Đóng worker/batch + auto report |~1,89giây discovery;5,74–5,83giây hai bài năm | Khoảng từ worker cuối kết thúc tới pipeline completed, không phải pure render time; đã nằm trong pipeline |
| Kiểm source thật sau promote |224pytest19,03giây;14report tests~1,20giây | Chỉ lượt kiểm cuối, không là tổng toàn bộ test/debug/profiling trong phiên |
| Review/code-fix/handoff/báo cáo thủ công | Có timestamp một số mốc, chưa có active timer đầy đủ | Phải giữ unknown, không suy từ mtime hoặc cộng các khoảng chồng nhau thành CPU/agent-time |
| OOS/forward/demo/challenge của chiến lược | Chưa chạy trong vòng này | Chưa có thời gian quan sát; forward cần dữ liệu tương lai/thị trường, không lấy CPU backtest làm ETA payout |
| Latency vận hành quote→signal→risk→order→fill/reconcile | Chưa đo trong vòng này | Cần số đo riêng theo ms, p50/p95, disconnect/recovery; không dùng throughput backtest thay latency broker/live |

Các con số là workload/source trước tối ưu lõi, trừ dòng kiểm sau promote.
Patch8f924908 giúp validate snapshot nhanh1,62–1,79× trên các case đã đo; **chưa
đo whole annual replay mới**, không chia toàn bộ thời gian cho1,79 để gọi ETA.

## 2. Tổng thời gian theo đường chạy thực sự

Khoảng có log đầy đủ: từ chuẩn bị Q1cache **10:16:43** tới commit đóng tài liệu
**13:34:04** ngày07/11 = **3giờ17phút21giây**. Đây chưa bao gồm research/code
ban đầu trước mốc đó. Hai bài năm dùng cùng một khoảng chờ, không cộng lần lượt.

| Đoạn trên critical path | Thời gian | Tỷ trọng khoảng đã quan sát |
|---|---:|---:|
| Q1cache preparation |2phút23giây |1,2% |
| Khoảng binding/preflight/bàn giao trước discovery |3phút32giây |1,8% |
| Discovery pipeline tới report |13phút8giây |6,7% |
| Đăng ký bài năm, lượt lỗi/dừng, calendar fix và recovery |14phút35giây |7,4% |
| Hai annual pipelines chạy song song tới report cuối |2giờ37phút45giây |79,9% |
| Sau report cuối tới commit: audit/promote/tests/tài liệu |5phút58giây |3,0% |

Tổng giây CPU numerical workers của ba batch:20.260,33giây ≈ **5giờ37phút40giây**;
không phải thời gian chờ3giờ17. Các khoảng binding/fix/docs là envelope nhiều
việc, không phải đo active effort từng tác vụ. Research/profiling/implementation
còn diễn ra chồng với numerical; không được cộng thêm toàn bộ lần nữa.

Evidence máy đọc được:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/pipeline-timing-review-20261107/timing-summary.json`.
Recipe `summarize.py` chỉ đọc native artifacts/Git timestamp, lưu source SHA256;
tổng6critical segments được đối soát bằng tổng observed span. Nó không chạy job.
Receipt/pipeline/phase_wall_seconds/phase_cpu_seconds/elapsed/CPU vẫn là nguồn gốc.
`machine-at-review.json` ghi máy lúc review: i5-9400F,6cores/6logicalprocessors;
đây không phải historical utilization profile từng run. Baseline đã chạy4workers
discovery và2workers annual. Có thể so4với6workers ở lô được đăng ký tiếp theo,
không coi6cores là bảo đảm6×speedup hoặc tự sửa concurrency của protocol cũ.

## 3. Nút thắt và hướng cải tiến

| Ưu tiên | Đã thấy / chưa biết | Hướng xử lý |
|---|---|---|
|1: numerical full year |Chiếm~80% khoảng có log; repeated ledger validation đã được profile |Đã gộp pass, giữ guards. Đo cùng workload ở lần nghiên cứu cần chạy tiếp; chưa mở benchmark năm chỉ để chứng minh nhanh |
|2: lựa chọn phép kiểm |Probe rất nhanh nhưng không lọc kinh tế; mọi ứng viên probe đều sizeable ở đợt đầu |Tăng ý tưởng/feasibility trước; economic coarse screen mới phải reuse core và đối chiếu tick trên positive/negative/ambiguous cases. Chưa có tầng bar-PnL đã validated để quảng cáo chạy100bản trong giây |
|3: rework và source ownership |Một lỗi startup làm UTCfailed/Compressioncontrolledstop; shared source phải chờ writers |Giữ regression/early-horizon check/scenario reuse. Hướng sau: executable source isolation theo commit cho job; sourcesnapshot hiện chủ yếu là provenance, chưa chứng minh toàn runtime độc lập |
|4: data preparation |142,8–670,8giây lần xây cache; cache recheck2,187/5,219/7giây đã nằm trong các batch |Chuẩn bị một lần theo input hash/schema, nhiều readers; không bỏ hash/quality để giảm vài giây |
|5: research/code/review |Có thể thành bottleneck khi nhân số ý tưởng, nhưng chưa có active time |Lô tiếp đánh dấu start/end, active/wait/overlap, source và đơn vị sốcandidate/cost/window; không suy human-time từ commit |
|6: report/hiển thị |Auto postprocessing chỉ vài giây; watcher tạm từng không xử lý null khi completed |Đã sửa null display; ưu tiên thấp hơn numerical và rework. Không cần dashboard/collector mới |

## 4. Mở rộng theo phễu, không nhân toàn pipeline

Các quy mô dưới đây là **đề xuất năng lực làm việc**, không phải ngưỡng thống kê
hoặc cam kết sẽ còn bao nhiêu winner. Ít mẫu giữ inconclusive; nếu không có bản
đáng kiểm thì dừng lô, không hạ tiêu chí để điền shortlist.

| Tầng | Quy mô đề xuất vòng tới | Kết quả / gate | Song song thế nào? |
|---|---|---|---|
| Kho ý tưởng/nguồn |30–50hồ sơ đầu tiên, mở rộng sau khi thấy mức trùng |Cơ chế, exact source, manual/auto, prop applicability, data/cost/license; gộp ý tưởng trùng |Research độc lập có thể song song; không mở broker/data permission từ nguồn ngoài |
| Chuẩn hóa rules + kiểm code tối thiểu |Khoảng10–20bản khả thi cho dữ liệu hiện có |Version/entry/exit/risk/clock rõ; causal fixtures và số tiền đơn giản trước tin kết quả |Nhiều candidates độc lập; không20người cùng sửa core/factory |
| Feasibility trên cache |Toàn bộ rules đã implemented của lô |Có tín hiệu, warmup/lot/cost khả thi; lưu reason và insufficient |Batch chung đọc data một lần; compute rất ngắn nên không cần một process/LLM cho mỗi rule |
| Economic development screen |Một lô hữu hạn, ví dụ8–12bản trước khi scale tiếp |Hiện phải dùng tick hoặc reuse kết quả đã có; mọi phiên bản/parameter trials được ghi, không chỉ top PnL |2–4numericworkers là mốc đã có, không là tối ưu tuyệt đối của máy; đo contention trước tăng |
| Historical robustness/validation sâu |Khoảng2–4bản có lý do, có thể0 |Freeze trước window mới, costs/tickDD/prop/rules; G1/G2 correctness không được dồn hết tới cuối |Candidates/accounts mô phỏng độc lập có thể song song; không dùng validation để tiếp tục chọn/sửa rồi gọi là OOS |
| Kiểm chéo sâu / forward |Chỉ các bản đủ gate; thêm mẫu đối chứng đã định từ bản bị gác |Không chỉ audit winners; đối chứng nhằm thấy sai số tầng nhanh, không chứng minh tỷ lệ bỏ sót edge nếu chưa có ground truth |Audit artifacts độc lập có thể song song; tick/account path và signal→fill vẫn phải đúng thời gian |

Tầng chậm **không bắt buộc chạy từng chiến lược lần lượt**. Hai bài năm vừa rồi
đã song song. Thứ tự bắt buộc là dữ liệu/đăng ký trước execution, stateful quotes
đúng chronology trong một account path, chọn/freeze trước validation, artifact
đạt trước promotion. Chia bừa một năm thành các tháng độc lập sẽ làm sai vị thế,
warmup, daily/overall risk và phase reset. Trên broker thật, mọi phiên cùng
account còn dùng chung quyền/risk/positions/pending/unknown locks.

## 5. Dự kiến khi tăng số lượng, không nhầm tầng nhanh

| Ví dụ trên cùng workload Q1/2022 | Thời gian | Tính chất |
|---|---:|---|
|8rules feasibility đã có |~0,963giây tổng |Đã đo; không PnL |
|100rules đơn giản đã có code, compute như8bản cũ |Thuần tính tuyến tính~0,78giây + load~0,90giây; dự trù vài giây tới vài chục giây |Ước tính chưa đo, hiện mới8rules; không gồm research/code/tests/data mới |
|20rules economic tick screen,4workers |5lượt×13,1phút ≈66phút |Ngoại suy baseline cũ, chưa chạy; giữ cùng data/2cost/4worker và độ phức tạp tương tự, contention có thể đổi |
|100rules economic tick screen,4workers |25lượt×13,1phút ≈5giờ28phút |Ngoại suy chưa đo, không phải100bản kiểm lợi nhuận trong vài giây; chưa tính full year/prop/OOS |
|Full-year sau core optimization |Chưa có whole-run benchmark |Chỉ có snapshot validation1,62–1,79×; không trình bày ETA chắc chắn |

Kho nghiên cứu nên giữ hypothesis/family/version, input/split/exposure, params,
source, costs, verdict/uncertainty và wall/CPU/rework của **mọi trial**, kể cả âm.
Nhiều kết quả trên cùng EURUSD/windows làm kho tri thức dày hơn, không tạo thêm
nhiều dữ liệu thị trường độc lập hoặc làm AI tự học nếu chưa có pipeline học.
Các cost scenarios/rerun kỹ thuật không phải những mẫu kinh tế độc lập.

Nguồn primary kiểm07/11: [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
khuyến nghị hypothesis trước outcome và giữ OOS. [Harvey–Liu, Evaluating Trading Strategies](https://people.duke.edu/~charvey/Research/Published_Papers/P116_Evaluating_trading_strategies.pdf)
giải thích việc thử nhiều chiến lược làm số đo tốt nhất bị thiên lệch nếu không
xét multiple testing. Do đó mở rộng được, nhưng không dùng số lượng hoặc top
leaderboard làm chứng nhận edge; DSR/PBO/FDR chỉ áp khi đủ dữ liệu/assumptions.
SSRN trả403; đã đọc bản paper từ trang tác giả Duke, không sao chép toàn văn.

**Khuyến nghị:** bắt đầu bằng kho30–50hồ sơ + một lô rules đã chuẩn hóa, mở rộng
probe hàng loạt, economic screen hữu hạn và giữ2–4bản kiểm sâu khi thật sự có
lý do. Nếu muốn economic screening cũng nhanh hàng loạt thì cần xử lý khoảng
trống coarse-PnL có kiểm chéo trước; chưa dispatch100study từ đề xuất này.
