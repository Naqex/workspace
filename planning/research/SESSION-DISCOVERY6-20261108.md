# Discovery6 — fixing windows, frozen trước numerical outcomes

## Cơ chế và quan hệ trials

[Bank of Canada WP2021-48](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/)
và [bài Journal of Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13306)
của Krohn/Mueller/Whelan mô tả USD lên trước fixes và giảm sau fixes, gắn order
imbalances. [SNB WP2011-04](https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04)
nghiên cứu local-hours/order flow. Đã đọc08/11; papers là lý do đặt hypothesis,
không chứng minh hiệu quả CFD/fees hiện tại hoặc quyền dùng mọi dữ liệu hãng.

Discovery4postfix16–20London đã xem2023/2024 và yếu; [ML](DISCOVERY5-RESULTS-20261108.md)
thất bại. Đợt này là data-informed descendants, không độc lập với các lần trước.
Không sửa parent hoặc gọi2023/2024cleanOOS. Khóa4rules sau, không grid hours:

| Rule | Entry sau đóng H1, đúng giờ local | Side | Exit deadline | Lý do khác paper |
|---|---|---|---|---|
| pre-ECB |02:00America/New_York,Mon–Fri|SELL EURUSD|14:00Europe/Berlin cùng ngày|H1 approximation,15phút trước14:15fix; DST của hai zones riêng |
| post-London |16:00Europe/London,Mon–Fri|BUY EURUSD|16:00America/New_York cùng ngày|Giữ thêm so16–20London, chừa1h trước rollover17NY |
| pre-Tokyo |18:00America/New_York,Mon–Thu|SELL EURUSD|10:00Asia/Tokyo tiếp theo|Bỏ1h sau rollover; exit5phút sau09:55fix; bỏFriday để không cố giữ qua weekend |
| composite |Cả ba slots trên, tối đa1position|Theo slot|Theo slot đang giữ|Một account sequential, không cộng net ba accounts; gặp position/pending thì skip slot |

Nếu thiếu đúng entry bar thì không vào bù; exit trễ thì next observed close
đề nghị EXIT và next quote fill, không bịa quote đúng deadline. Khi bar kết
thúc là thời điểm entry vẫn fill quote sau decision. Clock uses UTC timestamps
và ZoneInfo, không cố định offset DST. Mỗi emit chỉ một slot; rejected entry
không retry giữa giờ. SL1,5WilderATR14, noTP, risk25USD/initial10k, lot/cost/
financing/core nhưDiscovery4. Hai costs chuẩn/cao giữ nguyên, không tăng risk.

State phải giữ ATR/history/entry deadline/position identity; unknown external
position không tự nhận quyền quản lý. Warmup chỉ history, không gửi lệnh.
Fixtures:EU/US DST lệch tuần, cross-dateTokyo, Friday skip, missing entry,
late exit, SL/rejection reset, restore và composite non-overlap. Code tests
trước outcomes; shared coarse core trước, native tick kiểm khi có survivor.

## Bài screen hữu hạn và cách chọn

Reuse source-bound warmup+H1caches2023/2024; hai năm là accounts riêng bắt đầu
flat.4rules×2costs×2years, giữ toàn negatives/trades/open/pending. Không đọc2025+.
Nguồn/source/protocol/data pins vào manifest trước chạy; status/failure ở
attempt mới, không overwrite. Không broker/API/LLM calls trong numeric job.

Ưu tiên tối đa2rules dương cả hai annual windows ở cả hai costs, xếp theo
weakest-year stress; composite cùng family không là độc lập. Không có winner
thì không ép. Native tick,risk/DD, uncertainty/multiple trials,3/6/12month
prop paths, exact fresh-holdout và prospective forward/reconciliation còn cần
trước C1. C2review causality/accounting, review gap rồi fix/rerun affected scope;
PnL dương không tự đóng [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md).
