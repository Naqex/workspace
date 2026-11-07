# Kết quả năm: UTC2024 và Compression2023 — 07/11/2026

**Hai study đã hoàn tất và đối soát đạt; cả hai phiên bản không được nâng bước.**
Mỗi bản âm ở cả hai mức phí trong năm kiểm tiếp. Các kết quả dương trước đó
chưa cho thấy độ bền qua thời kỳ. Chưa có ứng viên đủ bằng chứng để đưa vào
challenge/quỹ; không tự tăng risk, sửa TP/SL hoặc chọn lại quý để cứu kết quả.

Đây là kết quả nghiên cứu lịch sử theo các giả định đã khai báo, không clean OOS
hoặc chứng nhận toàn bộ luật quỹ. 2025+ chưa mở. Không có lệnh broker/model call
trong các job số học. Native pipeline đã kết thúc; không còn numerical writer.

## Kết quả dễ đọc

Vốn đầu mẫu 10.000 USD, planned risk 25 USD/lệnh, một vị thế. Mỗi ô là **phí
chuẩn / phí cao**, net equity gồm lãi/lỗ mở; cuối năm cả hai bản đều đã flat.
Các mốc 3/6/12 tháng lồng nhau, không phải ba mẫu độc lập. Hai hàng khác năm,
không dùng để xếp hạng trực tiếp hai chiến lược trên cùng thị trường/thời kỳ.

| Bài, phiên bản bất biến | 3 tháng | 6 tháng | 12 tháng | Quyết định theo protocol |
|---|---:|---:|---:|---|
| UTC range nguyên bản, năm 2024 | −169,17 / −188,08 | −219,97 / −251,00 | −98,53 / −155,85 USD | Không promote bản trong bài; chưa chứng minh edge bền |
| Compression6/24, năm 2023 | −44,70 / −62,38 | −284,20 / −325,58 | −129,36 / −224,62 USD | Tạm gác phiên bản hiện tại |

| Risk/lifecycle cuối năm | UTC2024 chuẩn / cao | Compression2023 chuẩn / cao |
|---|---:|---:|
| Lệnh đóng | 214 / 214 | 111 / 111 |
| Tick max drawdown | 272,86 / 300,53 USD | 329,76 / 387,28 USD |
| Vị thế/pending cuối năm | Không / Không | Không / Không |
| First breach của profile khai báo | Không / Không | Không / Không |
| Vòng đạt được | Vẫn vòng 1, chưa đạt target | Vẫn vòng 1, chưa đạt target |

`running` trong prop lifecycle là trạng thái **chưa đạt tại cutoff**, không có
nghĩa job máy tính vẫn chạy. Không breach không đồng nghĩa có lời hoặc pass.
Profile FTMO 2-Step Swing là snapshot khai báo áp dụng ngược cho lịch sử;
broker fees/permissions/inactivity/payout và toàn bộ firm exceptions chưa được
chứng minh. Lợi nhuận mô phỏng không phải tiền có thể rút.

P/L theo Bid/Ask trước hoa hồng/slippage/financing cũng âm: UTC −42,73/−56,49 USD,
Compression −86,39/−87,85 USD. Spread đã nằm trong giá Bid/Ask, không trừ hai lần.
Vì vậy không có bằng chứng quy thất bại chỉ cho mức phí qua đêm hoặc lỗi sizing.
Compression còn nhạy financing: 21,22/97,80 USD trong hai kịch bản. Các khoản
gross − commission − slippage − financing đối chiếu đúng annual net ở cả bốn ca.

## Đã chứng minh phần nào?

| Cửa | Kết quả trong scope | Giới hạn còn lại |
|---|---|---|
| G0: thiết kế trước outcome | Hai protocol/registration và recovery bất biến, pin data/source/profile/cost/risk/cutoff | Prior exposure không được xác nhận là sạch |
| G1: dữ liệu/code/timing | Raw/hash/cache guards; fixtures, bounded golden parity, independent entry/exit checks; Compression annual 1.504 H4 × 2 ca khớp mọi exit/non-exit, 198 exits | Oracle dựa verified H4 và retained positions, chưa độc lập dựng toàn bộ raw/fill engine |
| G2: tiền/chi phí/risk | 12 sealed horizon rows đọc lại khớp report; cash/Decimal decomposition, tick DD/min-equity/Prague entrydays/fee calendar đạt | Theo costs đã khai báo và quotes thực sự có; không khẳng định tick history/fees broker hoàn hảo |
| G3: edge | Không đạt tiêu chí nâng bước của hai bài; giữ nguyên negative trials | Không kết luận cả họ chiến lược vô dụng hoặc có thống kê chứng minh không bao giờ có edge |
| G4: prop-fit | Không first breach trong declared profile; chưa đạt phase1 ở mọi cutoff | Full firm applicability/payout chưa đạt; không suy xác suất pass từ vài run |
| G5–G6: forward/quyền thực thi | Không thêm broker strategy handoff, không cấp quyền từ report | UTC offline stream proof cũ vẫn có scope riêng; research mới không là lệnh giao dịch |

