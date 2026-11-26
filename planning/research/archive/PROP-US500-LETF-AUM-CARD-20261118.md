# US500 sát giờ đóng cửa — kiểm giá trị bổ sung của quy mô ETF

Một phiên bản `US500-LETF-AUM`, Development 2018–2023. Dùng UPRO (+3x)
và SPXU (−3x) của cùng nhà phát hành, cùng chỉ số. Với tài sản đầu ngày
(A), leverage (L), và return chỉ số (r), trong mô hình không có dòng
vốn hay điều chỉnh vị thế sớm, phần đổi exposure để về target xấp xỉ
(L(L-1)Ar). Hai hệ số lần lượt là 6 và 12. Dấu luôn trùng momentum
khi tổng tài sản dương. Chỉ kiểm thông tin **cường độ tương đối** qua
(K = 6 A_{UPRO} + 12 A_{SPXU}). Đây là proxy cơ học từ hai quỹ,
không ước lượng tiền mua/bán thực, thời gian hedge hoặc creations.
Hai nghiên cứu có kết luận khác nhau khi xét dòng vốn và tách kênh tác động.
[Barbon và cộng sự](https://wp.lancs.ac.uk/fofi2022/files/2022/08/FoFI-2022-027-Mathis-Moerke.pdf) ·
[Ivanov–Lenkey](https://pure.psu.edu/en/publications/do-leveraged-etfs-really-amplify-late-day-returns-and-volatility/)

## Quy tắc và đối chứng

- Lịch NYSE 2018–2023 đã có trong repo, theo America/New_York. Chỉ phiên
  đủ 390 phút theo lịch. Return lấy US500 Bid Close 15:29 so với Bid
  Close phút cuối phiên cash trước, gồm cả overnight. Quyết định 15:30,
  BUY nếu dương, SELL nếu âm. Bằng 0 đứng ngoài. Fill M1 Open đúng 15:31.
  Đo markout tới M1 Open đúng 15:59. Cùng cửa sổ với thử close-momentum
  trước đây. Dùng return tới 15:29 để đại diện biến động tạo nhu cầu
  rebalance, thay vì dùng dấu của 30 phút đầu như thử nghiệm cũ.
  [Đối chứng lịch sử](US500-CLOSE-MOMENTUM-RESULTS-20261108.md)
- Dùng cột Assets Under Management của ProShares, tính (K) từ đúng
  phiên cash thứ hai trước ngày vào. Độ trễ để chừa nguyên một phiên
  cho cập nhật sau NAV 16:00, không có vintage timestamp từng dòng.
  Chọn ngày có (K) lớn hơn trung vị (K) của 20 phiên liền trước
  phiên quan sát (K). Đòi đủ hai quỹ và đủ 20 phiên. Không forward-fill
  qua ngày thiếu. So (NAV 	imes shares) với AUM làm kiểm tra đơn vị.
  Xem các split đã công bố, dùng AUM vì phép tách cổ phần không đổi
  tổng tài sản. Hai tệp NAV có giá và AUM trong 2018–2023.
  [ProShares Data Downloads](https://prod.proshares.com/resources/data-downloads) ·
  [UPRO split 2022](https://prod.proshares.com/press-releases/proshares-announces-etf-share-splits-122021) ·
  [SPXU reverse split 2021](https://www.proshares.com/press-releases/proshares-announces-etf-share-splits-10621)
- Đối chứng giá-only luôn theo dấu return trên cùng tập đủ thông tin
  trước entry, bỏ điều kiện AUM cao. Khi so phần thêm từ ETF, cân lại
  tần suất của đối chứng theo từng ô năm, chiều, độ lớn return (bước
  25 bp, gom mọi trị ≥200 bp một ô) và ATR14 quá khứ / prior close
  (bước 50 bp, gom ≥400 bp một ô). Dùng bình quân tất cả markout có giá
  trong ô của đối chứng, cân bằng đúng số ngày ETF có giá ở ô đó.
  Ô cần ít nhất hai ngày đối chứng không được ETF chọn và có đủ giá.
  Báo tỷ lệ tín hiệu ETF có đối chứng, cùng chênh lệch mức biến động
  thực tế trong các ô. Đây là đối chứng để quy thuộc lợi ích, không
  triển khai reweight theo cả năm như bot thời gian thực.
- Thiết kế stop như bài close cũ. Khoảng SL bằng 0,25 lần bình quân TR
  Bid của 14 phiên cash quá khứ liền nhau, cần đủ mọi phút theo lịch và
  close phiên trước để tính TR, kể cả phiên ngắn. Khoảng này đo khả
  năng chịu phí, chưa kích hoạt exit SL. Nếu thiếu TR thì vẫn tính
  markout nếu các giá cần thiết có mặt. BUY vào Ask, ra Bid. SELL vào
  Bid, ra Ask. Commission 0,50 USD/lot/side tại 1 USD/point/lot, trượt
  stress 0,75 point/side, cộng 2,50 points/vòng ngoài spread. So tổng
  ma sát là 2,50 cộng hai nửa spread tại entry/exit. Swap bằng 0.
- Stage‑0 cần từng năm ≥40 tín hiệu, ≥99% có giá hai đầu, median phí /
  median stop ≤12%, giữ ≥50% qua cap và mean net dương, ít nhất bằng
  median phí stress của năm. Cần thêm lợi ích **dương sau phí** so
  với đối chứng trên vùng có đủ mẫu, ít nhất 4/6 năm và dương gộp
  theo số tín hiệu được so, với vùng so được ≥90% toàn mẫu có giá.
  Biên dưới bootstrap theo tháng được báo để đọc bất định. Chỉ khi
  qua toàn bộ thì replay so BASE_GUARD với cùng vốn và risk. Nếu
  không chứng minh được giá trị thêm, gác công thức và dùng duy nhất
  một phép thử cơ chế độc lập có card riêng. Giá 2024–2026 giữ đóng.
