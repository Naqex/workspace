> Historical dispatch brief, superseded after root integration on 01/11/2026.
> This is not current authority to start providers, commit concurrently or use old ports.
> Current results: [replay-link-review.md](../../../projects/trader/foundation_v2/evidence/owner-system-audit-20261031/replay-link-review.md).
> Correction: fresh=1 opens a form; only clicking Create posts a new session.
> Existing activity tracking is separate from session creation.

# Brief: replay_link — link ?dataset= tự tạo session

`route-census.md` (cùng thư mục evidence owner audit) rủi ro 1: mở link `?dataset=X` không có `fresh=1` và không có session nhớ sẵn thì trang tự POST `/replay/sessions` khi mount (`foundation_v2/web/src/ReplayWorkspace.jsx` khoảng dòng 403). Bookmark hay mở lại link đều tạo session mới.

Việc:

1. Đọc code, tìm mọi nơi sinh link `?dataset=` (QuickSessionDialog, Dashboard, Data desk, Learn…) và xác định nơi nào thật sự cần tạo session ngay.
2. Hành vi mong muốn: chỉ thao tác người dùng (bấm tạo, hoặc link có `fresh=1` sinh từ nút tạo) mới tạo session. Mở link chỉ có dataset thì trang chỉ đọc: nếu dataset đã có session gần nhất, mở session đó; nếu chưa có, hiện màn chọn hoặc tạo session có nút rõ ràng. Reuse component có sẵn.
3. Sửa tối thiểu, giữ đúng các luồng đang dùng `fresh=1`.

Kiểm chứng:

- `npx vite build --outDir $env:TEMP\replaylink-build --emptyOutDir`.
- Browser test Playwright theo pattern có sẵn trên cổng 5246, API mock, ghi lại mọi POST. Mở `?dataset=X` thì 0 POST. Mở link `fresh=1` từ nút tạo thì đúng 1 POST. Reload thì không có POST mới.
- Chạy lại các browser test liên quan tới replay/dashboard quick session đang có.

Commit: `fix(web): open dataset links without creating a replay session`.
## Quy tắc chung cho mọi agent

- Workspace `D:\ANNAM\TradingWorkspace`, Windows/PowerShell. Trả lời tiếng Việt ngắn gọn, thân thiện.
- Server proxy AI đang quá tải. Gặp 429 thì cứ thử lại, làm chậm, gộp đọc file, ghi kết quả ra file sớm rồi cập nhật dần.
- Nhiều agent commit song song. Chỉ `git add` file của mình, kiểm tra `git diff --cached` trước khi commit, gặp `index.lock` thì đợi vài giây rồi thử lại.
- Repo Trader (`projects/trader`, branch `codex/note-workspace-completion`): trailer `AI-Model-Requested: unknown` rồi dòng cuối `AI-Tool: Codex`. Không stage `foundation_v2/evidence/` hay `tests/owner-*.browser.mjs` untracked.
- Khu AI (`Ai*.jsx`, `ai-*.css`, `FxReplayShell.jsx`, `main.jsx`) đang được agent `/root/studio_redesign` sửa. Không động vào các file đó.
- `src/testing-copy.json`: một entry một dòng, CRLF, không key trùng; chạy `node --test tests/testingCopy.test.mjs`.
- Không đụng cổng 5180/8010/3100/17852. Dùng cổng riêng được giao, `strictPort`, dừng đúng PID mình mở.