# R026: giữ để kiểm tiếp, chưa là chiến lược challenge

Thực hiện [recipe đã khóa](R026-RELATIVE-EQUITY-COMPONENT-20261108.md),
commit53fe30b trước numeric; source signal/test ở b421fe3. Câu hỏi mới dùng
chênh lệch cổ phiếu EUR/US để chọn BUY/SELL EURUSD trước giờ cuối tháng;
không đổi những bot FX cũ. Đây là price-proxy component, chưa SL/sizing/bot.

## Kết quả dễ hiểu

Đơn vị **tổng pip của các cơ hội theo bộ rule**, không phải%lãi tài khoản.
USDperstandardlot chỉ là đơn vị tính, không đề nghị giao dịch1lot.

| Năm | Cơ hội đủ/đã đăng ký | Phí chuẩn | Phí cao | Thắng/thua khi phí cao |
|---|---:|---:|---:|---:|
|2019|12/12|+21,6pip|+16,8pip|6/6|
|2022|10/12|+144,1pip|+140,1pip|7/3|

**Qua heuristic triage đã đăng ký:** mỗi năm≥10tháng resolved, tổng phí cao
dương cả hai năm. Chỉ là ưu tiên kiểm tiếp, không proof statistical edge,
prop-fit hoặc permission. Không tự mở2025+, mua challenge hay gửi broker.

2019 khá mong manh: thêm1,4pip chi phí/cơ hội đủ làm tổng stress về0. Đây là
phép chia từ outcome đã có, không strategy/cost tuning mới. Năm2019 primary
chỉ hơn baseline alwaysSELL1,6pip sau phí cao; chưa đủ nói tín hiệu tương đối
tốt hơn drift cố định. Năm2022 primary+140,1 so alwaysBUY+63,9/alwaysSELL−88,9.
Tháng tốt nhất đóng góp25,7%/40,8% tổng positive gains theo năm;22cơ hội không
cho phép suy xác suất pass hoặc hiệu quả độc lập từ4views×2costs.

Tháng05/2022 thiếu EZU/SPY ở endpoint áp chót27/05; tháng07thiếu hai ETF ở
endpoint đầu01/07. Raw cả hai side dừng19:58UTC trong khi quy tắc cần19:59.
Giữ hai tháng `unresolved_source_endpoint`, không carry/nắn giờ/thay ngày,
không tính0 hoặc xóa khỏi mẫu. Chưa xác minh vì sao source thiếu phút đó;
không tự gọi là NYSE earlyclose hoặc lỗi source toàn bộ. Nguy cơ missingness
ảnh hưởng tổng năm vẫn còn; triage10/12 không xóa uncertainty này.

## Đã kiểm đúng những gì?

| Lát | Evidence | Chưa chứng minh |
|---|---|---|
| Nguồn/data |72day fixtures,336instrument-side exports, raw+native price/volume/clock/grid/seals/producer pins; rõ padding/units/adjustment/role |Không independent feed, toàn kho data hoặc broker executable tick |
| Causal signal | First/penultimate NYSE close, EUR conversion đúng endpoint; London DST và delay15:00→15:01;5focused tests |Không exact10-market panel của paper, adjustment/corporate-action series chưa chứng thực |
| Financials |Separate Fraction/raw-delta implementation:352source endpoint prices,176event-cost calculations,24month census và16summaries khớp |Không SL/lot/account equity hoặc intrabar stop-first-crossing |
| Mutations |6trường hợp reject:phí,hướng,giá nguồn,futureknown-at,thiếu tháng,falsequalification |Không independent human/model audit hoặc exhaustive correctness proof |
| Selection |Primary/control/criteria trước outcome; giữ22resolved+2unresolved, costs/scenarios không independenttrials |2019/2022 đã exposed; chưa cleanOOS, statistical edge, prospective forward |
| Prop/owner |C1false,C2partial, promotionfalse; next review rõ |Chưa timefit3/6/12months,native prop-equity path,target account costs,owner demonstrated handover |

