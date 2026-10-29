# Phát triển trong Naqex Workspace

## Ownership

```text
workspace/
├── AGENTS.md                 # hướng dẫn agent và gate theo phạm vi
├── .agents/skills/           # workflow lặp lại đã kiểm chứng
├── docs/                     # hướng dẫn hiện hành, sơ đồ và assets README
│   └── archive/              # snapshot tài liệu lịch sử
├── planning/                 # scope → ledger/checkpoint do PLAN chỉ định
├── projects/                 # sản phẩm; mỗi thư mục là một Git repo
├── tooling/                  # kiểm tra và công cụ dùng chung
├── UI-Systems/               # UI foundations
├── UI/                       # quy tắc UI cho trading
└── education/                # course, bài tập và tiến độ
```

Source có owner theo sản phẩm. Plan không là cấu hình runtime, README không là
ledger, search index không là nguồn sự thật. Fork giữ layout/upstream riêng.
Không tách API, web và worker của Trader thành submodule nhỏ hơn.

## Bắt đầu một task

1. Đọc `AGENTS.md` gần file cần sửa và README của đúng sản phẩm.
2. Tìm implementation tương tự bằng `rg`; dùng [Xerj](../../tooling/search/README.md)
   khi cần tìm theo khái niệm trên corpus lớn. Xác nhận kết quả ở source gốc.
3. Chốt scope và bằng chứng cần có trong owner plan đang dùng; task nhỏ chỉ cần
   diff/PR, không tạo thêm plan hay tracker.
4. Sửa, kiểm chứng, commit và PR trong repo sở hữu code. Merge sản phẩm trước,
   rồi cập nhật pin bằng PR ở workspace.

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

Giữ instruction ngắn trong `AGENTS.md`; workflow nhiều bước nằm trong repo skill,
context dài nằm trong reference. Chỉ thêm MCP khi có nhu cầu thật và kiểm tra
quyền/data flow. Không chạy bộ cài tự sửa global config của bên thứ ba.

Khi sửa AGENTS/skill/MCP, dùng `ai-environment-maintainer` đang cài và chạy audit.
Config MCP của repo chỉ có lệnh tương đối và tool allowlist; secret/index không
được commit. Xerj là tùy chọn, `rg` luôn là đường cơ bản khi chưa có index mới.

## License và nguồn lịch sử

Phần Naqex sở hữu dùng [license hiện hành](../../LICENSE); quyền cá nhân,
research, thương mại và chia sẻ source được giải thích trong
[chính sách license](../licensing.md). Fork và vendor giữ điều khoản riêng.
Không sửa commit lịch sử để áp license hồi tố. README chỉ dùng tên hiện hành;
tên cũ trong receipts, Git history và snapshot archive là provenance được giữ.
