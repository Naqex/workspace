> Historical dispatch brief, superseded after root integration on 01/11/2026.
> This is not current authority to start providers, commit concurrently or use old ports.
> Current results: [AI-ENV-RESULT.md](AI-ENV-RESULT.md).

# Brief: ai_env — skills và AI environment

Owner giao: cải tiến và cập nhật skills, AI environment (kể cả skill bảo trì AI environment) và tools cho agents; tạo skill có thể cần sau này hoặc dùng dài hạn. Owner cho phép làm mọi thứ.

Bắt buộc đọc và làm theo `C:\Users\MIIKEY\.agents\skills\ai-environment-maintainer\SKILL.md`: audit bằng script của nó trước và sau, đặt đúng layer, giữ budget, chỉ tạo skill khi có bằng chứng thực. Audit lúc giao việc: ok, 0 lỗi, 0 cảnh báo, chain 21 KB/64 KB, 15 skill. Skill hiện có nằm ở `.agents/skills/*` (7 skill) và `projects/trader/.agents/skills/*` (3 skill).

## Bằng chứng thực từ phiên 31/10–01/11

A. Multi-agent trên một repo Git dùng chung: nhiều agent commit song song gây `index.lock`; mỗi agent phải chỉ add file của mình. File copy dùng chung (`testing-copy.json`) cần đúng một người ghi. Agent hay chết vì 429, nên khi giao lại phải dặn "tiếp tục từ diff hiện tại". Spec dài gửi trong message spawn bị cắt (agent nhận thiếu khoảng 17k ký tự), nên ghi spec ra file và gửi đường dẫn (thư mục này là ví dụ). Mỗi agent dùng cổng preview riêng (5241–5249) và dừng đúng PID của mình.
B. Paperclip pilot: xem `planning/checkpoints/ai-integrations-20261031/RECEIPT.md` mục "Pilot đội nghiên cứu Sky AI" và `tooling/paperclip/README.md`. Wakeup thủ công bị skip khi issue đã có run kết thúc, comment không đánh thức agent, nên phải dùng issue mới. Cần `PAPERCLIP_AGENT_JWT_SECRET` trong `.env`. Gateway 17852 trả 413 khi body vượt 64 KB. Có các bản sửa Windows sandbox/env.
C. Trader i18n: định dạng `testing-copy.json` như trong quy tắc chung; test áp quy tắc PnL thay cho P/L; các file AI dùng `say()` riêng.
D. Workflow nghiên cứu AI đề xuất: `planning/research/AI-RESEARCH-WORKFLOW-20261101.md` (cổng G0–G5).

## Việc gợi ý

Bạn tự quyết từng việc và nêu lý do. Tránh trùng skill đã có (github-issue-workflow, upstream-integrations, trading-ui-qa…).

1. Skill workspace cho điều phối multi-agent song song (mục A), ngắn gọn, có negative trigger. Nếu hợp hơn thì gộp vào skill có sẵn.
2. Skill hoặc reference vận hành Paperclip (mục B), có thể là reference của upstream-integrations.
3. Reference i18n cho Trader (mục C), gắn vào trading-ui-qa hoặc ui-platform-workflow.
4. Skill dài hạn cho nghiên cứu chiến lược theo cổng G0–G5 (mục D). Ghi rõ đây là đề xuất và skill không cấp quyền giao dịch.
5. Cải tiến script audit: kiểm link tương đối trong SKILL.md/references trỏ tới file không tồn tại, cảnh báo skill thiếu negative trigger. Giữ tương thích, chạy thử, không làm hook Stop ồn hơn.
6. Thêm `agents/openai.yaml` cho skill còn thiếu nếu thấy hữu ích.

## Ràng buộc

- Không cài package, MCP hay plugin mới; không đổi `~/.codex/config.toml`; không động secrets.
- Giữ AGENTS.md trong budget; chỉ thêm một dòng routing nếu thật cần.
- Skill global ở `C:\Users\MIIKEY\.agents` không nằm trong git: backup trước khi sửa và ghi rõ trong báo cáo.

## Kiểm chứng và commit

- Chạy audit với `-Force` sau thay đổi, kết quả phải 0 lỗi. Test script mới bằng một case dương và một case âm.
- Commit trong root repo chỉ các file `.agents/skills` và tooling liên quan, message `chore(ai-env): ...`, trailer `AI-Tool: Codex`. Skill trong `projects/trader` thì commit ở repo đó với trailer của Trader.
- Báo cáo: đã thêm/sửa gì, vì sao, kết quả audit, hash.
## Quy tắc chung cho mọi agent

- Workspace `D:\ANNAM\TradingWorkspace`, Windows/PowerShell. Trả lời tiếng Việt ngắn gọn, thân thiện.
- Server proxy AI đang quá tải. Gặp 429 thì cứ thử lại, làm chậm, gộp đọc file, ghi kết quả ra file sớm rồi cập nhật dần.
- Nhiều agent commit song song. Chỉ `git add` file của mình, kiểm tra `git diff --cached` trước khi commit, gặp `index.lock` thì đợi vài giây rồi thử lại.
- Repo Trader (`projects/trader`, branch `codex/note-workspace-completion`): trailer `AI-Model-Requested: unknown` rồi dòng cuối `AI-Tool: Codex`. Không stage `foundation_v2/evidence/` hay `tests/owner-*.browser.mjs` untracked.
- Khu AI (`Ai*.jsx`, `ai-*.css`, `FxReplayShell.jsx`, `main.jsx`) đang được agent `/root/studio_redesign` sửa. Không động vào các file đó.
- `src/testing-copy.json`: một entry một dòng, CRLF, không key trùng; chạy `node --test tests/testingCopy.test.mjs`.
- Không đụng cổng 5180/8010/3100/17852. Dùng cổng riêng được giao, `strictPort`, dừng đúng PID mình mở.