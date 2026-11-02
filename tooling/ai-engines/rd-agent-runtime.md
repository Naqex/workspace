# RD-Agent: môi trường Linux riêng

Owner đã cho phép cài Linux/Docker ngày 02/11/2026. Chọn **WSL2 Ubuntu 24.04 +
Docker Engine trong distro**: RD-Agent pin hiện tại yêu cầu Linux, phần finance
dùng Docker. Linux giữ package/venv; container giữ môi trường thí nghiệm có thể
dựng lại. Docker Desktop chưa cần cho luồng này. Đổi lại, runtime được quản lý
bằng lệnh và phải theo dõi cập nhật bảo mật của cả distro/Docker.

## Ownership và dữ liệu

| Thành phần | Nơi giữ |
|---|---|
| Source chuẩn/pin | Gitlink `projects/integrations/rd-agent` trong workspace |
| Distro WSL2 | `NaqexResearch`, Windows user hiện tại |
| Đĩa Linux | `.runtime/linux/NaqexResearch/ext4.vhdx` trên Windows |
| Bản source dùng để build package | `/opt/naqex/rd-agent/source` trong Linux; phải khớp gitlink |
| Venv độc lập | `/opt/naqex/rd-agent/venv` |
| Evidence/package freeze | `/opt/naqex/rd-agent/evidence`, bản sao Windows trong `.runtime/linux/evidence` |
| Worker và công việc | Native Paperclip; worker nghiên cứu vẫn paused |

VHDX là dữ liệu runtime có đăng ký với WSL. Không xóa/di chuyển nó bằng cleanup
cache hoặc `git clean -fdx`. Dùng WSL export/backup trước thay đổi distro. Bản
source Linux phục vụ build/runtime, không trở thành repo sản phẩm thứ hai.

Không thay `~/.wslconfig`, Docker Windows, provider/gateway hoặc service Trader.
Trong distro riêng: automount ổ Windows và Windows interop bị tắt; user mặc
định `naqex`. Docker chỉ dùng Unix socket, không mở TCP API. User này thuộc
Docker group, tức có quyền quản lý container/root trong distro; không đưa socket
Docker, venv/controller, toàn repo, secrets hoặc ổ Windows vào generated-code
container. Đây là giới hạn truy cập thực dụng, không là chứng nhận sandbox tuyệt đối.

## Kiểm tra và sử dụng

Luôn chỉ rõ distro/user/working directory để không vô tình dùng Linux mặc định
khác hoặc đường dẫn Windows đã tắt automount:

```powershell
wsl.exe --list --verbose
wsl.exe -d NaqexResearch -u naqex --cd /opt/naqex/rd-agent --exec /opt/naqex/rd-agent/venv/bin/python -m pip check
wsl.exe -d NaqexResearch -u naqex --cd /opt/naqex/rd-agent/source --exec git rev-parse HEAD
git -C projects/integrations/rd-agent rev-parse HEAD
```

Khi thực sự cần Docker cho job đã được duyệt:

Giữ start Docker, bounded job và cleanup trong cùng một shell WSL; xem recipe
[factor pilot](rd-factor-pilot/README.md). Không dựa vào hai lệnh WSL rời nhau
để giữ distro/service sống giữa các lần gọi.

Sau job, khi không có process/job khác sở hữu distro:

```powershell
wsl.exe -d NaqexResearch -u root --cd /root --exec systemctl stop docker.socket docker.service containerd.service
wsl.exe --terminate NaqexResearch
```

Docker service/socket/containerd đã tắt autostart. Không dùng `wsl --shutdown`
để dừng riêng runtime này. Không tự restart/terminate khi còn pip/apt hoặc job
đang ghi dữ liệu. Không tự cập nhật source pin cùng lúc sửa dependencies.

## Cài lại / nâng cấp

Trong một distro candidate riêng: cài Ubuntu từ catalog chính thức WSL; dùng
apt repository/signing key chính thức của Docker; tạo user và venv riêng; checkout
đúng gitlink; cài từ source và `pip check`. Lưu versions/freeze và kiểm tra
`rdagent --help`, Docker SDK ping cùng container smoke trước khi cutover.
Không chạy installer tải-và-thực-thi mù, không cài dependency vào TradingAgents
venv, không chỉnh global `safe.directory` để né ownership của repo Linux.
User `naqex` sở hữu bản source; đọc Git bằng chính user đó.

RD-Agent health check cần `--no-check-env` trong lượt kiểm tra runtime để tránh
gọi model/embedding mặc định. Dùng `--no-check-ports` khi chưa bật UI riêng.
Các check upstream có thể ghi lỗi nhưng vẫn trả exit 0: phải kiểm cả logs và
assert Docker SDK/container, không chỉ exit status.

## Gate còn lại

Một [pilot factor giả lập](rd-factor-pilot/README.md) đã đạt ngày 02/11: một
candidate Gemini, chạy upstream workspace/evaluators trong container giới hạn,
so oracle độc lập, kiểm tra nhân quả và execution failure. Không fit/chọn model
hay dùng dữ liệu thị trường thật. Đã gọi provider một lần, không retry.

Worker vẫn paused; adapter từ chối RD dispatch. Còn data adapter có provenance,
contract vòng finance đầy đủ và native dispatch/cancellation trước khi mở worker.
Chưa dựng image finance Qlib/CUDA lớn, tải dataset thị trường hay chạy một vòng
`fin_factor/fin_model/fin_quant`. Quant Lab giữ kiểm chứng chiến lược.

Kết quả và các lỗi cài đặt thực tế nối vào
[AI integration receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md).
Nguồn: [RD-Agent](https://github.com/microsoft/RD-Agent),
[WSL commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands),
[Docker Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
