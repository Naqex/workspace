# Time-fit study registration — 3/6/12 tháng

**Registration:** `eurusd-h4-ftmo-time-fit-3-6-12m-v1`
**Registered:** 2026-11-05 21:49 UTC / 2026-11-06 Asia/Saigon
**Status:** `design_registered`; exact execution binding nằm trong addendum bên dưới.

[Execution 2023](TIME-FIT-EXECUTION-20261106.md) khóa ngày/cost/risk;
[registration JSON](TIME-FIT-HISTORICAL-20261106.json) khóa source và input hashes.
Bản thiết kế ban đầu này chưa khóa đầy đủ các phần đó, nên tự nó không đủ để
được runner chấp nhận. Trạng thái thực thi xem receipt AI, không sửa registration
đã freeze sau khi nhìn outcome.

## Mục tiêu

Đo xem các candidate đã freeze có thể đạt mục tiêu phase và sống sót trong các
horizon 3, 6 và 12 tháng dưới profile prop đã pin hay không. Đây là bài đánh
giá time-fit, không phải tối ưu tham số và không cam kết pass challenge.

## Phạm vi cố định

- Thị trường: EURUSD CFD, tick Bid/Ask, H4 signal sau nến đóng, fill ở quote kế
  tiếp; giữ gap, không sort/deduplicate/fill.
- Candidate: Donchian, SMA, Z-score, Pullback, UTC range hiện có; không thêm
  candidate mới trong registration này.
- Horizons: 3, 6, 12 **tháng lịch**, ngày bắt đầu/kết thúc phải pin trước run;
  không thay bằng 90/180/365 ngày nếu chưa tạo trial mới.
- Risk/cost: reuse contract/risk đã freeze; không tăng lot để đạt target.
- Profile: FTMO 2-Step Swing là chuẩn chính; The5ers chỉ là profile đối chiếu
  sau khi có terms/account-specific snapshot riêng. Không gắn FTMO terms cho
  The5ers.
- Terms snapshot nguồn chính thức: [PROP-TERMS-SNAPSHOT-20261106](PROP-TERMS-SNAPSHOT-20261106.md).

## Metrics và trạng thái

Mỗi candidate × horizon × profile ghi:

- first breach và loại breach (daily/overall/equity/balance);
- days-to-target, qualifying days, phase transition và phase 2 survival;
- activation/inactivity status, holding/news exception status nếu profile có
  dữ liệu;
- maximum observed drawdown với coverage rõ, open positions, cost/financing,
  censored/unknown khi window chưa đủ;
- payout/eligibility chỉ ghi `not_implemented` cho tới khi terms và evaluator
  được pin.

Không dùng quarterly PnL để ngoại suy tuyến tính. Các window chồng nhau không
được tính là trial độc lập; prior exposure và dữ liệu đã consumed phải giữ
trong manifest.

## Gates trước khi chạy

1. Inventory data availability/consumed cho từng horizon mà không đọc outcome
   holdout.
2. Pin source, lifecycle profile, timezone/DST, cost và account terms.
3. Chạy preflight/coverage; thiếu historical broker cost, intrabar equity hoặc
   firm-specific rule thì giữ `unknown`.
4. Chỉ sau đó mới mở numerical run mới với output directory riêng.

Lifecycle evaluator offline hiện hỗ trợ target, daily/overall loss, trailing HWM,
reset/DST, minimum days và position policy. Activation/inactivity, news rules,
payout, historical fills và live reconciliation vẫn là gaps riêng.

**Model calls:** 0 · **Broker calls:** 0 · **Holdout:** chưa mở · **Promotion:** false.

## Inventory trước khi chạy — 06/11/2026

Metadata audit đã đọc 103 JSON files trong bốn private roots, ghi nhận 69
metadata records và không đi vào CSV/price series. Hash audit:
`7583740F7F3A267BA6DFDFECC7173CD0547682F7EFCD97BED826134AA4F67579`.

Các cửa sổ xuất hiện trong metadata là 12/2021, 03–14/01/2022, Q1/2022,
11–12/2022 và Q1/2023. Chưa thấy metadata đủ cho horizon 3/6/12 tháng; điều
này chỉ làm trạng thái **availability/consumption unknown**, không chứng minh
unseen và không cho phép mở numerical run. Cần tìm nguồn QDM/cache tương ứng và
pin terms trước bước preflight tiếp theo.

Inventory trên chỉ nói về những exports đã có, không phải inventory toàn bộ
cache QDM. Kiểm tiếp 06/11: cache có đủ dates; export năm 2023 và preflight đã
đạt 27.549.175 ticks, warmup reuse có 255 H4 hợp lệ. Q1 đã consumed; Q2–Q4 nay
đã đọc quality trong study historical robustness. Coverage vẫn là observed
quotes, không phải liên tục. Không còn cần hỏi owner cung cấp dữ liệu hoặc mua
challenge để chạy declared offline scenario này.
