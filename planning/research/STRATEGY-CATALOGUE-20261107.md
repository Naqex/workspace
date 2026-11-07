# Danh mục nghiên cứu chiến lược — 07/11/2026

Cập nhật08/11: 36 hồ sơ, trong đó15hồ sơ đã có implementation, tổng16rules
(8H4+8H1),20ý tưởng/biến thể chưa code và1thành phần risk. **Không có
nghĩa 36 chiến lược độc lập hoặc đã được kiểm định.** Bản ghi có cấu trúc nằm ở
[JSON](STRATEGY-CATALOGUE-20261107.json); bảng dưới là bản đọc của cùng dữ liệu,
không tạo registry/task/approval mới. Quy tắc chính xác nằm trong source và protocol của từng ứng viên.

| Nhóm dữ liệu | Hồ sơ | Ý nghĩa |
|---|---:|---|
| Đã code |15 hồ sơ /16 rules|Giữ cả kết quả âm; chưa có winner đủ qualification|
| Có dữ liệu giá để viết đặc tả |6|Chưa code/rerun; H1/D1 mới vẫn cần adapter và tests|
| Cần đọc phương pháp và quy ước giờ |3|Fixing/local-hours; không lấy abstract thay recipe|
| Cần lịch sử dài, nhiều cặp tiền hoặc dữ liệu cơ bản đúng thời điểm |9|Deferred, không mở thêm dữ liệu trong pilot|
| Thiếu point-in-time news |2|Deferred, không gọi lịch tin hiện tại là lịch sử chuẩn|
| Thành phần điều chỉnh rủi ro |1|Không phải lợi thế vào lệnh độc lập|

Họ và quan hệ gần nhau thể hiện trùng cơ chế; không dùng số family làm số kiểm định độc
lập. Đổi indicator/hour/exit vẫn tăng trial count. Các nguồn tham khảo gợi cơ chế
hoặc định nghĩa, không chứng minh ngưỡng cụ thể, lãi/lỗ EURUSD/H4 hay pass quỹ.
Ưu tiên dưới đây do project chọn để đa dạng câu hỏi và reuse data, không là
xếp hạng khả năng sinh lời từ paper hoặc cộng đồng.

## 36 hồ sơ

