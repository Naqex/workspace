# NASDAQ noise14: method admission trước một trial mới

Chưa numeric outcomes mới, chưa policy được triển khai hoặc candidate promotion.
Tiếp sau [R065 bounds](NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md); đây là
giả thuyết chuyển cơ chế sang thị trường khác, không chỉnh TP/SL của R065.

Primary method đã dùng cho R048: [Beat the Market, tác giả](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf),
method pp5–6, đọc lại09/11. Price bands phụ thuộc biến động cùng giờ trong
14 phiên trước; model gồm điều chỉnh opening gap. Paper nghiên cứu SPY,
không chứng minh một NASDAQ CFD hoặc chính sách hard-stop của project có lời.
Không lấy các headline returns hoặc volume CFD làm bằng chứng của bản mới.

Khác R065: tín hiệu phụ thuộc 14 phiên và giờ trong ngày, chờ deviation khỏi
band; không mua/bán chỉ theo hướng 5 phút đầu. Lý do thử là transfer của một
mechanism đã mô tả rõ trên asset có dữ liệu đã kiểm, không vì tối ưu tham số
cho năm 2022 đã thấy dương. Parent R048 có kết quả yếu ở các năm US500 đã
thử: [review/corrections](FTMO-INDEX-COMMISSION-RESULTS-20261108.md); giữ đầy đủ
negatives, không quảng bá đây là paper replication hoặc hypothesis độc lập.

## Lát tiếp có giới hạn

1. Reuse `index_noise_study.bands` và NASDAQ source-only M1/warmup/calendar
   đã có. Xác định Bid-chart hoặc paired-side midpoint proxy, known-at,
   early-close, prior14 calendar-session completeness và previous cash close.
   Missing một required prior day/slot không được lấy lùi xa để đủ14.
2. Freeze một recipe account: decision clock, delayed fill, initial hard SL,
   exit/reversal/re-entry, risk25USD/10k, NASDAQ declared cost/geometry và
   eligibility; đối chiếu khác biệt với R048 và paper. Không grid tham số.
3. Synthetic timing/sizing/exit/gap fixtures trước numeric. Không copy old
   R048 `path_unresolved` cash thành exact PnL; held gap giữ unknown, hoặc
   conditional outer bounds chỉ khi có protocol phù hợp và tách verdict.
4. Sau admission và registration mới chạy dev2019/2022, source đã exposed;
   null/control và exact code/input bindings. Không mở 2025+ hoặc gọi dev là
   clean OOS. Chỉ survivor có căn cứ mới chi tick/prop/OOS/forward review.

Không fetch source mới hoặc đổi account/provider từ method note này. Không
native broker calls, mua challenge, runtime rollout, skill/global config edits.
Trạng thái hiện tại: đủ câu hỏi để admission recipe; chưa bắt đầu backtest.
