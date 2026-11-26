# US500 V16 · Bỏ trượt giá có đủ để giữ lại ứng viên?

**Gác kho US500 intraday V16 đã thử.** Hạ trượt từ 0,75 về 0 điểm/phía
làm số cấu hình dương ở cả hai cụm tăng từ 4 lên 14. Tuy vậy, 0/98
vừa đủ nhịp vừa dương ở cả hai cụm. Cấu hình có cụm yếu tốt nhất ở mức
0 chỉ đạt **109,91 USD/năm** và **20,7 lệnh/năm** ở cụm 2018–2020.
Ngay ở midpoint trước mọi chi phí, điểm cao nhất của cụm yếu là
**288,32 USD/năm**. Cả hai số đều ở xa cổng nghiên cứu 1.000 USD/năm.
Không có cấu hình được chọn sang mô phỏng đường stop hoặc tài khoản.
BASE_GUARD giữ NOT_QUALIFIED.

## Phễu qua ba mức phí

Chỉ đọc 98 cấu hình endpoint V16 từ 202 dòng đã đăng ký. Gộp 92 cặp
P0/P1 và 6 bộ P0/P1/P2 cùng endpoint thành 98 hồ sơ, giữ 104 alias.
Phạm vi 2018–2020 và 2021–2023. Lấy lại lịch, cửa sổ entry, hướng lệnh,
SL tự nhiên, cutoff và giá Open M1 Bid/Ask gốc. Commission giữ 0,
funding giữ theo mô hình gốc, cap ma sát tại entry giữ 12%.
Số lot tham chiếu là 150 USD chia SL tự nhiên tính theo điểm, làm tròn
xuống 0,01 lot với 1 USD/điểm/lot. Trượt giá chỉ tác động phí và
việc qua cap. Trên lệnh được nhận ở nhiều kịch bản, lot giữ nguyên.
[Đối chứng commission](PROP-US500-TARGET-FEE-RESULTS-20261119.md) ·
[Protocol V16](GAP-IMMUNE-MULTIASSET-V16-PROTOCOL-20261116.md).

| Chỉ số trên 98 cấu hình | 0,75 điểm/phía | 0,25 điểm/phía | 0 điểm/phía |
| --- | ---: | ---: | ---: |
| Có ≥99% endpoint định giá được trong cả hai cụm | 98 | 98 | 98 |
| Thêm điều kiện ≥40 lệnh/năm và giữ ≥50% cơ hội, mỗi cụm | 20 | 20 | 20 |
| Sau bước trên, dương net cả hai cụm | 0 | 0 | 0 |
| Đạt ≥1.000 USD/năm ở cả hai cụm, kể cả bỏ yêu cầu nhịp | 0 | 0 | 0 |
| Dương cả hai cụm khi xét cả 98, giữ nguyên sổ 0,75 | 4 | 10 | 14 |
| Dương cả hai cụm khi xét cả 98, chạy lại cổng 12% | 4 | 10 | 14 |
| Cụm yếu tốt nhất khi chạy lại cổng, USD/năm | +16,44 | +65,24 | +109,91 |
| Cụm yếu tốt nhất trong nhóm 20 đủ nhịp, USD/năm | −189,24 | −76,91 | −5,86 |

Ở mỗi kịch bản, 24 cấu hình dương cả hai cụm ở midpoint, còn 14 sau
spread trước funding và slippage. Các tập dương net lồng nhau trong
ba kịch bản. 4 cấu hình chịu được mức 0,75, thêm 6 dương từ mức 0,25,
thêm 4 chỉ dương ở mức 0 trong các điểm đo đã khóa. Chúng thuộc F1
và F4. Đếm theo công thức trước khi đổi bội số SL thì còn 2, 5 và 7,
lần lượt. Bội số SL thay đổi quy mô lot, nên các dòng cùng tín hiệu
có thể cho số tiền khác.

| Trượt/phía | Lượt qua cap theo cấu hình, cụm đầu / sau | Lượt mới so với 0,75 | Số cơ hội khác nhau theo giờ tín hiệu, giờ vào và chiều |
| --- | ---: | ---: | ---: |
| 0,75 | 7.356 / 12.634 | 0 / 0 | 1.418 / 2.276 |
| 0,25 | 8.313 / 13.990 | 957 / 1.356 | 1.530 / 2.456 |
| 0 | 8.375 / 14.114 | 1.019 / 1.480 | 1.546 / 2.474 |

