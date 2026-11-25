# EURUSD F2 · Stop, phí hay tín hiệu sai hướng?

**Gác EURUSD F2 và phương án đảo chiều.** Trên toàn bộ tín hiệu có cặp giá
vào/ra, đảo hướng lỗ sau phí trong cả sáu năm. Trên 300 lệnh gốc có đường
stop ở 2018–2020, giữ tới hạn thay vì dùng stop làm tổng lỗ lớn hơn 5,58R.
Dữ liệu thiếu chọn lệch mẫu có stop. Kho tick phân giải được 1 trong 65
đường thiếu của tập fit, lệnh đó chạm stop. `BASE_GUARD` vẫn
`NOT_QUALIFIED`.

## 1. Tập tín hiệu và cách đo

Đúng cấu hình `EURUSD|F2:sma=20:pullback=2:structure=4|24H|P0`, được chọn
chẩn đoán sau khi đã biết kết quả âm. H4 xác định hướng bằng vị trí close
so với SMA20 và độ dốc SMA so với ba nến H4 trước. Trong hai nến H1 trước
phải có nến ngược hướng, rồi nến H1 hiện tại đóng vượt cực trị nến liền
trước theo hướng H4. Stop gốc đặt ở cực trị bốn nến H1 gồm cả nến tín
hiệu, đệm 0,1 × ATR14 H4 đã biết. Giữ tín hiệu đầu tiên mỗi ngày UTC.
Dùng nguyên entry, hạn +24h có clamp lịch đã lưu, phí và stop gốc.
Hạn clamp ngắn hơn 24h ở 161/699 và 156/677 cặp giá. Cửa sổ lấy quote
tối đa 60 giây. Cả hai cụm thuộc Development đã từng xem. Chỉ dùng
2018–2020 để xét điều kiện mở ứng viên, dùng 2021–2023 để đối chiếu.
[V10](ENTERPRISE-ALPHA-V10-PROTOCOL-20261115.md) ·
[V12](SL-ACTIVE-ENSEMBLE-V12-PROTOCOL-20261115.md) ·
[Phép chọn trước đó](PROP-PAST-ONLY-SLEEVE-SELECTION-20261119.md).

Đo từ QDM M1 Bid có UTC, Ask giả định cách Bid 1 pip. Ma sát vòng lệnh
gồm 1 pip spread, 0,7 pip commission, 0,2 pip slippage. Financing theo
mô hình gốc là 4 pip mỗi rollover 22:00 UTC, thứ Tư tính ba lần. So
midpoint, Bid/Ask rồi net trên cùng cặp giá. R trong chẩn đoán chuẩn hóa
cả hai chiều theo khoảng stop gốc biết lúc vào, nên chưa là R của một
chiến lược đảo chiều có stop riêng. Phí lịch sử là giả định mô phỏng.

## 2. Phân rã lỗ của F2 gốc

| Cụm | Tín hiệu | Qua phí và lot | Được cấp chỗ | Có đường stop | Thiếu đường stop | P0 đã định giá |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018–2020 | 701 | 407 | 365 | 300 | 65 | −130,75R |
| 2021–2023 | 678 | 515 | 432 | 224 | 208 | −160,75R |

Giữ quy tắc 12% phí/stop, lot ở risk định mức 150 USD và tối đa một vị thế
đang mở từ phép chọn trước. Vị thế thiếu đường giữ chỗ tới deadline. Với
365 danh tính đã cố định, 65 lệnh chưa rõ phải đạt bình quân
**+2,01156R/lệnh** để bù −130,75158R. Nếu biết stop xảy ra sớm hơn,
lượt vào sau có thể thay đổi do chỗ risk được giải phóng.

**Cầu nối chỉ trên cùng các lệnh có đủ cả endpoint lẫn stop.** R cộng dồn
với khoảng stop riêng của mỗi lệnh. Dấu dương ở dòng tác động stop có
nghĩa là giảm phần lỗ so với đóng ở endpoint.

