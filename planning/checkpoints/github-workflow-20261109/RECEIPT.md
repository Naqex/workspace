# GitHub workflow và dọn branch — 09/11/2026

Owner yêu cầu hoàn thiện hướng dẫn/skill sau khi khó hiểu danh sách branch.
Đây là task Git đang được giao riêng; Goal nghiên cứu prop vẫn paused.

## Thay đổi hướng dẫn

[README GitHub](../../../tooling/github-workflow/README.md) là cửa vào;
[branch lifecycle](../../../tooling/github-workflow/BRANCHES.md) sở hữu quy tắc
tên branch, base/worktree, commit/push/PR/CI/merge, submodule pin và cleanup.
Mở rộng skill `github-issue-workflow` hiện có, giữ tên để không hỏng callers;
AGENTS, development guide, CONTRIBUTING và README root đều dẫn về đúng owner.
Không thêm skill/MCP/hook hoặc quy trình quản lý song song.

Branch mới cho task này: `codex/quy-trinh-github`, base
`codex/naqex-workspace-pin` tại `41b1a48a141087786d3165b1ca1f323528f24e99`.
Đây là PR phụ thuộc source workspace đang dùng, không PR gom toàn bộ lịch sử
chưa vào main. Task này chỉ đổi hướng dẫn và lưu evidence; source hiện tại
không bị thay bằng local main cũ. Hội nhập lịch sử workspace/Trader là review
riêng, không tự merge hàng trăm commits hoặc relabel là đã nghiệm thu.

## Dọn thực tế đã kiểm

GitHub PR metadata, fetched `origin/main`, exact tips, open head/base PRs và
worktree lists được kiểm trước. Lưu đầy đủ tên/SHA và hành động ở private:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/git-branch-cleanup-20261109/`.
`before.json`, `after.json`, `completed.json` giữ cả lần guard từ chối và recovery.
Git/GitHub hiện hành vẫn là nguồn trạng thái; bảng này chỉ là snapshot ngày kiểm.

| Repo | Feature branch đã xóa local | Tip trước khi xóa | PR đã merge vào main |
|---|---|---|---|
| Workspace | `codex/naqex-workspace` | `d62fe3853a65f6735c02d75f89d8d9a6d7692384` | #1 |
| Workspace | `codex/agent-issue-workflow` | `f6151972b87d63d7d1dc2a3a432e81097272f264` | #4 |
| Trader | `codex/naqex-foundation` | `3122cdca38b0cbb7e60bac64cb002ac88cc439a4` | #1 |
| Trader | `codex/release-windows-fixtures` | `c4b8cef0fd7b5bd31a7a182e9617ce706387cdb4` | #10 |
| Trader | `codex/artifact-windows-path-identity` | `78c73f6795d09878ad0422f6c357c2b9fd22e5c6` | #11 |
| Trader | `codex/live-analytics-controls` | `51e6e23ed004e2cc144671927fff83bdb3a2dbc1` | #12 |
| Trader | `codex/trader-agent-provenance` | `4428cc0fabca4766262b6fe827f19e8efa9d600d` | #14 |

7 local branches đã xóa bằng `-d`. Chỉ 1 trong số đó còn trên server:
`workspace:codex/agent-issue-workflow`; đã xóa remote với expected-tip lease
chỉ cho ref cần xóa. 6 remote branches còn lại vốn đã không tồn tại. Không
rewrite commit history; cả 7 tip đều vẫn reachable từ đúng `origin/main`.
Đã kiểm lại cả local refs và remote advertised refs sau thao tác.

Local main không được checkout đã fast-forward và theo đúng `origin/main`:

| Repo | Trước | Sau | Tracking |
|---|---|---|---|
| Workspace | `e0fafdb` | `d9e8389` | Từ `legacy/main` sang `origin/main` |
| Trader | `159cd4fd` | `a8f3749d` | `origin/main` |

`branch -d` từng từ chối một ref sau khi upstream remote đã bị xóa: nó kiểm
HEAD hiện tại thay vì target main. Đã giữ failure, chứng minh ancestry vào
origin/main, trỏ upstream của đúng branch sắp xóa về target rồi dùng lại `-d`.
Không dùng `-D`. Bẫy này đã được bổ sung vào lifecycle guide.

## Các trường hợp được giữ và kiểm quy trình

- **Positive:** 7 tip đúng merged PR, không worktree/open PR, đều vào actual
  main; cleanup thành công và kiểm lại ref không còn.
- **Negative — reused branch:** workspace PR #2 đã merged nhưng branch
  `codex/naqex-workspace-pin` có commits mới sau merge; giữ baseline hiện tại.
- **Negative — worktree:** `codex/github-resolution-pin`, replay verification,
  research-metals/resume và các checkout khác đang gắn worktree được giữ;
  một PR merged không tự cho phép bỏ worktree.
- **Negative — pending PR:** VI Dubber #1 và Quant Trading #1 còn mở, CI đạt
  ở các SHA đã publish; giữ branch, không coi push hoặc CI pass là merge.
- `Nam`/legacy rollback branch chưa có ownership/retirement review riêng được
  giữ; không tự chuyển nhãn lịch sử thành đủ điều kiện xóa.

Đây là walkthrough trên Git/GitHub thật và cùng agent review, không phải
independent model test hoặc hook tự động chặn mọi branch sai tên.

## Kiểm chứng hướng dẫn

`quick_validate.py` cho skill đạt; scoped skill links 0 errors/warnings;
`tooling/github-workflow/check.py` cho forms đạt; diff whitespace check đạt.
Kiểm `--commit` đã bắt lỗi metadata ở `b4db388`: hai dòng AI bị tách thành
hai đoạn do dùng hai `-m`. Giữ nguyên commit đã publish, sửa hướng dẫn dùng
hai `--trailer` và thêm regression chạy native Git trong disposable repo.
Commit sửa kế tiếp phải qua `check.py --commit HEAD`; không nới validator
để chấp nhận block sai hoặc ghi metadata lịch sử là đã pass.
AI environment audit: 0 errors/warnings, 21 skills; global 12.279 B,
project 10.160/65.536 B, reserve 55.376 B, combined 22.439 B.
Chỉ router project đổi, không global config/permissions hoặc native agent assignment.
Không cần rerun backtest/product tests cho thay đổi hướng dẫn này.
