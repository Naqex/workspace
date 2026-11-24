# Chủ động quản lý skills

Owner giao05/11/2026: agent chủ động xét tạo/cập nhật/đánh giá/dọn skill khi làm
việc, không chờ nhắc. Dùng `ai-environment-maintainer` hiện có, không tạo manager
cạnh tranh hoặc sửa global policy. Đây là instruction khi agent chạy, không
daemon/scheduler hay hứa background tự chỉnh khi không có agent làm việc.

## Trigger và hành động

24/11 (`/learn` mặc định trình bày tiếng Việt đơn giản, dễ hiểu): Theo phản hồi trực tiếp của owner và bản đề xuất đã duyệt (`learning_proposal.md`), cập nhật có chọn lọc 2 tệp owner trong phạm vi workspace: (a) `.agents/rules/trading-workspace.md` (`trigger: always_on`, thêm 1 câu quy ước mặc định trình bày tiếng Việt đời thường, dễ hiểu trong báo cáo/giải thích, tránh thuật ngữ viết tắt nặng trừ khi owner chủ động yêu cầu phân tích chuyên sâu); (b) `knowledge/owner/PROFILE.md` (cập nhật dòng `Ngôn ngữ giao tiếp`). Không tạo skill mới, không sửa `AGENTS.md` hay cấu hình toàn cục.
Positive walkthrough: khi tổng kết kết quả chiến lược, vận hành VPS hay kiểm thử cho owner, trình bày ngắn gọn bằng ngôn ngữ đời thường kèm số tiền USD/VND và ý nghĩa thực tế. Negative: khi owner chủ động yêu cầu phân tích kỹ thuật chuyên sâu hoặc cần đường dẫn/mã code chính xác để kiểm chứng thì vẫn giữ nguyên độ chuẩn xác kỹ thuật. Đây là manual semantic walkthrough bởi cùng agent, chưa forward-test routing bằng model độc lập.

