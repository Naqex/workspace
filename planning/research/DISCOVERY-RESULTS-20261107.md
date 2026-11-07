# Discovery 3: kết quả và quyết định 07/11/2026

Đã hoàn tất bốn ứng viên × hai kịch bản phí trên Q1/2022, dữ liệu development
đã dùng. Giữ Compression để kiểm dài hơn, UTC range tiếp tục bài validation đã
đăng ký riêng. Hai bản còn lại không được nâng bước trong phép kiểm này.
**Chưa có chiến lược được xác nhận có edge hoặc đủ để thi quỹ.**

Protocol bất biến: [Discovery 3](DISCOVERY-ROUND3-20261107.md).
Vốn mô phỏng 10.000 USD; planned risk 25 USD/lệnh, một vị thế. Net equity gồm
lãi/lỗ vị thế còn mở, không ép đóng cuối mẫu.

| Phiên bản | Phí chuẩn | Phí cao | Lệnh đóng | Cuối mẫu | Quyết định |
|---|---:|---:|---:|---|---|
| Failed20: quét biên 20 nến rồi quay lại | −7,70 USD | −22,46 USD | 25 | Không vị thế | Tạm gác phiên bản này |
| Compression6/24: phá vùng giá vừa co hẹp | +50,38 USD | +28,47 USD | 27 | Một vị thế; floating −2,88/−3,00 USD | Kiểm độ bền dài hơn, chưa kết luận edge |
| UTC range-fade: quét rồi quay vào vùng đầu ngày | −71,78 USD | −76,84 USD | 28 | Không vị thế | Tạm gác phiên bản này |
| UTC range-breakout: đối chứng cũ | +34,13 USD | +26,67 USD | 49 | Không vị thế | Tiếp tục validation đã khóa |

Hai mức phí dùng cùng thị trường/tín hiệu nền; không phải hai mẫu độc lập.
Số lệnh trong bảng là đóng thực tế của mô phỏng, khác hypothetical opportunities
của probe. Drawdown của đợt discovery chỉ đo từ ledger; chưa full tick prop-fit.
Kết quả âm không loại cả họ ý tưởng, kết quả dương không tự cho phép chạy broker.

## Bằng chứng và thời gian

Root riêng: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/discovery-round3-20261107/execution-v1/`.
Native pipeline chạy 10:22:38–10:35:46 giờ Việt Nam; 4/4 completed_verified,
8/8 rows đã kiểm. Thời gian batch 786,39 giây, tổng CPU worker 2.439,14 giây.
Shared preparation 142,812 giây; preflight 2,02–2,22 giây mỗi ứng viên.

| Kiểm tra | Bằng chứng | Giới hạn |
|---|---|---|
| Giữ hành vi cũ | Bốn ca Z-score/UTC × phí trên 232.578 tick: checkpoint/decision/candidate khớp từng byte | Bounded consumed prefix, không chứng nhận mọi dữ liệu |
| Tín hiệu/lot mới | Sáu ca first-entry được tính độc lập từ 225.926 raw tick và warmup cache có hash | Chưa full raw warmup hoặc mọi exit/fill |
| Thoát lệnh mới | Công thức độc lập kiểm 372 H4 × 6 ca, 134 tín hiệu thoát khớp; có cả quyết định không thoát | Dựa cache có hash và vị thế từ ledger; chưa dựng lại toàn bộ raw hoặc mô phỏng fill độc lập |
| Dữ liệu probe | Aggregator riêng dựng 12 H4 hoàn chỉnh từ raw; cả tám rule khớp cached probes | Flat state, không phải portfolio hoặc PnL |
| Tiền/chi phí | Tám row được tính lại trade cost, cash và equity bằng Decimal | Theo cost assumptions đã khai báo, không khẳng định phí broker lịch sử |
| Native controller | Seals/source/protocol/input binding, completed/cancel/reuse regressions | Không thay G3 edge/G4 đầy đủ/G5 broker forward |

`discovery-report.json` SHA256:
`6e988a55bc8f1975995d8bbee41be768ce84c5abb01e52120f6d318bcbe434c4`.
Các proof ở `bounded-parity.json`, `first-entry-oracle.json`,
`probe-raw-parity.json`, `financial-audit.json`, `exit-rule-oracle.json` cùng root.

## Hậu kiểm hệ thống và bước tiếp

| Lát | Đánh giá | Quyết định |
|---|---|---|
| Danh mục | Đã có 8 rule; Donchian/SMA/Pullback vẫn chung họ trend | Đủ cho đợt mở rộng đầu, không coi số tên là số edge độc lập |
| Screen nhanh | Load/hash tám bản 0,900 giây, probe 0,063 giây; cả tám có cơ hội/lot khả thi | Giữ làm feasibility triage; đợt này không giảm số tick jobs. Không so <1s với mô phỏng lợi nhuận |
| Correctness | Gặp holiday fee trước first quote khi chạy UTC2024 | Đã sửa có opt-in, regression và immutable recovery; không bịa quote hoặc nới phí vị thế |
| Reuse | Raw/quality/H4/tick caches còn hợp lệ; chưa có scenario hoàn tất của hai lượt lỗi/dừng | Dùng lại cache, giữ attempts cũ; không gọi checkpoint chưa đủ là resume |
| Performance | Đợt bốn worker hoàn tất trong 13 phút 6 giây | Chưa có profile chứng minh cần Rust/GPU/dependency mới; giữ core hiện có |
| Edge/prop | Một quý không đủ; chưa clean OOS hoặc full firm eligibility/payout | Kiểm hai rule bất biến qua năm dài hơn trước risk/TP tuning |

Hai bài tiếp theo: [UTC2024](UTC-VALIDATION-20261107.md) và
[Compression2023](COMPRESSION-ROBUSTNESS-20261107.md). UTC v1 lỗi trước first
quote; Compression v1 dừng có kiểm soát trước sửa shared source. Các registration
gốc và partial artifacts giữ nguyên. Recovery protocols:
[UTC v2](UTC-VALIDATION-20261107-RECOVERY-V2.md),
[Compression v2](COMPRESSION-ROBUSTNESS-20261107-RECOVERY-V2.md).

Khi xong, đọc cả 3/6/12 tháng cùng account/phase/cost, phân rã thời kỳ và chi phí,
đối soát source/seals/cash/risk trước quyết định. Không cộng horizons lồng nhau
hoặc profits sau reset thành payout. Không tự thêm parameter/risk/TP variants
để cứu outcome. 2023/2024 là historical robustness, không clean OOS; 2025+ đóng.
Actual trạng thái/outcomes của hai bài được ghi tại receipt AI và report native.
