# Sàng lọc nhanh H1: kết quả pilot — 07/11/2026

**Chấp nhận dùng thử để xếp ưu tiên kiểm tick cho tám rules hiện tại trên dữ
liệu đã dùng. Chưa cho phép tự loại, nâng bước hoặc kết luận đủ điều kiện quỹ.**
Danh mục đã có [36 hồ sơ](STRATEGY-CATALOGUE-20261107.md), gồm8 rules hiện có,
27 ý tưởng/biến thể và1 thành phần risk; không phải36 edge độc lập.

[Protocol](COARSE-SCREEN-PILOT-20261107.md) được giữ nguyên sau outcome; bản
freeze ở attempt có SHA256
`de93568faa76991de2d31daa4cb1eb7443fdf0685c990eacd71895549b7c1069`.
Source sản phẩm `03436225`; tối ưu core trước đó `8f924908`.
Không mở dữ liệu2025+, không gửi broker/model calls hoặc chạy annual study mới.

## Hành vi và luồng dữ liệu

Raw QDM đã có → kiểm hash/order/grid/date → cache H1 gồm Bid/Ask và midOHLC
→ builder H4 hiện có → rules/sizing/cost/financing hiện có → PnL xấp xỉ.
Một cache phục vụ cả nhóm rules; không cache trạng thái position của strategy.
Cache mới có checksum/source/runtime binding, rehash raw khi load; không nới
guard của tick/inspection cache cũ sau khi source đã đổi.

Pending entry/strategy exit dùng quote đầu H1 sau decision. Cắt lỗ trong giờ
dùng mức SL hoặc gap đầu giờ; nó không biết tick đầu tiên thực sự vượt SL.
Thời điểm stop được ghi thành khoảng, không bịa một timestamp chính xác.
Cuối mẫu giữ position/pending/floating; phí financing không bị cộng hai lần.

Đánh đổi: bỏ full tick risk, full prop lifecycle và intrabar drawdown để giảm
chi phí sàng lọc. Margin ở đây chỉ kiểm xấp xỉ theo vốn ban đầu, chưa thay
account-wide equity/margin/risk owner. Đây là schema nghiên cứu riêng,
không phải native tick dossier được verified.

## Kiểm dữ liệu và kết quả

| Phần | Bằng chứng | Kết luận trong scope |
|---|---|---|
| Raw→H1→H4 |Warmup1.404.696ticks/550H1/133H4; quý5.837.028ticks/1.537H1/372H4|Toàn bộ H4 và excluded timestamps khớp sealed inspection archive|
| Fixture độc lập |8tests +2subtests,0,51giây|BUY/SELL, timing, phí/credit/floating, SL/gap, calendar/weekend, partialFriday, pending, cache/order/tamper đạt|
| Tick source hiện tại |03–07/01/2022;326.373ticks/118H1;4rules×2costs|8/8 khớp PnL đến cent, decisions, entry/closed/open/pending counts; không risk stop/rejection|
| Tick lịch sử cả quý |4Discovery rules×2costs; original dossiers kiểm lại bằng rawhash/seals/source-snapshot|8/8 trong budget đã khóa6,25USD; decisions, entries/sizes/prices, số lệnh, open/pending và financing khớp|
| Tính độc lập/edge |Q1/2022 đã consumed, source chia sẻ helpers với native|Không phải cleanOOS, independent engine oracle hoặc evidence kiếm payout|

Đối chiếu quý dùng cả bản lời và lỗ, không chỉ chọn winner. Chênh lệch dưới
đây là **coarse trừ tick**, trên vốn10.000USD/risk dự kiến25USD:

| Rule | Tick phí chuẩn/cao USD | H1 phí chuẩn/cao USD | Chênh lệch mỗi cost USD |
|---|---:|---:|---:|
| Failed20 |−7,70 / −22,46|−7,37 / −22,13|+0,33|
| Compression |+50,38 / +28,47|+50,42 / +28,51|+0,04|
| Range fade |−71,78 / −76,84|−71,70 / −76,76|+0,08|
| UTC range breakout |+34,13 / +26,67|+34,61 / +27,15|+0,48|

Trade audit xác định phần lệch đều ở stop fills: mức SL xấp xỉ tốt hơn quote
thực vượt mức từ1–6ticks giá trong các trade bị lệch. Entry, financing và
floating khớp theo số học; timestamp native exit nằm trong interval coarse.
**Sai số đang thiên về lạc quan**, không là noise ngẫu nhiên hoặc bound cho
mọi thị trường. Chưa có stress lịch sử buộc internal risk dừng trong mẫu này;
fixture gap không thay thế kiểm tail market. Không dùng budget6,25USD làm
ngưỡng edge/statistical significance hoặc error guarantee của run tương lai.

Bốn rules cũ còn lại đã chạy H1 nhưng không nằm trong acceptance đối chiếu
full-quarter lần này. Không nâng thành16/16 full-quarter tick parity.
Bounded tick cases có ít trades, một mẫu thời gian; chúng không xác nhận
độ đúng của toàn bộ market paths hay nguồn dữ liệu broker.

## Thời gian đo được

Máy Intel i5-9400F,6cores/6logical, Windows/Python3.12; một process, không GPU.
Mỗi benchmark case đo một lần, không là p95/capacity hoặc median ổn định.
Input read tách khỏi compute; thời gian nhỏ chịu nhiễu scheduling/CPU timer.