24/11 (Tạo mới repo skill `naqex-node-ops` cho vận hành Home-VPS local + Heroku EU Dead-Man's-Switch + Telegram Guard): Theo yêu cầu và phê duyệt của owner sau khi hoàn thiện máy phụ `naqex-node1` (`Windows 10 IoT Enterprise LTSC`, `192.168.1.28` / `100.72.70.18`), Heroku EU (`naqex-deadman-eu`, `12 USD/mo <= 13 USD/mo` Student cap), bot `@naqex_guard_bot` và di trú 2 collector Binance read-only (`OrderSend = 0`) sang `naqex-node1`: tạo mới `.agents/skills/naqex-node-ops/SKILL.md` đóng gói topology SSH 2 đường, phân bổ 3 ổ `C:/D:/E:` (khóa pagefile trên `C:`, cấm đặt MT5/bot lên ổ `E:` gãy ngàm), chuẩn kiểm tra NTP `< 2s`, quy trình update `.ex5`/preset/red-news fail-closed chỉ khi `open_positions = 0` kèm SHA-256 `9/9`, bảo trì Windows cuối tuần, vận hành Heroku/Telegram không lưu secret ra file/CLI, và tách rõ ranh giới khỏi `quant-factory-ops`. Không sửa `AGENTS.md` hay cấu hình toàn cục.
Positive walkthrough: yêu cầu kiểm tra sức khỏe `naqex-node1`, sửa lệch đồng hồ NTP, cập nhật `.ex5`/`naqex_red_news_utc.csv` khi flat, kéo log crypto shadow từ `naqex-node1`, hoặc bảo trì Heroku/Telegram định tuyến về `naqex-node-ops` với `OrderSend = 0` và rào chắn `open_positions = 0`. Negative: nghiên cứu chiến lược/backtest (`strategy-research`/`quant-factory-ops`), học trading, sửa UI, thuê VPS thương mại hoặc mở khóa Holdout `>= 2025-01-01` không kích hoạt skill này. Đây là manual semantic walkthrough bởi cùng agent, chưa forward-test routing bằng model độc lập. `check_skill_links.py --skills-dir .agents/skills --review-triggers` (`17 skills; 0 errors; 0 advisory warnings`), `audit-ai-environment.ps1 -Force` (`0 errors/0 warnings`; global `12.279 B`, project `10.298/65.536 B`, reserve `55.238 B`, combined `22.577 B`) và `system_doctor.py --mode fast` (`9/9 PASS`) đều đạt.

24/11 (`/learn` nén thời gian thông minh — Event-Driven Gates, Micro-Canary & Parallel Lanes): Sau khi owner chỉ ra việc đặt cổng chờ tuần tự theo ngày lịch cứng (`14d / 30d / nhiều tháng`) gây tốn thời gian không cần thiết khi vẫn đạt độ an toàn/hiệu suất tương đương, cập nhật có chọn lọc 3 tệp owner hiện có: (a) `.agents/skills/quant-factory-ops/SKILL.md` (thêm Mục 5: *Event-Driven Time Compression & Parallel Execution Discipline* — ưu tiên cổng sự kiện/mẫu thực + micro-canary giới hạn lỗ, chạy song song các nhánh độc lập, và kiểm định bác bỏ nhanh trên cache SSD cục bộ); (b) `.agents/skills/strategy-qualification/references/validation-gates.md` (thêm Luật 11 tách rõ *ràng buộc bất biến* vs *đệm ngày lịch tùy ý* khi xét chuyển pha `G5/G6`); (c) `knowledge/owner/PROFILE.md` (bổ sung sở thích nén thời gian thông minh đã xác nhận). Không tạo skill mới, không sửa `AGENTS.md` hay cấu hình toàn cục.
Positive walkthrough: khi lập lộ trình forward/challenge mới hoặc chờ telemetry thụ động, đề xuất rõ cả fast-path theo sự kiện (`>= 10–15` lệnh đóng sạch qua phiên/rollover/tin đỏ + micro-canary `39 USD`) lẫn conservative-path và lập tức đẩy song song các nhánh độc lập (R&D v2 trên Dev, VPS/Cockpit, Own-Book). Negative: không bao giờ nén ranh giới bất biến (`Holdout 2025+ SEALED`, `OrderSend = 0` mặc định, cấm sửa tham số v1 đang chạy live). Đây là manual semantic walkthrough bởi cùng agent, chưa forward-test routing bằng model độc lập. `check_skill_links.py --skills-dir .agents/skills --review-triggers` (`16 skills; 0 errors; 0 advisory warnings`), `audit-ai-environment.ps1 -Force` (`0 errors/0 warnings`; global `12.279 B`, project `10.298/65.536 B`, reserve `55.238 B`, combined `22.577 B`), `brain_cli.py index` (`705` files / `4.616` chunks) và `system_doctor.py --mode fast` (`9/9 PASS`) đều đạt.

24/11 (`/learn` hiệu chuẩn định cỡ kế hoạch tự chủ xuyên đêm theo thông lượng thực đo): Sau Đợt 1 (`26` mốc chạy xong trong `48` phút = `~32` mốc/giờ trên 4 lane XHigh), cập nhật có chọn lọc `.agents/skills/quant-factory-ops/SKILL.md` (thêm Mục 4: *Throughput-Calibrated Long-Horizon / Overnight Factory Sizing*, quy định định cỡ `~20–30` đơn vị việc/giờ song song, kết hợp chu kỳ R&D trên dữ liệu mới + vòng lặp phản hồi thực chiến định kỳ mỗi `2` giờ + rào chắn chống overfit/chống vẽ việc rác) và bổ sung 1 dòng kỳ vọng đã xác nhận vào `knowledge/owner/PROFILE.md`. Không tạo skill mới, không sửa `AGENTS.md` hay cấu hình toàn cục.
Positive walkthrough: yêu cầu chạy tự chủ `6–12` tiếng qua đêm định cỡ theo thông lượng thực đo của swarm và mở rộng theo dữ liệu/thị trường mới + live feedback định kỳ thay vì checklist tĩnh 25 mốc. Negative: task nhỏ 1–2 bước hoặc tái cày cùng tập FX Dev cũ bị chặn bởi rào chắn chống overfit/busywork. Đây là manual semantic walkthrough bởi cùng agent, chưa forward-test routing bằng model độc lập. `check_skill_links.py --skills-dir .agents/skills --review-triggers` (`16 skills; 0 errors; 0 advisory warnings`), `audit-ai-environment.ps1 -Force` (`0 errors/0 warnings`; global `12.279 B`, project `10.298/65.536 B`, reserve `55.238 B`, combined `22.577 B`) và `brain_cli.py index` đều đạt.

23/11 (Nâng cấp Research 2 chế độ + Personal Knowledge Vault & Owner Memory): Tạo mới repo skill `research-and-memory-ops` và cập nhật có chọn lọc 3 điểm nối hiện có theo yêu cầu chuẩn hóa quy trình research đa nguồn (EN/VI/CN/RU, Reddit, arXiv, OpenAlex, GitHub, Habr, QuantSE, PDF/YouTube) và bộ nhớ dài hạn của chủ sở hữu: (a) tạo `.agents/skills/research-and-memory-ops/SKILL.md` chuẩn hóa tra cứu Memory-First (`brain_cli.py owner-brief` + `query` `< 40 ms`), 2 chế độ research (Chế độ 1 AI tự research theo quyết định & Chế độ 2 owner chỉ đạo đa nguồn kết hợp `search_web` + `research_cli.py search/fetch`), phân tầng độ tin cậy `T1/T2/T3`, lưu tách biệt `knowledge/inbox/` (gitignored) → `knowledge/topics/` hoặc `planning/research/`, và vòng lặp học chủ sở hữu (`log-curiosity`, `log-decision`, `PROFILE.md`) kết thúc bằng `brain_cli.py index`; (b) nối liên kết từ `.agents/skills/evidence-continuity/SKILL.md`, `tooling/search/README.md` và `planning/CURRENT-CONTEXT.md`; (c) mở rộng `tooling/search/xerj.py` nhận `knowledge/**/*.md` (trừ `inbox/`/`archive/`) và thêm `check_brain_index()` + tối ưu `check_derived_cache()` (`1,79s → 0,17s`) vào `system_doctor.py`. Không sửa `AGENTS.md` hay cấu hình toàn cục.
Positive walkthrough: yêu cầu research sâu cộng đồng Nga/Trung/Reddit/arXiv hoặc ghi nhận câu hỏi/quyết định liên lĩnh vực của owner định tuyến vào `research-and-memory-ops`, tra `brain_cli.py` trước, trích xuất Markdown có nhãn `untrusted_external_data: true` và cập nhật index. Negative: hỏi đáp lặt vặt, dịch thuật, sửa copy, chạy backtest quant (`strategy-research`/`quant-factory-ops`) hoặc mở Holdout/lệnh sàn không kích hoạt skill này và bị chặn fail-closed. Đây là manual semantic walkthrough bởi cùng agent, chưa forward-test routing bằng model độc lập. `check_skill_links.py --skills-dir .agents/skills --review-triggers` (`16 skills; 0 errors; 0 advisory warnings`), `check_workspace.py` (`9 guides, 8 pinned submodules`), `audit-ai-environment.ps1 -Force` (`0 errors/0 warnings`; global `12.279 B`, project `10.298/65.536 B`, reserve `55.238 B`, combined `22.577 B`) và `system_doctor.py --mode full` đều đạt.

23/11 (Pass 28+ · `/learn` nâng cấp kiến trúc Quant Factory 4 tầng & rà soát điểm mù Pre-Holdout): Tạo mới repo skill `quant-factory-ops` và cập nhật có chọn lọc 3 tài liệu hiện có theo đề xuất `/learn` đã được owner duyệt: (a) tạo `.agents/skills/quant-factory-ops/SKILL.md` định nghĩa quy trình tự động kiểm định (`system_doctor.py --mode fast|full`), bảo trì cache `.npz` zero-pickle, chống phình index/JSON (`README <= 150 dòng`, `CURRENT-CONTEXT <= 12 KB`, branch JSON `< 900 KB`), nâng cấp thư viện cục bộ an toàn qua `uv pip --only-binary=:all:` vào `.runtime/quant-audit-v24`, và giữ nguyên ranh giới fail-closed (`holdout_rows = 0`, `OrderSend = 0`, không sửa global config); (b) cập nhật `whitebox-prop-discovery/SKILL.md` trỏ sang `quant_factory/`, `configs/*.json`, `exports/Include/Naqex_PropGuard.mqh` và `system_doctor.py` cho mọi đợt từ Pass 29+; (c) bổ sung mục 9–10 vào `strategy-qualification/references/validation-gates.md` (Cumulative DSR/PSR + Worst-5% Tail Correlation trước Holdout; Per-Symbol Concurrent Risk Cap `<= 1%` Funded chống luật gộp *trade-idea bundle* FTMO + `±5m` tin đỏ + hợp đồng parity `Naqex_PropGuard.mqh`); (d) nối `engineering-retrospective/SKILL.md` tới `quant-factory-ops` cho vận hành định kỳ. Không sửa `AGENTS.md` hay cấu hình toàn cục.
Positive walkthrough: yêu cầu kiểm tra sức khỏe hệ thống, tăng tốc quy trình, xử lý file JSON vượt `1 MiB` hoặc chuẩn bị Pass 29+ định tuyến về `quant-factory-ops`, chạy `system_doctor.py` và tái dùng `quant_factory/` + `configs/` thay vì viết lại script đơn khối. Negative: yêu cầu học trading, sửa UI, chọn chiến lược hoặc mở khóa Holdout `>= 2025-01-01` không kích hoạt `quant-factory-ops` và bị chặn fail-closed ở biên Holdout/OrderSend. Đây là manual semantic walkthrough bởi cùng agent, chưa forward-test routing bằng model độc lập. `check_skill_links.py --skills-dir .agents/skills --review-triggers` (`15 skills; 0 errors; 0 advisory warnings`), `check_workspace.py` (`9 guides, 8 pinned submodules`), `audit-ai-environment.ps1 -Force` (`0 errors/0 warnings`; global `12.279 B`, project `10.298/65.536 B`, reserve `55.238 B`, combined `22.577 B`) và `system_doctor.py --mode full` đều đạt.

23/11 (Pass 21–22 · `/learn` sau nâng hạng danh mục 3 động cơ): Tạo mới repo
skill `whitebox-prop-discovery` (Pass 21) và sau Pass 22 cập nhật có chọn lọc
theo đề xuất `/learn` đã được owner duyệt: (a) thêm mục 6–8 vào
`strategy-qualification/references/validation-gates.md` (mẫu đối chứng
`CONTROL` & bắt buộc xác nhận M1 Bid/Ask cho ứng viên H4/D1 từ bài học
`GBPJPY` Pass 19/21; kỷ luật Cụm A → Cụm B mù + BH FDR toàn `m_total` +
Matched-Hold Timing Permutation Null từ Pass 20–22; Outlier/Crisis Stress &
mặt phẳng 2D kép trước khi xuất `.mq5` từ Pass 22); (b) bổ sung runbook vận
hành vào `whitebox-prop-discovery/SKILL.md` (runtime `.runtime/quant-audit-v24`,
đường ống `dukascopy-node` M1 Bid+Ask `< 2025-01-01`, lưu ý pin
`rea-agents@6.7.0` trên `Node v24.19.0`, lệnh `inbox_intake_scanner.py` và
chuẩn hóa negative trigger `do not use`); (c) đồng bộ trạng thái 3 động cơ tại
`planning/CURRENT-CONTEXT.md`. Không tạo rule toàn cục hay sửa `AGENTS.md`.
Positive walkthrough: săn Động cơ #4 trên `XAUUSD`/`US100`/`GER40` bắt buộc
seal M1 Bid+Ask trước, chạy Cụm A → Cụm B mù, BH FDR toàn không gian, Outlier
Stress và 2D kép trước khi xuất `.mq5`. Negative: chỉ hỏi tiến độ, học trading,
sửa UI hoặc thả `.ex4/.ex5/.dll` vào `strategy-intel/inbox/` thì chỉ cách ly
đọc-không-chạy, không thực thi binary và không mở Holdout. Đây là manual
semantic walkthrough bởi cùng agent, chưa forward-test routing bằng model độc
lập. `quick_validate.py` (`Skill is valid!` cho cả `whitebox-prop-discovery` và
`strategy-qualification`), `check_skill_links.py --skills-dir .agents/skills --review-triggers`
(`14 skills; 0 errors; 0 advisory warnings`), `check_workspace.py` (`9 guides, 8 pinned submodules`)
và `audit-ai-environment.ps1 -Force` (`0 errors/0 warnings`; global `12.279 B`,
project `10.298/65.536 B`, reserve `55.238 B`, combined `22.577 B`) đều đạt.

23/11 — Tiếp quản toàn diện sau Pass 11/12 & audit `strategy-intel`: cập nhật
`strategy-qualification/references/validation-gates.md` (thêm 4 luật thực thi:
Straight-to-M1 Bid/Ask cho lệnh chờ nội ngày, FTMO Swap-3× pre-mortem, Monte
Carlo Random-Entry Null Test + độ bền tham số ±30% cho nhánh một chiều, và quy
tắc Air-Gap với kho intel bên ngoài) và trỏ 1 lần từ `strategy-research/SKILL.md`.
Không tạo skill mới hoặc sửa global config. Đồng thời compact `CURRENT-CONTEXT.md`
(88,2 KiB / 1.261 dòng → ~8,5 KiB, giữ byte-exact gzip + `MANIFEST.json` ở
`planning/archive/2026-11-23-pass12-takeover/`) và gỡ tiến độ V22 cũ khỏi `README.md`.
Positive walkthrough: đề xuất pending stop trong ngày (VD US500/GBPUSD ORB)
bắt buộc chạy thẳng M1 Bid/Ask; ý tưởng Long-only trên Vàng từ `strategy-intel`
chỉ nhận đặc tả toán học (Air-Gap) và chạy Random-Entry Null Test + Swap 3×.
Negative: hỏi tiến độ hoặc chạy lại regression không kích hoạt thu thập intel
hay mở Holdout. Đây là manual semantic walkthrough, chưa forward-test routing
bằng model độc lập. `check_skill_links.py --review-triggers` (13 repo skills,
0 errors/0 warnings), `check_workspace.py` (9 guides, 8 pinned submodules) và
`ai-environment-maintainer -Force` (0 errors/0 warnings; lưu ý script global
dùng `rg` nên trong shell không có `rg` trên PATH chỉ quét 4 global skills,
chưa sửa global script).

13/11 — owner đóng chiến dịch sau PR74, yêu cầu Stage-0 trước SL/TP/sizing.
Thêm policy tại `strategy-qualification/references/validation-gates.md`, route
một lần từ `strategy-research`; không tạo skill/script mới hoặc runtime gate.
Tự walkthrough với số giả định: mean net từng năm vượt friction, tỷ lệ scale10%
và reject20% → chỉ qua Stage-0; một năm âm, net nhỏ hơn friction, scale38%
hoặc reject51% → dừng; thiếu quote/cost → blocked. Không chọn lại horizon/cohort
để pass, không coi policy là chứng minh exhaustion/edge. Đây là semantic review,
không model forward-test hoặc backtest mới. Cả hai quick validators đạt.
Instruction kernel không đổi: global12.279B,project10.298/65.536B,
reserve55.238B,combined22.577B; reference chỉ tải khi cần.

13/11 — sau B2, owner yêu cầu design-from-constraints. Reuse
`strategy-qualification/references/validation-gates.md`: thêm owner-scoped
Prop Target Envelope và `PROP_TIMEFIT_REJECTED`; `risk-and-prop.md` chỉ link,
không nhân bản profile. Không skill mới/globalconfig/runtime enforcement.
Sửa các suy luận dễ sai:25–40R/năm chưa đủ6–12tháng mọirisk;15R×0,40%=6%
không phải<6%;daily cap độc lập;flat21:45UTC chưa chắc tránhrollover;R043swap
không thể cộng lại chointradayrecipe. R043 giữ regression, khôngoptimizechallenge.
Positive walkthrough: profile được đọc để soạn G0/B0 và count-only proposal,
không dispatch trước owner duyệt. Negative: F/R thấp hoặc60trades không tự
pass edge/timefit; chỉ hỏi status R043 không rerun; thiếu exitquote khôngswap0.
Đây là manualsemanticreview/sốhọc, không modelroutingtest hoặc backtest mới.
Quickvalidator/scopedlinks đạt; maintainer0errors/0warnings,21skills,
global12.279B,project10.298/65.536B,reserve55.238B,combined22.577B.

12/11 — owner yêu cầu audit và một task từ H1bias→zone/setup→entry tới payout.
Do scope drift đã xảy ra ởTC01, cập nhật7dòng trong `strategy-research`: đối
chiếu chỉ dẫn owner/taskstage trước study mới, tách các tầng strategy và không
gắn bản thiếufilter thành bản cófilter. Không tạo skill mới hoặc sửa global.
Walkthrough tự review: “tiếp H1→M15” phải vềT1/counterpart cóH1, không mởTC01;
owner yêu cầu research rộng thì vẫn được mở scope có đăng ký; chỉ hỏi status
không dispatch. Đây là semantic walkthrough, không chứng minh model luôn làm đúng.
Quickvalidator ban đầu thiếuPyYAML trong productvenv; dùng bundledPython với
`-X utf8` thì đạt, không cài package vào runtime. Maintainer `-Force`:0errors/
warnings,21skills,global12.279B,project10.298/65.536B,reserve55.238B,
combined22.577B. Runtime/worker đang chạy không tự nhận skill đã sửa.

11/11 — owner đổi từ reference-only sang full framework cả5engine. Reuse
`strategy-research` với [native engines](../../.agents/skills/strategy-research/references/native-engines.md),
`upstream-integrations` route tới runtimeguide/locks; không tạo5skill hay
globalconfig. Positive walkthrough: fullNautilusrequest→reuse locked1.xruntime,
không trộn downloaded2.xexamples;3Pythonfixtures vàLEANnativebacktest đã chạy.
Negative: chỉ hỏi tiến độ không install/rerun; smokeequal không US500parity,
4DBtests chặn khôngbypassTRUNCATE. Walkthrough tự review, không independentagent.
Hai skill validators/23local links đạt; maintainer0errors/warnings,
global12.279B,project10.298/65.536B,reserve55.238B,combined22.577B.

09/11 — source-transformations reference bổ sung xử lý LF/CRLF hash drift:
raw/pins gốc giữ nguyên, bind exact frozen snapshot và ghi current code hash
riêng; không normalize raw hoặc chấp nhận content drift. Actual role-source
v1 fail trước geometry; v2 chỉ reuse8raw/35.280fields,0network. Hai integration
negative cases semantic-change/missing-snapshot đều reject trước geometry;
[receipt](../../planning/research/OIL-EIA-ROLE-SOURCE-RESULTS-20261109.md).
Không thêm skill/helper/framework; lineage rule có case lặp và giữ scope.

09/11 — rà lại workflow/workspace trước resume: audit workspace/Trader đều
0 errors/warnings; 16 repo skill entrypoints đã xét trigger/boundary, 76 links
skill/reference hợp lệ. Research/qualification/evidence/retrospective có input
và quyền riêng; giữ nguyên, không gộp hoặc tạo skill manager/framework. Git
vừa tinh gọn được kế thừa, không audit full source/runtime hoặc chạy lại tests
không đổi. Tồn tại context status Goal cũ lẫn routing: lưu snapshot nguyên byte
và compact CURRENT-CONTEXT, sửa index/campaign state theo tool active.
Global/project/reserve giữ các số đo ở mục dưới; chỉ context/docs đổi.

09/11 — tinh gọn GitHub theo yêu cầu owner: giữ tên `github-issue-workflow`,
rút skill 56→31 dòng và ba tài liệu/skill GitHub chính giảm 55,7% byte UTF-8
(chuẩn hóa LF). [Archive](../../tooling/github-workflow/archive/20261109/README.md)
giữ bản trước, ngoài skill discovery. Walkthrough task này: protected repo →
PR, không issue mới; negative case chỉ hỏi/đọc → không Git artifact, broker
request không nhận quyền từ Git. Đây là self-review, chưa independent test.
Skill validator, 5 workflow tests, 33 active local links và đối chiếu 8 snapshot
với Git đạt. Audit workspace/Trader: 0 errors/warnings; không đổi global config.
Global 12.279 B; workspace instructions 10.298/65.536 B, reserve 55.238 B,
combined 22.577 B. Audit standalone Trader: 5.755/65.536 B, reserve 59.781 B,
combined 18.034 B; các chỉ số này theo chain file audit đọc, không cộng lại
parent workspace được chỉ định bằng prose trong checkout standalone.

09/11: `strategy-qualification` thêm nhánh
[chẩn đoán lỗ có chọn lọc](../../.agents/skills/strategy-qualification/references/selective-loss-diagnosis.md).
Reuse entrypoint hiện có; D0 đọc sổ cũ, D1 chỉ giữ/near-miss có câu hỏi rõ,
D2 đăng ký thay đổi sau khi xác minh nguyên nhân. Không hardcode ngưỡng hoặc
cho phép sửa strategy để cứu outcome. Positive manual walkthrough: Goldretained;
negative: R081gross/net yếu không phân tích filter tiếp; materialbug vẫn xử lý.
Actual30books/439tradecases/Fractionreview/6mutations ở
[receipt](../../planning/research/SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md).
Skillcreator validator/scopedlinks/maintaineraudit đạt0errors/0warnings;
global12.279B,project10.133/65.536B,reserve55.403B,combined22.412B không đổi.
Repo skill, chưa publish/assign Paperclip hoặc independentmodelroutingtest.

09/11: source-transformations reference thêm pilot→history partition/role
census trước PnL, không skill mới. [Case thật](../../planning/research/INDEX-PAPER-WINDOW-RESULTS-20261109.md)
raw reviewer bắt omitted US500Q2/Q4; helper full-year buộc4quarters/8side seals,
4regressions và affected repair đạt, unaffected reports/quotes giữ nguyên.
Negative walkthrough: pilot1/3 không là full-year proof; status-only không
kích hoạt fetch/fullrerun. Structure/scoped links và maintainer audit đạt
0errors/warnings, bytes/reserve không đổi. Repo reference, chưa native publish.

09/11: thêm nhánh conditional missing-price sensitivity vào
`strategy-qualification/references/validation-gates.md`, reuse G1/G2 owner,
không skill/config mới. R065 interval và R066 collapsed interval là positive
manual walkthroughs: giữ exact unknown, chỉ đổi ưu tiên nghiên cứu theo
registered criterion. Negative case: BI5 transport timeout không có source
envelope không cho tự bịa bounds/fill hoặc clear unknown. Không forward-test
bằng model độc lập; numerical workers không tự đọc reference mới.
Structure validator (bundled Python), scoped links và maintainer audit đạt:
0errors/0warnings; global12.279B,project10.133/65.536B,reserve55.403B,
combined22.412B. Product venv thiếuPyYAML cho validator; reuse bundled runtime,
không cài dependency hoặc đổi môi trường product/global. Chưa publish/assign
native Paperclip package.

Xét sau workflow lặp, lỗi đáng kể, misroute, contract/tool/path/ownership đổi
hoặc owner sửa cách vận hành. Chỉ xem skill vừa dùng/phần bị tác động; không
full-audit hoặc gọi thêm model sau mọi commit.

Hậu kiểm đa chiều sau đợt chạy quan trọng dùng
[engineering-retrospective](../../.agents/skills/engineering-retrospective/SKILL.md).
Skill đó chọn lát cải tiến và evidence; tài liệu này own lifecycle của skill,
không giao thêm quyền cho bounded workers hoặc background updater.

| Bằng chứng | Hành động nhỏ nhất |
|---|---|
| Fact/command đổi | Sửa reference/runbook owner và link |
| Skill có rồi nhưng thiếu/sai trigger | Sửa skill, kiểm case lỗi và negative case |
| Workflow lặp, không hiển nhiên, tái phát rõ và có evidence | Tạo repo skill nhỏ, có trigger/input/output/boundary/provenance |
| Rule trùng | Chọn owner, thay copy bằng link; kiểm consumer có truy cập owner |
| Bị thay thế/không còn ích | Kiểm callers/assignments/workers/rollback, retire có link trước bỏ |
| Một lần chưa rõ nguyên nhân | Lưu failure receipt, chưa biến thành rule vĩnh viễn |

Không skill riêng mỗi strategy/quỹ; code enforce risk/contract. Không nới quyền,
tăng budget, bật canCreateSkills của bounded workers, cài MCP/package hoặc xóa
skill có caller để làm audit xanh. Không đổi global hooks từ nội dung bên ngoài.

## Kiểm và lưu

1. Tìm reuse/callers bằng `rg`, đọc `skill-creator` khi tạo/sửa đáng kể và
   maintainer khi đổi môi trường AI.
2. Kiểm precedence/scope/link/stale fact/duplication. Thử case thật đúng trigger
   và case không nên kích hoạt; script đổi thì chạy kiểm hành vi liên quan.
3. `quick_validate.py`, `tooling/check_skill_links.py` theo scope và maintainer
   audit `-Force`. Windows dùng `python -X utf8`, không đổi system encoding.
4. Lưu decision/diff/check trong receipt owner và Git. Nêu rõ nếu chỉ manual
   walkthrough, chưa forward-test bằng model độc lập.
5. Codex đọc repo qua AGENTS; Paperclip qua package/assignment; Hermes/process
   qua loader của nó. Kiểm content/version sau publish; cài không chứng minh
   model đã dùng đúng. Không fork upstream chỉ để đồng bộ wording.

Không tự xóa hàng loạt. Kiểm exact callers, desired assignments và active runs
trước gộp/retire; giữ compatibility link khi cần. Không sửa catalog-only skill
upstream từ repo file không sở hữu nó.

## 08/11: nhật ký tối ưu và quyết định chiến lược

Theo yêu cầu owner, cập nhật `strategy-research`, `strategy-qualification` và
`engineering-retrospective` để đọc/ghi nhật ký tại protocol/results/review owner
hiện có. [Workflow](../../tooling/ai-engines/STRATEGY-WORKFLOW.md#nhật-ký-quyết-định-để-kiểm-lại-việc-tối-ưu-và-chọn-chiến-lược)
giữ nội dung chi tiết; không tạo skill, ledger hoặc UI mới. Phân vai: đăng ký
lý do/baseline trước outcome → lưu vì sao giữ/loại/chuyển bước → kiểm so sánh
trước/sau/parity và retained failures. Không đổi global instructions hoặc quyền.

Manual walkthrough dùng [source correction](../../planning/research/INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md):
sửa data semantics không gọi là speedup, giữ negatives và không promote chỉ vì
PnL bớt âm. Negative case: chỉ hỏi tiến độ hoặc sửa copy không kích hoạt full
experiment/audit hoặc rerun batch. Đây là review nội dung, chưa forward-test
routing bằng model độc lập. Ba skill structures/links và maintainer audit đạt
0errors/0warnings; global12279B,project10133B,reserve55403B,combined22412B.
Local native-package bundle đã xuất để kiểm nội dung; chưa publish/assign
runtime Paperclip trong lượt này, không suy repo edit thành agent đang chạy
đã nhận instruction. Numerical/source workers không đọc Markdown vừa sửa.

## 08/11: bàn giao để owner hiểu và vận hành bot

Mở rộng `strategy-qualification` bằng `references/owner-handover.md`; không
tạo skill mới vì kiểm định đã sở hữu quyết định chuyển bước/bàn giao. Nhánh
này dùng khi chuẩn bị prospective demo/challenge hoặc owner chưa giải thích
được bot do AI/code tạo. Đầu ra: thẻ chiến lược gắn version, ví dụ lời/lỗ/lỗi,
USD/R, stop/reconcile/recover và điều kiện quỹ; lưu trong dossier/report cũ.
Không yêu cầu trade tay có lãi, không tự ghi owner hiểu hoặc cấp quyền broker.

Manual walkthrough dùng parent PreECB đang gác: bàn giao → đọc reference,
giải thích rules và giữ `prepared_not_demonstrated`; hỏi tiến độ → không bắt
học hoặc chạy batch/audit mới. Đây là kiểm nội dung bằng cùng agent, chưa là
đánh giá routing bằng model độc lập hay diễn tập thực tế của owner. Structure
validator, scoped skill links và maintainer audit đều đạt: 0 errors/warnings;
global 12.279 B, project 10.133/65.536 B, reserve 55.403 B, combined 22.412 B.
Repo skill đã sửa; chưa publish/assign package Paperclip, không suy worker
đang chạy đã nhận nội dung này. Không thay global config hoặc service nền.
