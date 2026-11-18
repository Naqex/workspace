# GBP V25 — nhận diện đúng recipe trước khi so hiệu suất

S01 gốc là `GBPUSD.SWEEP.ASIA.LONDON.DAY`: H1 quét biên 00–06UTC, đóng trở lại
vùng ở quyết định08–11UTC, SL ngoài nến quét ±0,1ATR14 trước nến; một signal/
ngày, BUY/SELL; không điều kiện H4 hướng cho SWEEP. Exit gốc DAY20:30UTC
clamp lịch đã khai báo. Source S01 có đúng300 raw2022–23, two-hour correction.

Main V23 2.288 endpoint thuộc nhiều B2/B3 recipes, không cùng cohort S01.
20:00UTC là một điểm giá H1 khác20:30UTC. V25 giữ nguyên S01 entry/SL và
đăng ký **một diagnostic `S01_H1_2000`**: exit20:00UTC, bốn nút OHLC/H1,
OLHC và OHLC. Đây là counterfactual resolution scenario được owner yêu cầu,
không nhận là replay gốc S01 hoặc đường tick/M1.

Dev2018–23, warmup2017-11. Paired H1 source admission V11, không mở later.
Áp đúng correction-card S01 vào hai H1 năm2022 trong bản sao RAM, kiểm units
gốc trước thay, raw source bất biến. Signal parity2022–23 với source S01
phải được báo; khác thì không coi là cùng recipe implementation.
Exact cost15% theo paired spread +9USD/lot; 12% chỉ audit, không chọn lại gate.
Đóng trước ngày kế tiếp nên funding0; giữ phí stress, natural SL, hai chiều.

Standalone risk150USD và satellites .25/.50×150USD, cùng marked book với
BASE_GUARD; FX commission/slippage/tick value cùng khai báo với EURUSD nhưng
giữ identity/quote path GBP riêng. NetR common=USD/150. ExTop5/10 bỏ trade
lớn nhất trên chính Dev cohort; không lấy Top10 kỳ sau.
Giữ gap count, endpoints missing, H1 uncertainty; mọi marked-book metrics
chỉ scenario. Không cho satellite qua gate/lifecycle khi2018–23 thiếu path
M1/tick, dù net/DD có cải thiện. Không tìm giờ exit hoặc tham số khác.