Protocol dùng **lastNYSE session proxy** có chủ đích; không gọi nó là verified
historical WMR calendar hoặc khớp benchmark. Adaptation này không cần mua
WMR data chỉ để giao dịch theo lịch riêng; khi qualification phải giữ đúng
claim, kiểm calendar/availability đã biết trước và target execution contract.
Không tự dựng một gate mua dữ liệu chỉ để replicate benchmark không dùng.

Source admission đã đọc giá. “Chưa tính PnL” không nghĩa unseen; toàn bộ
khung2019/2022 giữ development/exposed. ETF price/adjustment unknown là giới
hạn cần kiểm, không tự kết luận series có lookahead hoặc buộc total returns
khi paper nói Total Market. Không thay proxy sau outcome để giữ winner.

## Thời gian, lỗi và hậu kiểm

| Phase thực đo | Wall | Nhận xét |
|---|---:|---|
| Thu source336parts |353,596s|28rawcache hits từ pilot,308URL mới;0helper transientretryevents |
| Admission72fixtures |10,562s|Hash/schema/giá/volume/source kiểm toàn exported fixture; không tạo source DB khác |
| Numeric + final bindings/output |3,724s|Tạo24monthrows,4views×2costs; bao gồm đọc raw endpoints, không chỉ CPUalgebra |
| Producer tổng |14,302s;CPU12,906s|Bao gồm admission; không cộng lại14,302+10,562+3,724 |
| Fraction/raw reviewer +6mutations |0,669s|Read/bind và separate codepath; không simulator rerun |

Download+producer+review≈368,567s, khoảng6phút09giây; không gồm nghiên cứu,
viết/reviewcode, pilot hoặc human/agentwalltime. Không claim speedup so batch
53phút có workload khác. Bottleneck lượt này là networkwait; chưa có lý do
GPU/Rustkernel hoặc parallel source fetch khi provider behavior chưa được đo
thêm. Giữ cache reuse/seals, không bỏ validation để giảm vài giây.

Lỗi chuẩn bị đầu tiên: Windows pathseparator không khớp raw-binding key,
0networkcalls/0outcomes; giữ `relative-equity-data-v1/failure.json`. Chuẩn hóa
bằng resolvedPath cho lookup, tạo v2 mới; reuse28pilotraw đúng hash, không
sửa pilot. Data/compute/review đã terminal; không còn worker của đợt này.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/relative-equity-data-v2`:plan/source snapshots,72fixtures,
  native/raw/seals,events/progress/result; giữ v1 prep failure.
- `execution-v1/relative-equity-component-v1`:manifest/source snapshots,
  input-admission,events/result/progress,independent-code-path-review.
- ResultSHA `6b800784eb7e9e409d3a8bd03c0bb117f411185b02cca1ae0889f7e5f211ee3e`;
  reviewSHA `e247012f709bf50a61f3fd702d45681dfe014bfd1b6382016f17173ad1328ab0`.
- Scripts `prepare-relative-equity-data-v1.py`, `download-relative-equity-data-v1.cjs`,
  `run-relative-equity-component-v1.py`, `check-relative-equity-component-v1.py`;
  pins/snapshots giữ versions thực thi; separate codepath cùng agent.

**Bước tiếp:** giữ recipe nguyên vẹn, kiểm thêm2020/2021/2023/2024 trước viết
risk-wrapper. Đồng thời audit missing/calendar/adjustment và chi phí target
trong đúng phạm vi; không thêm parameters hoặc suy thời gian challenge từ
pips chưa có SL/lotsize. Giữ hai năm hiện tại làm baseline exposed, không
rerun. Nếu longer evidence không giữ được economics thì chuyển hypothesis.
Goal mới còn active, C1/C2 chưa đạt; catalogue ghi component, không tăng số
policy/edges bằng views/costs/fixtures.
