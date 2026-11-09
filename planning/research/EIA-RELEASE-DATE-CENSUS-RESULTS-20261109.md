# EIA: đã kiểm ngày phát hành, chưa xác minh giờ phát hành trong quá khứ

Tiếp [sourcepilot](OIL-EIA-SOURCE-PILOT-RESULTS-20261109.md) theo
[mechanism plan](MECHANISM-FIRST-EXECUTION-20261109.md). Chỉ đọc lịch sự kiện
từ [archive chính thức](https://www.eia.gov/petroleum/supply/weekly/archive/),
không đọcgiáthịtrường/PnL mới, không suy mọi thứ Tư đều phát hành10:30ET.

| Năm | Số ngày phát hành | Thứ Tư | Thứ Năm | Thứ Sáu |
|---|---:|---:|---:|---:|
|2019|52|44|6|2|
|2022|51|44|7|0|

104links/bản báo cáo đại diện **103ngày sự kiện**, do hai tuần dữ liệu được
công bố cùng29/06/2022. Không tạo event22/06 hoặc trade hai lần29/06.
[Thông cáo EIA29/06/2022](https://www.eia.gov/pressroom/releases/press507.php)
xác nhận hai tuần kết thúc17/06 và24/06 cùng phát hành sau sự cốhardware.

## Lỗi đã bắt và sửa

Parserattempt1 đòi URLdate vàvisiblelabel khớp, dừng trướcoutput khi gặp
`2022_06_17_data/...php` có visiblelabel29. Đây là URL theo **tuần dữ liệu**,
không phải ngày phát hành. Không nới regex rồi âmthầm lấy17/06: thêm đúng
exception đã có primaryproof, bắt visiblelabel29, giữ cảhai sourceURLs trong
event29/06. Những mismatches khác tiếp tục bị chặn.

5focusedtests đạt:dedup/unknownclock,other-year exclusion,badorigin/date/path,
missingscope vàactualdelayed-data regression. Separate regex+visiblelabel
census trên savedHTML khớp HTMLParser toàn104links/103events, biết xuất xứ
month/data exception. Sameagent, không independentfeed/humancheck.

SnapshotHTML175.464bytes/sourceSHA vàtimefetch ởprivate
`execution-v1/eia-calendar-source-v1/`; oldparser vàfailure-attempt1 giữ.
Sourcefetch1request, khoảng2sbao gồmPython; dateparse/review0,063s. Không
download104báocáo/historicalmarketdata hoặcchạy strategy. Existingheader
market-holdout rule vẫn giữ; archive chứa lịch nhiều năm nhưngoutput chỉ2019/
2022, không phải mở marketprice2025+. Code chặn thay scope ngầm.

`events.json` giữ `actual_release_time_et=null`, publicationtime vàadvance
schedule chưaverified, tradingeligibilityfalse. Datecensus không chứngminh
tin đãpublic lúc10:30 trên mọi ngày hoặc nhữngexception đã được biết từ trước.
Chưaadmit shock/surprise predictor, ETF→CFDtransfer, fees/spec hoặcPnL.
Endpoint16:00Open củaUSOpilot vẫnmissing, không bịlịch mới làmthànhvalid.

EventsSHA`36aa7870ba27016a4d68fbbe84464cea7eca908c2e860f577f6b661950b204f9`.
Saved `check-eia-calendar-v1.py`; core `tooling/ai-engines/eia_release_dates.py`.
Next:actualhistoricalreleasehours/PITexceptions vàendpointsemanticregistration,
không tựdùngWednesdaymask/10:30default đểmở economicbatch.
