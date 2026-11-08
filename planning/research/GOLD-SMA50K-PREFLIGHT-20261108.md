# Gold SMA50k — kiểm nguồn, sổ tiền và time-fit trước tick qualification

## Câu hỏi và baseline đã xem

Tiếp campaign C1/C2 từ `CURRENT-CONTEXT.md`, không tạo strategy mới. Giữ exact
`xauusd-h4-sma20-80-atr14-r025-v1`, SMA20/80, SL2ATR14, exit mất direction,
nominal50k/risk0,25% (125USD), hai declared costs của Discovery9. Đã xem
[outcomes](METAL-DISCOVERY9-10-RESULTS-20261108.md); survivor được chọn sau xem
outcome. Review này không là preregistration của một bài kiểm định edge mới.

Baseline là15annualbooks riêng2010–2024/scenario. Input QDM BidM1
`d209df9a5ce871f1992eb312595ebef2c19a884c1fe0a1be6bfb76d86cf471b9`,
protocol Discovery9
`ec8cfe824b78391b259c303f21adca65c549e871d99aab51ed996411c1587b9c`.
Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1`;
baseline `metal-discovery9-screen/attempt-v1`, export ở
`metal-discovery9-preparation/export/XAUUSD_TW-M1-No Session.csv`.

## Review khóa trước diagnostics mới

1. Kiểm hash input/protocol/source-snapshot, binding manifest→result→30book
   files; liệt kê source khác currentD:Trader7ab57907, không sửa pins lịch sử.
   Reviewer độc lập dùng stdlib/Decimal, không gọi simulator/financial helper.
2. Từng trade: tính lại gross từ side/entry/exit/quantity/100oz; commission
   2×2,50×lot, slippage2×0,10/0,20×100×lot; round cents half-up ở net theo
   declared model. Kiểm financing20/40×lot×weekday multiplier, event unique,
   event clock22UTC; position ID/entry/exit intervals và tổng debits.
3. Đối soát cash=50k+sum(price-net)-financing, equity-net=cash+floating-50k,
   trade-net=price-net-trade-financing; entries=closed+open; no/minlot skips.
   Floating chỉ đối soát ledger, chưa có independent mark quote proof.
4. Diagnostic đã exposed: annualnet, trades/win/loss, funding, concentration
   top5 positive trade contributions và net bỏ5best (không trading variant),
   annual bands. Không fit distribution hoặc gọi sample independent/OOS.
5. Time-fit: dùng Jan1 account thật của từng annualbook, prefixes3/6/12calendar
   months (Apr1/Jul1/Jan1next), không cắt rolling windows thành fresh accounts.
   Reconstruct cash credits tại exit interval end, debits tại declared22UTC;
   khoảng close cắt boundary phải ghi unresolved, không gán exact exit tick.
   Báo prefix realizedcash, closed count và open positions ở boundary. Cash
   không là equity/DD; không ghép năm, compounding hoặc ước tính pass-duration
   bằng target/meanreturn. Prefixes cùng annualbook chồng nhau.
6. Kiểm highest flat cash credit checkpoints trong mỗi annualbook như
   diagnostic. Không suy no-breach/pass từ cash: thiếu intrabar equity, native
   prop/reset clock, pending state và phase2. Target10%/5% chỉ là references,
   không chạy phase2 hay tự forceclose vị thế để đạt target.
7. Raw source/clock: chỉ đọc export đã consumed2009.11–2024; kiểm schema,
   order, OHLC/grid, row count/gaps, first/last và per-year observedH1 coverage/
   partialH1 counts. Không coi thiếu quote là thị trường đóng; không tự padding.
   Không dùng public one-day match để chứng nhận toàn history/targetbroker.

Nếu financial/source invariants fail: giữ attempt và failure; quarantine đúng
evidence bị ảnh hưởng, sửa reviewer hoặc producer theo rootcause rồi kiểm lại
phần affected. Test negative bằng mutations commission/funding/count/input
binding trong memory, không sửa baseline. Không đổi strategy/risk/cost để cứu.

## Target contract và quyết định

Public [FTMO2-Step](https://ftmo.com/en/2-step-challenge/) kiểm08/11:10%/5%,
daily5%/overall10%,4tradingdays, unlimited. [Profit Target](https://academy.ftmo.com/lesson/profit-target/)
yêu cầu closed profit và tất cả positions đã đóng. Với50k:5.000/2.500USD;
không lấy floating cuối năm làm đạt target. Đây không là terms account-specific.

Current target XAU geometry/Ask/spread/swap/commission execution/feed clock
chưa đủ chứng cứ. Generic symbols page không tự chứng minh row XAUUSD của
account. Review terms hiện hành khi có primary-source capability; ghi unknown
thay vì coi model declared là FTMOverified.

Verdict tối đa: research survivor còn đáng tick-review hay chưa đủ time-fit;
không chứng nhận edge/challenge-ready. Không đặt ngưỡng triage mới hồi tố.
Nếu lợi nhuận yếu/tập trung hoặc thiếu source/spec/path, ghi limitation và
chọn lát giải quyết bất định hữu hạn; không rerun annual simulation không đổi.

## Thực thi và quyền

Attempt mới `gold-sma50k-evidence-review-v1`; manifest pins protocol/reviewer/
baseline, progress phase/counter, deadline300s, CANCEL và failure/result.
Hash/read/financial/clock/diagnostic timers riêng, không cộng với researchtime
hoặc benchmark cũ. Artifacts private; results/nextdecision lưu research owner.

Không network data download/model/broker/simulator calls; web chỉ public terms.
Không mở2025+, OrderCheck/OrderSend, account/provider/mua challenge/production.
Không sửa dirtyC:worktree hoặc baseline; không publish skill/native UI.
