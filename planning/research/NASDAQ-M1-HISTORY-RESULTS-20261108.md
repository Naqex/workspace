# NASDAQ M1: dữ liệu đã đủ cho phép sàng lọc đăng ký

Đã hoàn tất [protocol](NASDAQ-M1-HISTORY-PROTOCOL-20261108.md) qua
[recovery v2](NASDAQ-M1-HISTORY-RECOVERY-20261108.md). Đây là kiểm dữ liệu,
chưa chứng minh chiến lược có lợi thế hoặc đủ điều kiện challenge.

## Kết quả đã đối soát

| Phần | Kết quả |
|---|---:|
| Raw day/side responses | 1.704/1.704, trong đó252 response trống hợp lệ |
| Book đã niêm phong | 8/8 |
| Nến M1 riêng từng phía | 1.596.126 |
| Đối chiếu giá/volume với raw, canonical và Fraction decoder | 7.980.630 trường khớp |
| Nến do native decoder tự chèn đã loại khỏi source-only view | 442.602 |
| Timestamp chỉ có một phía / crossed Open hoặc Close | 0 / 0 |
| Mutation bị chặn | 5: giá, thiếu row, giờ tương lai, hash sai, quyền giả |

Raw trống không là missing transport hoặc nến giá0. Không có explicit volume0
trong lần này; loader vẫn giữ khi source có. Mọi ngày calendar/raw response
đều được tính, không loại ngày xấu khỏi denominator. Raw/private artifacts
giữ nguyên; normalization là output mới có hash/lineage/version.

| Vai trò | Phiên cash dự kiến | Đủ cả phiên và giá sau close+1phút | Lookback14TR và giá sau close đủ |
|---|---:|---:|---:|
| Warmup2019, Nov–Dec2018 | 40 | 40 | 26 |
| Development2019 | 252 | 250 | 208 |
| Warmup2022, Nov–Dec2021 | 43 | 42 | 16 |
| Development2022 | 251 | 247 | 177 |

Cả4roles đạt gate đã đăng ký: mỗi dev>=200completecashdays, warmup>=20,
và dev có rolling readiness. Full paired source admission cũng đạt trong
scope được kiểm. Gaps ngoài cash vẫn tồn tại, tối đa khoảng3ngày; không suy
ra continuous ticks/giờ targetbroker hoặc mọi gap là maintenance đã xác minh.
Session calendar vẫn là declared NYSEcash proxy, không ETF/CFD equivalence.

## Thời gian và bài học kỹ thuật

| Lát | Đã đo |
|---|---:|
| V1 dừng vì output tuple/JSON contract | 23,303s, 0book; giữ failure |
| V2 thu/chuẩn hóa/niêm phong8books | 719,816s wall;18,078s CPU |
| Review toàn nguồn/chất lượng | 91,228s wall;90,766s CPU |
| Reuse61rawdays đã tải ở lần lỗi | Hash khớp; không refetch |

Source IO/chờ mạng chiếm phần lớn lần chuẩn bị mới, không có bằng chứng GPU
sẽ giải quyết nút này. Raw cache và sealed books đã dùng lại được; không tải
lại hoặc chạy nguyên batch chỉ để benchmark. Fixture output shape trước fetch
và16source helper tests chặn lại lỗi tuple/object; không thêm skill vì workflow
debugging/source transformations hiện có đã đủ. Component có10tests riêng;
source review pass không thay kiểm economics/prop/OOS.

Private `execution-v1/nasdaq-m1-history-v2` dưới existing campaignroot giữ
result/review/config/manifest/raw-source-bindings/quality/cash-session-quality/
source snapshots. ResultSHA
`3058b26de169c11ff0fbb841ec11d74df1c81b1035de4cad4d1aad901a0006e7`.
Review receiptSHA
`8b0bced9723138d52242552a66ed74c33f5a43d8d3013288b515d2db7c4b9703`.
Reviewer sourceSHA
`2a2e01bda41bd464faf073496016c91a220b7afbe4e76f54c7ea130c6edf0482`;
đây là hash code, không receiptSHA. Producer PID27988 terminal0, reviewer
terminal0;0broker/modelcalls, không2025+holdout. Trader không đổi.

**Tiếp:** [cash RSI component](NASDAQ-CASH-RSI-COMPONENT-PROTOCOL-20261108.md)
đã đăng ký trước outcomes và source admission đạt. Chỉ kiểm một recipe
after-cost trước SL/sizing/prop/cleanOOS; không gọi sourcepass là hoàn tất Goal.
