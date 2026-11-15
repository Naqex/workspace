# V11 — selective cache purge, cross-drive admission và ensemble cố định

Task `dcef7958-01c0-4b7c-97f6-8b896d1ca898`. PR89 merge `3dd35a7`;
branch `codex/ensemble-and-storage-v11`. Một PR mới dự kiến90, không tự merge.
Giữ VI WIP, Trader pin, raw sources và mọi frozen attempt/seal. Không broker,
paid provider, Astra hoặc runtime promotion. Không agent delegation trong task.

## Quyền và diễn giải

Owner cho phép xóa đúng manifest V10 `E-cleanup-dry-run-manifest.json`.
Đây là cache có thể tái tạo, không phải quyền mirror/purge E hoặc xóa research.
Mỗi target phải đúng root/path, không reparse/embeddedGit, file set/size/mtime
khớp manifest và không có process đang tham chiếu. Kiểm trước toàn bộ, giữ
target lệch hoặc có dữ liệu thị trường; ghi cụ thể thay vì ép đạt119,79GB.
Before/after inventory D workspace và E backup là logical readable bytes;
hai VI permission gaps không thành0, không thay ACL.

V10 yêu cầu20admitted/year trung bình mỗi cụm và4/6positiveyears, không80
hoặc mọi năm dương. Owner nay cho phép gate mới ở ensemble: đây là **V11 trial
sau khi thấy V10**, không sửa verdict/pins V10. Equal weighting vẫn có selection
bias. IR=IC×sqrt(breadth) cần bets độc lập và assumptions; không lấy544ô
tương quan làm544bets hoặc chứng nhận edge từ dual-cluster positivity.

2024–13/10/2026 chưa đo F1–F4 trong V10, nhưng đã exposed qua chiến dịch khác
và ảnh hưởng hướng nghiên cứu: **reused historical validation**, không cleanOOS.
Trước composition commit chỉ đọc metadata availability/timestamps ngoài Dev,
không phân tích giá/returns validation. Không giá sau13/10/2026.

## Storage và cross-drive metadata

Reconcile V10 manifest bằng SHA256 trước mutation. Không thêm target purge
ngoài manifest kể cả thư mục mới tên cache. Tách exact bytes/files đã xóa với
net before/after vì các job khác có thể ghi. Log intent và từng target completion.
Không lấy hash metadata làm content-duplicate proof. Không follow junctions.

Đọc metadata D:/ANNAM và E:/BACKUP-TRADINGWORKSPACE; root D/E chỉ định tuyến
thêm nơi có dấu hiệu trading. Exclude OS/apps/games/dependencies/build targets,
không đọc nội dung dự án cá nhân không liên quan. Ghi excluded/error roots.
Nhận diện symbol/timeframe/date span qua manifests/path hoặc timestamp-only;
không tự coi tên filename là source quality. QDM inventory là metadata.
CSV/binary/Parquet chỉ admit sau schema/coverage/units/quote/cost specification.
Mount/index read-only theo path/hash, không nhân bản full market data.

Asset mới chỉ quét nếu full2018–2023 +causal warmup đã admission cùng cost/spec.
Reuse đúng grid F1–F4 V10, không mở rộng lookbacks/directions/horizons.
Thêm asset làm tăng trial history, ghi trước numeric; thiếu source hoặc cost
thì ghi gap và không dựng M1 từ H1 hoặc tự giả đây là target fills.

## Extraction và component admission (Development2018–2023)

Nguồn chính: V10 reviewed matrix/discovery, không original lỗi DAY.
Mọi row vẫn là raw endpoint markout, chưa SL-active hoặc equity account.

Xuất toàn bộ544ô với dual-cluster SYM rawNetR>0 và retain15%≥50% ở **mỗi cụm**,
cùng Top15 cũ kể cả fail. Direction BOTH như registered, không side tuning.
Bảng có raw/admitted/year, natural scale, raw/admitted means, six annual R,
entry-date daily endpoint-R drawdown và lý do V10 từng từ chối. R-DD kiểu này
không được gọi floating/daily prop loss.

Component gate:

- SYM raw và admitted NetR>0 ở cả hai cụm.
- Admitted mean SYM netR/trade≥0,04 trên cả Dev.
- Retain≥50% và pooled medianF/medianNaturalSL≤15% ở mỗi cụm.
- Endpoint coverage100%: không bỏ missing-price rows để cứu gate.
- Không cadence hoặc số năm dương tối thiểu ở từng nhánh. Báo ASYM riêng;
  không chọn cost view thuận lợi sau outcome.

Không dùng pHolm/DSR V10 làm gate component mới; vẫn giữ/report chúng và
trial count. Việc nới gate là owner-authorized V11, không chứng minh V10
đã sai về statistical evidence.

