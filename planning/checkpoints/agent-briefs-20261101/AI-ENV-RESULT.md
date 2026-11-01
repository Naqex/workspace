# AI environment — kết quả 01/11/2026

Đã thêm một skill điều phối agent, hai reference theo nhánh và helper kiểm link
repo. Không sửa root/global AGENTS, global skill, config, hook, secret hoặc source
Trader. Không cài package/MCP, gọi provider hay tạo agent con.

## Thay đổi và quyết định

- `.agents/skills/parallel-agent-workflow/SKILL.md`: scope/file ownership, brief
  bền vững thay cho message dài, một writer cho file chung, resume từ diff/process
  hiện tại, serialize Git index và bàn giao evidence. Trigger chỉ dành cho điều
  phối đã được ủy quyền; không tự mở worker. Bằng chứng đầu vào là các lỗi thực
  đã ghi trong brief ai_env.md: index.lock, copy registry chung, message bị cắt,
  agent gián đoạn và port/PID riêng. Không hard-code cổng hay model từ phiên cũ.
- `upstream-integrations/references/paperclip.md`: chẩn đoán wakeup/issue, JWT,
  413 và Windows env/sandbox theo receipt. Link tới guide/receipt làm owner;
  không sao chép registry cổng hoặc lệnh sửa config. Nhấn mạnh pilot succeeded
  không chứng minh credential/quota/model/tool còn sẵn sàng hiện tại. Không lưu
  chi tiết provider/model hết hạn thành policy lâu dài.
- `ui-platform-workflow/references/trader-i18n.md`: route đúng catalog/enum và
  `say(vi, english)` đang có; giữ placeholder, PnL, CRLF/one-entry-per-line,
  không key trùng và một writer cho shared catalog. Dẫn test thực, phân biệt
  giới hạn JSON.parse với duplicate key và rendered VI/EN. Không đổi code i18n.
- `tooling/check_skill_links.py`: CLI chỉ đọc, scope rõ bằng --skills-dir;
  kiểm SKILL.md và references/**/*.md, reuse check_links sẵn có. Shared checker
  thêm reference definitions, bỏ literal inline/fenced examples; giữ mặc định
  product-identity check cho workspace checker. Relative targets được kiểm theo
  file nguồn và workspace boundary. Không HTTP, không đọc config/secret và không
  auto-fix. --review-triggers là heuristic tùy chọn, không làm Stop hook ồn hơn.

Không tạo skill chiến lược G0–G5: source hiện tự ghi “đề xuất, chưa enforce”,
chưa có bằng chứng cả workflow diễn ra. Reference Paperclip chỉ route tới đề
xuất và giữ quyền holdout/broker riêng. Không bổ sung openai.yaml hàng loạt vì
không có thay đổi UI invocation nào cần metadata đó. Không sửa global maintainer
vì helper local đáp ứng nhu cầu mà không tăng global coupling.

## Luồng chính và trade-off

Agent điều phối đọc skill → chia file/runtime ownership → durable brief → worker
receipt/diff → một integrator review và serialize Git. Không có ledger cạnh tranh.
Link checker nhận root + các scope tường minh → tìm SKILL/reference → dùng chung
parser/link resolver → exit 1 nếu thiếu/thoát boundary; trigger advisory không
làm task fail. Parser phục vụ Markdown thường: inline, reference definitions,
HTML href/src; path có space/parentheses dùng angle brackets. Không kiểm anchor,
remote URL, full CommonMark hay khẳng định semantic routing đúng chỉ từ regex.

## Kiểm chứng thực đã chạy

1. Audit trước và sau bằng global audit script với -ProjectRoot workspace -Force:
   đều status=ok, 0 errors, 0 warnings. Global12,288 B; active21,387/65,536 B;
   reserve44,149 B. Skill count15 →16. Không thay instruction chain/budget.
2. `python -m unittest discover -s tooling/tests -p 'test_check*py' -v`: 8/8 pass.
   Ba fixture mới chạy CLI trong temp workspace:
   - dương: relocate vào đường dẫn có space; link tới reference và contract,
     percent-encoded path/anchor; remote .invalid không cần mạng; code examples
     không bị coi là target;
   - âm: reference đích không tồn tại và link từ reference thoát workspace cho
     exit1 và đủ hai lỗi;
   - scope thiếu không false-pass; trigger không có exclusion chỉ advisory;
     không bật option thì im lặng.
   Năm regression của workspace checker vẫn pass.
3. `python tooling/check_skill_links.py --skills-dir .agents/skills --skills-dir
   projects/trader/.agents/skills --review-triggers`: 11 skills, 0 errors,
   0 advisory warnings. Chỉ đọc hai scope đã biết, không scan vendor/global.
4. `python tooling/check_workspace.py`: 9 guides, 7 pinned submodules pass.
5. Skill-creator quick_validate cho parallel-agent-workflow,
   upstream-integrations và ui-platform-workflow: cả ba valid.
6. Semantic routing review thủ công: hai lane cùng checkout dùng brief/one-writer/
   integrator; sửa đơn lẻ không cần skill song song. Paperclip skipped issue đi
   nhánh diagnostic; adopt source khác không tải nhánh đó. VI/EN copy đi i18n;
   tư vấn chiến lược/tính toán không kích hoạt UI hoặc parallel workflow. Đây là
   review rule, không phải benchmark selector hoặc lần chạy agent mới.
7. `git diff --check`: pass trong working tree lúc kiểm. Diff đã review chỉ gồm
   skill/reference/helper/test thuộc scope; không stage/commit theo phân công
   integrator. Không có commit hash của lane; root sẽ commit checkpoint chung.

## Tiếp tục

Integrator review các file trên rồi stage đúng scope. Có thể chạy link checker
thủ công trong lần bảo trì skill kế tiếp; chưa móc vào Stop hook. Không cần
reconnect cho CLI đọc file; discovery tự động của skill mới trong phiên sau chưa
được tuyên bố đã kiểm chứng runtime.
