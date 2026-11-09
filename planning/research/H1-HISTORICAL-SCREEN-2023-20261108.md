# H1 Discovery4: historical screen2023 — đăng ký trước outcome

08/11/2026. Parent [tám recipes bất biến](CHALLENGE-DISCOVERY-ROUND4-20261108.md),
SHA256`874cb378c69a6cae8dfcca11142bc9ef23c7422617a708e2e5b0a8f21c4b5255`.
[Campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) giữ C1/C2; cả hai chưa đạt.

## Câu hỏi và scope

Giữ cả8H1recipes trên2023 đã consumed, không chỉ chọn BB vì đẹp ởQ1/2022.
Đây là historical robustness của rules đã freeze, **không cleanOOS**. Chưa
đọc numerical outcome2023 của tám rules khi đăng ký file này.2025+đóng.

Raw pins kế thừa source đã dùng:

- Warmup01/11–31/12/2022:
  `77fcaa2722b336e729cb5fcce0b6f2aec1be9a652bbfdc7eabeb58a88a6f518a`.
- Evaluation01/01–31/12/2023:
  `0cc3d1206f83f0bd53fbe5eea512542f58f4172a435bfecc590ecb49906531ce`.

Paths/source/runtime/protocol/candidate/account/cost pins ở registration JSON
đi kèm. H1 cache chuẩn bị một lần từ raw qua reader/guards hiện có; không đổi
raw, fill missing hours hoặc nới current source binding để reuse old cache.
Mỗi input prep tối đa600s, một writer; numerical screen hữu hạn8×2costs.

## Những gì giữ nguyên

Tất cả entry/exit/clock/DST/SL1,5ATR14/timed exit/sizing của parent. Initial10k,
planned25USD, một position, hai cost scenarios nhưQ1;5USD/lot roundtrip,
slippage0/0,00002, actual declared financing snapshot9,3/−0,31 và20/20.
Số liệu reference là scenario dùng spec capture hiện có, không được gọi phí
broker2023 đã verified. Spread embedded trong Bid/Ask, không trừ thêm lần nữa.

H1screen chưa có internal tick risk/prop path/intrabar DD. Nó không tự stop
ở ngưỡng loss của native account và không mô phỏng phase transitions; native
review có thể đổi kết luận economics vì các giới hạn đó. Không force-close
cuối mẫu hoặc cộng PnL mở thành tiền rút. Giữ cả vị thế/pending/funding/floating.

## Đánh giá đã khóa

- Báo annual và contribution theo tháng/quý từ cùng account path; trade counts,
  PnL sau funding và cost sensitivity. Các windows lồng nhau không độc lập.
- Giữ nguyên ưu tiên ở parent: tối đa2bản đủ lý do qua tick deep review, theo
  economics hai mức phí, robustness hai periods và ambiguity. Không mặc định
  promote nếu screening dương hoặc yêu cầu phải có survivor. Dấu gần0/stop
  ambiguity phải tick review trước kết luận, không auto reject family.
- Có negative-control và near-zero tickQ1 đang chạy độc lập; lỗi material về
  decisions/counts/accounting thì quarantine scope liên quan, fix/regression
  rồi đăng ký lại source, giữ output cũ. Không đổi thresholds sau outcome.
- Stage này không đánh giá G3/G4/G5 hoàn chỉnh; chỉ tạo bằng chứng chọn câu hỏi
  deep review. Không tự mở2024/holdout, sizing grid, broker/model/provider.

## Kiểm chứng trước numerical screen

Registered CLI phải reject input/protocol/source/cost/candidate khác pin,
unknown registration và2025+ trước khi load cache/simulate; lỗi có progress và
failure artifact. Numeric `simulate_coarse` giữ nguyên source từQ1 đã kiểm;
chỉ thêm cổng đăng ký historical. Toàn bộ16Q1scenarios phải khớp lại sau CLI
plumbing change, ngoài timer. Actual commands/results vào AI receipt/attempt.
