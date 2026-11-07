# Compression6/24 — kiểm lịch sử dài hơn, 07/11/2026

Owner giao liên tiếp discovery/testing; sau Q1/2022đã freeze ở
[Discovery3](DISCOVERY-ROUND3-20261107.md), compression net equity chuẩn/cao
+50,38/+28,47USD,27closed trades và1position mở. Kết quả chỉ hỗ trợ thêm một
bài kiểm, không đủ edge. Bản này giữ nguyên, không sửa theo Q1outcome hoặc
data2023đã xem qua các nghiên cứu khác. Không gọi năm2023clean OOS.

| Phần | Contract trước outcome mới |
|---|---|
| Candidate | `eurusd-h4-compression6-24-atr14-time6-r025-v1`, exact rules/SL/exit/risk từ Discovery3 |
| Hypothesis | Sau giai đoạn range6co hẹp so range24, continuation còn tạo net dương sau chi phí qua năm dài hơn, không chỉ Q1/2022 |
| Warmup/evaluation | Reuse01/11–31/12/2022và01/01–31/12/2023 từ accepted exports/cache; không export/download mới |
| Role | Historical robustness/selection, prior exposure unverified;2023đã consumed bởi các candidates khác, không OOS |
| Account |10kUSDinitial,25USDplanned risk,1position,internal100/500; newaccount đầu study |
| Cost/clock | Exact reference/stress terms trước,22UTCweekday/Wed×3; quotes/H4UTC, resetEurope/Prague; không đổi phí hoặc thêm filter |
| Prop observations | Reuse declared FTMO2-Step Swing profile, actual phase reset; unsupported full-firm exceptions/eligibility/payout giữ unknown |
| Cutoffs | Exclusive01/04/2023,01/07/2023,01/01/2024,3/6/12months nested |
| Primary | Annual net equity hai costs cùng firstbreach/phase/coverage; phase archives riêng, không cộng thành payout |
| Secondary |Quarter contributions cùng account, trades/floating/holding/cost/lot/tickDD/headroom; không minimumwinrate chung |
| Limits |1worker6h/worker8h/batch ceilings, no auto retry, không mid-scenario resume; có thể chạy song song UTC2024 vì independent offline accounts |

Material correctness lỗi→quarantine phần ảnh hưởng. Firstbreach→không đủ
profile/config. Netkhôngdương ởmộtcost→không promote trong bài, không loại cả
họ. Dươngcảhai/khôngbreach→reviewthêm, chưa edge/prop qualification. Not-reached
giữ not-reached, không ép tănglot/kéo window. Zero trades/thiếu coverage giữ
inconclusive. Không chọn winner solely theo net hoặc dùng horizons thành mẫu
độc lập. Không tuning risk/TP/threshold trong attempt; thay rules là trial mới.

Freezeprotocol,input/source/runtime/profile/decision hashes trước numerical;
newregistration digest explicit tại existing registry, không sửa oldJSON hoặc
nới sourceguard. Kiểm synthetic newcandidatephase reset và preflight trước
dispatch, giữ numerical source khi writers hoạt động. Không broker/model,
không mở2025+/holdout hoặc provider. Receipt AI giữ actual state/outcomes.