Bộ tám rules hiện tại chưa có bản đủ để nâng sang challenge trong các phép kiểm
đã có. Donchian/SMA/Pullback/Z-score/failed20/fade giữ các quyết định và kết quả
cũ; kết quả mới bổ sung thất bại của hai bản còn đáng kiểm, không xóa lịch sử.

## Hậu kiểm kỹ thuật và cải tiến đã áp dụng

- Calendar startup: UTC v1 lỗi trước first quote ngày nghỉ; Compression v1
  dừng an toàn trước thay shared source. Pristine flat account giờ ghi zero
  non-applicability rõ ràng; không bịa quote/cash hoặc nới guard phí vị thế.
  UTC2024 có đúng một exemption Jan1/2024 ở mỗi cost, reader đã kiểm.
- Dùng lại raw/quality/H4/tick caches, không export/download hoặc chạy lại
  discovery đã xong. Mid-scenario CLI resume vẫn chưa hỗ trợ; completed scenario
  seals có thể reuse đúng binding. Không gọi checkpoint riêng là resume đầy đủ.
- Kiểm sớm 3/6 tháng trong lúc chạy đã phát hiện được lỗi reader nếu có;
  không đợi toàn năm mới lần đầu thử postprocessing. Các kiểm sớm và cuối đều đạt.
- Source giữ nguyên đến khi **cả hai pipeline và report kết thúc**. Sau audit,
  Trader `8f924908` mới gộp parent/child tick ledger validation thành một pass,
  giữ đầy đủ V2 margin/money/provenance checks; không cache mutable prefix như trusted.
  Regression forged margin ở `f267eec8`. Hai file triển khai khớp byte prototype.
- Snapshot validation ABBA nhanh 1,62–1,79× ở các workload đã đo; full annual
  snapshots cũng giữ serialized hashes. Bốn bounded tick scenarios giữ exact
  checkpoint/decision/candidate parity. **Chưa đo full annual replay speedup của
  source mới**, không chạy lại cả năm chỉ để làm benchmark.
- Source thật sau promote: 224 pytest + 144 subtests đạt trong 19,03 giây;
  13 horizon-reader + 1 discovery-reporter tests đạt. Hai deprecation warnings
  test-client là maintenance ngoài phạm vi, không đổi dependency để tắt cảnh báo.
- Script theo dõi tạm từng không xử lý `% = null` khi job đã completed; đã sửa
  null handling. Native pipeline/report không lỗi hoặc chạy lại vì lỗi display đó.

Không cần skill, GUI, collector, Rust/GPU hoặc service mới cho lát này. Bài học
đã nằm ở runner/reader/regression và guide hiện có; các skills research,
qualification, debugging và retrospective vẫn đúng ownership.

## Bằng chứng và tiếp tục

Protocol/recovery: [UTC](UTC-VALIDATION-20261107-RECOVERY-V2.md),
[Compression](COMPRESSION-ROBUSTNESS-20261107-RECOVERY-V2.md).
Discovery: [kết quả bốn ứng viên](DISCOVERY-RESULTS-20261107.md), gồm nguồn mở
rộng AQR/BIS và giới hạn triển khai. Receipt giữ dispatch/failure/source history.

| Artifact private | Trạng thái / binding |
|---|---|
| `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/utc-validation-20261107/execution-v2/` | Pipeline completed khoảng13:28 VN; 1/1 verified, 6 rows; batch9.458,86 giây, CPU9.378,21875 giây |
| `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/compression-robustness-20261107/execution-v2/` | Completed13:12:20 VN; 1/1 verified, 6 rows; batch8.512,56 giây, CPU8.442,96875 giây |
| `horizon-report.json/.md`, `final-audit.json`, `horizon-metrics-audit.json` mỗi root | Final audit thực hiện trước thay numerical source; full reread/seals/cash/risk/source không drift tại thời điểm audit |
| UTC report SHA256 | `9e519fe89de8d1de6edd2b1bc130cd9f1a7305002ddb64d493be260710b35583` |
| Compression report SHA256 | `ba3536a58ab93bab43a44094e7940fe79ab5c18732cc13754a0333c1175eb337` |

Report gốc pin numerical source `e7b332dd` (test-only commit sau đó không đổi
numerical bytes), giữ source snapshots. Core hiện tại `8f924908` có scope kiểm
riêng nêu trên; đọc kết quả cũ không yêu cầu replay bằng source mới hoặc sửa pin.
Actual broker/runtime/API acceptance không được suy ra từ các kiểm research này.

**Thứ tự tiếp theo:** giữ các phiên bản không đạt; chỉ mở vòng discovery mới khi
có cơ chế/data/chi phí đủ khác để giải quyết bất định, không parameter grid nhằm
cứu kết quả. Hai hướng dài hạn/multi-currency còn cần data inventory và contracts;
không gọi chúng đã implemented. Chưa mở final holdout2025+, risk/TP grid hoặc
broker. Mục tiêu vẫn là lợi thế sau chi phí phù hợp vốn prop, không thử hết mọi
chiến lược hoặc buộc tìm winner trong một đợt.
