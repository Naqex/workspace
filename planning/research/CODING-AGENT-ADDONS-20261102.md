# Ponytail và công cụ bổ trợ coding agents

Khảo sát ngày 02/11/2026, bổ sung cho
[Hermes/OpenClaw](HERMES-OPENCLAW-20261102.md). Chỉ đọc docs/source; chưa cài,
chạy installer, bật hooks hay benchmark các ứng viên dưới đây.

## Quyết định theo môi trường hiện có

| Công cụ | Vai trò | Đề xuất |
|---|---|---|
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Skills hướng tới thay đổi nhỏ nhưng đủ yêu cầu; có review/audit | Tham khảo review/audit; chưa cài plugin global vì policy minimal-change/reuse đã có |
| [Superpowers](https://github.com/obra/superpowers) | Bộ workflow thiết kế, plan, TDD, review và thực thi bằng agents | Chưa thêm cả bộ vào workspace; trùng workflow đang có và thêm trigger/quy trình rộng |
| [GSD Core](https://github.com/open-gsd/gsd-core) | Quản lý công việc theo phase và context mới cho từng agent | Hợp để thử ở project mới; chưa tạo hệ plan/state cạnh tranh ở workspace này |
| [RTK](https://github.com/rtk-ai/rtk) | CLI rút gọn output và có cơ chế rewrite lệnh theo host | Ứng viên ưu tiên thử riêng khi output thực sự là bottleneck; chưa bật hook toàn cục |

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
