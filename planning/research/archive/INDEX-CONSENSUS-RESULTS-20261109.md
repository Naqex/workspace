# R078/R079: đồng thuận giảm số lệnh, chưa tạo lợi thế sau phí

[Protocol](INDEX-CONSENSUS-PROTOCOL-20261109.md) `bef54a8` và implementation
`113b068` trước group outcomes. Cả hai đã terminal và qua separate Fraction
review, **không đạt retention**. Goal C1/C2 vẫn active, chưa có ứng viên challenge.

Hai tín hiệu cùng hướng không có nghĩa xác suất thắng chắc chắn cao hơn. Ở đây
điều kiện đó giảm số giao dịch, nhưng không làm tổng tiền sau phí dương ở hai
năm đã đăng ký. Không thử ngược điều kiện hoặc đổi clock/fee sau kết quả.

## Kết quả đã kiểm

Một đơn vị giả định = 1 USD cho mỗi điểm chỉ số; chưa lot, tài khoản 10k hoặc
risk 0,25%. Không cộng USD/unit giữa hai tài sản thành portfolio. Delay 1 s là
primary; 2 s và 60 s giữ làm các kịch bản khác, không chọn bản đẹp sau outcome.

| Component / delay | 2019 phí chuẩn | 2019 phí cao | 2022 phí chuẩn | 2022 phí cao |
|---|---:|---:|---:|---:|
| US500 / **1 s primary** | −173,40 | −363,40 | −191,05 | −370,05 |
| US500 / 2 s | −181,30 | −371,30 | −224,39 | −403,40 |
| US500 / 60 s | −190,76* | −377,76* | −199,64 | −378,65 |
| NASDAQ / **1 s primary** | −418,10 | −611,10 | −587,42 | −774,42 |
| NASDAQ / 2 s | −441,64 | −634,64 | −744,61 | −931,61 |
| NASDAQ / 60 s | −395,19 | −588,19 | −685,13 | −872,13 |

US500 chọn 190 / 179 ngày trong 2019 / 2022; NASDAQ chọn 193 / 187. So với
parent: US500 247 / 250, NASDAQ 249 / 250 ngày. *US500 2019 / 60 s chỉ 187 / 190
resolved; giữ ba unknown, số trên là known-partial sum, không full annual net.
Primary 1 s và 2 s resolved mọi selected planned day. No-exposure không fake fill.

3.018 cashday-delay records, 2.247 planned và 2.244 resolved asset-day-delay cases;
22.440 role/cost cases lặp calendar, assets, delays và controls. First-half trên
consensus mask trùng primary theo định nghĩa, không là bằng chứng độc lập hoặc
benchmark phải vượt. Unfiltered parent net chỉ diagnostic: NASDAQ 2022 / 1 s
stress +140,46 → consensus −774,42 USD/unit, không chọn thêm filter để cứu.

## Correctness, reuse và thời gian

| Lát | Bằng chứng và quyết định |
|---|---|
| G0 / selection | Published conjunction đã ở queue; exact gate/control/cost/delay khóa trước group outcomes, years vẫn consumed development |
| Chọn tín hiệu | 5 focused tests: agree/disagree/flat/missing/unknown; future price/net không chọn cohort, scope/authority, input immutable, census và redundant-control gate |
| Synthetic reviewer | 24 rows / 120 cost-role cases qua Fraction; 4 mutations reject trước market run |
| Actual reviewer | 3.018 rows exact parent binding, Fraction signs/costs/sums/gates, 22.440 role/cost checks và 4 mutations reject |
| Nguồn | Reuse sealed corrected parent quotes/costs/source receipts; không đọc lại 16 triệu raw ticks hoặc gọi nguồn/model/broker |
| Producer | 2,563 s wall / 2,484 s CPU; prep 0,410 s; selection+summary US500 0,254 s, NASDAQ 0,241 s |
| Reviewer | 2,757 s wall / 2,703 s CPU; kiểm đủ current workload, không sampled-only |

Đây là thời gian cho hypothesis mới trên dữ liệu đã kiểm, không speedup của
whole-history intake hoặc cả chiến dịch. Không có bottleneck cần GPU/Rust/DB
mới ở lượt này. Không sửa source/cost helpers hoặc parent artifacts để reuse.
Khi rà test discovery đã bỏ imported TestCase alias gây chạy lại sáu parent
tests không cần thiết; final scope là năm tests mới. Mọi kiểm tra đều đạt.
Skills hiện có đủ cho conjunction/reuse; không cần thêm skill chỉ cho filter.

Giới hạn: arithmetic khác nhưng cùng agent, không independent human/model;
quotes archived không actual broker fills. Chưa SL/sizing/margin/account equity,
target fees, prop/time-fit, clean OOS/prospective hoặc owner handover.

## Evidence và bước tiếp

Private base `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
output `execution-v1/index-consensus-components-v1/` giữ config, manifest,
source snapshots, rows, summaries, result/review, progress/events và timings.
Saved scripts `run-index-consensus-v1.py`, `review-index-consensus-v1.py`;
`consensus-preflight-v1.json` giữ synthetic receipt và code bindings.

Result SHA `7435c556b1e5c1fcadadd5f177b7a6ba8dff5210b9bcf7c87929b0ccf001994a`;
reviewer SHA `51c6ca162e1119ae9d49cd945593e7b9b8e55abf4d5db7d76b1ce2714b5cc487`.
Review SHA `2f743ba5fcfe6c7a9d443e0df2cfa2349153b82592b5beb55b130f388077c60a`;
không còn numerical job.

Gác exact R078/R079 và các close-momentum recipes đã thử; không flip subgroup,
retune hoặc lấy stress tốt riêng năm để gọi winner. Tiếp [method admission
EU-open và đối chiếu oil mapping](EU-OPEN-AND-OIL-METHOD-20261109.md): cơ chế
uncertainty resolution khác close hedging, ưu tiên source đã có; chưa new net.
