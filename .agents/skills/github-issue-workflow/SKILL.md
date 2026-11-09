---
name: github-issue-workflow
description: Manage Naqex commits, pushes, branches, PRs and optional issues with the lightweight solo/small-team workflow. Use for Git changes or synchronization, not general research or broker/deploy authority.
---

# GitHub workflow gọn

Đọc [workflow hiện hành](../../../tooling/github-workflow/README.md), chọn
đường theo rủi ro và policy thật của repo. Giữ tên skill để callers cũ dùng tiếp.

- Chỉ đọc thì chưa cần Git artifact. Việc nhỏ một writer: main nếu được phép;
  protected main thì một branch/PR cho đợt liên quan. Không hạ protection.
- Tiếp tục cùng mục tiêu thì dùng branch/PR đang mở; không tạo theo lượt chat,
  agent, file hoặc từng kết quả. Issue chỉ khi cần theo dõi ngoài PLAN hiện có.
- Kiểm đúng repo/status/ownership, sửa và validate theo rủi ro, review diff,
  commit coherent rồi push cụ thể. Hai AI trailers theo README; không bảng
  danh tính lặp trong PR/issue. PR gọn: thay đổi/vì sao, checks, giới hạn nếu có.
- Merge khi đã được giao và required checks đúng HEAD đạt; xác nhận base,
  đồng bộ checkout sạch và dọn refs đủ điều kiện. Không hỏi lại quyền đã có.
- Với worktree, repo con hoặc cleanup, đọc
  [chi tiết Git](../../../tooling/github-workflow/BRANCHES.md). Publish repo con
  trước pin workspace; giữ WIP, active consumers và source/runtime khác nhau.

Nếu cần issue: reuse issue có sẵn trong `Naqex/workspace`, ghi repo sở hữu,
vấn đề/mục tiêu, evidence và điều kiện hoàn tất; link PLAN thay chép checklist.
Không tạo issue cho mỗi commit/PR; không đóng khi chỉ source/CI đạt mà acceptance
còn chờ. Review độc lập chỉ khi cần theo rủi ro và được giao; không giả self-review
là độc lập. Không thêm service cleanup hoặc quyền broker/deploy qua Git.

Bản cũ được [archive](../../../tooling/github-workflow/archive/20261109/README.md);
không đọc/bật lại mặc định.