| Thành phần | 2018–2020 · cùng 300 lệnh | 2021–2023 · cùng 224 lệnh |
| --- | ---: | ---: |
| Midpoint tới hạn, theo hướng gốc | −54,76R | −168,73R |
| Spread | −12,56R | −9,41R |
| Commission | −8,79R | −6,58R |
| Slippage | −2,51R | −1,88R |
| Financing nếu giữ tới hạn | −57,71R | −37,13R |
| **Net tại hạn** | **−136,33R** | **−223,73R** |
| Đổi giá thoát do stop | −39,53R | +26,64R |
| Giảm financing do thoát sớm | +45,11R | +36,34R |
| **Net với stop P0** | **−130,75R** | **−160,75R** |

Trong mẫu fit đã nhận, 211 lệnh có stop sớm. 139 lệnh trong nhóm này
có đủ đường tới hạn, 72 lệnh có stop trước khi đường tới hạn bị thiếu.
89 lệnh có giá còn lại tới hạn. 65 lệnh chưa rõ đều có cặp giá vào/ra,
nhưng thiếu một phần đường sau entry. Các nhóm cho kết quả khác nhau:

| Fit 2018–2020 · lệnh được cấp chỗ | Số lệnh có cặp giá | Mid theo hướng gốc tại hạn, pip/lệnh | Net gốc tại hạn, pip/lệnh |
| --- | ---: | ---: | ---: |
| Stop sớm, đường tới hạn đầy đủ | 139 | −20,68 | −27,16 |
| Stop sớm, thiếu đường sau stop | 72 | −19,51 | −27,69 |
| Có kết quả P0 còn lại | 89 | +35,38 | +30,43 |
| Thiếu sau entry, chưa rõ stop hay giữ tới hạn | 65 | +16,56 | +8,57 |

Nếu chỉ nhìn nhóm đã biết chạm stop, đảo hướng ở endpoint có vẻ lời
**+13,22 pip/lệnh**. Sổ thô giữ cả nhóm chưa rõ stop, và chọn được nhóm
stop sớm chỉ sau khi biết diễn biến. Vì vậy bảng này dùng để nhận diện
lệch mẫu. Net tại hạn của 65 lệnh không định giá được stop của chúng.

### Đối chiếu tick trong đúng 65 đoạn thiếu của tập fit

Kiểm cache QDM `EURUSD_TICK_TW` theo seal lịch sử, lệnh xuất UTC và
schema Bid/Ask. Cả 65 cặp đầu/cuối khớp từng mức Bid ở hai cách xuất
dữ liệu. Spread tick trung vị 0,30 pip ở entry và exit. Khi thay Ask
proxy bằng Ask tick trong phép đo endpoint riêng, net hướng gốc tăng
từ +8,57 lên +9,22 pip/lệnh trên đúng 65 cặp.

Một đường có đủ dữ liệu đến lần chạm stop đầu tiên, đạt −21,80 pip
sau phí (−1,005R theo stop gốc). 64 đường vẫn thiếu phút trước lúc
thoát có thể định giá. Trong số đó có 17 đường ghi được tick vượt
stop sau phần thiếu, nên thời điểm và giá chạm đầu tiên vẫn chưa rõ.
Không nối các giá tick này vào sổ legacy. Hai nguồn xuất qua QDM cho
bằng chứng đối chiếu giá, chưa xác nhận tính độc lập hay fill tài khoản
đích. Không có phép sửa sổ hay mô phỏng overlap lại từ 65 đường này.

## 3. Đảo chiều trên toàn bộ tín hiệu, trước khi lọc stop

Bảng dùng cùng giờ và cặp quote cho tất cả hướng, gồm cả các lệnh chưa
rõ đường stop. Số pip là trung bình mỗi tín hiệu có giá.

