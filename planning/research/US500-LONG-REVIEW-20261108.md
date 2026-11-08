# US500 RSI: lịch sử dài không xác nhận kết quả tốt của 2022–2024

**Hai phiên bản không đạt tiêu chí giữ lại đã đăng ký.** Không giảm phí, tăng
risk, loại năm thua hoặc đổi cutoff để cứu kết quả. Bản gốc có hai năm không
khớp được lệnh; đó là giới hạn vận hành của dữ liệu, không phải năm có edge bằng 0.

[Protocol RSI gốc](US500-CASH-RSI-LONG-VALIDATION-20261108.md),
[bản preclose và sentinel](US500-PRECLOSE-SENTINEL-LONG-20261108.md),
[chính sách nguồn thiếu](INDEX-HISTORY-PARTIAL-AVAILABILITY-20261108.md).
Mỗi năm là một tài khoản mô phỏng riêng 10.000 USD, planned risk 25 USD/lệnh.
Tổng dưới đây là tổng net của các annual books, **không CAGR hoặc tài khoản
được vận hành liên tục**. Net gồm cả vị thế còn mở cuối mẫu.

## Kết quả, USD

| Năm | RSI chuẩn | RSI stress | Lệnh vào | Preclose chuẩn | Preclose stress | Lệnh vào |
|---|---:|---:|---:|---:|---:|---:|
| 2013 | 47,71 | 33,73 | 4 | 40,61 | 28,11 | 3 |
| 2014 | −19,63 | −57,04 | 15 | −28,62 | −64,94 | 15 |
| 2015 | 13,91 | 2,98 | 4 | −83,02 | −127,70 | 22 |
| 2016 | 0 | 0 | 0 | 38,09 | 1,50 | 13 |
| 2017 | 0 | 0 | 0 | −11,16 | −32,02 | 8 |
| 2018 | −74,38 | −111,40 | 20 | −106,55 | −143,80 | 27 |
| 2019 | −115,89 | −129,91 | 12 | −99,13 | −114,20 | 12 |
| 2020 | −9,28 | −19,61 | 12 | −39,79 | −49,12 | 12 |
| 2021 | 23,44 | 10,27 | 10 | 64,42 | 50,58 | 11 |
| 2022 | 38,25 | 21,09 | 25 | 13,78 | −0,12 | 25 |
| 2023 | 25,72 | 6,43 | 17 | 45,88 | 26,04 | 19 |
| 2024 | 93,92 | 77,77 | 17 | 93,40 | 74,46 | 19 |
| **Tổng các books** | **23,77** | **−165,69** | **136** | **−72,09** | **−351,21** | **186** |

RSI gốc: 6/12 năm stress dương; stress theo bốn block ba năm lần lượt
−20,33 / −111,40 / −139,25 / +105,29 USD. Preclose: 5/12 năm dương;
−164,53 / −174,32 / −112,74 / +100,38 USD. Cả hai không đạt heuristic
≥8/12 năm dương và cả bốn block dương. Heuristic không là kiểm định thống kê
hoặc bằng chứng loại cả họ mean reversion.

RSI có 135 lệnh đã đóng và 1 lệnh mở; preclose 184 đóng và 2 mở, mỗi kịch bản.
Winrate của lệnh đã đóng ở stress khoảng 54,8% và 54,9%, nhưng mean net chỉ
−0,049R và −0,076R/lệnh: **winrate trên 50% vẫn có thể lỗ sau phí**.
Funding stress của hai tập books là 249,52 / 370,04 USD. Đây là kịch bản phí
đã khai báo, chưa phải lịch sử swap/dividend của tài khoản quỹ đích.

## Review quy trình và giới hạn

- V6 hoàn tất 74/74 phần quarter-side trong 2.200,38 giây; kế thừa các phần
  đã seal và cache từng request. Có 11 request không khả dụng, không điền giá;
  raw sides/unpaired rows/availability journals được giữ. Hoàn tất tải scope
  không có nghĩa nguồn đầy đủ. V1–V5 và mọi lỗi cũ vẫn còn.
- Cash minutes thiếu theo năm: 2013: 5.067; 2014: 120; 2015: 416;
  2016: 1.170; 2017: 855; 2020: 1.170; 2023: 46. Các năm còn lại có đủ
  timestamp cash, chưa chứng minh quote mới hoặc khả năng khớp.
- Có tổng 16 bản ghi entry/exit stress với cả hai side volume bằng 0, thuộc
  2014/2015/2018 khi cộng hai phiên bản; cùng timestamp có thể bị đếm lại.
  Không tự kết luận volume 0 là giá giả, nhưng không dùng chúng để chứng nhận
  broker fills. M1 stops/overnight missing paths vẫn chưa native tick/prop DD.
- Tái hiện ba lỗi ở funded-book reviewer: sửa `entry_fill` mà net giữ nguyên
  vẫn qua; trùng position ID bị dictionary che mất; `closed_trades` sai không
  bị bắt. Đã vá kiểm giá entry (cả Bid/Ask của open position), uniqueness và
  bộ đếm. Chín tests liên quan đạt sau vá; ba negative regressions đã fail
  trước vá. Fixture open-book lần đầu thiếu trường close, đã bổ sung fixture;
  không che lỗi bằng nới assertion hoặc sửa numeric outcome.
- Bộ kiểm đã sửa đọc lại **24 annual books / 72 scenario files** gồm 24 null
  controls trong 24,68 giây: source snapshots, protocol/calendar, raw hashes,
  entry/SL/lot/cost/funding/cash/floating khớp. **0 simulation/network calls**.
  Chưa có independent human/model sign-off hoặc selection-adjusted edge test.

Artifacts ở private campaign `execution-v1/us500-long-selection-review-v1`;
manifest bind reviewer/driver và hai parent results. Parent numerical attempts
`us500-rsi-long-v3` và `us500-preclose-long-v1` giữ source/data/result snapshots;
không thay pin cũ hoặc viết đè kết quả để nâng acceptance.

## Bước tiếp

Ngừng thử thêm cutoff/threshold cho hai bản này. Dùng lại lịch sử đã seal cho
[hướng R009 xu hướng tháng](US500-MONTHLY-TREND-PREPARATION-20261108.md),
có long-only benchmark và tài khoản mô phỏng liên tục để tách câu hỏi mới.
Không lấy history đã nhìn làm unseen OOS. C1 chưa đạt; C2 mới có thêm bằng
chứng trong scope, vẫn thiếu native index path/target contract và các cửa
edge/prop/forward. Không mở 2025+, broker hoặc mua challenge.
