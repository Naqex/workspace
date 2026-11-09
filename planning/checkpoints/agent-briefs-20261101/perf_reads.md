> Historical dispatch brief, superseded after root integration on 01/11/2026.
> This is not current authority to start providers, commit concurrently or use old ports.
> Current results: [frontend-performance-audit.md](../../../projects/trader/foundation_v2/evidence/owner-system-audit-20261031/frontend-performance-audit.md).

# Brief: perf_reads — ghi khi rời trang Gateway và N+1 ở Dashboard

`route-census.md` rủi ro 3 và 4. Không sửa `AiGatewayPanel.jsx` (agent Studio đang giữ file đó). Phần Gateway chỉ phân tích và gửi đề xuất trong báo cáo; root sẽ áp dụng sau.

1. Dashboard N+1: Dashboard đọc metadata và analytics riêng cho từng dòng session. Đọc frontend (component dashboard sessions) và backend Rust (`foundation_v2/api-rust`, analytics routes) xem đã có endpoint batch chưa. Nếu có thì dùng; nếu chưa thì thêm endpoint batch nhỏ có giới hạn (ví dụ tối đa 50 id), giữ tenant isolation và cache summary (DB-06 vừa thêm lane cache riêng ở `analytics/routes.rs`). Không migration.
2. Gateway: giải thích vì sao rời trang lại POST `local-gateway/refresh`, có cần không, và đề xuất sửa (diff ngắn) trong báo cáo.

Kiểm chứng:

- `cargo test --lib` cho phần đã sửa và `cargo check --all-targets`.
- Vite build vào `$env:TEMP\perfreads-build`.
- Browser test cổng 5248, API mock: số request khi mở Dashboard với 20 session giảm từ khoảng 2N xuống hằng số. Đo trước và sau rồi ghi số.

Commit: `perf: batch dashboard session reads`, có thể tách thành 2 commit api và web.
## Quy tắc chung cho mọi agent

- Workspace `D:\ANNAM\TradingWorkspace`, Windows/PowerShell. Trả lời tiếng Việt ngắn gọn, thân thiện.
- Server proxy AI đang quá tải. Gặp 429 thì cứ thử lại, làm chậm, gộp đọc file, ghi kết quả ra file sớm rồi cập nhật dần.
- Nhiều agent commit song song. Chỉ `git add` file của mình, kiểm tra `git diff --cached` trước khi commit, gặp `index.lock` thì đợi vài giây rồi thử lại.
- Repo Trader (`projects/trader`, branch `codex/note-workspace-completion`): trailer `AI-Model-Requested: unknown` rồi dòng cuối `AI-Tool: Codex`. Không stage `foundation_v2/evidence/` hay `tests/owner-*.browser.mjs` untracked.
- Khu AI (`Ai*.jsx`, `ai-*.css`, `FxReplayShell.jsx`, `main.jsx`) đang được agent `/root/studio_redesign` sửa. Không động vào các file đó.
- `src/testing-copy.json`: một entry một dòng, CRLF, không key trùng; chạy `node --test tests/testingCopy.test.mjs`.
- Không đụng cổng 5180/8010/3100/17852. Dùng cổng riêng được giao, `strictPort`, dừng đúng PID mình mở.