# AI integrations

Source ngoài đã chọn nằm ở `projects/integrations/`; sản phẩm Trader, Quant Lab
và VI Dubber giữ ở `projects/`. [Catalog](catalog.json) giữ đường dẫn, role và
upstream; `.gitmodules` giữ remote checkout, gitlink của workspace giữ revision.
Không ghi SHA phiên bản chạy vào nhiều config độc lập.

| Thành phần | Cách dùng hiện tại |
|---|---|
| Paperclip | Fork [Naqex/paperclip](https://github.com/Naqex/paperclip); UI thật nhúng trong Trader; [launcher và data boundaries](../paperclip/README.md) |
| RD-Agent | Source upstream pin `484776c2` (1.0.0); worker Paperclip đã chuẩn bị nhưng paused. Chưa cài Linux/Docker hoặc chạy thí nghiệm |
| TradingAgents | Đã nối native process adapter của Paperclip; NAQ-4 chạy Gemini và có báo cáo VI. LangGraph là dependency engine; chưa kiểm chứng chiến lược |
| Quant Lab | Giữ `projects/quant-trading`; kiểm chứng/offline receipts. Engine bên ngoài được reuse khi cần; không thay engine chỉ để đồng bộ tên thư mục |

```powershell
git submodule update --init -- projects/integrations/paperclip projects/integrations/rd-agent projects/integrations/TradingAgents
node tooling/integrations/doctor.mjs
node tooling/integrations/doctor.mjs --runtime
```

Doctor mặc định chỉ đọc Git/license/path; `--runtime` thêm GET health loopback
của Paperclip. Không đọc secret, import engine, gọi model hoặc tạo job. Source
ready không chứng minh dependency, job hay broker readiness. Cấu hình cổng dùng
`projects/trader/foundation_v2/local-services.json`; không lấy cổng upstream mặc định.
Launcher Paperclip cần checkout feature Trader như hướng dẫn của nó; gitlink
Trader baseline hiện chưa chứa config này, nên chưa tuyên bố clean-clone runtime ready.

## Fork và cập nhật

Paperclip checkout nhánh `codex/naqex-integration`, origin là fork Naqex, upstream
là paperclipai/paperclip. Nhánh master của fork có thể mới hơn pin chạy; không
checkout master hoặc dùng `submodule update --remote` khi khởi động. TradingAgents
giữ origin Naqex và upstream TauricResearch. RD-Agent dùng upstream nguyên bản
đến khi có thay đổi cần fork; không nhân fork chỉ vì đã chọn dùng.

Clone mới có thể chưa có remote tên upstream. Thêm remote đúng URL trong catalog
khi thực sự cần cập nhật. Đọc AGENTS/rules/manifest của repo trước khi chạy code.
Candidate update ở checkout riêng: review diff/license/install scripts, môi trường
riêng, focused validation, rồi mới đổi pin. Backup/duyệt migration và runtime
cutover theo scope hiện hành. Không ghi đè dữ liệu để rollback source.

## Đường dẫn, environment và rollback

Windows junction của node_modules và Python editable install có thể trỏ tuyệt
đối về checkout cũ. Sau relocation phải relink/reinstall đúng môi trường và kiểm
đường dẫn module thực; `git mv` pass không chứng minh runtime pass. Không dùng
venv đã chuyển như environment portable; khôi phục dependency bằng manifest/
lockfile khi cần dựng lại. Lát local hiện đã cài lại riêng editable TradingAgents.

Cutover 31/10 giữ instance Paperclip tại `.runtime/paperclip/instances/trader-ui/`;
SQL backup + stopped-cluster/config/owner snapshot tại
`.runtime/paperclip/cutover-20261031/`. Node junction snapshot/repair receipt ở đó.
Đây là dữ liệu local có thể nhạy cảm, không commit. Rollback: dừng đúng owner,
đảo relocation source và launcher bằng Git; relink/reinstall dependency theo
đường dẫn phục hồi; giữ instance hiện tại. Chỉ restore snapshot DB nếu dữ liệu
thực sự hỏng, sau khi đã sao lưu dữ liệu mới và owner duyệt việc mất thay đổi mới.

Plan/acceptance: [AI workspace](../../planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md),
[issue #6](https://github.com/Naqex/workspace/issues/6). [Engine jobs](../ai-engines/README.md)
giữ contract bounded input và hướng dẫn giao việc qua UI gốc. Paperclip sở hữu
dispatch, concurrency và cancellation; wrapper không tự retry outcome chưa rõ.
Không tạo agents chạy command tùy ý từ catalog source. Kết quả thực tế và gate
RD-Agent nằm trong [receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md).
