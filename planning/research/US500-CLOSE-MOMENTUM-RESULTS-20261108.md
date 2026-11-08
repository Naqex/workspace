# First→last half-hour — không đạt ở chi phí đã đăng ký

[Protocol](US500-CLOSE-MOMENTUM-20261108.md) đã chốt trước kết quả. Một phiên
bản trên dữ liệu M1 Bid/Ask canonical2022–24, giữ nguyên risk/cost/SL; không
download hay model/broker calls. Đây là adaptation CFD, không replication SPY.

| Năm | Net chuẩn / stress USD trên10k | Entries mỗi scenario |
|---|---:|---:|
|2022|−562,28 / −796,05|235|
|2023|−751,67 / −1.068,46|218|
|2024|−619,79 / −949,77|234|

Cả ba năm âm ở cả hai mức phí: không giữ cho bước kiểm sâu. Không tăng risk,
giảm phí hoặc bỏ năm để cứu kết quả. Đây là các annualbooks riêng; chưa kiểm
native risk/prop DD, không suy thành kết quả challenge hoặc tài khoản liên tục.

3studies×2costs+3nullcontrols+3financialreviews hoàn tất42,281s. 687trades mỗi
scenario đều đã đóng, không forceclose cuối mẫu; nullcontrols0. V1private
controller dispatch nhầm dailyreversionentrypoint bị explicitcandidateguard
chặn trước PnL; V2 sửa đúng argv và giữ failureV1. Không gọi first-pass đạt.

Ba kiểm tra causal policy và sharedbook SELL fixture đã đạt: Bid100 vào,
Ask95,2 thoát, net12,67USD. Typo trong test được sửa trước chạy số học.
Private `execution-v1/us500-close-momentum-dev-v2` giữ source/protocol/data/
results/reviews/logs. Đây là kiểm trong cùng lượt agent, chưa independent
reviewer sign-off. Không suy paper sai từ adaptation khác instrument/fees.
Campaign vẫn tiếp tục;2025+ đóng, không mua challenge.
