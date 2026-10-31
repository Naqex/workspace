# AI integrations — adoption và runtime cutover

31/10/2026, Asia/Saigon. Scope/acceptance:
[owner plan](../../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md),
[issue #6](https://github.com/Naqex/workspace/issues/6).
Đây là source/runtime foundation; chưa acceptance toàn vòng AI autonomy.

## Kết quả

| Thành phần | Source | Bằng chứng hiện tại |
|---|---|---|
| Paperclip | `projects/integrations/paperclip`, Naqex fork, `42fd568cf8f588334cacc6004aa23aff54daa52b` | Remote branch `codex/naqex-integration` đúng pin; upstream riêng; native UI/API chạy lại sau relocation |
| RD-Agent | `projects/integrations/rd-agent`, Microsoft upstream, `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` | Git submodule, README/pyproject/requirements/CLI và MIT license đã đọc; chưa cài dependencies hoặc chạy job |
| TradingAgents | `projects/integrations/TradingAgents`, Naqex fork, `ecaafe585a98478ef7dbcf5678f4a64b5e7d1066` | Code giữ nguyên từ `6bfea6a6`; chỉ sửa đường dẫn evidence trong UPSTREAM-SYNC.md sau relocation; editable reinstall `--no-deps`, import version0.7.0 và module path mới đúng |
| LangGraph | Dependency TradingAgents | Import được trong cùng venv; không clone source hoặc dựng UI/service riêng |
| Quant Lab | `projects/quant-trading` | Giữ nguyên; không có source/runtime mutation trong lát này |

Fork Paperclip: <https://github.com/Naqex/paperclip>. Fork default master mới hơn
pin chạy; tạo fork không tự cập nhật runtime. `.gitmodules` trỏ fork/branch,
gitlink giữ commit cụ thể. Root gitlink Trader vẫn baseline cũ như trước, không
kèm WIP audit hoặc lịch sử product ngoài scope vào commit adoption này.

## Luồng và trạng thái được giữ

Trader preview5218 → iframe Paperclip17860 → API/storage/DB Paperclip riêng17861.
Nguồn đã chuyển nhưng instance giữ tại `.runtime/paperclip/instances/trader-ui/`.
Company `f2b281a7-f974-43a2-ae81-5472a09d6260` / `Naqex AI` giữ nguyên; sau
cutover vẫn 0 agents. Không tạo task/agent/heartbeat run hoặc gọi provider.
Heartbeat scheduler tiếp tục tắt; manual execution API của Paperclip vẫn tồn tại.

Sau cutover: launcher23408, server11428, PostgreSQL624 tại lúc kiểm tra. Các PID
là evidence thời điểm, không phải ID để kill trong phiên sau. Đọc owner/process
thực tế khi resume. Windows standalone CLIProxyAPI8317 vẫn PID18940; cổng17852
chưa mở. Không cập nhật Trader5180/API8010 hoặc terminal broker.

Launcher gọi lại báo "already running" đúng source/revision, không tạo instance
thứ hai. Layout, theme và outer sidebar preference giữ nguyên; Paperclip vẫn
English ở lát này, chưa triển khai patch Việt hóa.

## Backup và Windows dependency relocation

- Backup qua API chính thức `POST /api/instance/database-backups` trước cutover:
  `.runtime/paperclip/instances/trader-ui/backups/paperclip-20261031-230528.sql.gz`.
  Gzip đọc được 1,533,841 bytes SQL; SHA256
  `1b0b332a4efc711a587cbb52914e66e6692f2d63e6ae8f52d101fe6d63bb9b41`.
- Stopped-cluster/config/owner/company snapshot và junction inventory giữ local
  tại `.runtime/paperclip/cutover-20261031/`; không commit data hoặc secret.
- 5,034 junction nội bộ node_modules được đổi từ source cũ sang source mới;
  kiểm toàn bộ target trong inventory: 0 broken. Không sửa dependency versions.
- TradingAgents editable package được cài lại bằng `uv pip install --python
  .venv/Scripts/python.exe --no-deps -e .`; interpreter import chỉ đúng source mới.
  Đây không chứng minh toàn bộ venv/console scripts có thể di chuyển portable.

## Kiểm chứng

- `node tooling/integrations/doctor.mjs --runtime`: ba source khớp gitlink,
  origin/license, clean; health Paperclip khớp revision.
- Doctor negative cases: thiếu source trả `missing-source`; path thoát workspace
  bị từ chối. Script không import engine hoặc dispatch công việc.
- `python tooling/check_workspace.py`: 9 guides, 7 pinned submodules pass.
  Unit tests topology/links: 5 pass. Node syntax checks doctor/launcher pass.
- Native browser QA trên preview5218, 1920/dark/VI, 1440/light/EN, 390/dark/VI:
  8 cases pass (native render, dialogs/Escape, document/search persistence,
  sidebar preference, unavailable + retry). Browser chặn writes/external;
  report ghi 0 writes, 0 external requests, 0 page errors.
  Ảnh1920/390 đã xem: iframe tới đáy, mobile không tràn ngang; upstream focus
  sau Escape vẫn BODY như trước, không phải trigger.
- Browser probe là bản copy script đã có, chỉ đổi import/output paths, không sửa
  tests/receipt lịch sử. Script/output/ảnh mới ở
  `.runtime/research/paperclip-localization-20261031/adoption-browser.mjs` và
  `.runtime/paperclip/cutover-20261031/browser/`.
- Không chạy lại full build/test Paperclip vì source revision/behavior không đổi;
  thay đổi ở root paths/launcher/docs, đã kiểm đúng native runtime consumer.

## AI environment và skill dài hạn

Thêm skill repo `.agents/skills/upstream-integrations/SKILL.md`, nested
`projects/integrations/AGENTS.md` và route ngắn từ root AGENTS. Hướng dẫn setup/
rollback ở `tooling/integrations/README.md`; catalog là owner path/role/upstream,
cổng vẫn dùng config Trader hiện có. Không đổi global config/MCP hoặc cài plugin.

Skill-creator quick validation pass. Semantic review: task fork/relocation/
upstream update đi đúng skill; task tư vấn Quant Lab hoặc chỉnh UI thông thường
không thuộc trigger. Đây là review trigger thủ công, chưa là benchmark bộ chọn
skill tự động. Phiên hiện tại đọc file trực tiếp; discovery ở phiên sau theo
cơ chế repo skills, không tuyên bố tool mới đã được expose.

Deterministic audit workspace: 0 errors/warnings; global12,288 B, active21,387 B,
reserve44,149 B trên ceiling65,536. Audit riêng Paperclip: 0 errors/warnings,
active25,923 B theo chain riêng của audit ở Git root submodule. Nếu cộng cả
parent workspace + integrations + upstream AGENTS trong ngữ cảnh hiện tại:
36,122 B, còn29,414 B; cao hơn target32KiB nhưng vẫn giữ reserve16KiB. Giữ nguyên
policy upstream thay vì cắt instruction của tác giả chỉ để giảm số đo.
Chưa tạo skill research/model workflow từ luồng chưa thực hiện.

## Thất bại trong quá trình và cách xử lý

- Guard PowerShell ban đầu bọc REST array trong `@(...)` nên đếm sai; dừng trước
  mutation, sửa đọc `.Count` trên REST array thực, xác nhận0 agents rồi mới dừng.
- Sau khi dừng server, `pg_ctl stop` báo PID đã mất: xác minh cả3 process và
  ports đã dừng trước backup/move. Startup sau đó xử lý stale PID; health/company
  và DB hiện có được kiểm lại. Không gọi stop/kill theo port hoặc chạy initdb mới.
- `git mv` lần2 yêu cầu stage `.gitmodules`; stage riêng file move rồi tiếp tục.
- Lệnh Start-Process bị policy chặn trước execution. Dùng exec session chạy
  launcher đã có để khởi động đúng instance; không tìm cách tắt approval policy.
- Editable install với `--no-build-isolation` thất bại vì venv thiếu setuptools;
  chạy lại với build isolation theo pyproject, `--no-deps`, thành công. Không sửa
  manifest để né lỗi hoặc nâng toàn bộ dependency.

## Điểm tiếp tục

Nền fork/source/runtime hoàn tất trong scope trên. Việc tiếp theo trong owner
plan: mở rộng i18n Paperclip theo từng khu vực UI, cấu hình company/roles và
workflow cho owner review; sau đó nối một job engine có contract/provenance và
cancel/retry rõ ràng. RD-Agent cần qualification Linux/container/WSL theo source;
chưa cài hoặc bật môi trường đó từ lát adoption. Giữ UI-first và ngân sách/quyền
owner đã chốt, không đổi "source-ready" thành "autonomy-ready".

Clean-clone runtime còn phụ thuộc feature checkout Trader có
`foundation_v2/local-services.json` (`18e9348d` hoặc hậu duệ); root gitlink hiện
chưa nâng. Không stage gitlink Trader đang chứa lịch sử/WIP ngoài scope. Engine
jobs và packaging gate tiếp tục mở trên issue/plan; broad UI audit vẫn pause.
