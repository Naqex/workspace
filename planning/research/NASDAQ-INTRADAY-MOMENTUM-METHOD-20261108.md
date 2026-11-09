# Bước tiếp: first-half → last-half momentum, reuse NASDAQ M1 đã kiểm

Đây là method admission trước outcome mới, không cứu R063 bằng sửa RSI/IBS.
Ưu tiên một câu hỏi giao dịch trong ngày để tránh phụ thuộc overnight financing
của R063. Liên quan R051 đã thất bại trên US500; transfer sang NASDAQ là trial
cùng họ, không independent edge. Chưa gọi là account policy hoặc challenge.

## Nguồn và giới hạn

Đã refresh08/11
[author university record, Gao/Han/Li/Zhou2018](https://profiles.wustl.edu/en/publications/market-intraday-momentum/):
SPY1993–2013, first-half-hour gồm previouscashclose→10NY, dự báo last-half-hour;
abstract có thêm10ETFs. Không suy một ETF cụ thể là QQQ chỉ từ abstract.
Paper gợi ý cơ chế rebalancing/information, không chứng minh NASDAQ CFD hiện
có lợi thế. Publisher và SSRN fullpage trả403; Reading repository có anti-bot,
không bypass hoặc claim đã đọc fullpaper mới. Fullmethod của R051 được kế
thừa đúng scope từ [US500 protocol](US500-CLOSE-MOMENTUM-20261108.md), không
nâng ngày review cũ thành fresh fulltext verification.

Source data đã đạt: [M1 results](NASDAQ-M1-HISTORY-RESULTS-20261108.md),8books,
development2019/2022 + warmups. Không cần download mới, không dùng2025+.
Sameprovider/cashproxy/CFD adjustment và target costs vẫn có giới hạn.

## Lát hữu hạn để triển khai kế tiếp

Đăng ký economic protocol và fixtures trước numeric: pure signal reuse
`index_close_momentum.plans_for`, không financial US500 book. Exact method
là sign(previouscashBidClose→09:59BidClose), entry15:31M1Open, exit15:59M1Open,
regular390mincashdays; calendar halfdays skip trước outcome. Giữ previous14TR
readiness từ parent, tính hoàn toàn từ ngày trước; không nhìn đủ cả ngày hôm
nay để quyết định entry. No volume/news filter, no parameter grid.

Pricecomponent1hypotheticalunit, cả BUY và SELL theo sign; observed entryAsk/
exitBid choBUY, entryBid/exitAsk choSELL, slip0,25/0,75,commission0. Entry/exit
cùng ngày, không dự định funding. Thiếu endpoint phải unresolved trong cùng
denominator, không nextquote/skipbadtrade. Component chưaSL/margin/sizing;
survivor mới cần wrapper/prop/ticks/selection-aware OOS.

Retention phải khóa trước đo, gồm net sau phí cả2years, lượng observations,
endpoint coverage và comparison/control thích hợp; không chọn threshold sau
outcome. Oracle khác arithmetic và future-mutation trước numeric. Tận dụng
batch validation/quality/lineage đã có, không tải lại toàn nguồn hoặc tạo
engine/UI/skill mới. Chưa có kết quả kinh tế R064 trong bước method này.
