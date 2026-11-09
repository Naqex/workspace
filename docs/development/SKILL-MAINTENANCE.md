# Chủ động quản lý skills

Owner giao05/11/2026: agent chủ động xét tạo/cập nhật/đánh giá/dọn skill khi làm
việc, không chờ nhắc. Dùng `ai-environment-maintainer` hiện có, không tạo manager
cạnh tranh hoặc sửa global policy. Đây là instruction khi agent chạy, không
daemon/scheduler hay hứa background tự chỉnh khi không có agent làm việc.

## Trigger và hành động

09/11: `strategy-qualification` thêm nhánh
[chẩn đoán lỗ có chọn lọc](../../.agents/skills/strategy-qualification/references/selective-loss-diagnosis.md).
Reuse entrypoint hiện có; D0 đọc sổ cũ, D1 chỉ giữ/near-miss có câu hỏi rõ,
D2 đăng ký thay đổi sau khi xác minh nguyên nhân. Không hardcode ngưỡng hoặc
cho phép sửa strategy để cứu outcome. Positive manual walkthrough: Goldretained;
negative: R081gross/net yếu không phân tích filter tiếp; materialbug vẫn xử lý.
Actual30books/439tradecases/Fractionreview/6mutations ở
[receipt](../../planning/research/SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md).
Skillcreator validator/scopedlinks/maintaineraudit đạt0errors/0warnings;
global12.279B,project10.133/65.536B,reserve55.403B,combined22.412B không đổi.
Repo skill, chưa publish/assign Paperclip hoặc independentmodelroutingtest.

09/11: source-transformations reference thêm pilot→history partition/role
census trước PnL, không skill mới. [Case thật](../../planning/research/INDEX-PAPER-WINDOW-RESULTS-20261109.md)
raw reviewer bắt omitted US500Q2/Q4; helper full-year buộc4quarters/8side seals,
4regressions và affected repair đạt, unaffected reports/quotes giữ nguyên.
Negative walkthrough: pilot1/3 không là full-year proof; status-only không
kích hoạt fetch/fullrerun. Structure/scoped links và maintainer audit đạt
0errors/warnings, bytes/reserve không đổi. Repo reference, chưa native publish.

09/11: thêm nhánh conditional missing-price sensitivity vào
`strategy-qualification/references/validation-gates.md`, reuse G1/G2 owner,
không skill/config mới. R065 interval và R066 collapsed interval là positive
manual walkthroughs: giữ exact unknown, chỉ đổi ưu tiên nghiên cứu theo
registered criterion. Negative case: BI5 transport timeout không có source
envelope không cho tự bịa bounds/fill hoặc clear unknown. Không forward-test
bằng model độc lập; numerical workers không tự đọc reference mới.
Structure validator (bundled Python), scoped links và maintainer audit đạt:
0errors/0warnings; global12.279B,project10.133/65.536B,reserve55.403B,
combined22.412B. Product venv thiếuPyYAML cho validator; reuse bundled runtime,
không cài dependency hoặc đổi môi trường product/global. Chưa publish/assign
native Paperclip package.

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

## 08/11: bàn giao để owner hiểu và vận hành bot

Mở rộng `strategy-qualification` bằng `references/owner-handover.md`; không
tạo skill mới vì kiểm định đã sở hữu quyết định chuyển bước/bàn giao. Nhánh
này dùng khi chuẩn bị prospective demo/challenge hoặc owner chưa giải thích
được bot do AI/code tạo. Đầu ra: thẻ chiến lược gắn version, ví dụ lời/lỗ/lỗi,
USD/R, stop/reconcile/recover và điều kiện quỹ; lưu trong dossier/report cũ.
Không yêu cầu trade tay có lãi, không tự ghi owner hiểu hoặc cấp quyền broker.

Manual walkthrough dùng parent PreECB đang gác: bàn giao → đọc reference,
giải thích rules và giữ `prepared_not_demonstrated`; hỏi tiến độ → không bắt
học hoặc chạy batch/audit mới. Đây là kiểm nội dung bằng cùng agent, chưa là
đánh giá routing bằng model độc lập hay diễn tập thực tế của owner. Structure
validator, scoped skill links và maintainer audit đều đạt: 0 errors/warnings;
global 12.279 B, project 10.133/65.536 B, reserve 55.403 B, combined 22.412 B.
Repo skill đã sửa; chưa publish/assign package Paperclip, không suy worker
đang chạy đã nhận nội dung này. Không thay global config hoặc service nền.
