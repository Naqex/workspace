# Rest-of-day: tín hiệu tốt hơn first-half nhưng chưa qua phí/gate

[Protocol](INDEX-REST-OF-DAY-PROTOCOL-20261109.md) `fb7ec16` và implementation
`d1503ce` trước outcomes. R076/R077 là related momentum components trên hai
CFD proxies, không futures-paper replication hoặc independent discoveries.
Đã terminal và full Fraction review; Goal C1/C2 chưa đạt.

## Kết quả và phạm vi

Một hypothetical unit =1 USD/price unit, không lot, vốn tài khoản hoặc risk
0,25%. Không cộng USD/unit của S&P và NASDAQ thành portfolio return.

| Component / năm | Planned / resolved | Primary chuẩn | Primary stress | Primary−first-half stress |
|---|---:|---:|---:|---:|
| US500 2019 | 247 / 246 | −158,96 | −404,96 | +20,81 |
| US500 2022 | 250 / 250 | −121,12 | −371,12 | +419,39 |
| NASDAQ 2019 | 249 / 249 | −287,99 | −536,99 | +38,56 |
| NASDAQ 2022 | 250 / 250 | +232,20 | −17,80 | +2.088,82 |

Các cột tiền là USD/unit của **known endpoint sums**. US500 23/12/2019 thiếu
entry M1Open 15:31, exit có quote: giữ unresolved, không PnL0/next-quote fill.
Vì vậy US5002019 không là full-year net đã biết, cũng không là upper/lower
bound của ngày thiếu. US5002022 vẫn âm và đủ làm frozen two-year gate fail;
không cần archive chase ngày thiếu để quyết định ưu tiên recipe này.

1.006 cashday rows =503 dates×2 assets, không 1.006 ngày độc lập. 996 planned /
995 resolved asset-days, 9.950 cost-role cases có lặp costs/controls, không
9.950 trades độc lập. US5002019 có 2 regular days thiếu predictor, 15 holding
windows thiếu M1 bên trong; các nhóm khác không internal gaps ở resolved
windows. Không suy endpoint PnL thành SL/equity/prop path. Một first-half control
phẳng giữ costs=None/no exposure/net0, không fake fill để đủ denominator.

**Decision:** gác exact R076/R077 theo frozen retention. rROD tốt hơn first-half
ở cả bốn paired stress comparisons, nhưng primary không dương cả hai năm sau
phí. Không hạ phí, flip side hoặc tune threshold/clock/asset/window để cứu.
Điều này không bác bỏ cả family, hoặc chứng minh latency/model approximation
không thể tạo false negatives. Chưa account policy, clean OOS/prop/forward proof.

## Chi phí đang ảnh hưởng thế nào?

Diagnostic chỉ đọc sau outcome, không new strategy/gate. `gross_quote` đã tính
Bid/Ask spread nhưng chưa explicit slippage; dùng raw precision, không làm
tròn trước từng phép trừ như account money. Commission/funding=0 theo declared
scenario, không historical target-broker proof. Per-case net có cents rounding.

| Asset / năm | Gross sau embedded spread, chưa slip | Slip stress | Net stress sau làm tròn |
|---|---:|---:|---:|
| US5002019, phần known | −36,153 | 369,00 | −404,96 |
| US5002022 | +3,846 | 375,00 | −371,12 |
| NASDAQ2019 | −163,692 | 373,50 | −536,99 |
| NASDAQ2022 | +356,654 | 375,00 | −17,80 |

Không chỉ do tăng slip: NASDAQ2019 và phần known US5002019 đã âm trước explicit
slip. NASDAQ2022 nhạy chi phí, chưa đủ chọn riêng năm đẹp hoặc sửa fee. Số
diagnostic không là executable zero-cost/midpoint strategy, causal error bound
hoặc pass chance. `cost-decomposition-v1.json` giữ exact values/rounding residuals,
0,152 s, không numerical rerun hay thay verdict.

## C2, reuse và hậu kiểm

| Lát | Bằng chứng | Quyết định |
|---|---|---|
| Logic/timing | 8 new tests: late-vs-firsthalf signs đối nghịch, common mask, flat control, gaps, DST, future mutation, geometry/census/authority; 11 opening/sub-cent regressions | Tách tín hiệu khỏi shared price/cost/calendar/summary primitives |
| Giữ hành vi cũ | Actual R074+R075: 1.006 rows toàn fields và summaries exact, 9,689 s | Compatibility check có lý do, không rerun research cũ hoặc repin old artifacts |
| Separate arithmetic | 28 synthetic cases/2 profiles trước new outcomes; full Fraction review của signals/endpoints/costs/controls/census/gate | 3.982 endpoint price fields, 149.230 cost/metadata fields; 18 actual mutations reject |
| Source | Reuse sealed source views/proof receipts; 2.641 source/input pins kiểm trước/sau; frozen historical code snapshots khi live code khác | Raw/calendar/output trực tiếp; không source fetch/rewrite/migration |
| Reliability | Một stdin preflight launcher SyntaxError trước import; giữ failure, sửa thành saved script v2 rồi đủ28cases đạt trước numeric | Không economic failure mới hoặc resimulate đã chạy |
| Performance | Prep 7,966 s; compute 0,312 s wall /0,313 CPU; toàn producer19,237 s/CPU19,172; full reviewer14,132 s/CPU14,141 | CPU loop nhỏ, chưa cần GPU/Rust/parallelization; không bỏ hash/review để nhanh |

Same agent/provider, implementation/arithmetic khác nhưng không independent
human/model signoff. Không gamma observation, account sizing/SL/margin, target
broker costs/fills/ticks, prop daily/overall equity, OOS/prospective/handover.
Không cộng research/code time chưa đo vào wall batch hoặc suy speedup từ workload
khác. Skills hiện có đủ; correctness/reuse đã sửa ở code, không thêm framework.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`,
output `execution-v1/index-restofday-components-v1/` giữ config/pins/snapshots/
per-asset-year rows/summary/result/review/events/progress/timings/cost diagnostic.
Preflight failure/script/parity receipt ở private root. Producer và reviewer
terminal0, không job còn phải đợi.

- Result SHA: `b7addd0471e29d69d73162244c4715a441dd3b4025b4f7b73c2e3f7e7e292b15`.
- Review receipt SHA: `afa19d8dcf3276f96591832c35243ee389fae29c6e046bbba3cfb02852f66d10`.
- Reviewer source SHA: `ca5d7dd3b9f0789f7e49fc58839229887e7287d8be08945c3b4dcc3e2deb8588`.

Catalogue77 records /58 policy-model versions /25 native /9 controls;
R076/R077 là components, chưa account policies. **Tiếp:**
[bounded tick timing/source calibration](INDEX-CLOSING-TICK-CALIBRATION-PROTOCOL-20261109.md)
trước mở thêm filters hoặc nhiều price recipes. M1Open kế tiếp là delay proxy,
không delay thực đã đo. Pilot không PnL, không tự biến recipe fail thành pass.
