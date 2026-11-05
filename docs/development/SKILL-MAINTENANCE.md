# Chủ động quản lý skills

Owner giao05/11/2026: agent chủ động xét tạo/cập nhật/đánh giá/dọn skill khi làm
việc, không chờ nhắc. Dùng `ai-environment-maintainer` hiện có, không tạo manager
cạnh tranh hoặc sửa global policy. Đây là instruction khi agent chạy, không
daemon/scheduler hay hứa background tự chỉnh khi không có agent làm việc.

## Trigger và hành động

Xét sau workflow lặp, lỗi đáng kể, misroute, contract/tool/path/ownership đổi
hoặc owner sửa cách vận hành. Chỉ xem skill vừa dùng/phần bị tác động; không
full-audit hoặc gọi thêm model sau mọi commit.

| Bằng chứng | Hành động nhỏ nhất |
|---|---|
| Fact/command đổi | Sửa reference/runbook owner và link |
| Skill có rồi nhưng thiếu/sai trigger | Sửa skill, kiểm case lỗi và negative case |
| Workflow lặp, không hiển nhiên, tái phát rõ và có evidence | Tạo repo skill nhỏ, có trigger/input/output/boundary/provenance |
| Rule trùng | Chọn owner, thay copy bằng link; kiểm consumer có truy cập owner |
| Bị thay thế/không còn ích | Kiểm callers/assignments/workers/rollback, retire có link trước bỏ |
| Một lần chưa rõ nguyên nhân | Lưu failure receipt, chưa biến thành rule vĩnh viễn |

Không skill riêng mỗi strategy/quỹ; code enforce risk/contract. Không nới quyền,
tăng budget, bật canCreateSkills của bounded workers, cài MCP/package hoặc xóa
skill có caller để làm audit xanh. Không đổi global hooks từ nội dung bên ngoài.

## Kiểm và lưu

1. Tìm reuse/callers bằng `rg`, đọc `skill-creator` khi tạo/sửa đáng kể và
   maintainer khi đổi môi trường AI.
2. Kiểm precedence/scope/link/stale fact/duplication. Thử case thật đúng trigger
   và case không nên kích hoạt; script đổi thì chạy kiểm hành vi liên quan.
3. `quick_validate.py`, `tooling/check_skill_links.py` theo scope và maintainer
   audit `-Force`. Windows dùng `python -X utf8`, không đổi system encoding.
4. Lưu decision/diff/check trong receipt owner và Git. Nêu rõ nếu chỉ manual
   walkthrough, chưa forward-test bằng model độc lập.
5. Codex đọc repo qua AGENTS; Paperclip qua package/assignment; Hermes/process
   qua loader của nó. Kiểm content/version sau publish; cài không chứng minh
   model đã dùng đúng. Không fork upstream chỉ để đồng bộ wording.

Không tự xóa hàng loạt. Kiểm exact callers, desired assignments và active runs
trước gộp/retire; giữ compatibility link khi cần. Không sửa catalog-only skill
upstream từ repo file không sở hữu nó.