| ID | Ý tưởng | Họ / quan hệ | Loại | Dữ liệu / tình trạng | Nguồn |
|---|---|---|---|---|---|
|R001|Donchian20/10|Theo xu hướng / phá biên|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL, NY125|
|R002|SMA20/80|Theo xu hướng / phá biên; gần R001|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL, AQR-TS|
|R003|Z-score20 ±2|Hồi về trung bình giá|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL, TV-BB|
|R004|Pullback20/80|Theo xu hướng / phá biên; gần R002|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL|
|R005|UTC range00–08 breakout|Phá biên phiên|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL, NY150|
|R006|Failed20 breakout|Đảo chiều ở biên; gần R001|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL, NY125|
|R007|Compression6/24 breakout|Theo xu hướng / phá biên; gần R001|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL, NY150|
|R008|UTC range fade|Đảo chiều ở biên; gần R005|Đã có|Đã code (chưa đủ bằng chứng)|LOCAL, NY125|
|R009|Time-series momentum dài hạn|Xu hướng dài hạn|Ý tưởng mới|Gác: lịch sử, dữ liệu hoặc contract|AQR-TS|
|R010|TSMOM theo volatility|Xu hướng dài hạn; gần R009|Biến thể|Gác: lịch sử, dữ liệu hoặc contract|AQR-TS|
|R011|Bollinger re-entry|Hồi về trung bình giá; gần R003|Đã có|Đã code (chưa đủ bằng chứng)|TV-BB, LOCAL|
|R012|RSI contrarian có xác nhận|Hồi về trung bình giá; gần R003|Đã có|Đã code (chưa đủ bằng chứng)|TV-RSI, LOCAL|
|R013|ATR shock fade|Hồi về trung bình giá; gần R003|Đã có|Đã code (chưa đủ bằng chứng)|NY125, LOCAL|
|R014|Range midpoint fade|Đảo chiều ở biên; gần R006|Đã có|Đã code (chưa đủ bằng chứng)|NY125, LOCAL|
|R015|Previous-day high/low breakout|Phá biên phiên; gần R001|Đã có|Đã code (chưa đủ bằng chứng)|NY125, NY150, LOCAL|
|R016|London opening-range breakout|Phá biên phiên; gần R005|Biến thể|Có giá; còn spec/adapter/tests|NY150|
|R017|New York opening-range breakout|Phá biên phiên; gần R016|Biến thể|Có giá; còn spec/adapter/tests|NY150|
|R018|Asia range → London breakout|Phá biên phiên; gần R005|Biến thể|Có giá; còn spec/adapter/tests|NY150|
|R019|Break → retest prior level|Theo xu hướng / phá biên; gần R015|Biến thể|Có giá; còn spec/adapter/tests|NY125|
|R020|Fixing reversal có điều kiện|Dòng tiền quanh fixing|Ý tưởng mới|Cần đọc method và clock|BOC48|
|R021|Pre-fix USD drift|Dòng tiền quanh fixing; gần R020|Đã có|Đã code (chưa đủ bằng chứng)|BOC48, LOCAL|
|R022|Post-fix USD reversal|Dòng tiền quanh fixing; gần R020|Đã có|Đã code (chưa đủ bằng chứng)|BOC48, LOCAL|
|R023|Local trading-hours currency flow|Dòng tiền theo phiên|Ý tưởng mới|Cần đọc method và clock|SNB04|
|R024|Post-weekend gap fade|Hồi khoảng trống giá|Ý tưởng mới|Có giá; còn spec/adapter/tests|LOCAL|
|R025|Weekday/calendar effect|Lịch giao dịch|Ý tưởng mới|Có giá; còn spec/adapter/tests|QC|
|R026|Month-end fixing flow|Dòng tiền quanh fixing; gần R020|Biến thể|Cần đọc method và clock|BOC48|
|R027|News-surprise continuation|Sự kiện / tin tức|Ý tưởng mới|Gác: thiếu tin tức đúng thời điểm lịch sử|NEWS|
|R028|News overreaction reversal|Sự kiện / tin tức; gần R027|Biến thể|Gác: thiếu tin tức đúng thời điểm lịch sử|NEWS|
|R029|Currency carry|Chênh lệch lãi suất|Ý tưởng mới|Gác: lịch sử, dữ liệu hoặc contract|CARRY|
|R030|Carry + trend|Chênh lệch lãi suất; gần R029|Biến thể|Gác: lịch sử, dữ liệu hoặc contract|CARRY, AQR-TS|
|R031|Long-horizon value / PPP|Định giá dài hạn|Ý tưởng mới|Gác: lịch sử, dữ liệu hoặc contract|AQR-VM|
|R032|Value + momentum|Định giá dài hạn; gần R031|Biến thể|Gác: lịch sử, dữ liệu hoặc contract|AQR-VM|
|R033|Cross-sectional FX momentum|So sánh nhiều đồng tiền|Ý tưởng mới|Gác: lịch sử, dữ liệu hoặc contract|BIS366|
|R034|FX factor-residual reversion|So sánh nhiều đồng tiền; gần R033|Ý tưởng mới|Gác: lịch sử, dữ liệu hoặc contract|AQR-VM|
|R035|Cointegrated FX spread|So sánh nhiều đồng tiền; gần R034|Ý tưởng mới|Gác: lịch sử, dữ liệu hoặc contract|QC|
|R036|Volatility targeting / exposure cap|Điều chỉnh rủi ro|Thành phần|Thành phần risk, không edge|AQR-TS, LOCAL|

## Nhánh đã triển khai và bước tiếp

[Discovery4](CHALLENGE-DISCOVERY-ROUND4-20261108.md) đã code8H1rules từ các hồ
sơR004/11/12/13/14/15/21/22. Giữ cả H4 và H1 version trong JSON, không xem
hai timeframe là hai edge độc lập. [Kết quả](DISCOVERY4-RESULTS-20261108.md) và
[selection-v2](H1-SELECTION-V2-AND-2024-20261108.md) giữ decisions/protocol.
Không khởi động lại các hồ sơ đã implemented từ phần đề xuất cũ.

