# GitHub workflow gọn cho Naqex

Dành cho một owner hoặc nhóm nhỏ dùng AI agents. **Kiểm thay đổi → commit →
push; dùng PR khi repo yêu cầu hoặc thay đổi cần cô lập/review.** Agent tự xử
lý Git trong phạm vi được giao; owner chỉ cần xem kết quả và việc còn vướng.

## Chọn đường ngắn nhất

| Tình huống | Cách làm |
|---|---|
| Chỉ hỏi/đọc/research, chưa sửa file | Không tạo branch, issue hay PR |
| Docs, context, sửa nhỏ ít rủi ro; một writer | Sửa trên main nếu repo cho phép; nếu bắt PR thì gom thay đổi liên quan vào một branch/PR ngắn |
| Feature, sửa tính toán/dữ liệu/quyền, thay đổi rộng hoặc thử nghiệm | Một branch `codex/<short-english-task>` và PR cho một mục tiêu |
| Tiếp tục cùng công việc qua nhiều lượt chat | Dùng tiếp branch/PR đang mở; không tách theo lượt chat, agent hoặc từng báo cáo |
| Nhiều agent thực sự ghi đồng thời | Cô lập các lane cần thiết; một integrator quản lý main/pin |
| Việc hoãn, bug cần người khác theo dõi, chưa có nguồn trạng thái | Issue ngắn; tìm issue có sẵn trước |
| Đã có PLAN/ledger theo dõi | Link nguồn đó; không tạo issue chỉ để lặp lại checklist |

**Đã kiểm 09/11/2026:** `Naqex/workspace` và `Naqex/trader` đều yêu cầu PR,
CI và áp protection cả admin; required approving reviews = 0. Vì vậy hai repo
này vẫn dùng PR. Không đổi server settings hoặc bypass để có đường direct-main.
Các repo khác kiểm policy thực tế trước khi chọn; thiếu quyền đọc thì không
suy ra không có protection. Đây là lựa chọn phù hợp nhóm nhỏ của Naqex, không
phải tuyên bố GitHub bắt mọi project phải làm giống nhau.

## Agent làm một đợt công việc

1. Xác định đúng repo, HEAD/status và writer/worktree đang dùng. Giữ WIP của
   người khác. Fetch khi bắt đầu hội nhập/push, không lặp full inventory sau
   từng chỉnh sửa. Chọn đường trong bảng; xem [chi tiết Git](BRANCHES.md) khi
   có branch/worktree/submodule hoặc cleanup, không bắt đọc archive.
2. Sửa và kiểm chứng theo rủi ro; review diff/secret trước stage đúng file.
   Gom code, tests và docs cùng mục tiêu trong một PR, commit theo lát hoàn
   chỉnh. Không mở PR cho từng file/kết quả hoặc trộn việc không liên quan.
3. Push branch cụ thể. PR chỉ cần **thay đổi/vì sao, cách kiểm và giới hạn
   đáng kể**; bỏ mục không có nội dung. Issue không bắt buộc. Git đã giữ tác
   giả/commit; không viết lại bảng danh tính agent trên mọi issue/PR.
4. Đã được giao merge: chờ required checks trên đúng HEAD, không conflict,
   rồi merge và xác nhận vào base. Chưa được giao merge thì báo PR sẵn sàng.
   Close issue chỉ khi acceptance đã đạt; `Refs` cho phần còn chờ.
5. Đồng bộ checkout sạch về base, dọn branch đủ điều kiện. Với repo con,
   publish/merge source trước rồi pin workspace; không promote runtime vì
   source đã merge. Không bắt owner duyệt lại thao tác Git đã được giao.

Không cần reviewer thứ hai cho mọi docs/fix nhỏ; tự review và checks phù hợp
là đủ trong policy hiện tại. Thay đổi tiền/risk/accounting/quyền/dữ liệu hoặc
kiến trúc cần review kỹ tương ứng và giữ gate domain; agent không được gọi
self-review là independent review. Review riêng phải gắn đúng revision.

## Dấu vết tối thiểu

Commit có AI đóng góp đáng kể giữ hai trailers máy đọc được; agent tự thêm,
không buộc owner quản lý model hoặc điền lại trên PR:

```powershell
git commit -m "fix: describe the change" --trailer "AI-Tool: Codex" --trailer "AI-Model-Requested: unknown"
```

Dùng raw ID được cấu hình hoặc `unknown`, không đoán từ alias. Trailers cùng
một block; human/mechanical commit không cần. Ghi thêm role/model/reviewed SHA
chỉ khi review/handoff/điều tra cần; không dựng bảng xếp hạng model.

Khi sửa forms/trailers/validator, dùng `python tooling/github-workflow/check.py`
và tests trong `tooling/github-workflow/tests`. Không chạy lại bộ đó cho mọi
bản research nếu tooling không đổi; CI vẫn chạy các checks repo yêu cầu.

## Archive và mở rộng sau này

[Bản đầy đủ trước tinh gọn](archive/20261109/README.md) giữ workflow, skill và
biểu mẫu nguyên bản, không nằm trong đường instruction mặc định. Chỉ lấy lại
phần cần khi có collaborator thật, yêu cầu kiểm toán hoặc một lỗi chứng minh
cần thêm quy trình. Không bật lại toàn bộ chỉ vì số agent tăng.

Quyền Git không cấp quyền broker/deploy/release/migration; secret, dữ liệu và
validation giữ gate hiện hành. Không thêm bot cleanup, tracker hoặc service.

Đối chiếu: [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow),
[protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
