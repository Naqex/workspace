# Recovery lỗi nhãn log trước khi tiếp tục recent screen

12/11/2026, nối [protocol đã khóa](US500-RECENT-SCREEN-PROTOCOL-20261112.md).
Attempt `us500-recent-development-v1` dừng tại 2024/RS03/reference sau 23 sổ,
115,69 giây. Giữ nguyên failure, source snapshot, seals và mọi kết quả âm/unknown.

## Nguyên nhân và thay đổi trước outcome tiếp

`FrozenPolicy` trả cả `kind=confirm` của trace trong entry decision. Khi thiếu
quote, native adapter thêm `kind=entry_prefix_gap` hoặc `missing_exact_fill`,
gây TypeError trùng keyword. Chỉ đổi boundary: entry decision giữ action,
timestamp, side, ATR và level; nhãn kind chỉ nằm trong policy_events. Không đổi
trigger, entry/exit clock, stop, sizing, costs, shortlist hoặc scoring.

Regression mới tái hiện TypeError trước sửa; sau sửa cả missing decision-minute
và missing fill-minute từ chối entry, không tạo trade. 8 setup tests, 5 runner
tests và 20 core native tests đạt. Golden actual-data 2022/RS01/reference đã
replay bằng source sửa: 195 trades, toàn bộ artifact khớp sau khi chỉ bỏ nhãn
`decision.kind` trong bản cũ; unresolved=1 giữ nguyên. Golden này không phải
new strategy trial hoặc bằng chứng edge mới; thời gian đo 10,10 giây gồm load.

## Quy tắc reuse cho attempt v2

Runner nhận parent và recovery contract cụ thể, kiểm exact manifest/completed
hash, stage/codes/years và mọi old→new source hash. Contract riêng ở campaign:
`execution-v1/us500-recent-recovery-contract-v2.json`. Bốn source delta được
review: policy boundary, regression setup, runner recovery và runner tests.
Các source/data/protocol pins khác không được drift; không bỏ guard mặc định.

Mỗi saved book phải có seal khớp book/review/parent manifest; input bindings,
signals và cadence mới phải khớp bản cũ. Chạy lại Fraction accounting reviewer,
policy-clock check, identity và metrics trước reseal vào output mới. Copy byte
book cũ, không overwrite parent hoặc tự biến unknown thành known. Hỏng một
binding thì dừng để điều tra, không tự rerun/skip qua lỗi. Các sổ chưa xong chạy
native bằng source mới. Đây là reuse sổ hoàn thành, không resume giữa tick.

Đầu ra v2 mới, deadline 1.800 giây, status/events/CANCEL giữ nguyên. Sau development
mới khóa selection theo protocol rồi chạy 2026 và historical stress. Không mở
outcomes 2026 của cả tám setup hoặc tuning rules trên dữ liệu mới.
