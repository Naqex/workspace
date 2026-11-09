# Archive workflow GitHub trước tinh gọn — 09/11/2026

Snapshot nguyên byte tại workspace commit `e7a66834900917c207a1425f55086d3a85012226`,
trước yêu cầu tinh gọn cho một owner/nhóm nhỏ AI coding. Không là instruction
hiện hành; không đưa vào skill discovery. Tên `.before` tránh nhầm entrypoint.

| Snapshot | Đường gốc trong workspace |
|---|---|
| workflow.before.md | tooling/github-workflow/README.md |
| branches.before.md | tooling/github-workflow/BRANCHES.md |
| skill.before.md | .agents/skills/github-issue-workflow/SKILL.md |
| pr-template.before.md | .github/pull_request_template.md |
| bug.before.yml | .github/ISSUE_TEMPLATE/bug.yml |
| task.before.yml | .github/ISSUE_TEMPLATE/task.yml |

Các link tương đối trong snapshot giữ ngữ cảnh đường gốc; đọc qua bảng trên
hoặc `git show <commit>:<path>`, không coi link archive là đường runtime.
Bản Trader trước đổi có snapshot riêng trong repo Trader tại
`docs/archive/github-workflow-20261109/` và Git commit `ec364087`.

Khi cần quy trình nhiều người/kiểm toán: đối chiếu yêu cầu hiện tại, lấy lại
phần cần vào tài liệu/skill hiện hành qua một thay đổi có review; không copy
đè toàn bộ hoặc thay protection. Các form/check/CI vẫn được giữ và dùng được.

[Workflow đang dùng](../../README.md).