R023 vàR020 còn cần method/data phù hợp; các ORB vẫn gần UTC range. Các nhóm
long-horizon/multi-symbol/PITnews giữ deferred. Catalogue là kho tra cứu, không
automatic dispatch hoặc quyền mở dữ liệu holdout/broker.

## Nguồn và giới hạn

Đọc metadata/summary của các nguồn gốc sau; chưa đọc toàn bộ mọi paper.
Không import code/dataset; trước implement recipe từ ngoài phải kiểm method,
license và point-in-time mapping. Không coi kết quả futures/forwards dài hạn
là kết quả CFD bán lẻ; không suy quyền EA/news/holding của FTMO/The5ers từ paper.

- **NY125** — [Currency Orders and Exchange-Rate Dynamics](https://www.newyorkfed.org/research/staff_reports/sr125.html), 2001. official_research_summary; Order/level mechanism; not our rolling thresholds.
- **NY150** — [Stop-Loss Orders and Price Cascades in Currency Markets](https://www.newyorkfed.org/research/staff_reports/sr150.html), 2002. official_research_summary; Stop cascade mechanism; not a compression recipe.
- **BOC48** — [Foreign Exchange Fixings and Returns Around the Clock](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/), 2021. official_research_summary; Fix-related drift/reversal; full method/clock must be read before replication.
- **SNB04** — [Intraday patterns in FX returns and order flow](https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04), 2011. official_research_summary; Historical local-hours effects; not a current EURUSD bot guarantee.
- **AQR-TS** — [Time Series Momentum: Original Paper Data](https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data), 2012 paper / 2018 page. author_dataset_description; 12-month lookback/monthly holding; futures/forwards, not H4 CFD.
- **AQR-VM** — [Value and Momentum Everywhere: Factors, Monthly](https://www.aqr.com/Insights/Datasets/Value-and-Momentum-Everywhere-Factors-Monthly), 2012 paper / 2026 page. author_dataset_description; Long/short multi-market factors; not EURUSD-only replication.
- **BIS366** — [Currency Momentum Strategies](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies), 2011. official_research_abstract; Cross-sectional currency momentum with costs/limits to arbitrage.
- **CARRY** — [Carry Trades and Currency Crashes](https://economics.princeton.edu/working-papers/carry-trades-and-currency-crashes/), 2008. author_university_summary; Carry mechanism and negatively skewed crash risk; CFD swaps not policy rates.
- **NEWS** — [How Economic News Moves Markets](https://www.newyorkfed.org/newsevents/news/research/2008/rp080908), 2008. official_research_summary; Announcement surprise responses; does not validate continuation/reversal rules.
- **TV-RSI** — [Relative Strength Index](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/), page checked 2026. official_indicator_definition; Indicator definition only; no profit evidence.
- **TV-BB** — [Bollinger Bands](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/), page checked 2026. official_indicator_definition; Indicator definition only; no profit evidence.
- **QC** — [Backtesting Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide), prior verified 2026-11-07. official_methodology_prior_evidence; Workflow reference in AI plan; not strategy khả năng sinh lời evidence.
- **LOCAL** — [Naqex exact eight candidate rules](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md), source 03436225. local_source_and_protocol; Exact implemented rules/history; published literature is mechanism context only.

Nguồn StLouis2011-021 đã có ở research cũ nhưng refresh PDF lỗi502 lượt này;
không nâng thành đã xác minh lại hoặc dùng làm chứng nhận recipe mới. QC tái dùng
bằng chứng đã ghi cùng ngày trong AI plan. Nguồn indicator chỉ cho định nghĩa;
R024/25/35 chưa có bằng chứng gốc cho lợi thế và được ghi rõ trong JSON.

[Protocol pilot](COARSE-SCREEN-PILOT-20261107.md) và [review kết quả](COARSE-SCREEN-REVIEW-20261107.md)
giữ scope/accuracy/timing. [Kết quả năm cũ](HISTORICAL-RESULTS-20261107.md) vẫn
có hiệu lực; catalogue không tự hồi sinh các version đã gác.
