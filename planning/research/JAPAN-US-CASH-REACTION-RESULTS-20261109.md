# R087: đầu phiên Nhật chưa cho lợi thế khai thác được sau phí

Đã chạy và đối soát **485 phiên / 20 sổ / 4.850 trường hợp dự kiến** theo
[protocol](JAPAN-US-CASH-REACTION-PROTOCOL-20261109.md) commit `f42a74f`, khóa
trước giá mới. **Không giữ R087 để kiểm challenge**: phần đã biết lỗ sau phí
ở cả hai năm; 2019 còn thiếu nhiều phút nguồn. Không đổi giờ, hướng hay mức
phí để cứu kết quả. Catalogue 87 hồ sơ / 58 account-policy versions.

## Tín hiệu hay chi phí làm kết quả yếu?

Đơn vị **JPY trên một đơn vị nghiên cứu** có giá trị 1 JPY/index point.
Chỉ cộng những phiên đủ dữ liệu theo protocol; không phải tiền lãi/lỗ trên
tài khoản, return theo vốn, hoặc PnL trọn năm.

| Khoản, cùng tập phiên đã biết | 2019 | 2022 |
|---|---:|---:|
| Phiên đủ dữ liệu để tính |174|232|
| Midpoint price PnL, trước phí |+781,824|−676,615|
| Spread đã nằm trong Bid/Ask |−1.170,026|−1.637,209|
| Trượt giá cơ sở |−348|−464|
| **Net cơ sở** |**−736,202**|**−2.777,824**|
| Trượt giá stress, thay khoản cơ sở |−1.044|−1.392|
| **Net stress** |**−1.432,202**|**−3.705,824**|
| Commission / funding khai báo |0 / 0|0 / 0|

- **2019:** midpoint dương nhưng chưa đủ trả spread; ngay cả bỏ extra
  slippage, observed Bid/Ask price PnL đã âm. Chưa là edge có thể giao dịch.
- **2022:** midpoint đã âm, nên phí thấp hơn đơn thuần không giải quyết
  tín hiệu yếu trên tập phiên này. Không coi commission0/funding0 là đủ rẻ.
- Stress primary tốt hơn always-BUY +449,757/+23,910 JPY trên common cohort,
  nhưng tốt hơn một đối chứng lỗ chưa đủ; primary net vẫn âm.

Midpoint chỉ là benchmark kế toán từ separate-side source prices, không giá
có thể khớp hoặc measured market impact. Slippage1/3 points mỗi chiều là
scenario, không phí FTMO/The5ers đã xác minh. Không trừ spread hai lần.

## Dữ liệu thiếu được giữ như thế nào?

| Năm | Lịch Nhật dự kiến | US signal còn mới ≤72h | Đủ strict source roles | Unknown | Coverage |
|---|---:|---:|---:|---:|---:|
|2019|241|236|174|62|73,73%|
|2022|244|236|232|4|98,31%|

13 phiên calendar-stale giữ row/lý do, không có entry; không dùng giá để chọn
những phiên này. Trong cohort đủ mới, 66 phiên unknown giữ nguyên mẫu số.
`full_eligible_net=null` ở cả hai năm; không biến known-subset sum thành
annual net. Toàn bộ nguồn không qua gate coverage95% ở 2019; 2022 qua
coverage nhưng known net âm. Chưa có positive evidence đủ để xử lý gap sâu.

**Quyết định đã ghi trước economics** tại private
`pre-economic-coverage-decision.json`: giữ strict roles, không fill, drop hoặc
đổi giờ/threshold nếu known subset dương. Rule cần đủ 29 source minutes gồm
holding/exit; không endpoint-only thay vào để làm đủ mẫu sau outcome.
Chưa bác bỏ mọi opening-reversal/cross-market hypothesis.

Bốn raw files rỗng đúng cấu trúc: Bid/Ask ngày 19/04/2019 và 15/04/2022.
Không suy thành TSE đóng cửa đã xác minh; lịch JPX cash khác lịch CFD vendor.
Phần lớn gap2019 là vài phút không được raw liệt kê, không thiếu file/quên
load quý. Không carried-close/volume0 padding để tự tạo quan sát nguồn.

## Đã kiểm gì?

