# Kiểm tín hiệu SMA vàng: đóng một khoảng trống C2

09/11/2026, trước lần tính signal-oracle mới. Outcomes đã biết ở
[review SMA50k](GOLD-SMA50K-REVIEW-20261108.md); đây không preregistration edge,
không chiến lược mới và không đổi verdict research survivor/low priority.

## Binding và phạm vi

- Exact `xauusd-h4-sma20-80-atr14-r025-v1`, 15 annual-reset books 2010–2024,
  mỗi book 50.000 USD/risk 125 USD, reference và cost-stress, tổng 30 books.
- Baseline private `execution-v1/metal-discovery9-screen/attempt-v1/`;
  reuse pins của `gold-sma50k-evidence-review-v1/manifest.json` và review result
  `ba1f6d5d08fdd065e8ecb21e223cedf763074db96edcf04716f1f980cd179927`.
- Raw Bid M1 SHA256
  `d209df9a5ce871f1992eb312595ebef2c19a884c1fe0a1be6bfb76d86cf471b9`;
  source đã consumed 2009-11–2024, không 2025+. Rehash trước dùng. Nếu phải
  đọc raw để dựng H1/H4 thì ghi phase/counter và giữ derivative để reuse.
- Bind 21 original source snapshots và 30 exact book hashes trước signal
  comparison; không dùng current Trader code thay cho snapshots khác version.

## Oracle và điều kiện kiểm

1. Reviewer không import simulator, candidate hay indicator implementation.
   Dựng H1 OHLC từ raw M1 bằng integer ticks 0,001; H4 chỉ nhận đủ bốn giờ
   UTC, không padding. Partial M1 trong giờ giữ theo semantics cũ; không biến
   đây thành chứng nhận feed đầy đủ/target broker. Đối chiếu excluded H4.
2. Warmup từ Nov 1 năm trước, reset mỗi annual book. SMA sign dùng integer
   `4*sum(last20)-sum(last80)`; chỉ cross sau khi đã có previous 80-bar sign.
   ATR14: seed 14 true ranges (first TR=high-low), Wilder smoothing tới hiện
   tại, stop distance=2ATR. Independent Decimal precision 80, tolerance
   absolute 1e-23 USD cho distance của producer precision 28; SMA sign exact.
   Constant declared spread/2 dịch mọi OHLC cùng lượng, không đổi SMA/TR.
3. Position side tại decision lấy từ sealed entry/exit path; stop trong H1
   được xem đã đóng trước H4 observe như coarse kernel. Đây là **conditional
   signal-path audit**, không độc lập chứng minh vị thế/stops của kernel đúng.
4. Với mọi completed H4, không chỉ các lệnh được ghi: BUY/SELL khi flat và
   cross, EXIT khi held BUY mất positive sign/SELL mất negative sign. Kiểm
   no-signal, missed/extra/duplicate decisions, decision timestamp=H4 end;
   stop distance và sizing 125 USD, 100oz, tick reserve0,001, two-side slip
   0,1/0,2 và commission5USD/lot RT, floor step0,01 như declared contract.
5. Queued entry/exit chỉ được consume tại first modeled minute của H1 kế
   tiếp có nguồn, không trước decision; so tất cả recorded entry fills và
   strategy exits. Stop/gap exits không tự là strategy EXIT. Giữ pending cuối
   năm thay vì forcefill. Không tính lại PnL hoặc thay phí.
6. Synthetic fixtures trước actual: warmup/equality/cross BUY–SELL/held EXIT,
   Wilder seed/smoothing, missing H1, constant-shift invariance, prefix/future
   mutation và missing/extra decision. Actual mutation ít nhất timestamp,
   side, distance, quantity, omission, duplication phải bị chặn.

Nếu không khớp, lưu failure, khoanh semantics/reviewer/producer trước sửa;
không đổi tolerance cho qua hoặc overwrite baseline. Oracle mismatch chưa tự
chứng minh producer sai. Native source, finance review trước vẫn có scope riêng.

## Output và vận hành

Private attempt mới `gold-sma-signal-review-v1`, một writer, CANCEL/deadline
300s, phase/counter/events/progress/result/failure, code/protocol/input pins,
timing wall/CPU. Source derivation tách signal comparison và mutations; report
scope/count/mismatch/limitations ở research owner. Không gọi reviewer code riêng
thành independent human/feed review. Không job nền sau terminal.

Kết quả khớp chỉ đóng khoảng trống SMA/ATR/decision trong phạm vi đã nêu.
Không đổi C1/edge/prop/time-fit/authority, không account policy/trial mới,
không holdout/broker/network market/model calls. Existing skills đủ; không
thêm framework, global config, runtime rollout hoặc signal optimization.