| Chặng | Wall đo được | Phạm vi / reuse |
|---|---:|---|
| Research/spec/code trước protocol |Chưa đo đầy đủ|Không suy từ commit/mtime hoặc báo0|
| Chuẩn bị cold H1 từ raw warmup+quý |73,38giây|7.241.724quotes; không export/download; dùng lại cho cả nhóm|
| H1 cached screen8rules×2costs |1,85giây|Gồm load/hash/compute/output; tổng compute các row0,972giây; đây là16 scenarios xấp xỉ|
| Tổng hai chặng máy trên |75,23giây|Cộng thời gian chạy đo được; không gồm khoảng người review/dispatch giữa chặng|
| Bounded H1cache load/hash |0,804giây|Ngoài compute timing|
| Đọc raw prefix cho bounded tick |3,274giây|Một lần; không tính vào từng case compute|
| Native tick8bounded cases |20,713giây|Gồm accounting/checkpoint writes và tick/internal risk; không có prop observer|
| Coarse8bounded cases |0,04894giây|Tổng compute; không có full risk/DD hoặc native journal/checkpoint|
| Đối chiếu/manual review/catalogue/docs |Có log mốc, chưa active timer đầy đủ|Không cộng chồng thành agent-time hoặc cost/token|

Ratio compute trong bounded workload khoảng423× vì **khác mô hình/phạm vi**,
không phải tăng tốc423× cho native engine. Mục tiêu engineering≥5× của pilot
đạt trong scope xấp xỉ này. Không lấy ratio để chia thời gian annual, số đo
13phút discovery cũ hoặc3giờ17phút toàn quy trình. Dữ liệu mới phải trả chi
phí chuẩn bị; source đổi có thể làm cache invalid theo đúng guard.

Số đo1,85giây là economic approximation, khác feasibility probe<1giây trước
đây vốn chưa tính PnL. Job numeric có0model calls; agent research/code/review
vẫn dùng token của phiên. Không benchmark RAM peak/cache mới hàng trăm rules.

## Hậu kiểm kỹ thuật và quyết định

| Lát | Phát hiện | Hành động |
|---|---|---|
| Correctness |H1stop lạc quan; full tick risk/prop bị lược ở prototype|Ghi rõ assumptions trong schema/report; bắt buộc tick review trước quyết định kinh tế|
| Data/reuse |Cache tick cũ invalid sau source change|Giữ guard; tạo H1 mới từ raw một lần; đối chiếu H4 với sealed archive|
| Reliability |Harness đầu tiên đọc cả key schema như input|Đã sửa harness chỉ nhận warmup/development trước bounded dispatch; chưa có numerical output bị mất/overwrite|
| Performance |Đọc chuẩn bị chiếm phần lớn cold run|Reuse cache cùng binding; chưa có lý do thêm GPU/Rust/service/parallelism cho H1loop nhỏ|
| Catalogue |Nhiều tên chỉ là biến thể/thiếu data|Ghi parent/family/readiness/source relation; chưa gọi36bots hoặc tự dispatch|
| Workflow/skills |Các workflow hiện có đã bao phủ freeze/evidence/review|Không thêm skill hay tracker/UI cạnh tranh; lưu delta ở plan/receipt/index|

Không phát hiện material implementation bug mới trong phạm vi kiểm. H1model
chỉ phù hợp triage các rules tương thích; đổi timeframe/TP/risk/entry cần
version/protocol/tests mới. Chưa có calibrated false-negative rate hoặc edge
ground truth để tự loại cả family.

Khuyến nghị tiếp: khóa spec nhóm nhỏ khác cơ chế từ catalogue, triển khai và
kiểm fixtures trước; chạy H1 để sắp thứ tự tick review, giữ một số bản định
gác để kiểm chéo theo protocol mới. Annual/OOS/holdout/demo không tự dispatch.
Không quay lại annual versions đã completed chỉ vì có screen nhanh.

## Evidence và tái hiện

Private attempt:
`E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\coarse-screen-pilot-20261107\execution-v1`.

- `protocol.md`, `inputs.json`, `activity.jsonl`: scope, dispatch và raw pins.
- `preparation/`, `hour-cache/`, `coarse/`: output riêng, progress/log và source pins.
- `input-parity.json`: full H4 equality; `original-dossier-audit.json`:4 original
  source-snapshot dossiers/raw hashes/seals đã verified.
- `historical-comparison.json`, `historical-trade-audit.json`:8quarter comparisons.
- `bounded-comparison/comparison.json`, per-case native/coarse results và
  `bounded.log`:8current-source cases. `validate_pilot.py`, `audit_trades.py`,
  `verify_original.py` giữ harness tại attempt; không có worker còn chạy.
- `evidence-seal.json`: hash outputs/harness quan trọng, không ghi secrets/raw data.

Focused fixtures đã chạy:
`foundation_v2/.venv/Scripts/python.exe -m pytest -q foundation_v2/tests/test_forex_coarse_screen.py`.
Không chạy lại suite không đổi chỉ vì viết report. CLI prepare dùng
`scripts/forex_coarse_screen.py --input-manifest <inputs> --cache-dir <hours>
--protocol <frozen> --output-dir <new-dir> --prepare-only`; bỏ prepare-only để
screen. Bounded harness chỉ đọc prefix đã consumed; output root phải mới khi
thực sự tái chạy. Không overwrite accepted attempt hoặc đổi protocol theo outcome.
