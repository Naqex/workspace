# Phát triển trong Naqex Workspace

## Ownership

```text
workspace/
├── AGENTS.md                 # hướng dẫn agent và gate theo phạm vi
├── .agents/skills/           # workflow lặp lại đã kiểm chứng
├── docs/                     # hướng dẫn hiện hành, sơ đồ và assets README
│   └── archive/              # snapshot tài liệu lịch sử
├── planning/                 # scope → ledger/checkpoint do PLAN chỉ định
├── projects/                 # sản phẩm và integrations/; mỗi repo có Git riêng
├── tooling/                  # kiểm tra và công cụ dùng chung
├── UI-Systems/               # UI foundations
├── UI/                       # quy tắc UI cho trading
└── education/                # course, bài tập và tiến độ
```

Source có owner theo sản phẩm. Plan không là cấu hình runtime, README không là
ledger, search index không là nguồn sự thật. Fork giữ layout/upstream riêng.
Không tách API, web và worker của Trader thành submodule nhỏ hơn.

`projects/integrations/` giữ source Paperclip, RD-Agent và TradingAgents;
[catalog, doctor và workflow cập nhật](../../tooling/integrations/README.md).
Paperclip là fork upstream cho UI điều hành AI, được Trader nhúng qua origin local.
Setup, data boundaries và rollback:
[Paperclip local](../../tooling/paperclip/README.md).
Cổng integration do [cấu hình Trader](../../projects/trader/foundation_v2/local-services.json)
và [hướng dẫn local services](../../projects/trader/foundation_v2/docs/LOCAL-SERVICES.md)
quản lý; dùng các nguồn này khi thêm service, không lấy cổng mặc định upstream.

## Bắt đầu một task

1. Đọc `AGENTS.md` gần file cần sửa và README của đúng sản phẩm.
2. Tìm implementation tương tự bằng `rg`; dùng [Xerj](../../tooling/search/README.md)
   khi cần tìm theo khái niệm trên corpus lớn. Xác nhận kết quả ở source gốc.
3. Chốt scope và bằng chứng cần có trong owner plan đang dùng; task nhỏ chỉ cần
   diff/PR, không tạo thêm plan hay tracker.
4. Sửa, kiểm chứng, commit và PR trong repo sở hữu code. Merge sản phẩm trước,
   rồi cập nhật pin bằng PR ở workspace.

### Tìm đúng context để tiếp tục