## Composer không weight search

Một lần build cố định, không thử mọi subset K hoặc maximize Sharpe/Calmar.
Daily vectors ban đầu dùng entry-date raw endpointR (zeros weekdays), cùng
V10; đây là selection proxy, chưa actual daily mark-to-market PnL.

1. Trong cùng asset/family, nối edge nếu corr daily≥0,30 hoặc trùng≥50%
   decision timestamps (giao/min số events); connected components là các
   cụm cơ chế. Quy tắc overlap chặn nhiều stop/horizons của cùng entry được
   tính thành các nhánh độc lập.
2. Mỗi cụm giữ medoid có tổng distance(1−corr) nhỏ nhất; tie lexicographic ID.
   Không chọn highest profit/Calmar sau khi nhìn validation.
3. Sort representatives theo asset/family/ID/horizon; nhận tuần tự nếu corr
   với mọi đại diện đã nhận<0,30; giữ tối đa8. Không tìm ordering/subset khác.
   Báo correlation/overlap matrix và những đại diện bị chặn.
4. Equal risk1R mỗi trade của từng sleeve; K phải3–8.

Ensemble Dev gate: avg admitted≥50/year ở mỗi cụm (120/year là mục tiêu,
không trần),≥5/6positiveyears, raw/admitted clusterNetR>0 cả SYM/ASYM,
NetR/Max cumulative endpointR-DD **lớn hơn mọi sleeve thành phần**.
Không tự thêm ngưỡng cải thiện phần trăm. Báo min annual cadence.

Nếu đủ gate endpoint: replay selected components trên M1 với naturalSL,
nohardTP, cùng horizon/calendar; hai intraminute orderings, quantity/cost
rounding, shared risk và equity/daily Prague reset. Không thay stop/entry/
hold horizon để cứu kết quả. Correlation actual daily MTM, cluster economics,
5/6years/cadence và efficiency phải còn đạt; missing path là unknown, không0.
Fixed reference150USD/trade trên50k, account-wide open-stop budget800USD,
không phase/risk grid. Budget áp cùng cho mọi sleeve.

GoldA là đối chứng cũ, không tự thành một component để đủ K. Chỉ xét đúng
1variant thêm GoldA sau khi structural ensemble đã đạt Dev path gate; chỉ giữ
nếu Dev cải thiện và không làm âm2018–2020. Ghi binary selection exposure.

## Freeze, validation và account lifecycle

Không đủ K hoặc gate thì lưu composition=None và canceled downstream; không
được ép tạo portfolio cho đủ bảng9năm. Nếu đủ, commit danh sách/logic/risk/cost/
calendar/source trước lần mở validation đầu tiên; một release, không refit.

Validation2024/2025/2026YTD đo từng sleeve và ensemble cả SYM/ASYM. M1/tick
gaps/Ask proxy/margin/calendar/news restrictions vẫn phải được ghi; không claim
FTMO-qualified khi chưa target-native path/terms admission.
Nine-year annual metrics chỉ lấy actual SL-active continuous equity; không
điền raw endpointR thành Challenge/account results.

Nếu qua Dev path gate, reuse lifecycle/account engine qua Quant Core adapter:
50k, fixed150USD/sleeve trade, shared800USD budget;5%daily/10%static và
10%/5%targets theo scenario cũ. Monthly starts2018–21(48),2022–24(36),
2024–Oct2026(34); các cohort overlap không là independent pass trials.
Biweekly funded harvester theo policy engine có sẵn, fees/split explicit;
không cắm giả policy vào backend fixed fixture. Unsupported adapter semantics
là gap cần sửa/đối soát, không đổi tên simulation cũ thành ensemble mới.

## Engineering, kiểm chứng và bàn giao

`cross_drive_audit` là explicit read-only health command, không daemon và
không bảo đảm cache không bao giờ mọc lại. Báo growth/budget violation;
chỉ một audit định kỳ mới có thể theo dõi tương lai, chưa tạo automation.
Không sửa frozen financial code/seals để thêm maintenance.

Smoke mục tiêu<1s, không bỏ meaningful tests để ép timing. Full giữ1030IDs cũ
và tests mới,0skip trên Windows; CI3checks đúngHEAD. Test actual containment,
manifest drift/protected paths/partial failures, dedup/correlation/drawdown
fixtures và independent scalar recomputation. Oracle cùng implementer khác
arithmetic; không tự nhận independent person review.

Report4phần +compactJSON +private receipts/path/hash; giữ failures/canceled
stages và cập nhật context/index. Push một PR mới, chờ3CI, không tự merge.
