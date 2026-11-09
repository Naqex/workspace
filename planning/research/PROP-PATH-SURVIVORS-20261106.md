# Hai ứng viên còn lại — đo tick risk và lifecycle trước đổi risk/exit

Owner giao06/11: hoàn thiện phép đo, kiểm độc lập exit, kiểm ngắn đầy đủ rồi chạy
Z-score và UTC range. Đây là lượt mới sau [annual review](TIME-FIT-RESULTS-20261106.md),
không sửa hoặc giả resume execution-v2. Nguồn dữ liệu2023đã consumed; không clean
OOS, không đo edge mới từ cùng một sample, không mở2024/2025+.

## Contract đã chọn trước lượt annual mới

| Phần | Cấu hình |
|---|---|
| Candidate | `eurusd-h4-z20-2-atr14-time6-r025-v1`; `eurusd-h4-utc-range00-08-atr14-r025-v1` |
| Tín hiệu/SL/exit | Giữ bản gốc; chỉ H4 đóng, next quote, initialSL2ATR14; không TP mới |
| Vốn/risk |10.000USD initial; fixed25USD dự kiến/lệnh,1position; internal100USD/ngày,500USDoverall giữ nguyên |
| Warmup |01/11–31/12/2022, hash và path cũ |
| Evaluation |01/01–31/12/2023; cutoff exclusive01/04,01/07,01/01/2024 |
| Phí | Giữ commission2,50USD/lot/side; reference slip0, finance buy9,3/sell−0,31; stress slip0,00002/side, buy/sell20 |
| Calendar phí |22UTC weekday, Wed×3; declared scenario, không gọi phí broker lịch sử |
| Phạm vi | Offline numerical, không model/broker, mua challenge, provider mới hoặc holdout |
| Concurrency/ceiling |2worker;6giờ/worker,8giờ/batch; preparation20phút riêng; không auto retry. Hard ceilings khác ETA |

Full numerical source, runtime, inputs/spec/protocol/profile và registration JSON
được pin sau các kiểm ngắn, trước dispatch. Thay numerical source làm mất quyền
reuse outcome cũ; cache reader/source binding phải hợp lệ, không thay expected
hash để ép dùng cache. Giữ registration/run cũ nguyên vẹn.

## Profile khai báo và nguồn

Kiểm lại trang chính thức [FTMO Trading Objectives](https://ftmo.com/en/trading-objectives/)
ngày06/11/2026, đúng **2-Step** (không lấy3%daily/trailing/consistency của1-Step
hoặcInstant): target10%/5%, daily5% theo balance00:00CE(S)T, staticoverall10%
theo initial, equity gồm floating/swaps/commission;4ngày có mở vị thế mỗi vòng,
flat để đạt target. Nguồn mô tả equity **below**floor làvi phạm; comparator`lt`,
target`gte` theo ví dụ balance11.000USD khiinitial10.000USD. Ngưỡng nguyên vẹn
khác phanh nội bộ bảo thủ`<=`. Không gọi profile này là contract account đã mua.

Order reset_then_fees khi fee giả lập trùng nửa đêm là **assumption đã khai báo**,
không khẳng định broker post fee như vậy. Quotes/candlesUTC, resetEurope/Prague
theoDST. Đây là áp profile hiện khai báo lên dữ liệu2023, không tái dựng terms
hay fees lịch sử. Snapshot/nguồn trước ở [terms](PROP-TERMS-SNAPSHOT-20261106.md).
Không dùng funded/reward/inactivity/news/forbidden-practices chưa triển khai để
tự kết luận full FTMO compliance hoặc payout eligibility.

## Phép đo và hành vi

- Quote trước/sau fill, cả entry+SL trong một tick, đều cập nhật peak→trough DD,
  minimum equity, đệm daily/overall và observed underwater span. Không log mỗi tick.
- Native evaluator sở hữu target/reset/qualifying day/first breach/flat pass.
  Adapter cache threshold từ money oracle và chỉ gọi native ở milestone; không
  parseMarkdown hoặc gọi LLM trong replay loop.
- Reset dùng balance đã biết trước quote mới; cash event dùng valuation quote
  cuối, ghi rõ stale basis, không tạo giá nửa đêm. Không bù cash hậu kiểm cho
  prop snapshot thiếu phí vì nó có thể làm sai risk path.
- Nếu đạt vòng khi flat/pending0, tại H1 boundary kế tiếp **trước end**: archive
  fullaccount và accounting cũ, native next_phase/start, execution/risk account
  mới10k, positions/pending0. Indicator history giữ causal, position-age/day latch
  của account cũ reset; fee calendar chỉ tiếp
  từ cursor cũ. Không replay lại hoặc trừ target để giả phase2.
- Sau breach/final pass không nhận entry mới. Phanh nội bộ xử lý pending close
  ở quote hợp lệ tiếp theo; không giả close ở end. Native eval chốt tại terminal;
  tick count/DD account có thể tiếp tục ghi phần đóng còn lại.
- Horizon/report tách active phase balance với phase archives, không cộng lợi
  nhuận challenge thành vốn/payout. Status`running` của simulation được trình
  bày là **chưa đạt tại cutoff**, không giả numerical process còn đang chạy.

## Acceptance trước dispatch

1. Regression tick-risk/finance/horizon/registration và native prop contract.
2. Exit oracle độc lập: Z-score prior20/reversion/six actual closes, cảBUY/SELL;
   UTC20:00/next valid/missing bar/cross day; SL ưu tiên queued strategy exit.
3. Synthetic path: intrabar recovery, first-breach latch/equality, Prague/DST,
   same-instant fees, pending/flat/minimum entry days, actual account reset và
   phase2; invalid quote window không commit observer.
4. Consumed Jan1–Jan3/2023prefix: hai candidate×hai costs, observeron/off giữ
   exact execution checkpoint/decisions/candidate state, seals/reader có prop
   packet; đo overhead riêng, không claim annual speedup từ mẫu này.
5. Controller cancel/owner-crash/reuse checks tại existing owner; không khởi
   động writer trùng. Chỉ dispatch sau preparation/source/profile/registration
   binding đúng; output mới, không auto retry.

## Quyết định sau outcome

Primary: coverage/correctness, first breach, lifecycle status/phase/qualifying
days tại3/6/12tháng; sau đó tick DD/headroom và active-phase cash/equity. Gặp
material correctness failure thì dừng affected evidence; thiếu nguồn/coverage
ghi unknown, không sửa profile/parameters để pass.

Ngay cả `completed_pass` chỉ là **đạt declared numerical profile** trong sample
đã consumed; không là edge, calibrated pass probability, full firm compliance
hoặc authority. Nếu vẫnphase1/notreached thì giữ trạng thái đó, không tăng lot.
Risk12,50/25USD và TP2Roverlay vẫn là các thí nghiệm riêng sau review, chưa chạy
từ registration này. Receipt AI hiện có giữ actual status, commands, evidence và
private output locators; tài liệu này giữ scope, không là tracker thứ hai.
