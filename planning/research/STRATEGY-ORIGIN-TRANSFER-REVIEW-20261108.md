# Nguồn gốc và phép chuyển chiến lược — 08/11/2026

Thực hiện acceptance3 của [repairprotocol](SCREEN-CALIBRATION-REPAIR-20261108.md).
Không thay rules/outcomes cũ hoặc tạo thêm policy chỉ bằng ghi lại tên nguồn.
Phân loại ở đây là review bằng chứng, không attribution tác giả của code.

| Họ đã dùng | Nguồn chứng minh điều gì | Exact version của project đổi gì | Cách gọi đúng / bước cần trước biến thể tiếp |
|---|---|---|---|
| Donchian/SMA H4 FX/Gold | Trend following là họ công khai; AQR2017 khảo sát monthly portfolio67markets,1/3/12month signals | Một instrument, H4/20–80 hoặc20–10, ATR stop, lotgrid/CFDfunding, annualreset | Projectrecipe/marketadaptation. Không dùng AQR làm evidence cho exactpolicy; cần matched horizon/universe/volatility/roll/fees trước nói replicate |
| RSI/BB/Z/shock/pullback | Định nghĩa indicator hoặc cơ chế reversion/trend | Reentrythresholds, lookback, stop1,5ATR, mean/timeexit và mộtposition | Projecthypothesis. Giữ phiên bản đã âm; baseline tính tay xác nhận indicator/signal, không historical benchmark bắt buộc lời |
| Prior-daybreak/fade/ORB | NYFed125 mô tả orders/levels; không rule previousUTCday>=18hours hoặc H1close breakout | Đổi leveldefinition, H1confirmation, entry08–16UTC, expiry/SL/20UTCexit | Mechanismadaptation. H1close có thể trễ so firstbreak; chưa measured transferloss. R019 cần exantelevel/retest/expiry rõ, không giả originalpaper xác nhận |
| Fixing | BoC2021-48 khảo sát G9/USD1999–2019 và dealerflow; các fixing09:55Tokyo/14:15Frankfurt/16London | EURUSD đơn lẻ; preECBexit14:00Berlin (sớm15min), Tokyoexit10:00 (trễ5min), H1boundary/quoteafterdecision, SL/entryskip; portfolio/data khác | Không exactreplication. Freeze mechanismprobe đúng clock trước đưa SL/size/propwrapper vào; thiếu dealerflow/G9 thì chỉ proxyprobe, không gọi paperreplicated |
| US500 noise/reversion/closemomentum | Các cơ chế equity intraday/daily có nguồn nhưng không nativeCFDquote/propcontract | ETF/equity/futures→CFD, M1cashhours/sourcepadding correction, gaps, fixedfraction/SL/overnightholding | Market/sourceadaptation. Giữ correctedbooks; targetlot/point/swap/gap chưa đủ thì chưa promote |
| Ridge/Forest | MLmethods có thể fit features/labels, không tự tạo tradeableedge | Labels4observedhours không SL nhưng strategy cóSL; features/regime/training của project | Trainedprojectpolicy; không nguồn nào xác nhận exactFXedge. Giữ2real+2shuffledcontrols và overlap/exposure |

## Quyết định triển khai

FullpaperBoC §V.E/pp33–35(nội dung), đọc tiếp08/11, tự đánh giá spreadcost và
thấy nhiều windows không còn lời khi dùng fullindicativespread. Không dùng
spreadgiảm50% trong paper như quyền giảmspreadCDFcủa project. Vì thế bước
fixing tiếp phải kiểm clock **và cost-admissibility** trước wrapperbot; đây là
thu hẹp câu hỏi theo bằng chứng nguồn, không khẳng định exactrecipe có edge.

- Không tải/mua thị trường hàng loạt để cố dựng lại AQR67markets, không dùng
  paper1999–2019 làm lời hứa về broker/prop hoặc dữ liệu chưa mở.
- Lát research kế tiếp nên kiểm **transfer của fixing clock**, vì có cơ chế
  định thời rõ và rawEURUSD đã consumed. Trước numeric, protocol riêng khóa
  exactclock/quoteavailability/cost/window/control và ghi proxy chỉEURUSD;
  không sửa các Discovery6hours để cứu outcome. Đây là đề xuất chưa chạy,
  không có policy/recipe“đã được chứng minh”. Nếu data không tái hiện được
  câu hỏi thì defer thay vì tự đổi sang unconditionaltrade.
- R019 vẫn là ý tưởng riêng chưa code. Không tự đưa lên đầu chỉ vì dễ reuse
  parent. Original→project table là điều kiện design trước outcome, không là
  giấy phép replay data chưa mở hoặc tự chọn subperiod sau khi xem PnL.

## Nguồn và giới hạn đã kiểm

- [AQR2017](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf),
  pp2–3:method/universe. Paper không xác nhận currentFTMOcosts hoặc exactH4recipe.
- [BoC2021-48 fullPDF](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf),
  pp1–4(nội dung):fixingtimes/G9/sample/mechanism, đọc08/11. Không importcode/data.
- [NYFed125 summary](https://www.newyorkfed.org/research/staff_reports/sr125.html):
  orders/roundlevels, không prior-day/H1thresholdspecification.
- Exactprojectrecipes và khác biệt đã ghi từ trước outcomes trong
  [Discovery4](CHALLENGE-DISCOVERY-ROUND4-20261108.md),
  [Discovery6](SESSION-DISCOVERY6-20261108.md), [Discovery7](ORB-DISCOVERY7-20261108.md),
  [ML](DISCOVERY5-RESULTS-20261108.md); source limits trong
  [catalogueJSON](STRATEGY-CATALOGUE-20261107.json).

Đây là focused transferreview của các họ đang xét, không full replicationaudit
mọi53records hoặc bằng chứng sẽ tìm ra winner bằng fixingprobe.
