# NYFX: kịch bản khoảng trống đã đối soát, không giữ exact recipe

[Protocol](NY-FX-GAP-SCENARIOS-PROTOCOL-20261109.md) được commit `67933d0`,
implementation `209de7e` trước outcomes. Đây là hai mô hình có điều kiện cho
những phút archive không có quote, **không khôi phục giá thị trường bị thiếu**.
[Strict annual result](NY-FX-PAIRED-LATENCY-RESULTS-20261109.md) vẫn N/A và
`unknown_exposure`; parent H1 negatives cũng giữ nguyên.

## Kết quả và quyết định

Vốn mô phỏng 10.000 USD reset mỗi năm, planned risk 25 USD/lệnh. Hai mô hình
`observed_events` và `adverse_envelope` cho cùng các số dưới đây. Không có
adverse-envelope exit trong actual runs vì envelope ở các gap đang giữ vị
thế không chạm SL. Điều đó không chứng minh mọi hidden path hoặc broker fill.

| Reversal | Phí chuẩn (USD) | Phí cao (USD) | Lệnh đóng mỗi cost |
|---|---:|---:|---:|
| 2019, lag 15 phút — primary | −823,78 | −1.094,70 | 499 |
| 2019, lag 60 phút | −1.025,94 | −1.297,16 | 469 |
| 2022, lag 15 phút — primary | −275,54 | −413,86 | 486 |
| 2022, lag 60 phút | −200,59 | −335,47 | 454 |

64 books: 32 nonnull kết thúc `conditional_flat`, 32 null không trade/PnL.
14.520 closed paths có lặp giữa costs/scenarios, không là số trade độc lập.
Primary không đạt frozen gate net > 0 trong cả hai stress years/scenarios.
**Gác exact NYMA4 recipe theo sensitivity evidence**, không tune MA/SL/risk/
cost/clock hoặc promote momentum control để cứu primary. Không bác bỏ cả họ
mean reversion hoặc kết luận original strict annual PnL đã biết.

Adverse model không là global lower bound: exit sớm có thể đổi re-entry,
cash và margin. H1 future envelope chỉ dùng cho stress, không vào signal/
sizing. Conditional cash không chứng minh equity/daily drawdown được đo.
Không có OOS/prop/forward/owner-handover hoặc challenge qualification mới.

## Correctness, lineage và hậu kiểm kỹ thuật

| Lát | Bằng chứng | Quyết định |
|---|---|---|
| Giữ strict behavior | Một actual 2019 reversal lag15 reference book khớp toàn object với frozen original; 5 latency regressions đạt | Giữ default strict; không sửa hash/pin cũ theo code mới |
| Gap semantics | 6 tests mới, 32 synthetic producer/Fraction cases: BUY/SELL, phí, next-quote gap SL, không fake mark/fill/cash, gap chưa đăng ký/crossed/intent/exit vẫn unknown | Giữ hai model tách rõ; actual run chưa có adverse exit nên nhánh này dựa trên synthetic oracle |
| Financial review | Separate Fraction dựng H1/TR/signals/sizing/gap/cash/cost/census cho đủ 64 books; 64 strict-prefix checks; 6 mutations entry/quantity/net/count/authority/conditional scope bị từ chối | Đã kiểm trong scope; cùng agent/provider, không independent human/model signoff |
| Source/reuse | Rebind raw/tick/H1 seals, kiểm absent cả hai side/no ticks; common M1 OHLC và H1 observed extrema; không download lại | Reuse nguồn đã review, không rewrite raw hoặc clear strict unknown |
| Reliability | Preflight v1 lỗi tìm filename vì Windows separator, giữ failure; sửa bằng pathlib.name trước conditional outcomes | Không numerical failure mới; không rerun books đã review |
| Performance | Producer 93,415 s wall / 92,719 s CPU; reviewer 115,232 s / 114,906 s CPU; strict preflight 4,544 s | Workload đã hữu hạn và đủ nhanh; chưa có lý do GPU/Rust/framework hoặc profiling tiếp |

Tests mới 0,294 s và regressions 0,179 s; không cộng các phase này thành tổng
thời gian từ ý tưởng đến kết luận vì research/code time chưa đo. Không gọi
model đổi semantics là speedup so với strict study.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
output `execution-v1/ny-fx-gap-scenarios-v1/` giữ config/manifest/snapshots,
admissions, books, progress/events/result/review. Producer/reviewer terminal 0.

- Result SHA256: `86db3587d8574c36cfebc438e045d7cc73f313a1d026586137d1a006ed0625cc`.
- Review receipt SHA256: `fb57d24bf7ea3b17a1df27a0cb93c3e01edadbd24ecd5b9e461202d5867bf4a1`.
- Reviewer code SHA256: `b53b14af519d8273af36dee237028db44ae586b20a48fc60d1dea35184ea7a25`.

Catalogue thêm 4 model revisions vào R070–R073: 73 records / 58 versions /
25 native / 9 controls. Hai gap scenarios không đếm thành 8 chiến lược mới.
Strict snapshots cũ vẫn là owner cho strict pins; code live đã đổi version.

**Tiếp:** khảo sát một cơ chế khác có primary-source rationale, tận dụng
NASDAQ M1/calendar đã review; freeze component/cost/control/gate trước
outcomes. Chưa có đăng ký hay kết quả của hypothesis mới trong tài liệu này.
Goal C1/C2 vẫn active; không broker calls hoặc holdout mới.
