# FTMO native · đăng ký sàng lọc H4/D1 Mon–Fri

Nguồn duy nhất là 39 Parquet từ audit `36f1535`. Khóa theo giờ nền tảng
từ 2025-01-01, không dùng OHLC hoặc kết quả holdout trong phép chạy. Chọn
giao đoạn chung đủ năm 2018–2024. Cluster A 2018–2020, B 2021–2024.
Cho phép warmup trước 2018 khi nguồn có sẵn. Nến và phiên dùng giờ nền tảng.

## Ba họ và đúng một biến thể đối chứng giờ thoát

- BREAKOUT. H4 Donchian 20, D1 Donchian 10, lấy các nến trước nến tín hiệu.
  ATR Wilder(14) của nến trước phải ở dưới trung vị của 20 ATR trước đó.
  Vượt biên bằng close, SL 1 ATR của nến tín hiệu. Thoát khi close rơi qua
  đường giữa của kênh trước nến đó hoặc hết tuần. Chung mã/chung lúc ưu tiên
  D1. XAUUSD chỉ H4.
- PULLBACK. H4 và hướng từ D1 đã hoàn tất. Trend D1 close > EMA50 > EMA200
  cho BUY và đảo dấu cho SELL. H4 trước chạm hoặc xuyên EMA20 và đóng phía
  hồi. Nến H4 hiện tại đóng lại qua EMA20 và vượt high/low nến hồi theo
  hướng trend. SL 1 ATR H4, thoát theo Friday. D1 chỉ làm bias.
- SWEEP. H4 quét một biên high/low của 5 D1 đã đóng và close trở vào vùng.
  Loại nến quét hai phía và yêu cầu ADX Wilder(14) D1 < 25. SL ngoài cực trị
  H4 thêm 0,1 ATR. TP đường giữa vùng, cố định từ entry.

## Khớp mô phỏng, chi phí và cửa quyết định

- Stage-0 dùng toàn bộ tín hiệu, không xét SL/TP, +24 giờ lịch broker hoặc
  cutoff thứ Sáu nếu đến trước. Tách count và mất đường, gross, spread,
  commission, slippage, swap theo năm. Mức SL tự nhiên dùng chuẩn hóa và đo
  tỷ lệ ma sát so với stop, không dùng để kéo rộng SL hay lọc phí khi replay.
- Mọi entry tại H1 open đầu tiên đúng hoặc sau khi nến tín hiệu đóng, tối đa
  một giờ trễ. D1 chỉ đã đóng khi tới mốc mở D1 kế tiếp (hoặc 24 giờ, mốc
  sớm hơn). Với H4 dùng open+4 giờ, tránh lấy nến sau chưa biết. Một vị thế/mã
  và họ. Entry Mon–Fri, flat thứ Sáu 23:00 server (50–55 phút trước giờ
  đóng thường). Can thiệp lịch của phép thử ở cả hai cấu hình là break dài.
  Đường H1 nhảy >2 giờ trong vị thế hoặc thiếu H1 tại cutoff: ghi unresolved,
  không bịa fill. Không chứng nhận lịch nghỉ ngoại lệ hay news theo năm.
- SL/TP theo H1 Bid OHLC với Ask dựng bằng spread cố định. Trong cùng một
  bar chưa biết thứ tự, ưu tiên SL. Gap mở phiên chạm SL khớp theo open có
  trượt; TP limit khớp tại mức mục tiêu. Dùng mốc cuối bar cho PnL của stop
  intrabar; nếu stop xảy ra ngay tại open dùng mốc open. Mark-to-market
  tại H1 close bằng giá thanh lý, tính phí và swap đã tích lũy.
- Base-Real spread London trung vị và 0 slippage thêm. Stress-Real giữ
  0,20 USD/oz mỗi phía market/stop của vàng, 0,75 điểm của US500 và 0,20 pip
  mỗi phía FX (mức EURUSD B0 dùng chung, bảo thủ hơn proxy 0,10 pip của một
  số lane). TP limit 0 slippage. FX 5 USD/lot RT, US500 0, vàng 0,0007%
  notional mỗi phía theo giá fill. Swap theo point và side audit `36f1535` tại
  00:00 broker, ngày tính fees là ngày broker vừa kết thúc, hệ số 3 theo spec.
  JPY quy đổi theo USDJPY H1 causal. Margin dùng mức 1 lot quan sát `36f1535`
  và đối chiếu USD notional lịch sử theo leverage mã, lấy phía cao hơn.
- Đối chứng cùng tín hiệu và stop/exit, thêm cutoff 20:30 UTC mỗi ngày. Dùng
  H1 open 20:00 UTC trước cutoff, quy đổi bằng giả định broker New York+7h
  cho cả giai đoạn. Đọc gap giữa mốc theo dữ liệu có sẵn, ghi rõ xấp xỉ 30 phút.
  PnL delta báo giữa hai policy và thêm cặp cùng intent để tách đổi cohort.
- Risk cố định 0,50% vốn danh nghĩa 10k và 50k. Sizing dùng lỗ tại stop gồm
  giá fill, phí, slippage, làm tròn xuống lot 0,01. Portfolio chặn khi tổng
  margin ước tính vượt 100% vốn và gộp lịch H1, không compounding. R theo
  ngân sách danh nghĩa, USD chính xác theo lot từng quy mô. Corr theo equity
  PnL ngày server, đồng bộ ngày và các ngày 0. Max DD từ H1 close/realized,
  chưa đo intrabar equity hay DD rule tài khoản. Top 5/10 chia tổng lãi
  dương và báo net bỏ các lệnh đó để tránh mẫu số gần 0.
- Mức tối thiểu cho PROMISING: stress dương ở cả hai cụm, ≥15R/năm và
  H1 portfolio DD ≤20R ở 10k, net vẫn dương bỏ top 10. 30R/năm là mốc kinh tế
  đích, không phải chứng nhận qua Challenge. Cửa Stage-0 giữ riêng theo quy
  ước skill gồm dương từng năm, gross đủ bù ma sát, median friction/stop ≤12%
  và giữ ≥50% intent. Markout net stress trung bình phải lớn hơn ma sát thực
  thi trung bình trên cùng mẫu. Ba họ được đo SL-active theo chỉ thị, kết quả trên họ
  rớt Stage-0 là chẩn đoán. Không đổi cấu hình sau khi thấy giá trị kinh tế.
