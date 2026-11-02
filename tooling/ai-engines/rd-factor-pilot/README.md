# RD-Agent: pilot factor giới hạn

Pilot operator-triggered dùng Gemini sinh một file Python, rồi chạy bằng
`FactorFBWorkspace` và evaluators của RD-Agent pin hiện có. Dữ liệu hoàn toàn
giả lập: 160 ngày × 8 mã, factor `close[t] / close[t-3] - 1` theo từng mã.
Không phải vòng `fin_factor`/Qlib đầy đủ, backtest hay kiểm chứng lợi nhuận.
Paperclip worker vẫn paused; adapter hiện chưa dispatch pilot này.

## Luồng và giới hạn

1. `pilot.py <job-directory>` ghi prompt và contract trước khi gọi model.
2. Operator gọi model đúng một lần bằng kết nối project đã được duyệt, lưu
   requested/reported model, usage và SHA256; review candidate trước khi chạy.
   Script pilot không đọc credentials hoặc tự gọi provider.
3. `--candidate <file> --image sha256:...` chạy candidate trong Docker, so với
   oracle vòng lặp độc lập; giữ đủ index/order và 24 giá trị NaN warmup.
4. Chạy candidate với prefix và dữ liệu tương lai bị thay đổi để kiểm
   invariance. Negative control dùng công thức cố ý nhìn trước; kiểm tra riêng
   một candidate phát sinh lỗi để xác nhận workspace nhận ra execution failure.
5. Lưu `result.json`, `executions.json`, fixture, candidate và task. Không tự
   thử candidate khác, sửa chiến lược, promote hoặc mở broker.

Contract ghi train/validation/test 90/30/40 ngày để cố định ý định; pilot này
không fit hoặc chọn model, nên không báo OOS performance hay chống overfitting
đã hoàn tất. Prefix cutoff ở ngày 120 là kiểm tra nhân quả, không là backtest.

Container: network none, user 1000:1000, CPU 1, RAM 512 MB, pids 64, 50 giây,
cap-drop ALL, no-new-privileges, root filesystem read-only, tmpfs 32 MB. Chỉ
workspace output được ghi và folder input được mount read-only; không mount
Docker socket, controller/venv, credentials hoặc ổ Windows. Workspace output
chưa có disk quota riêng; đây là pilot code đã review, không là sandbox chứng
nhận cho code thù địch. Linux controller có quyền Docker và phải giữ độc lập.

## Chạy lại có chủ đích

Theo [runtime guide](../rd-agent-runtime.md), dùng riêng `NaqexResearch`.
Chuyển ba file `Dockerfile`, `docker-python.sh`, `pilot.py` đã review vào
`/opt/naqex/rd-agent/pilot-tooling-20261102/` bằng archive qua stdin WSL;
không bật Windows automount. `naqex` sở hữu tooling/job directories. Tạo
directory job mới; không ghi đè evidence của lượt đã hoàn tất.

Các lệnh sau chạy trong **cùng một shell root của distro**, working directory
Linux truy cập được bởi `naqex`. Shell giữ distro/Docker sống trong suốt job
và dừng dịch vụ khi kết thúc; chỉ dùng khi không có job khác sở hữu runtime:

```sh
set -eu
systemctl start docker.service
trap 'systemctl stop docker.socket docker.service containerd.service' EXIT
tooling=/opt/naqex/rd-agent/pilot-tooling-20261102
job=/opt/naqex/rd-agent/pilots/replace-with-new-job-id
install -d -o naqex -g naqex "$job"
cd "$job"
runuser -u naqex -- docker build -t naqex-rd-factor:pilot "$tooling"
image=$(docker image inspect --format '{{.Id}}' naqex-rd-factor:pilot)
docker image inspect "$image" > "$job/image.json"
runuser -u naqex -- /opt/naqex/rd-agent/venv/bin/python "$tooling/pilot.py" "$job"
# Tạo/review candidate ngoài root shell, lưu model-attempt.json trước khi execute.
runuser -u naqex -- env -i HOME=/home/naqex USER=naqex PATH=/usr/bin:/bin \
  LANG=C.UTF-8 DO_NOT_TRACK=1 LITELLM_LOCAL_MODEL_COST_MAP=True \
  /opt/naqex/rd-agent/venv/bin/python "$tooling/pilot.py" "$job" \
  --candidate "$job/candidate-reviewed.py" --image "$image"
```

Hai pha chuẩn bị và execute có thể dùng hai shell, mỗi shell tự giữ Docker
và cleanup như trên. Provider request dùng kết nối project ở phía operator.
Wrapper được gọi bằng `sh`, không phụ thuộc executable bit sau khi chuyển
từ Windows. Base image tag và package versions chưa khóa toàn bộ dependencies;
mỗi rebuild phải lưu image ID mới. Đây chưa là launcher/cancellation contract
của Paperclip.

Sau job, đọc nội dung result và exit status, lấy bản sao evidence về Windows
bằng các regular files được chọn từ archive; không extract symlinks mù.
Chỉ terminate đúng distro khi không còn owned job. Nếu đã bật gateway riêng
cho pilot, trả nó về trạng thái trước đó sau kiểm tra PID/path/start time.

## Lượt đã kiểm chứng

02/11/2026: 1.280 rows, 1.256 giá trị hợp lệ; 5 upstream evaluators đạt 1;
oracle, prefix/future perturbation và failure controls đạt. Một provider call,
không retry. Chi tiết, hashes và các lần sửa harness nằm trong
[receipt hiện có](../../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md).
Không chạy lại job/model chỉ để xác nhận tài liệu không đổi.
