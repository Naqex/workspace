# S&P 500 đầu phiên: exact transfer không đạt, nguồn cũ tái dùng được

[Protocol](US500-OVERNIGHT-REVERSAL-PROTOCOL-20261109.md) `2f87501` khóa trước
outcomes; shared component `206bd06`, source-reader recovery `226b3a8`. R075
là transfer cùng family sau khi R074 NASDAQ thất bại, không independent
discovery hoặc paper replication. Đã terminal và full Fraction review.

## Kết quả và quyết định

Một hypothetical unit worth 1 USD/price unit; **không tài khoản 10.000 USD**,
không lot/risk 0,25%. Overnight gap ngược chiều, fills 09:32→09:59 New York,
spread quan sát và declared commission 0/slip 0,25 hoặc 0,75 mỗi side.

| Năm | Planned / resolved | Primary chuẩn (USD/unit) | Primary stress | Long control stress | Short control stress |
|---|---:|---:|---:|---:|---:|
| 2019 | 248 / 248 | −273,82 | −521,82 | −393,31 | −533,72 |
| 2022 | 250 / 250 | −520,05 | −770,05 | −580,63 | −382,92 |

503 cashdays đều có row; 499 regular days có predictor hợp lệ, một gap bằng 0
không trade và 4 halfdays skip theo calendar. 498 planned đều có cả endpoints.
3 holding windows năm 2019 thiếu M1 bên trong, giữ census và không xóa trade;
endpoint component không chứng minh SL/equity/prop path. Opposite-gap stress
−405,21 / −193,50 USD/unit cũng âm, không được promote từ control.

**Gác exact R075.** Không tune side/clock/threshold/fees hoặc thêm wrapper cho
recipe không qua frozen net/control gate. Kết luận về CFD adaptation và costs
đã khai báo; không bác bỏ mọi opening reversal hoặc nghiên cứu ETF/futures.
G3–G6/prop/time-fit/OOS/prospective/handover chưa được chứng minh; chưa có ứng
viên challenge. Năm 2019/2022 là consumed development, không clean holdout.

## Source recovery và kiểm chứng

Source admission v1 bị chặn trước PnL vì validator hiện tại khác phiên bản đã
tạo proof cũ. Đó là version mismatch thật, không lý do bỏ guard hoặc kết luận
giá cũ sai. Giữ failure tại `us500-overnight-source-admission-v1/`.

`verify_source_proof(..., frozen_source=True)` mới cho phép bind đúng bytes
code/protocol trong **chính source view's snapshot**, còn raw inputs/calendar/
canonical output vẫn được hash trực tiếp. Flag phải là bool; mặc định vẫn
strict/current. Missing/corrupt/ambiguous snapshot, forged validator hoặc redirect
data bị reject. Không thực thi code snapshot và không sửa hash/pin/proof cũ.
Trạng thái chỉ là frozen-producer-proof reuse, không current producer validation.

V2 admission đã rebind đủ 4 source years 2018/2019/2021/2022: 2.525.288 side
records theo original sealed census. 2018/2021 chỉ cung cấp đúng previous
cashsession endpoint, không PnL mới. Raw/source prices không rewrite/download.

- 6 frozen-source tests và 6 source-view regressions đạt; 3 US500 profile tests,
  7 NASDAQ regressions, 1 sub-cent money regression và 6 FOMC helper tests đạt.
  Khác profile không được dùng nhầm source/market identity hoặc candidate.
- Dùng chung component cho hai consumer; old NASDAQ entry point còn tương thích.
  Actual 503 rows **toàn field** và summary khớp frozen R074 trong 5,284 s.
  Kiểm revision có lý do, không chạy lại để nghiên cứu cùng hypothesis cũ.
- 12 synthetic Fraction cases trước US500 outcomes; full review 503 rows,
  1.992 endpoint price fields, 3.984 cost-role cases / 59.760 cost+metadata
  fields, signals/previous expected session/rounding/control/census/gate.
  7 mutations signal/time/quote/cost/net/missingday/authority bị từ chối.
- Producer pin 2.623 source/input paths, kiểm lại cuối lượt. Reviewer khác
  arithmetic/path nhưng cùng agent/provider, không human/model signoff độc lập.
  Không target broker costs/fills/ticks, account/SL/prop/forward proof.

## Hậu kiểm và số đo

| Phase | Wall | CPU | Quyết định |
|---|---:|---:|---|
| Source admission v2, 4 năm | 33,480 s | 4,766 s | Chi phí chủ yếu hash/I/O, không tải lại hoặc rebuild nguồn |
| Chuẩn bị hai năm cho numeric | 3,580 s | Chưa đo riêng | Đọc quarterly source một lần rồi giữ cash minutes cần dùng |
| Compute hai năm | 0,136 s | 0,125 s | Chưa đáng GPU/Rust/parallelization |
| Producer toàn lượt | 12,299 s | 12,172 s | Bao gồm prep/compute/pins/output, không cộng lại hai dòng trên |
| Full reviewer | 7,818 s | 7,766 s | Giữ riêng số học Fraction và kiểm source bindings |

Không cộng research/code/rework chưa đo thành total campaign time. Không claim
speedup so NASDAQ vì input/provenance workload khác. Reliability fix có giá trị
lâu dài: code nâng phiên bản không buộc regenerate historical data hoặc sửa pins.
Hậu kiểm thêm phát hiện case metadata giả mạo: input đã mất không được match
với hash null. Đã sửa fail-closed và thêm regression; 4 actual source admissions
vẫn exact với receipt trước trong 5,045 s, không numeric rerun. Old numerical
pins bind snapshots; `source-reader-hardening-review-v1.json` và snapshot riêng
ghi bản guard mới, không sửa manifest lịch sử. Original data không có null
hash nên không có bằng chứng financial outcomes bị ảnh hưởng.

Không có evidence cần cleanup raw, thêm database, skill, GPU hoặc framework.
Nguồn/cost/default metadata giữ tách biệt; chưa đổi Trader/runtime/global config.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/us500-overnight-source-admission-v1/` giữ failure,
`us500-overnight-source-admission-v2/` giữ source receipt, và
`us500-overnight-reversal-component-v1/` giữ pins/config/snapshots/rows/summary/
result/review/progress/events/timing. V2 source, producer, reviewer terminal 0.

- Source-admission result SHA: `d5a2c23310729dab1a456cc66aa0d16e5cce5e65fbc014aa8caac5e5d3b12190`.
- Numerical result SHA: `a940b49c3c1f25e9a119efabd629d0c769b4a0dee54ac27456d06006f9c1b2eb`.
- Review receipt SHA: `8a4284ac56cd871074d8d4b426a8402f737cc19dd1adaf058979314dea76ba0a`.
- Reviewer code SHA: `83cf25892dc1c5984ae26c06e915bc763c60a0d768384ae4700aed6b6e09df14`.

Catalogue 75 records / 58 policy-model versions / 25 native / 9 controls;
R075 là component, chưa account policy. Goal C1/C2 active. Bước tiếp là
[rest-of-day hedging-pressure method admission](INDEX-REST-OF-DAY-METHOD-20261109.md),
predictor khác opening gap/first-half, không đảo outcome hoặc cứu R075.
