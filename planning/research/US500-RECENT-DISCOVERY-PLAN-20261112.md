# Mở rộng setup US500, ưu tiên gần hiện tại

Owner12/11/2026 yêu cầu research nhiều setup, thử gần/xa, tự chấm/kiểm và đề
xuất; **cho phép offline2025 và2026 tới hiện tại**. Đây là override mới cho
study này, không sửa các protocol/negative/authorization lịch sử. Không broker,
account/provider mới, trả phí, live risk hoặc mua challenge. Không tự tạo Goal.

## Luồng hữu hạn và đầu ra

Research+lineage → freeze8setups rõ → cadence/quality → tối đa4economic screens
trên development → recent2025 → khóa shortlist tối đa2 trước outcome2026 →
2026YTD và historical stress chọn lọc → bảng evidence/score/recommendations.
Không mặc định phải tìm winner; fail/inconclusive giữ nguyên.

2022–24 là development đã exposed.2013–21 là historical robustness phụ và
data-limited; ưu tiên2016/2020/2021 làm economic stress khi có cơ sở, không
đòi mọi setup thắng mọi năm.2025 là recent comparison/selection nên sau khi
xem không gọi finalholdout.2026 chỉ evaluation sau shortlist freeze; nếu
history/exposure không chứng minh pristine thì ghiunverified, không tự gọi
cleanOOS. Không tuning trên2026 rồi coi kết quả cùng window là validation mới.

Ngay trước chạy numeric mỗi stage phải có exact rule/exit/risk/cost/selection
protocol và source checkpoint. Study mới không được tự dispatch từ bản PLAN
này. Mọi variant/failure/scopechange phải giữ và đếm vào history.

## Nguồn gần: phạm vi chủ nhân vừa mở

Tái dùng dukascopy-node1.51.1/private research, USA500.IDX-USD/usa500idxusd,
pairedM1 Bid/Ask, nguồn public hiện có, không tài khoản/secret. Download finite:
2025-01-01 inclusive → **2026-11-12T00:00:00Z exclusive**, đủ các phiên NY đã
đóng tới11/11/2026; không future dates hoặc mặc định2026full-year.

Source-only ingestion/quality có thể chạy trước shortlist nhưng không tính
setup/PnL2026 hoặc in giá ra context trước freeze. Native response cache giữ,
source-explicit timestamps và toàn retained OHLC/volume phải được đối chiếu
decoder riêng, không dùng native carried-close padding làm observation.
Các source proofs/calendar/cutoff cần bind trước numerical reader.

Default helper vẫn đóng2025+; chỉ named window
`us500-recent-discovery-20261112` đúng instrument/from/to mới cho offlinefetch.
Không dùng cờunlimited/skipguard, không thay các rawBI5/legacy strategy gates.
Smoke2ngày trước bulk; dừng403/429/WAF/schema hoặc budget/deadline, không bypass.
Giữ partial/unavailable nguồn, không chuyển thành market-no-setup hoặc0PnL.

NYSE cash09:30–16:00NY/DST; lịch2025 phải thêm09/01nationalmourning bên cạnh
holiday/early closes;2026truncate tới11/11. Đây vẫn là proxycash clock, chưa
targetFTMO contract. Nguồn chính thức:
[2025–27holiday announcement](https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx),
[09/01closure](https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx),
[2026calendar](https://www.nyse.com/trade/hours-calendars).

## Chấm điểm phải tách hai trục

Readiness: rule rõ/timing/quality/accounting/cost/trace/ops gaps. Economics:
net sau costs, coststress, drawdown đúngscope, tradecount/dependence/cadence,
độ tập trung lợi nhuận và kết quả recent2025/2026. Không cộng điểm để PnL đẹp
bù lỗi dữ liệu hoặc để nhiều lệnh bù expectancy âm. Unmeasured luônN/A,
không dùng0 hoặc điểm cao bịa. Chưa có intraminute-equity/news/targetfills thì
prop-fit chưa verified dù aggregate score tốt.

Reports dùng bảng đơn giản: setup hoạt động thế nào → evidence near/far/recent
→ vì sao giữ/gác → điểm có căn cứ/unknown → bước tiếp nhỏ nhất. Logs/status/
phase timing/checkpoint/private source artifacts giữ ở campaign, index/context
chỉ route. Không cần framework/skill mới để làm vòng này.
