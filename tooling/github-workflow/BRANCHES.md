# Git: các trường hợp cần chú ý

Mặc định dùng [workflow gọn](README.md); chỉ đọc phần liên quan dưới đây.

## Agent chọn sửa tại chỗ, branch hay worktree?

Một writer làm tuần tự: dùng checkout hiện có. Cùng mục tiêu thì tiếp tục
branch/PR đang mở; một branch cho một đợt coherent, không một branch mỗi chat.
Việc nhỏ dùng main nếu policy cho phép; protected main thì PR ngắn. Việc độc
lập/rủi ro hoặc cần bỏ thử nghiệm thì branch `codex/<short-english-task>`.

Concurrent writers hoặc checkout cần giữ cho WIP/job: worktree riêng khi cần;
read-only reviewers không cần branch/worktree riêng. Một người quản lý index
trong mỗi checkout. Worktree không cô lập port, database, broker hay output;
không để các lane cùng ghi một job. Không đổi branch dưới worker đang dùng.

## Nhiều repo trong workspace

Chạy Git trong repo sở hữu file, xác nhận `git rev-parse --show-toplevel`.
Ở worktree từ submodule, nếu root sai hoặc báo xóa hàng loạt thì dừng stage;
kiểm `core.worktree` và ownership trước, không reset/clean để che lỗi.

Commit/push/merge repo con trước; xác minh SHA trên remote rồi cập nhật đúng
gitlink workspace. Main của repo con có thể đang ở worktree khác; checkout
submodule detached tại SHA được pin là bình thường. Không giành branch main,
đổi `.gitmodules` hoặc nâng các pin ngoài task. Integration fork có consumer
riêng giữ branch theo [integration guide](../integrations/README.md).

## Merge và dọn branch

Merge đúng HEAD đã kiểm vào base thật; base trung gian chưa là vào main.
Không force-push, admin bypass hoặc hạ required checks. CI fail thì sửa lỗi,
không tắt test/secret scan. Post-merge fetch và xác nhận source đã vào đích.

Dọn trong phạm vi owner đã giao, khi tip đã vào đích và không có worktree,
worker/WIP hoặc PR còn dùng head/base. Giữ main, integration và rollback
anchors. Local dùng `git branch -d`; remote kiểm tip chưa đổi trước xóa đúng
ref. Không dùng wildcard hoặc `-D` để ép dọn; squash không khớp ancestry thì
kiểm exact PR/patch hoặc giữ branch để rà. Branch dùng tiếp sau merge cần
kiểm commit mới, không dựa vào PR cũ.

Checkout sạch của mình trở về base bằng fast-forward; giữ checkout khác và
WIP. Không archive/xóa worktree do chat khác sở hữu. Lịch sử và rollback
không đòi giữ mọi feature branch; yêu cầu lưu archive tài liệu không là lệnh
xóa hay gắn tag cho tất cả branch. Chưa đủ evidence thì giữ và nêu lý do.

Lỗi ref dài trên Windows: kiểm với `git -c core.longpaths=true`; không xóa
refs/đổi global config để né. Hướng dẫn chi tiết cũ nằm trong
[archive](archive/20261109/README.md), không là policy hiện hành.
