# R033: pilot sức mạnh tương đối ba đồng tiền

Đăng ký trước outcomes, thuộc [campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Không phải replication, account backtest hoặc quyền giao dịch.

## Quyết định phương pháp trước đo

Đọc [BIS366, §2–4.1 và §4.2](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies.pdf)
ngày 08/11/2026: paper phân biệt momentum theo từng series với xếp hạng các
đồng tiền; có cả xếp hạng spot changes và excess returns gồm forward/interest.
Paper dùng tối đa 48 currencies; nghiên cứu size xét tối thiểu 6. Nó không
chứng minh rổ **EUR/GBP/AUD** hoặc spot-CFD của project có lợi thế. Không nhập
code/data paper, không lấy annual return của paper làm target của project.

**Primary duy nhất:** R033-MOM1-3FX-v1, mua đồng tăng mạnh nhất và bán đồng yếu
nhất trong tháng trước, giữ một tháng. Cơ chế khác unconditional fixed-hour
flow đã thử. Đây là pilot nhỏ để xác định price/funding economics và data
contract trước khi đầu tư vào universe rộng hơn. Ba currencies quá hẹp để
đại diện toàn FX; kết quả âm chỉ gác exact adaptation, không reject cả R033.
Opposite-ranking control có cùng costs chỉ là falsification, không thành
candidate nếu primary thất bại. Không grid lookback/hours/universe sau số.

## Source admission và causal panel

- Reuse EURUSD monthly `records.json`/source-review tại
  `multiasset-monthly-input-v1`, và GBPUSD/AUDUSD source H1 books/review tại
  `fx-h1-history-v3`. Không tải thêm hoặc sửa dữ liệu cũ. Pin mọi input và
  source receipts trước compute. Raw history vẫn giữ tại owner cũ.
- Tạo panel mới 3 instruments × 144 months 2013–2024 × 2 roles = 864 rows.
  Reuse clock của EURUSD records: last NYSE session close cho signal, first
  NYSE session 10:00 New York cho rebalance. Đây là clock adaptation của
  project, không FX official month-end fixing hoặc calendar của paper.
- EURUSD giữ nguyên quote/known-at/role. GBP/AUD `signal_close` lấy Close của
  source H1 kết thúc tại cutoff (`timestamp=cutoff−1h`), known-at=cutoff.
  Rebalance lấy Open của H1 bắt đầu tại target, known-at upper bound=target+1h.
  Giá Open chỉ interval proxy; **không actual joint quote hoặc causal fill**.
- Chỉ quan sát Bid/Ask nguồn, dương/đúng grid, Ask≥Bid cho field dùng. Không
  đo midpoint extrema từ Bid/Ask highs/lows. Thiếu/crossed giữ explicit unknown.
  AUD Ask Jan2013 thiếu và các source gaps lịch sử không tự biến mất.
- Months đánh giá **2014–2024**: prior November/December2013 đủ để có một
  completed-month return vào January2014. Các năm này historical consumed,
  clean OOS=false. Không 2025+; chọn window vì coverage, trước outcome.
- Tại entry month t, xếp hạng `mid_close[t−1]/mid_close[t−2]−1`, chỉ khi tất
  cả known-at < entry target. Không dùng giá entry hoặc exit tính ranking.
  Highest=BUY, lowest=SELL. Nếu max hoặc min không unique, cả tháng flat do
  causal tie, không lexicographic rescue. Input thiếu không phải tie/flat.

## Economics của component

Một book primary và một opposite control, mỗi book có reference/stress.
Mỗi tháng 5.000USD long notional + 5.000USD short notional **cố định**, không
compound, lot rounding, SL, margin hoặc account equity path. Units mỗi leg =
5.000 / entry mid; lots=units/100.000. Đây là continuous allocation proxy,
không đề xuất risk/lot cho owner. Không nhân risk budget theo số symbols.

BUY vào Ask, ra Bid; SELL vào Bid, ra Ask. Full close/reopen mỗi tháng dù
symbol không đổi, phí/slippage hai side, BidAsk embedded. Commission2,50USD/
lot/side; reference slip0, stress0,00002/side. Funding **debit cả hai hướng**:
reference10USD/lot/ngày, stress20USD/lot/ngày, mỗi weekday22UTC, Wednesday×3,
events `(entry_target, exit_target]`. Đây là declared uniform scenarios, **chưa
historical/current FTMO/The5ers swap**, không copy swap EURUSD cho GBP/AUD.
Không tự bỏ funding do USD-neutral; không hạ phí sau outcome.

Final December2024 giữ hai exposures mở, mark bằng `signal_close` tháng12;
chỉ entry fee/slippage + funding đến mark, không exit fee/slippage hoặc forced
close. Tách cash/floating/closed tháng và open-mark. Native cost function dùng
rounding2digits; financing cộng unrounded events rồi round2. Không gọi tổng
USD qua các tháng là cash rút hoặc probability pass.

Mọi 132 tháng giữ trong census. Missing signal/entry làm bài inconclusive;
missing future exit giữ entry eligibility nhưng unresolved, không lọc entry
trước bằng future availability hoặc ghi 0. Pilot không tiếp tục account state
sau missing close; chỉ có independent monthly contributions, không account PnL.

## Retention, kiểm chứng và hành động sau

Metrics: primary/control/reference/stress net USD, gross/fees/slippage/funding,
annual cohort contributions, concentration/top positive months, per-symbol
exposures, resolved/missing/tie counts, final cash/floating và open legs.
Không tính intraday drawdown, prop pass hoặc calibrated confidence từ panel.

Chỉ ưu tiên mở rộng universe nếu primary cả reference/stress net>0, stress
ít nhất **8/11 năm dương**, cả blocks2014–16 / 2017–19 / 2020–24 dương, và
132months đều resolved hoặc causal-flat với terminal mark hợp lệ. Đây là
heuristic research priority, không statistical certificate. Không đổi gate
sau outcome. Failure không chứng minh cả cross-section family vô dụng.

Runner `run-fx-cross-section-pilot-v1.py`, reviewer
`check-fx-cross-section-pilot-v1.py` tại campaign root. Output mới
`execution-v1/fx-cross-section-pilot-v1`, source-snapshot và pinned config/
manifest trước số, 1writer, deadline180s/CANCEL/PID/progress/events/failure.
Preflight: rank direction, ties, known-at, missing entry/future exit, flatprice
cost, funding boundaries/triple, finalmark noexitcost. Numeric reuse native
roundtrip cost; không thêm generic engine hoặc source download.

Reviewer riêng dùng Fraction, calendar và rounding riêng; kiểm source panel
với parent receipts/sealed books, toàn rankings/132months×4views/trades/
funding/summary/retention. Mutations: source price, future signal, rank/side,
financing, missing row, false tick/OOS/challenge claims. Không numeric oracle
reuse runner/native cost implementation. Cùng agent/provider không independent
human/model audit. Giữ failures và chỉ sửa reviewer nếu lỗi ở review, không
rerun số để làm đẹp. Hậu kiểm gọn và cập nhật catalogue/context sau batch.

Survivor vẫn cần universe đủ rộng, selection-aware OOS, target costs, stops/
lot/account-wide risk, causal execution/ticks, prop/time-fit, forward và owner
handover. Chưa có challenge candidate; Goal active, không broker authority.
