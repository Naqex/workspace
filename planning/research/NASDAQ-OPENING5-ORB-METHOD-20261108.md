# NASDAQ opening5 direction + bracket: primary method trước protocol mới

Đọc sau [R064 negative](NASDAQ-INTRADAY-MOMENTUM-RESULTS-20261108.md), không
đảo signal của R064. Câu hỏi: một rule vào sớm, SL cố định và giữ tail lớn có
khác fixed-hour cuối phiên và dailyreversion đã thử không? Chưa outcomes mới.

## Nguồn primary và điểm dễ hiểu nhầm

Đọc08/11 từ [PDF do tác giả cung cấp](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
qua [author papers index](https://concretumgroup.com/papers/), Method pp4–6:
Zarattini/Aziz, first2023-04-24, bảnPDF ghi2025-09-22; path2026/02 không là
ngày publication. StudyQQQ/TQQQ2016-01-01→2023-02-17. Không own2025+data.

Rule được paper gọi ORB ở đây là **hướng nến5phút đầu rồi vào**, không đợi
giá breakout high/low: first5up→long, down→short, doji→none. Stop ở phía đối
diện của nến đầu; TP10R hoặc cuối phiên. Paper dùng1%risk,4xleverage và giả
định no slippage. Những giả định/returns đó không tự áp cho CFD hoặc quỹ.
Không copycode/data; chỉ lấy cơ chế/rule làm hypothesis.

Primary olderORBcrudeoilPDF từ DivaPortal timeout; SSRN link4416622 trả403.
Không bypass hoặc claim đọc nguồn unavailable. Không dùng headline gains từ
authorindex làm evidence của project; cũng không dùng quotevolume thay
stock-volume/Stocks-in-Play filter trong paper khác.

Source capture private `nasdaq-orb-method-source-v1`:PDF2.596.401bytes, SHA
`bb800b06ee8e28c9fb40826a4b086f03e7268eec351152e8b970838f76e51fc8`,
URL/date/version/source.json,0,635s fetch. Metadata capturekhông độc lập chứng
thực historical bytes. Giữ private, không redistribute paper trongGit.

## Adaptation cần khóa trước numeric

Reuse NASDAQ sourceM1/calendar/warmups2019/2022 đã kiểm, không download mới.
Đề xuất một exactopening5recipe, không5/15/30grid:

- BidOpen09:30→BidClose09:34, đủ5sourceM1 cảsides; known09:35NY. Entry
  one-minute-delay exact09:36M1Open, khác giả định entry09:35 của paper.
- Stopfirst5BidLow choBUY/first5BidHigh choSELL. Target10×distance từ actual
  entryquote đến stop; side-specific Bid/Ask/protection. Không ATR/trailing/
  discretionaryveto hoặc giảmTP sau thấy outcome. Calendarhalfday phải
  xác định EoD; chốt exactexitminute trước run.
- Ưu tiên đăng ký researchriskwrapper25USD trên initial10k (0,25%), spread/
  slip0,25/0,75 và NASDAQ declared geometry đã có; không dùng paper1%risk để
  ép target. Quantity/minstep/margin/stopcost và accountcash phải kiểm trước.
- Reuse native protective primitive. BothSL/TPreachable cùngM1 là ambiguous,
  giữ unresolved hoặc xuống lower-timeframe theo protocol; không tự stopfirst
  hoặc chooseprofit. Gap/missingpath không được silently fill hoặc reset
  account. Unknownexposure cần block laterentries, không đóng giả cuối năm.

Đăng ký exactrisk/cost/execution/gap/gate/control và fixtures trước PnL.
Signal/quantity/firstprotectiveexit/accounting oracle dùng arithmetic khác.
Nếu cần targetedrawticks để giải ambiguity thì register source-only recovery,
giữ failures và rerun affectedscope, không sửa lịch sử hoặc mở holdout.

Đây là method/preparation, chưa R065implementedpolicy hoặc challengecandidate.
PaperETF và CFD khác source/execution/costs; prospective/prop/OOS/handover vẫn
là requirements riêng. Reuse research/qualification/continuity/debugging skills,
chưa có workflow mới lặp đủ evidence để tạo skill/framework khác.
