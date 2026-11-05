# Log/status đủ để vận hành và sửa lỗi

Quyết định05/11/2026: dùng status/receipt native hiện có và structured logs
trong consumer. Chưa cài collector/Grafana/Loki/OpenTelemetry service chỉ để
có dashboard. Local app/research vẫn do native Paperclip/runner own state.

| Loại | Ý nghĩa / owner |
|---|---|
| Status/receipt | Snapshot mới nhất của phase, input/run identity, progress và kết quả; không sửa tay để tự pass |
| Event log | Lịch sử chuyển bước/lỗi/counter, hỗ trợ trace theo run; không là task ledger |
| Checkpoint | State phục hồi theo contract, không tự là resume đã hỗ trợ |
| Result | Numeric outcome/provenance; process complete không chứng minh edge |
| Health/liveness | Quan sát riêng; timestamp cũ/PID tồn tại không đủ kết luận process còn đúng hoặc đã hỏng |

## Mức ghi tối thiểu theo rủi ro

Job dài cần run/attempt ID, source/config/input/protocol binding, PID/creation
identity nếu supervisor có, UTC timestamp, phase/progress, log/checkpoint locator,
deadline/cancel/recovery semantics. Event nên có sequence, level, error code,
stage thất bại và code location. Giữ quan hệ task→job→attempt khi giao qua native.
Không ghi secrets, authheaders/cookies, tài khoản thừa, full provider prompt/
response hoặc mỗi tick theo mặc định. Debug chi tiết chỉ trong scope sự cố.

Không bắt mọi edit/command nhỏ tạo một hệ logging mới; command exit/build/test
output cùng receipt phù hợp là đủ. Trước thay đổi cơ chế ghi hoặc format, mô tả
ngắn cho owner sẽ nhìn thấy gì; không tạo UI ngoài để nhân bản Paperclip.

## Consumer đang có

- Shadow: `shadow_watch.py` đọc native checksummed lifecycle, heartbeat và
  native documents; không thay bằng một runner status khác.
- API Rust đang có `tracing` startup/drain và launcher pump stdout/stderr;
  Paperclip local cấu hình file logs. Đây là các owner sẵn có, chưa được audit
  mọi endpoint/request tracing hoặc secret redaction trong task này.
- Forex study: `receipt.json` + `events.jsonl` + `failure.json` khi lỗi.
  Stdlib rotating handler tối đa1MiB/file +2backups, một writer/attempt; stdout
  vẫn là JSONprogress. Đây là event diagnostics, không xóa raw data/evidence.
- `strategy_evidence.py status --run-dir <attempt>` đọc snapshot và tuổi bản tin;
  stale báo process state unknown, không tự failed hoặc restart/resubmit.
- Errors lưu type/code/stage/source locations, không exception text/locals.
  CLI in lỗi gọn; từ artifact pin source tái hiện đúng failure. Consumer gọi
  Python main trực tiếp còn phải áp redaction ở boundary riêng của nó.
- Phase validation dài có thể chưa có counter mới; đây là last-progress time,
  không giả heartbeat background hoặc %completion. Terminal phase khác health.
- Forex batch tách lỗi quan sát khỏi điều khiển: receipt đang replace/khóa đọc
  có retry ngắn với Windows sharing error rồi báo `progress_read_error`; lỗi ghi
  JSON/Markdown projection báo `projection_errors`. Chúng không hủy numerical
  workers. Config/result/accounting và terminal persistence vẫn bắt buộc;
  thiếu/tamper ở đó không được nâng thành completed_verified.
- CLIresearchresume hiện chưa hỗ trợ. Có checkpoint không là quyền overwrite
  attempt hoặc replay lại broker request; unknown sends chỉ reconcile.

Trên Windows, PID của launcher/venv redirector có thể khác PID do worker ghi
trong receipt. Khi cần stop/recover, kiểm creation identity/process ownership
và supervisor của job; không coi kill launcher là đã dừng toàn bộ descendants.

Log rotation chỉ tác động diagnostic file của attempt đó. Giữ raw ticks,
manifest/results/failure/checkpoint và receipt; không thêm job retention/xóa
toàn bộ từ một logging task. Khi multi-service/multi-machine thực sự khó trace,
đánh giá OpenTelemetry/collector với data-flow/permission/cost/rollback riêng.

## Research và nguồn

Đọc05/11: [Python3.12 logging cookbook](https://docs.python.org/3.12/howto/logging-cookbook.html)
và stdlib RotatingFileHandler qua Context7 `/python/cpython`; runtime là Python3.12
đã có, không nâng theo phiên bản docs latest. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
phân biệt logs/metrics/traces. Các nguồn hỗ trợ cách instrument; quyết định chưa
cài backend ngoài dựa vào scope một máy và khả năng native hiện có.

Các skills nghiên cứu/vận hành/debugging dẫn tới guide này. Không cần một
skill logging riêng khi chưa có workflow độc lập với các consumer đó.
