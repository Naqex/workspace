# Commission0: hai bản intraday vẫn chưa đủ điều kiện đi tiếp

**Publicspec follow-up08/11:** [renderedrows/clock](FTMO-SYMBOL-AND-CLOCK-ADMISSION-20261108.md)
xác nhận publicUS500.cashcontract1/Swing15/commission0 và swappoints;
chưa xác minh targetaccount/point/lotgrid/historicalclock, không đổi oldstudies.

**Đã có kết quả thay thế cho phần source:** decoder tự chèn carried-close
bars vào phút thiếu. [Correction/results hiện hành](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md)
đã tạo explicit views2022–24 và chạy/kiểm lại đúng sáu sách, giữ rules/risk/cost;
cả hai vẫn không đạt triage. Bảng dưới giữ historical expanded-view và
cost-parity, không ghi đè. Source-only M1 mới vẫn chưa chứng minh tickfills.

Theo [protocol đăng ký trước outcome](FTMO-INDEX-COMMISSION-REVIEW-20261108.md),
đã chạy R048 noise14 và R051 first→last30min trên canonical unfiltered2022–24.
Chỉ commission thay từ declared0,5USD/lot/chiều sang0 theo công bố hiện hành
của [FTMO](https://ftmo.com/en/blog/zero-commissions-on-indices/). Đây là
counterfactual target-cost scenario, không lịch sử FTMO được xác nhận từng năm.
Source implementation `75f7ecf`, giữ strategy rules, 10k/planned25USD/lệnh,
observed Bid/Ask spread và slippage0,25/0,75 mỗi chiều.

| Policy | Năm | Net reference USD | Net stress USD | Entries mỗi scenario |
|---|---:|---:|---:|---:|
| Noise14 | 2022 | 251,67 | 181,19 | 156 |
| Noise14 | 2023 | −61,74 | −158,16 | 153 |
| Noise14 | 2024 | −72,35 | −156,91 | 147 |
| First→last30 | 2022 | −301,27 | −562,28 | 235 |
| First→last30 | 2023 | −380,64 | −751,67 | 218 |
| First→last30 | 2024 | −239,11 | −619,79 | 234 |

**Cả hai không đạt tiêu chí mọi năm dương ở cả hai costs đã đăng ký.** Noise14
tổng ba annualbooks reference+117,58/stress−133,88USD, tập trung vào2022;
first→last30 tổng−921,02/−1.933,74USD. Các năm reset riêng, không CAGR hoặc
continuous account/prop-DD. Không thay threshold/risk/stop hoặc bỏ năm để cứu.

## Correctness và giới hạn

- Cost profile được truyền xuyên CLI→manifest→sizing→simulation→reviewer;
  marker/mức commission khác manifest hoặc profile không biết bị chặn. Default
  legacy0,5 và old-model version vẫn giữ, artifact cũ vẫn đọc theo legacy.
- Không hoàn phí vào PnL cũ: ở reference mới, **1.041 giao dịch có quantity
  khác** reference cũ. Các fixtures BUY/SELL tính tay xác nhận q3,84→4,54 và
  net12,67→19,52USD cho path đã biết; spread/slippage/funding vẫn tồn tại.
- Actual6books,12numeric scenarios+6null đều có financial/source/raw bindings
  review; null0, không open/pending cuối. Không trade nào đi qua ngày UTC;
  first→last30 funding0 trong actual cases, không dùng điều đó đặt swap0 chung.
- Newstress (slippage0,75/chiều+commission0) có cùng total per-lot round-trip
  charge1,5 với oldreference (slippage0,25+commission0,5 mỗi chiều). Đã so thật
  **1.143 trades và10.279 decisions**: signal/time/quantity/fills/SL/net/cash/
  position/pending/rejections/gaps exact, trừ cost-breakdown/version khác chủ ý.
  Comparison0,21s, không rerun simulation; không là native tick parity.
- Reviewer mới đọc lại actual legacy noise2022/reference/stress/null: bindings
  và numbers đúng, không tái mô phỏng hoặc sửa snapshot cũ.
- 48 focused tests đạt ở cost implementation, gồm8new cost tests và các
  causal/default/mark/funding regressions. Không fullproduct hoặc independent
  human/model sign-off; dữ liệu/cost/selection/tick-path limits vẫn giữ.

Command đã chạy từ workspace: `projects/trader/foundation_v2/.venv/Scripts/python.exe
-X utf8 -m unittest discover -s tooling/ai-engines/tests -p 'test_*index*.py' -v`.
Sau carryfix chỉ chạy lại suite bị đổi với `-p test_review_index_noise.py -v`;
không lặp toàn bộ test hoặc numerical batch không bị ảnh hưởng.

## Lỗ hổng carry phát hiện sau batch

Unfunded intraday reviewer trước đây nhận trade thoát ngày sau dù không đánh
giá funding. Negative fixture đã tái hiện FAIL (ValueError không được ném).
Source `879344a` thêm `carry_requires_funded_review`;10 reviewer tests đạt.
Các lệnh carry phải qua funded path và calendar funding review, không lấy
closed-trade net thiếu phí làm accepted evidence. Actual batch này không có
cross-day trades nên không có numeric outcome bị đổi. Batch snapshots/reviews
vẫn giữ source trước guard; không tự nâng thành đã chạy reviewer mới toàn bộ.

## Time, artifacts và kết luận

Toàn batch6books gồm simulation và arithmetic review **86,05s**; không tải
dữ liệu mới, broker/model calls hoặc2025+ holdout. Controller23752/launcher8012
đã kết thúc và lock release. Private root `execution-v1/ftmo-index-commission0-v1`
giữ manifest/config/source/protocol snapshots, children logs/PROGRESS,18scenario
files,6reviews, `equal-total-cost-parity-v1.json`, legacy-compat review và
carry-guard regression receipt. Vẫn giữ old declared-fee attempts riêng.

Commission đã có nguồn công bố chính thức; target geometry/lot/margin,
actual spread/slippage/swaps/dividends, missing-path/native prop và OOS/forward
vẫn chưa được xác nhận đầy đủ. Không sửa nhãn `broker_spec_verified=False`.
Không thêm strategy version chỉ vì cost scenario đổi; catalogue vẫn53records/
41policy versions. Giữ negative outcomes và chuyển research sang cơ chế khác
có lý do; không promote hai bản này hoặc mở grid phí/SL. **C1/C2 chưa hoàn tất.**
