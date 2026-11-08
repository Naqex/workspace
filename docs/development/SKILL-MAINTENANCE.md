# Chủ động quản lý skills

Owner giao05/11/2026: agent chủ động xét tạo/cập nhật/đánh giá/dọn skill khi làm
việc, không chờ nhắc. Dùng `ai-environment-maintainer` hiện có, không tạo manager
cạnh tranh hoặc sửa global policy. Đây là instruction khi agent chạy, không
daemon/scheduler hay hứa background tự chỉnh khi không có agent làm việc.

## Trigger và hành động

Xét sau workflow lặp, lỗi đáng kể, misroute, contract/tool/path/ownership đổi
hoặc owner sửa cách vận hành. Chỉ xem skill vừa dùng/phần bị tác động; không
full-audit hoặc gọi thêm model sau mọi commit.

Hậu kiểm đa chiều sau đợt chạy quan trọng dùng
[engineering-retrospective](../../.agents/skills/engineering-retrospective/SKILL.md).
Skill đó chọn lát cải tiến và evidence; tài liệu này own lifecycle của skill,
không giao thêm quyền cho bounded workers hoặc background updater.

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

## 08/11: nhật ký tối ưu và quyết định chiến lược

Theo yêu cầu owner, cập nhật `strategy-research`, `strategy-qualification` và
`engineering-retrospective` để đọc/ghi nhật ký tại protocol/results/review owner
hiện có. [Workflow](../../tooling/ai-engines/STRATEGY-WORKFLOW.md#nhật-ký-quyết-định-để-kiểm-lại-việc-tối-ưu-và-chọn-chiến-lược)
giữ nội dung chi tiết; không tạo skill, ledger hoặc UI mới. Phân vai: đăng ký
lý do/baseline trước outcome → lưu vì sao giữ/loại/chuyển bước → kiểm so sánh
trước/sau/parity và retained failures. Không đổi global instructions hoặc quyền.

Manual walkthrough dùng [source correction](../../planning/research/INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md):
sửa data semantics không gọi là speedup, giữ negatives và không promote chỉ vì
PnL bớt âm. Negative case: chỉ hỏi tiến độ hoặc sửa copy không kích hoạt full
experiment/audit hoặc rerun batch. Đây là review nội dung, chưa forward-test
routing bằng model độc lập. Ba skill structures/links và maintainer audit đạt
0errors/0warnings; global12279B,project10133B,reserve55403B,combined22412B.
Local native-package bundle đã xuất để kiểm nội dung; chưa publish/assign
runtime Paperclip trong lượt này, không suy repo edit thành agent đang chạy
đã nhận instruction. Numerical/source workers không đọc Markdown vừa sửa.
