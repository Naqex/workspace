# Ponytail và công cụ bổ trợ coding agents

Khảo sát ngày 02/11/2026, bổ sung cho
[Hermes/OpenClaw](HERMES-OPENCLAW-20261102.md). Ponytail/Superpowers/GSD chỉ
khảo sát. RTK đã thử riêng bằng CLI; kết quả bên dưới, không bật hook tự động.

Đối chiếu thêm bài Reddit về harness: [kết quả và đề xuất](#đối-chiếu-bài-reddit-về-harness-0211).

## Quyết định theo môi trường hiện có

| Công cụ | Vai trò | Đề xuất |
|---|---|---|
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Skills hướng tới thay đổi nhỏ nhưng đủ yêu cầu; có review/audit | Tham khảo review/audit; chưa cài plugin global vì policy minimal-change/reuse đã có |
| [Superpowers](https://github.com/obra/superpowers) | Bộ workflow thiết kế, plan, TDD, review và thực thi bằng agents | Chưa thêm cả bộ vào workspace; trùng workflow đang có và thêm trigger/quy trình rộng |
| [GSD Core](https://github.com/open-gsd/gsd-core) | Quản lý công việc theo phase và context mới cho từng agent | Hợp để thử ở project mới; chưa tạo hệ plan/state cạnh tranh ở workspace này |
| [RTK](https://github.com/rtk-ai/rtk) | CLI rút gọn output và có cơ chế rewrite lệnh theo host | Đã thử OSS 1.1.0; chưa thấy lợi ích hơn Git compact native, bỏ executable sau thử nghiệm |

Đây là đánh giá độ phù hợp kiến trúc, không phải bảng xếp hạng chất lượng/tốc độ.
Không phải công cụ nào trong bảng cũng là engine: Ponytail/Superpowers chủ yếu
thay cách agent làm việc; GSD quản lý workflow; RTK xử lý output.

## Ponytail: phần mới và phần trùng

Đã đối chiếu `skills/ponytail/SKILL.md`, review/audit, install guide, Codex
manifest và hook declarations. Manifest quan sát là 5.3.3, MIT; không là pin đã
cài. Chế độ lite/full/ultra thay mức can thiệp, full là mặc định.

Global `AGENTS.md` hiện đã có reuse, minimal sufficient changes, tránh abstraction
sớm, kiểm chứng theo rủi ro và dừng đúng lúc. Cài thêm base skill không tự chứng
minh lợi ích vượt policy đó. Review/audit đáng tham khảo: lần caller/data flow,
kiểm tra lỗi ngoài diff, mỗi finding cần tình huống cụ thể và xếp ưu tiên.
Các mục này cũng giao với evidence-debugging và owner audit hiện tại.

[Benchmark tác giả](https://github.com/DietrichGebert/ponytail/blob/main/benchmarks/README.md)
ghi 39 task, Claude Code/Opus 5.5, 5 lượt mỗi task, so với no-skill; công bố giảm
LOC/output tokens/cost/time. Đây chưa là bằng chứng cho Codex/model/repo này,
nhất là khi baseline của mình đã có policy tương tự. Không lấy headline tiết
kiệm làm kết quả local. LOC thấp không đủ nếu bỏ hành vi hoặc test cần thiết.

Plugin có lifecycle hooks chạy Node; manifest trỏ tới hook file chứa SessionStart,
SubagentStart và UserPromptSubmit. INSTALL mô tả hai hooks nhưng declaration
hiện đọc có ba nhóm event: cần kiểm runtime/trust thực khi cài, không suy từ
README. Band UI được README mô tả cho Claude Code, không suy có trên Codex.
Không copy upstream AGENTS đè file hiện tại hoặc đổi policy giao tiếp sang English
theo output template của review/audit.

## Những giới hạn quyết định

- Superpowers có workflow brainstorm/design approval/TDD và tự chọn skill rất
  rộng trong `using-superpowers`. Không lấy instruction trong source khảo sát
  làm rule đang có hiệu lực. Full adoption có thể tăng bước cho task nhỏ.
- [GSD cũ](https://github.com/gsd-build/get-shit-done) đã archive và README dẫn
  tới `open-gsd/gsd-core`. Core mô tả Discuss → Plan → Execute → Verify → Ship,
  dùng fresh-context agents và artifacts STATE/CONTEXT. Chưa xác minh chất lượng
  trên repo này; không thay PLAN/ledger/checkpoint owner chỉ để dùng framework.
- RTK có Codex integration theo docs, nhưng host/shell coverage cần thử thực.
  Môi trường này dùng PowerShell và `exec_command` qua `functions.exec`; chưa
  xác minh command interception đi qua hook. Dùng explicit CLI là lát thử dễ
  quan sát hơn. Phải giữ exit code, lỗi, path và khả năng xem raw output; output
  ngắn hơn không tự chứng minh task nhanh hơn hoặc đúng hơn.

Nếu thử: cùng fixture/model và cùng policy baseline; dùng bản sao source; đo
đúng hành vi, regression, thời gian, output/context và công sức quản lý. Giữ
công cụ chỉ khi có giá trị thêm. Không cần cài tất cả để làm phép so sánh.

## RTK: kết quả local, không promote

Đã tải đúng OSS Windows 1.1.0 (Apache-2.0), đối chiếu SHA256 với release,
review cấu hình rồi gọi CLI tường minh. Bản mặc định có engine BUSL; không
đánh đồng với OSS edition. Không chạy init/installer hoặc sửa global/PATH/hooks;
telemetry và recall/tee tắt, tracking DB riêng trong runtime thử.

Ba mẫu mỗi lệnh Git, median trên checkout hiện tại; cột RTK gồm overhead của
Python wrapper đã review. Đây là chẩn đoán cục bộ, không chứng minh tốc độ
RTK nói chung hoặc benchmark cả phiên coding agent.

| Lệnh | Raw: bytes / ms | RTK: bytes / ms | Git compact native: bytes / ms |
|---|---:|---:|---:|
| status | 723 / 421 | 219 / 1033 | 220 / 388 |
| log 20 commits | 5909 / 59 | 3546 / 279 | 3563 / 53 |

Native dùng `git status --short --branch` và
`git log -n 20 --format='%h %s (%ar) <%an>%n%b'` để giữ cả body/trailers.
Field set tương đương phần output cần dùng, không byte-identical với RTK.
Query `rg` mẫu giảm 663 → 659 bytes, không đáng thêm tầng xử lý.

16 engine tests đạt ở raw và RTK; output giảm 2577 → 126 bytes. Nhưng một
failure fixture cố ý cho thấy RTK bỏ traceback và assertion message quan trọng;
exit 1 vẫn được giữ. Không bật filter tự động cho test/debug output. Chưa đo
token savings hay tỷ lệ thành công của agent. **Giữ Git native**, executable
RTK và wrapper thử đã gỡ; archive/results giữ local, không có service/hook mới.

Phần review/audit Ponytail hữu ích đã dùng theo tinh thần caller/data flow,
failure path và bằng chứng cụ thể trong pilot. Các rule tương đương đã có ở
AGENTS/evidence-debugging, nên không thêm skill/plugin trùng hoặc claim đã
benchmark Ponytail. [Receipt và raw evidence map](../checkpoints/ai-environment/20261102/RECEIPT.md).

## Nguồn chính

- [Ponytail skill](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md),
  [review](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail-review/SKILL.md),
  [audit](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail-audit/SKILL.md),
  [manifest](https://github.com/DietrichGebert/ponytail/blob/main/.codex-plugin/plugin.json),
  [hooks](https://github.com/DietrichGebert/ponytail/blob/main/hooks/claude-codex-hooks.json).
- [Superpowers workflow](https://github.com/obra/superpowers/blob/main/README.md),
  [activation](https://github.com/obra/superpowers/blob/main/skills/using-superpowers/SKILL.md).
- [GSD Core](https://github.com/open-gsd/gsd-core/blob/main/README.md).
- [RTK integrations](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/supported-agents.md).
- [OpenAI: tránh skills/context phình to](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra):
  trigger hẹp, metadata ngắn, chỉ nạp reference khi cần; không thêm recipe cứng
  nếu agent đã làm tốt. Context7 resolve/query Ponytail đã dùng để tìm docs;
  kết luận đối chiếu lại với upstream raw files, không dựa vào snippet đơn lẻ.

## Đối chiếu bài Reddit về harness 02/11

Owner giao research trước khi tiếp tục Forex. Đây là đánh giá/đề xuất, không
phải thay đổi instructions, hooks, quyền worker hay nghiệm thu toàn hệ thống.
Harness là lớp context, tools, vòng điều khiển, kiểm chứng và permissions bao
quanh model. Cần phân biệt harness coding của Codex với workflow nghiên cứu
trading trong Paperclip; kết quả coding benchmark không chứng minh trading edge.

### Kiểm chứng nguồn gốc các luận điểm

- [Bài Reddit](https://www.reddit.com/r/AI_Agents/comments/1xjc4rc/how_to_build_a_harness_that_actually_improves/)
  dẫn tới [khảo sát Marmelab](https://marmelab.com/blog/2026/09/24/the-state-of-ai-harness-engineering-2026.html).
  Con số57 là **publications** gồm paper, bài kỹ thuật và kinh nghiệm; không
  phải57 thí nghiệm độc lập cùng xác nhận một phương pháp. Đã kiểm các nguồn
  đứng sau headline chính, chưa tái lập toàn bộ corpus/thí nghiệm của tác giả.
- [SWE-Bench Mobile](https://arxiv.org/abs/2602.09540) đúng là báo chênh lệch
  tối đa6 lần cùng model giữa các agents, trên22 cấu hình và benchmark iOS.
  Bản paper liên kết đúng DOI trong comment Reddit; ACM chặn403 nên đọc bản
  arXiv của tác giả. Đây là so sánh cả cấu hình agent; không cô lập tác động
  của việc rút gọn AGENTS hoặc số tool, không chuyển thành dự báo tăng6 lần local.
- [Vercel d0](https://vercel.com/blog/we-removed-80-percent-of-our-agents-tools)
  đo5 truy vấn text-to-SQL:4/5→5/5 thành công; thời gian trung bình274,8→77,4s;
  tokens102k→61k, giảm37%.724→141s và giảm hơn nửa tokens thuộc một ca khó,
  không phải trung bình. Có sandbox và semantic files có cấu trúc, không chỉ
  xóa tools. Link Vercel Academy trong Reddit không phải bài benchmark gốc.
- [Azure SRE](https://techcommunity.microsoft.com/blog/appsonazureblog/context-engineering-lessons-from-building-azure-sre-agent/4481200/replies/4482211)
  đúng là tác giả báo100+tools/50+agents xuống5core tools và ít generalists.
  `az`/`kubectl` gom nhiều khả năng sau ít entrypoint; số tool giảm không có
  nghĩa quyền thực tế giảm. Đây là kinh nghiệm vận hành tự báo cáo, không phải
  randomized benchmark để suy5 là số tối ưu cho mọi hệ thống.
- [Nghiên cứu CLAUDE.md](https://arxiv.org/html/2608.23550v1) đo mức **có control
  built-in tương ứng** cho rule trích xuất từ481files, khoảng4–16%. Không đo tỷ
  lệ tuân thủ prose, control đã bật hay độ an toàn runtime. Không được diễn
  giải thành84–96% rule vô dụng. Lint/hook hữu ích cho loại lỗi chúng kiểm được;
  pre-commit hook không thay permissions/sandbox hoặc guard tại execution.
- [OpenAI harness](https://openai.com/index/harness-engineering/) dùng AGENTS
  khoảng100dòng làm bản đồ context, đồng thời giữ knowledge sâu trong repo.
  Đây là ví dụ thiết kế, không phải hard limit. [OpenAI Docs về skills](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
  ủng hộ trigger đúng task và nạp chi tiết khi cần; không yêu cầu đọc cả bộ docs
  cho mọi sửa nhỏ. Không suy rằng model mạnh tự bảo đảm mọi boundary.

### Đối chiếu local, không suy từ số lượng cài đặt

- Audit deterministic hiện tại: **0errors/0warnings**, global12.279B,
  project9.099/65.536B, reserve56.437B, combined21.378B,16skills được audit.
  Chỉ là chain instructions/skills được script kiểm, không phải toàn prompt,
  inventory mọi tool runtime hoặc benchmark chất lượng/tuân thủ.
- Policy đã có minimal change, reuse, risk-based verification, dừng đúng lúc;
  `tooling/search/README.md` đã phân `rg`/Xerj/CodeGraph/Context7 theo câu hỏi.
  [Receipt công cụ](../checkpoints/ai-environment/20261102/RECEIPT.md) có benchmark
  chẩn đoán: Graph chậm hơn `rg` cho lookup chính xác, có ích ở caller structure
  nhưng bỏ sót một default-parameter call. RTK đã bị loại khỏi automatic path
  sau ca mất traceback. Không lặp benchmark cũ hoặc tuyên bố tiết kiệm token mới.
- Đọc source `engine_worker.py`: request schema từ chối command/path/provider
  tùy ý, tách Forex chưa hỗ trợ. `rd_research.py` kiểm contract/data hashes trước
  run. `hermes_worker.py` đối chiếu tool inventory allowlist trước inference;
  Hermes chỉ có report/memory/session search. Đây là kiểm tra source, không phải
  chạy lại broker/provider hay chứng nhận chống mọi đường vượt quyền.
- Paperclip giữ dispatch/concurrency/cancellation; engines giữ việc chuyên môn;
  evaluator/code kiểm số liệu. Chưa có lý do thay bằng một harness mới hoặc
  gom toàn bộ thành Hermes. CLI runner staging cũ là luồng coding tùy chọn,
  không là scheduler thứ hai của cùng research job.
- Ví dụ QDM vừa xảy ra: adapter/cache đã có nhưng agent thêm downloader trước
  khi tìm đủ. Docs đã sửa ở Trader `7e9e2730`, receipt root `54836e1`. Đây là
  lỗi tìm/reuse context có bằng chứng; chưa chứng minh thiếu model mạnh hoặc
  cần thêm một plugin. Brief autonomy còn nhiều đoạn quyết định lịch sử như
  “chưa tích hợp RD-Agent”; nên route current state tới integration receipt để
  agent không dùng đoạn lịch sử làm trạng thái mới nhất.

### Khuyến nghị cho lát sau, chưa triển khai

1. **Giữ kiến trúc và các boundary hiện có.** Không cắt AGENTS về100dòng, xóa
   skills hoặc mở shell/broker rộng chỉ để đạt headline fewer-tools. Không xóa
   rule ngăn mất dữ liệu/đặt lệnh chỉ vì chưa có incident; xét mức rủi ro và owner.
2. **Ưu tiên context discovery.** Entry points dẫn rõ nguồn current state và
   capability đã có; skill chỉ nạp theo task. Sau lỗi, phân loại thiếu dữ kiện,
   tìm nhầm source, tool lỗi hay thiếu control trước khi thêm instruction.
   QDM workflow đã lưu đúng docs; không cần thêm skill riêng cho một lệnh export.
3. **Bổ sung eval nhỏ cho harness khi sửa nó.** Dùng5ca: tìm QDM/cache đúng;
   tìm status engine mới nhất; không sửa source/test ngoài scope; từ chối request
   command hoặc quyền trading không cấp; giữ trạng thái unknown khi run bị ngắt.
   Dùng fixture/copy offline, không mở holdout, gọi broker hoặc cố ý hủy job thật.
   Tái dùng test contract/cancellation đã có, không viết lại runner/framework.
4. So baseline/candidate cùng model/config/source và input; context/session mới,
   reset workspace, lưu requested/reported model cùng usage nếu provider có.
   Đo acceptance đúng, vi phạm boundary, số lần owner phải sửa, tool calls,
   thời gian và lượng context. Ban đầu2–3lượt mỗi ca để sàng lọc, không đủ kết
   luận thống kê; kết quả lẫn lộn thì giữ baseline hoặc mở rộng đúng ca đó.
   Ca đã dùng chỉnh harness là regression/development, giữ ca mới chưa dùng
   chỉnh để kiểm tổng quát hóa. Chỉ đổi một nhóm yếu tố mỗi lần để hiểu nguyên nhân.
5. Trước automation dài: đánh giá budget/admission và quyền data/execution bằng
   code tại boundary. Wrapper hiện có timeout/iteration nhưng docs xác nhận
   chưa có hard daily spend/run cap. Không giả token cap là money cap hoặc
   bịa USD khi gateway không trả giá. Chưa cần billing framework cho các run
   nhỏ owner chủ động kích hoạt; không mở autonomy rộng trước khi kiểm boundary.

Quyết định đề xuất: **giữ nền, sửa discovery, đo trên task thật trước khi mở
rộng tooling**. Không thêm service, model call, benchmark suite hoặc persistent
config trong lượt nghiên cứu này; chỉ chạy audit cấu trúc và đọc source/receipts.