Mọi lượt qua cap có giá tại endpoint theo quy tắc lấy quote quan sát đầu
tiên sau cutoff. Ở mức 0, có 252 / 74 lượt theo cấu hình dùng quote muộn
hơn một phút. Funding gốc vẫn tính nếu quote kéo qua ngày UTC. Độ phủ
endpoint vì vậy chỉ nói có giá để định giá, còn tính liên tục của đường
giá, khả năng khớp đúng giờ và lần chạm SL vẫn chưa được kiểm. Các cơ hội
qua cap mới ở cả hai cụm chỉ đến từ F2/F5. Chúng không tạo thêm cấu hình
dương cả hai cụm so với phép hoàn trượt trên sổ cũ. Đếm ngày vào UTC đã
khử trùng ở mức 0 còn 658 / 757. Báo cáo JSON có overlap riêng F1–F5.
Không cộng PnL giữa các cấu hình có chung cơ hội thành đường vốn.

## Phí hòa vốn trên cùng lệnh và cùng lot

Ví dụ đại diện là F1 H4, cửa sổ 10 nến, impulse 0,5, multiple 1, DAY P0.
Đây là cấu hình có cụm yếu cao nhất ở mức 0. Cả ba mức phí dùng đúng
62 / 143 lệnh đã định giá và 536,14 / 1.304,48 lot-phía. Báo cáo bảng
này theo tổng từng cụm ba năm.

| Khoản đo | 2018–2020 | 2021–2023 |
| --- | ---: | ---: |
| Gross tại midpoint | +465,53 USD | +1.315,50 USD |
| Phí spread suy từ giá giữa và giá khớp hai phía, có làm tròn | 126,36 USD | 317,17 USD |
| Gross sau spread | +339,16 USD | +998,33 USD |
| Funding | −9,42 USD | 0 USD |
| Trượt 0,75 điểm/phía | 402,11 USD | 978,36 USD |
| Net ở 0,75 / 0,25 / 0 điểm/phía | −72,36 / +195,71 / +329,74 USD | +19,97 / +672,21 / +998,33 USD |
| Trượt hòa vốn, điểm/phía | +0,615 | +0,765 |
| Phí hòa vốn tương đương, bp/phía | +2,077 | +1,824 |
| Trượt để đạt +1.000 USD/năm, điểm/phía | −4,981 | −1,534 |
| Phí tương đương để đạt +1.000 USD/năm, bp/phía | −16,816 | −3,658 |

Hòa vốn là tiền sau spread và funding chia tổng lot đã khớp hai phía.
Để đạt 1.000 USD/năm, lấy tử số đó trừ 3.000 USD cho mỗi cụm ba năm
rồi mới chia. Mức âm có nghĩa cần khớp tốt hơn giá Bid/Ask bình quân
từng ấy điểm trên cùng sổ mới chạm mục tiêu. Cột bp tính khoản tiền
tương đương trên giá trị midpoint của từng phía và cùng lot. Ngưỡng
hòa vốn chỉ dùng để diễn giải sổ cố định. Ở phép đổi cổng 12%, tập lệnh
mở rộng nên kết quả có thể tăng hoặc giảm. Các mức 0 và 0,25 là giả định
mô phỏng. Cần fill thực để biết mức trượt của tài khoản đích.

## Quyết định và đối soát

Trượt giá giải thích vì sao một số cấu hình đổi dấu. Ở kho V16 này, nó
không giải thích khoảng cách đến mục tiêu. Tổng lợi nhuận trước mọi phí ở
cụm yếu cũng mới 288,32 USD/năm ở cấu hình tối đa hóa chỉ số đó. Dừng
đào sâu kho này theo hướng hạ phí, dành công nghiên cứu cho cơ chế mới.
Kết luận giới hạn ở 98 cấu hình và phép đo endpoint đã đăng ký. Sổ luôn
BUY gần trọn phiên dương khoảng 83 USD sau riêng spread toàn kỳ là một
đối chứng theo lịch riêng. S-Sign vẫn thiếu sổ dự báo có timestamp.
[Cửa sổ cash](PROP-US500-CASH-SESSION-20261119.md) ·
[Kiểm nguồn S-Sign](PROP-US500-SPY-S-SIGN-PREFLIGHT-20261119.md).

Receipt local tại ai-engine-jobs/prop-us500-v16-slippage-20261119 trên ổ E.
Registration khóa trước phép đo. Chạy run_v16.py với PYTHONPATH trỏ tới
tooling/ai-engines và uv offline có numpy, zstandard, tzdata. Kiểm lại
196 cặp mã/cụm ở mức 0,75 theo receipt cũ, số vào/giá thiếu/net và phép
phân rã của cả ba mức. Đọc lại JSON nén kèm SHA256, đối soát số học bằng
Decimal. Lượt gộp overlap đầu tiên nhóm quá chi tiết theo từng cấu hình.
Đã sửa thành F1–F5 và xác nhận toàn bộ kết quả tiền giữ nguyên giữa hai
lượt. Giữ receipt lần đầu để đối chiếu. Chỉ dùng nguồn giá 2018–2023.