| Việc đang làm | Đọc đúng nguồn trước |
|---|---|
| Lấy lịch sử Forex, tìm downloader/cache đã có | [QDM CLI của Trader](../../projects/trader/docs/quantdatamanager.md); [contract Forex](../../planning/research/FOREX-PROP-PILOT-20261102.md) giữ khoảng dữ liệu được phép |
| Tiếp tục AI research | [AI plan](../../planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope; [receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md) giữ kết quả, lỗi và bước tiếp |
| Chọn engine hoặc kiểm quyền worker | [Integration guide](../../tooling/integrations/README.md) → [engine contracts](../../tooling/ai-engines/README.md); research/review không cấp quyền broker, holdout hoặc promotion |
| Job bị ngắt, báo cáo còn `running`, chưa rõ nên retry | [Vòng đời engine job](../../tooling/ai-engines/README.md#one-analysis) và native run/receipt của job đó; artifact tồn tại không chứng minh thành công |
| Sửa Trader hoặc rollout một source candidate | [Hướng dẫn Trader](../../projects/trader/AGENTS.md) và [runtime guide](../../projects/trader/foundation_v2/docs/RUST-NATIVE-RUNTIME.md); source, pin và runtime là ba trạng thái riêng |

Brief/research có thể giữ các quyết định lịch sử. Đọc nhãn ngày/phạm vi và đi tới
PLAN/receipt được dẫn, không lấy một câu “chưa tích hợp” trong thảo luận cũ làm
trạng thái mới nhất. Bảng này chỉ dẫn tới owner hiện có, không sao chép tiến độ.

| Thao tác tại workspace root | Lệnh |
|---|---|
| Kiểm tra docs/pins/cấu trúc hiện hành | `python tooling/check_workspace.py` |
| Tests bộ kiểm tra workspace | `python -m unittest discover -s tooling/tests -p test_check_workspace.py` |
| Kiểm tra UI consumer registry | `node tooling/ui-qa/ui-registry-check.mjs --json` |
| Tests registry | `node --test tooling/ui-qa/tests/registered-products.test.mjs` |
| Xem thay đổi repo con | `git submodule foreach git status --short` |
| Khôi phục đúng pin | `git submodule update --init -- projects/trader` |

Lệnh riêng của từng sản phẩm nằm trong README/AGENTS của repo đó. Không dùng
`git add .` ở workspace để gom mọi repo/WIP vào một commit. `--remote --merge`
không phải cách cập nhật pin có kiểm chứng.

## Đường dẫn và dữ liệu local

- Script suy repo root từ vị trí script. README dùng link tương đối; code dùng
  resolver/config hiện có. Không chèn đường dẫn máy của người viết vào source.
- Database, broker terminal, dataset, model, credential và vendor có license
  riêng nằm trong local storage được cấu hình; không di chuyển chỉ để đổi tên.
- `.runtime/`, `.artifacts/`, `.tmp/` và `.worktrees/` là dữ liệu local bị ignore.
  Ignore không chứng minh file có thể xóa.
- Checkout đang chạy có thể còn tên thư mục cũ. Tên repo không bắt buộc trùng
  tên thư mục local; chỉ đổi root/runtime sau khi có cutover và rollback phù hợp.
- ID, namespace, storage key và receipts lịch sử giữ nguyên để tương thích.

## AI tooling

[Workflow GitHub](../../tooling/github-workflow/README.md) quy định khi nào tạo issue,
metadata model và bàn giao PR. Dùng forms/skill hiện có trước khi thêm tracker mới.

Giữ instruction ngắn trong `AGENTS.md`; workflow nhiều bước nằm trong repo skill,
context dài nằm trong reference. Chỉ thêm MCP khi có nhu cầu thật và kiểm tra
quyền/data flow. Không chạy bộ cài tự sửa global config của bên thứ ba.

Khi sửa AGENTS/skill/MCP, dùng `ai-environment-maintainer` đang cài và chạy audit.
Config MCP của repo chỉ có lệnh tương đối và tool allowlist; secret/index không
được commit. Xerj là tùy chọn, `rg` luôn là đường cơ bản khi chưa có index mới.

### Quản lý bộ công cụ hiện tại

Chưa cần thêm manager hoặc dashboard. Dùng đúng owner hiện có:

| Cần quản lý | Nguồn/cách kiểm tra |
|---|---|
| Skills, hooks, MCP và instruction budget | Skill `ai-environment-maintainer` và deterministic audit của skill |
| Source fork, pin, origin/upstream, license | [Integration catalog/doctor](../../tooling/integrations/README.md); `node tooling/integrations/doctor.mjs` |
| Tool/index và freshness | [Search tooling](../../tooling/search/README.md); lockfiles và manifest tương ứng |
| Cổng, process, dữ liệu local | Local-services registry/guide ở trên; launcher/owner receipt của runtime |
| Giao việc, retry/cancel và lịch sử engine jobs | [Native Paperclip contract](../../tooling/ai-engines/README.md) |
| Scope và tiến độ được nghiệm thu | PLAN → ledger/checkpoint mà PLAN chỉ định |

Đây là bảng điều hướng, không là registry/tracker mới. Chỉ thêm công cụ quản lý
khi có lỗi vận hành lặp lại mà các owner/check hiện tại chưa giải quyết được.

## License và nguồn lịch sử

Phần Naqex sở hữu dùng [license hiện hành](../../LICENSE); quyền cá nhân,
research, thương mại và chia sẻ source được giải thích trong
[chính sách license](../licensing.md). Fork và vendor giữ điều khoản riêng.
Không sửa commit lịch sử để áp license hồi tố. README chỉ dùng tên hiện hành;
tên cũ trong receipts, Git history và snapshot archive là provenance được giữ.