| Năm | Cặp giá / tín hiệu | Mid hướng gốc | Net hướng gốc | Mid đảo | Net đảo | Luôn BUY net | Luôn SELL net | Đối chứng tuần net |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 232/232 | −4,62 | −11,20 | +4,62 | −1,95 | −8,22 | −4,93 | −10,18 |
| 2019 | 236/237 | +0,55 | −5,96 | −0,55 | −7,06 | −9,15 | −3,87 | −11,33 |
| 2020 | 231/232 | +9,38 | +2,77 | −9,38 | −15,99 | −2,63 | −10,59 | −19,15 |
| 2021 | 220/220 | −1,07 | −7,64 | +1,07 | −5,51 | −7,76 | −5,39 | −10,83 |
| 2022 | 226/227 | −0,29 | −6,84 | +0,29 | −6,27 | −6,87 | −6,24 | −17,17 |
| 2023 | 231/231 | −3,39 | −10,04 | +3,39 | −3,25 | −8,20 | −5,09 | −10,98 |

| Cụm | Mean mid đảo | Mean net đảo, CI 95% theo tuần | Mean net đảo theo R gốc | Lợi thế so đối chứng tuần, CI 95% | Net đảo bỏ 3 tuần lời nhất |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018–2020 | −1,75 pip | −8,32 [−12,38; −4,22] pip | −0,471R | +5,22 [+2,96; +7,69] pip | −9,55 pip |
| 2021–2023 | +1,60 pip | −4,99 [−9,07; −1,01] pip | −0,288R | +8,01 [+5,66; +10,54] pip | −6,08 pip |

Hoán đổi 9.999 lần trong tuần, giữ số BUY và SELL từng tuần. Có 94/157
và 73/156 tuần có cả hai chiều. Bootstrap 9.999 lần theo cụm tuần, dùng
seed đã khóa. Giá trị p một phía **0,0001** ở hai cụm đo mức vượt đường
hoán đổi. Đường đối chứng lỗ nhiều hơn, và chiều đảo vẫn lỗ tuyệt đối
ở cả sáu năm. Cụm fit có mid đảo âm và net vẫn **−3,65 pip** nếu giả sử
financing bằng 0, giữ ma sát khớp lệnh. Khoản lỗ cụm fit cũng lớn hơn
mức 1 pip có thể hoàn lại nếu chỉ thay spread proxy bằng spread bằng 0,
với các yếu tố khác giữ nguyên.

## 4. Quyết định và bằng chứng

Chiều đảo trượt cổng lợi nhuận sau phí theo từng năm, khoảng tin cậy
net và độ nhạy bỏ ba tuần lớn nhất. Dừng trước bước dựng stop đối ứng,
tái lập vị thế hay chạy replay tài khoản. Kết luận về Challenge giữ
nguyên. Phép đo chứng minh không có cơ sở đi tiếp cho luật đối ứng này
với cùng thời điểm, horizon và phí đã khóa. Đường stop gốc còn thiếu
64/65 vị thế qua phép đối chiếu fit, và 208 vị thế ở ba năm kế tiếp
chỉ mang trạng thái thiếu đường V12 trong lượt này.

Bằng chứng trong `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-eurusd-f2-direction-20261119/`.
Đối chiếu hash V10/V11/V12, timestamp/side/stop, cặp Bid/Ask tại hạn,
tổng net R với sổ parent và đồng nhất phương trình phí trên mẫu chung.
Verifier đọc lại sổ nén Zstd, đối chiếu từng dấu chiều, coverage và sổ
tick riêng. Dữ liệu đọc nằm trong Development và warmup đã niêm phong.

| Artifact | SHA256 |
| --- | --- |
| `registration.md` | `06e32c7a438ffe6475fece6122e5ce22bed5c39e3a36f52a52a229ea08d0ad65` |
| `2018-ledger.private.json.zst` | `eb30f9f89a5fb9396a537c9fe76dc5ce6abf770a962f3231a8880a0c13b4bf46` |
| `2021-ledger.private.json.zst` | `f12c7f3f23d2599b2a34dd9771f3b389235cf3968f9a292c4d8c1d4bdf6ce9be` |
| `tick-witness-registration.md` | `74d0b1d8e5ced037ef6ee7bee3034ef7d15194ffb695865eac12dc506a19c8a2` |
| `tick-witness-ledger.private.json.zst` | `3750d4eab0bc7deffcc10c96ff72a29708a5b755b73cd8a73ef89146fca611b5` |