| Lát | Bằng chứng và giới hạn |
|---|---|
| Lịch trước giá | Cabinet holiday CSV đã pin, JPX cash exclusions, đủ241/244 phiên; US calendars có early close/DST; tuổi signal≤72h. Đây là declared cash proxy, chưa mọi halt/CFD account |
| Tests |4 focused tests: UTC/JST/NY/DST/holidays/stale/holdout; Close khác Open, future exit không đổi signal; missing/internal/crossed/flat/null; summary scope.6 FOMC regressions đạt khi mở helper cho JPN identity |
| Nguồn Nhật |970 day-side exports:962 GET mới,8 pilot reused,0 transient errors. Kiểm full **5.432.990 OHLCV fields** bằng Decimal và Fraction raw delta khác; 28.130 role-side checks |
| Nguồn Mỹ |Reuse accepted full-quarter canonical proofs, không tải lại history.988 selected raw day-sides /4.940 field checks, kiểm cả loader không bỏ raw Close hợp lệ; known-at trước decision |
| Preflight riêng |4.850 synthetic financial cases;6 financial/state mutations + malformed-empty +raw price/time bị từ chối |
| Kết quả thật |4.322 resolved financial cases đối soát/4.850 planned;528 unknown cases=66 phiên×4 exposed rules×2 costs. Giữ cả calendar skips và null.5 actual mutations net/clock/unknown/authority/gate bị từ chối |
| Phạm vi review |Same agent, phương pháp số học khác; chưa independent feed/model/human. Không simultaneous ticks, SL/sizing/margin/equity/prop/time-fit/OOS/forward hoặc broker |

## Lỗi reviewer và phục hồi

Reviewer v1 dừng khi Fraction decoder cũ đọc baseprice `None` của nguồn rỗng.
Producer đã giữ nguồn rỗng là unknown đúng semantics; lỗi ở reviewer assumption,
không phải thay strategy/data. V1 source và failure giữ nguyên. Reviewer v2
chấp nhận **chỉ** packet có các cột rỗng đồng nhất/clock/grid đúng; malformed
empty-column mutation bị reject. Không điền giá, loại ngày hoặc refetch.
V2 source-review hash và reviewer hash nằm trong receipt trước economics;
old source-manifest vẫn giữ v1 pin/snapshot, không sửa pins lịch sử.

## Thời gian và hệ thống

| Phase | Wall | CPU |
|---|---:|---:|
|Fetch962 files mới +8 reuse|296,713s|13,329s|
|Chuẩn bị nguồn/pins/roles|20,400s|17,734s|
|Full source review v2 +synthetic|111,079s|101,078s|
|Economics20 books|1,771s|1,734s|
|Review kết quả +actual mutations|2,637s|2,594s|
|**Tổng successful worker phases**|**432,600s ≈7phút13s**|Không gồm research/authoring và failed reviewer v1|

Full raw validation là phần CPU lớn nhất; tải nguồn có network/pause đã khai
báo. Không A/B speedup so study khác và chưa profile từng hàm. Những artifacts
đã seal có thể reuse đúng bindings; không chạy lại4.850cases/raw chỉ để đổi
báo cáo. Existing skills đủ; chưa GPU/Rust/framework mới có lợi ích được đo.
Collector này chưa có CLIresume được kiểm uninterrupted-equivalence; perfile
seals hỗ trợ đối soát/tái sử dụng ở attempt mới, không tự chứng minh resume.
Đã sửa guard/progress runner cũ bằng10 transition tests trong
[R086 report](US500-FOMC-PRICE-MOMENTUM-RESULTS-20261109.md#guardprogress-đã-sửa-không-chạy-lại-market-history).

## Artifacts và bước tiếp

Private base `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/japan-us-cash-calendar-v1/`, `japan-us-cash-source-v1/` và
`japan-us-cash-component-v1/` giữ calendar, raw/native/seals, prepared rows,
source/financial manifests+snapshots+reviews, failures/progress/events.

- Source resultSHA `480ab5a68c0acd086b064bb1aa7e0a50be9ecc89f4e4a0e2b6943e10934bd9d6`.
- Source reviewSHA `2deaacbc9c8cda4a4a2ddc0a716a18700fbde872c2df8a181278ae1af4111ae4`.
- ResultSHA `9685390322180a70cb19bd1d1b0a8313261d23481a1395660c7a00dfde95111e`.
- ReviewSHA `401a1396ee96f7ab4a0052dd4f384359d306c32e2f2522ab2fda51bb355c7069`.

Gác exactR087; không tự đổi08:45, long/short, market, filter hoặc fees để cứu.
Nguồn Nhật và joint-clock giờ có evidence reusable; đó không tự là lý do
chạy mọi biến thể trên cùng source. Tiếp đánh giá **cơ chế có observable
primitive khác**, trước source/PnL mới; nếu parent survivor có material
technical gap thì xử lý đúng gap thay broad grid. Catalogue87/58, chưa ứng
viên challenge; Goalactive/C1C2 chưa đạt. Không còn job lượt này đang chạy.
