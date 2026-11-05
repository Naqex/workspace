# Time-fit study registration — 3/6/12 tháng

**Registration:** `eurusd-h4-ftmo-time-fit-3-6-12m-v1`
**Registered:** 2026-11-05 21:49 UTC / 2026-11-06 Asia/Saigon
**Status:** `frozen_registration_not_executed`

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
