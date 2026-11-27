# V13 — Đã định giá lại; chưa đủ điều kiện mở Validation

**No-Go ở Development theo cổng đã đăng ký.** 19/19 cấu hình trọng tâm được định giá
đủ 2,156/2,156 lượt theo mô hình quote kế tiếp. Tổ hợp
cơ học còn 3 nhánh, SYM +50,232R / ASYM +52,386R trong 2018–2023,
nhưng 2018 có 43, 2019 có 47 tín hiệu, dưới sàn 50 **mỗi năm**.
Không thay cổng sau khi thấy kết quả. 2024–2026 vẫn đóng; không chạy lifecycle 9 năm.
Giá trị dương này có điều kiện: không có component nào chứng minh đủ đường giá nguồn.

[Protocol](PATH-RESOLUTION-AND-DEDUP-V13-PROTOCOL-20261115.md) freeze `5d0f7a5`;
code trước outcome `edd5e46`. PR #91 merge `ad362ea`; branch V12 đã xóa.
Private job: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/path-resolution-and-dedup-v13-20261115`. Compact JSON cùng tên giữ IDs, annuals và SHA256.

## 1. Pháp y 28 cấu hình và 19 trường hợp trọng tâm

V12: 2,715/3,179 lượt định giá; V13: 3,165/3,179. Khôi phục 450 lượt bị chặn.
26/28 cells định giá toàn bộ; 2 EURUSD F5 H1/n10 còn 7 lượt sai clock mỗi cell:
entry sau hạn đóng DAY; một lượt còn chậm qua cuối tuần. Không sửa tín hiệu để cứu chúng.
Các số này đếm lượt theo cấu hình; nhiều mode dùng lại cùng tín hiệu, không phải mẫu độc lập.

28 cells đã được chọn sau khi xem V12 trên 2.888 cells. V13 không reset lịch sử
lựa chọn này; positive point estimate không phải kiểm định edge sau multiple testing.

Trong các đường V12 bị chặn: 467 khoảng nghỉ/gap riêng, gồm 91 khoảng
chỉ là giờ nghỉ đã khai báo; 24 khoảng sát giờ nghỉ còn thiếu 1–2 phút ngoài lịch;
352 khoảng chỉ có phút nguồn không được xác minh. Tổng 434 phút chưa rõ + 6.900
phút nghỉ hàng ngày của vàng. Không có gap lễ/early-close chưa khai báo trong chính
cohort bị chặn này. Lịch 2018–2021 đã có guard từ V8; giả thuyết thiếu lịch là nguyên
nhân chính không được số liệu ủng hộ. EURUSD không có giờ nghỉ CME hàng ngày.

Nguồn FTMO lịch sử truy cập trực tiếp bị TLS timeout; MT5 URL thử trả 404.
Receipt được giữ. Giữ lịch guard đã đăng ký cùng correction 31/12/2021
(normal hours; vẫn giữ guard bảo thủ 16:58), không gọi lịch này là FTMO-certified.

**Cách xử lý:** giữ nguyên entry/SL/mode; stop vượt gap khớp tại open bất lợi cộng
phí stress. Hạn thoát thiếu quote chờ open kế tiếp; deadline trong giờ nghỉ vàng
chờ giờ mở lại và tính swap. Guard holiday/Friday khóa từ trước, không lùi đến
last quote bằng hindsight. Endpoint chỉ dùng open; không đọc high/low tương lai.
P1 chỉ có hiệu lực từ bar sau trigger. Stop qua open ghi nhận ngay thời điểm open.

**Giới hạn:** nếu thiếu một phút giữa phiên, giá có thể chạm SL rồi hồi ngay trong
phút đó. Open kế tiếp không chứng minh điều ngược lại và không là worst-case bound.
Auditor xác nhận mô phỏng khớp hợp đồng; không tạo ra dữ liệu đã mất.

Kiểm thêm native tick cache, chỉ các giờ Development liên quan: 376 gap chưa rõ,
48 gap có đầy đủ giờ tick đã admission và không có quote bên trong; 328 gap chưa có native tick hour trong manifest.
Đọc 37 giờ tick; không có trường hợp phát hiện tick bên trong gap M1 ở phần có giờ được admission.
Không download thêm, không thay source/matrices hoặc chạy lại tài chính. No-quote
trong cache được admission vẫn không chứng nhận feed broker chưa từng có giá khác.

`*` là 19 trường hợp chỉ vướng path ở V12. Cột phút = chưa xác minh / nghỉ đã khai báo.
Full Config ID giữ cả asset/recipe/horizon/mode để đối soát.

| Case | Config ID | Tổng | V12 đủ | V13 đủ | Phút ? / nghỉ | Kết luận |
|---|---|---|---|---|---|---|
| C01* | `XAUUSD\|F3:compression=NR:n=14:multiple=2\|DAY\|P0` | 104 | 94 | 104 | 24/0 | 2018:ECONOMIC, MEAN_BELOW004 |
| C02* | `XAUUSD\|F3:compression=NR:n=14:multiple=2\|DAY\|P1` | 104 | 94 | 104 | 24/0 | 2018:ECONOMIC, MEAN_BELOW004 |
| C03* | `XAUUSD\|F3:compression=NR:n=14:multiple=2\|48H\|P0` | 104 | 65 | 104 | 176/3720 | 2018:ECONOMIC, MEAN_BELOW004 |
| C04* | `XAUUSD\|F3:compression=NR:n=14:multiple=2\|48H\|P1` | 104 | 65 | 104 | 176/3660 | 2018:ECONOMIC, MEAN_BELOW004 |
| C05* | `XAUUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=1\|48H\|P0` | 74 | 61 | 74 | 47/1140 | scenario component |
| C06* | `XAUUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=1\|48H\|P1` | 74 | 61 | 74 | 47/1140 | scenario component |
| C07* | `XAUUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=2\|48H\|P1` | 74 | 59 | 74 | 52/1440 | scenario component |
| C08 | `XAUUSD\|F3:compression=BB:n=60:quantile=0.15:multiple=2\|24H\|P1` | 105 | 82 | 105 | 74/1380 | scenario component |
| C09* | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|DAY\|P0` | 95 | 89 | 95 | 9/0 | scenario component |
| C10* | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|DAY\|P1` | 95 | 89 | 95 | 9/0 | scenario component |
| C11* | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|24H\|P0` | 95 | 76 | 95 | 58/1080 | scenario component |
| C12* | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|24H\|P1` | 95 | 76 | 95 | 58/1080 | scenario component |
| C13* | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|48H\|P0` | 95 | 73 | 95 | 76/1680 | scenario component |
| C14* | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|48H\|P1` | 95 | 73 | 95 | 73/1560 | scenario component |
| C15 | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=2\|DAY\|P0` | 95 | 88 | 95 | 15/0 | MEAN_BELOW004 |
| C16 | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=2\|DAY\|P1` | 95 | 88 | 95 | 15/0 | MEAN_BELOW004 |
| C17 | `XAUUSD\|F4:hour=16:impulse=1:timing=MONTH:multiple=2\|DAY\|P0` | 50 | 47 | 50 | 4/0 | MEAN_BELOW004 |
| C18 | `XAUUSD\|F4:hour=16:impulse=1:timing=MONTH:multiple=2\|DAY\|P1` | 50 | 47 | 50 | 4/0 | MEAN_BELOW004 |
| C19 | `EURUSD\|F3:compression=NR:n=7:multiple=1\|DAY\|P1` | 193 | 172 | 193 | 36/0 | 2021:ECONOMIC, MEAN_BELOW004 |
| C20 | `EURUSD\|F3:compression=NR:n=14:multiple=1\|DAY\|P1` | 109 | 95 | 109 | 27/0 | MEAN_BELOW004 |
| C21 | `EURUSD\|F5:tf=H1:n=10:adx=25:buffer=0.1\|DAY\|P0` | 163 | 141 | 156 | 30/0 | PATH_OR_ENDPOINT_INCOMPLETE |
| C22 | `EURUSD\|F5:tf=H1:n=10:adx=25:buffer=0.1\|DAY\|P1` | 163 | 143 | 156 | 26/0 | PATH_OR_ENDPOINT_INCOMPLETE |
| C23* | `EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P0` | 200 | 181 | 200 | 39/0 | scenario component |
| C24* | `EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P1` | 200 | 181 | 200 | 39/0 | scenario component |
| C25* | `EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P2` | 200 | 181 | 200 | 38/0 | scenario component |
| C26* | `EURUSD\|F5:tf=H4:n=10:adx=25:buffer=0.1\|DAY\|P0` | 116 | 98 | 116 | 40/0 | scenario component |
| C27* | `EURUSD\|F5:tf=H4:n=10:adx=25:buffer=0.1\|DAY\|P1` | 116 | 98 | 116 | 40/0 | scenario component |
| C28* | `EURUSD\|F5:tf=H4:n=10:adx=25:buffer=0.1\|DAY\|P2` | 116 | 98 | 116 | 39/0 | scenario component |

Net R sau phí **SYM** từng năm, trên cohort cost-admitted được định giá:
đây là kết quả theo giả định gap, chưa phải tiền trên tài khoản quỹ.

| Case | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|
| C01 | -3.162 | -3.245 | +4.884 | +1.295 | +2.087 | -0.072 |
| C02 | -3.162 | -3.245 | +4.884 | +1.295 | +2.087 | -0.072 |
| C03 | -2.409 | -8.245 | +3.366 | -0.702 | +3.585 | -0.116 |
| C04 | -2.232 | -8.245 | +3.366 | +1.782 | +3.296 | -0.116 |
| C05 | -1.439 | -2.741 | +6.767 | +1.277 | -6.173 | +14.345 |
| C06 | -2.459 | -3.251 | +6.767 | +2.669 | -3.638 | +11.411 |
| C07 | +1.475 | -1.229 | +3.020 | -0.940 | -4.734 | +7.643 |
| C08 | -2.958 | +3.425 | +1.909 | +1.608 | -0.695 | +3.273 |
| C09 | -1.968 | +4.011 | +3.373 | +1.668 | -0.792 | +2.805 |
| C10 | -1.968 | +4.011 | +3.373 | +1.668 | -0.792 | +2.805 |
| C11 | -3.257 | +3.454 | +9.702 | -0.382 | -5.196 | +8.816 |
| C12 | -3.257 | +3.908 | +9.702 | -0.382 | -5.121 | +7.857 |
| C13 | -3.929 | +9.517 | +11.386 | +0.382 | -6.144 | +12.452 |
| C14 | -3.929 | +7.961 | +11.386 | -0.378 | -4.696 | +10.945 |
| C15 | -2.753 | +3.257 | +1.813 | +0.553 | -0.982 | +1.668 |
| C16 | -2.753 | +3.257 | +1.813 | +0.553 | -0.982 | +1.668 |
| C17 | +0.144 | +1.215 | -0.767 | +0.020 | -1.704 | +2.203 |
| C18 | +0.144 | +1.215 | -0.767 | +0.020 | -1.704 | +2.203 |
| C19 | +3.598 | -4.499 | +2.103 | -2.539 | +2.791 | -2.470 |
| C20 | +2.860 | -5.039 | +3.626 | -3.328 | +4.353 | -0.285 |
| C21 | +13.900 | +13.227 | -8.289 | +3.029 | -1.631 | -1.331 |
| C22 | +10.353 | +13.227 | -6.256 | +4.307 | -0.453 | -0.109 |
| C23 | +13.997 | -4.532 | -2.503 | +1.731 | +1.801 | +14.996 |
| C24 | +14.598 | -4.004 | -4.498 | +1.731 | +3.656 | +14.214 |
| C25 | +14.817 | -4.532 | -1.694 | +1.298 | +3.986 | +8.530 |
| C26 | +9.469 | +0.573 | -3.213 | +3.381 | +5.521 | +12.854 |
| C27 | +9.469 | +0.573 | -3.213 | +3.381 | +7.376 | +12.072 |
| C28 | +6.930 | +0.573 | -3.213 | +2.948 | +7.705 | +7.833 |

Net R **ASYM** trên cùng các cohort:

| Case | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|
| C01 | -3.162 | -3.245 | +4.884 | +1.295 | +2.087 | -0.072 |
| C02 | -3.162 | -3.245 | +4.884 | +1.295 | +2.087 | -0.072 |
| C03 | -2.018 | -7.418 | +3.849 | -0.414 | +4.018 | +0.207 |
| C04 | -1.840 | -7.418 | +3.849 | +1.989 | +3.729 | +0.207 |
| C05 | -1.506 | -2.658 | +7.139 | +1.383 | -6.009 | +15.060 |
| C06 | -2.526 | -3.168 | +7.139 | +2.790 | -3.474 | +12.140 |
| C07 | +2.003 | -1.192 | +3.228 | -0.891 | -4.562 | +7.980 |
| C08 | -2.717 | +3.427 | +2.111 | +1.718 | -0.608 | +3.477 |
| C09 | -1.968 | +4.011 | +3.373 | +1.668 | -0.792 | +2.805 |
| C10 | -1.968 | +4.011 | +3.373 | +1.668 | -0.792 | +2.805 |
| C11 | -3.285 | +3.592 | +9.730 | -0.251 | -4.927 | +9.055 |
| C12 | -3.285 | +4.046 | +9.730 | -0.251 | -4.851 | +8.096 |
| C13 | -3.957 | +9.737 | +11.510 | +0.501 | -5.645 | +12.707 |
| C14 | -3.957 | +8.148 | +11.510 | -0.253 | -4.322 | +11.216 |
| C15 | -2.753 | +3.257 | +1.813 | +0.553 | -0.982 | +1.668 |
| C16 | -2.753 | +3.257 | +1.813 | +0.553 | -0.982 | +1.668 |
| C17 | +0.144 | +1.215 | -0.767 | +0.020 | -1.704 | +2.203 |
| C18 | +0.144 | +1.215 | -0.767 | +0.020 | -1.704 | +2.203 |
| C19 | +3.598 | -4.499 | +2.103 | -2.539 | +2.791 | -2.470 |
| C20 | +2.860 | -5.039 | +3.626 | -3.328 | +4.353 | -0.285 |
| C21 | +13.900 | +13.227 | -8.289 | +3.029 | -1.631 | -1.331 |
| C22 | +10.353 | +13.227 | -6.256 | +4.307 | -0.453 | -0.109 |
| C23 | +13.997 | -4.532 | -2.503 | +1.731 | +1.801 | +14.996 |
| C24 | +14.598 | -4.004 | -4.498 | +1.731 | +3.656 | +14.214 |
| C25 | +14.844 | -4.532 | -1.690 | +1.304 | +3.995 | +8.550 |
| C26 | +9.469 | +0.573 | -3.213 | +3.381 | +5.521 | +12.854 |
| C27 | +9.469 | +0.573 | -3.213 | +3.381 | +7.376 | +12.072 |
| C28 | +6.938 | +0.573 | -3.213 | +2.954 | +7.715 | +7.846 |

Full annuals cũng có trong JSON; không loại SELL hoặc chọn mode
theo một năm riêng. 16 component đủ cổng mô phỏng; **0** component đủ chứng nhận
nguồn không còn phút chưa rõ. Đặc biệt 19/19 định giá được không đồng nghĩa 19/19 có edge.

## 2. Tổ hợp cơ học và trạng thái FTMO 9 năm

Medoid/overlap/correlation <0,25, tối đa 8, không search subset hay tối ưu trọng số.
Equal risk giữ ba nhánh sau; không tăng risk để chữa thiếu cơ hội:

| Asset | Config được chọn |
|---|---|
| XAUUSD | `XAUUSD\|F3:compression=BB:n=60:quantile=0.1:multiple=1\|48H\|P0` |
| XAUUSD | `XAUUSD\|F4:hour=15:impulse=1:timing=MONTH:multiple=1\|24H\|P1` |
| EURUSD | `EURUSD\|F5:tf=H4:n=5:adx=25:buffer=0.1\|DAY\|P0` |

Correlation ba cặp: −0,03465; −0,03018; +0,06914. Chỉ là correlation proxy
daily MTM trên Development, không chứng nhận độc lập thống kê.

| Năm | Tín hiệu | SYM Net R | ASYM Net R | SYM DD đóng ngày (R) | Daily/static account loss |
|---|---|---|---|---|---|
| 2018 | 43 | +9.301 | +9.206 | 5.178 | Chưa đo |
| 2019 | 47 | -3.366 | -3.143 | 7.325 | Chưa đo |
| 2020 | 57 | +13.966 | +14.366 | 4.951 | Chưa đo |
| 2021 | 51 | +2.626 | +2.863 | 9.879 | Chưa đo |
| 2022 | 66 | -9.493 | -9.059 | 11.161 | Chưa đo |
| 2023 | 76 | +37.198 | +38.153 | 6.168 | Chưa đo |

Mean SYM +0,14774R/tín hiệu (340 lượt / 6 năm, trung bình 56,7/năm).
Hai cụm SYM +19,901R / +30,331R; 4/6 năm dương; bỏ năm tốt nhất còn +13,034R.
Đạt nhánh OR về ổn định đã đăng ký, nhưng 2023 đóng góp 74,05% tổng SYM.
2019 và 2022 vẫn âm; chưa chứng minh thu nhập đều hoặc tốc độ vượt Challenge.
Các cột DD là biến động đánh dấu **cuối ngày UTC**, không phải floating intraminute,
Prague Daily Loss, static account loss hay shared-account replay.
SL-Active không đồng nghĩa đã kiểm xong mọi luật FTMO.

| Hạng mục | Trạng thái |
|---|---|
| 2024, 2025, 2026 YTD giá mới cho V13 | CLOSED — không được đọc |
| Monthly 2-Step + biweekly payouts 2018–2026 | NOT RUN — Dev cadence fail |
| Standalone Funded 50k / payout USD | NOT RUN / N/A |
| Min lot, rounding sizing, margin, tin tức, path nguồn thật | Chưa được admission |

Không điền 0 payout như một kết quả mô phỏng. Nếu sau này được giao tiếp, dữ liệu thị
trường 2024–2026 đã exposed từ chiến dịch trước; F5 chỉ là first evaluation của
cơ chế trên dữ liệu đã exposed, không tự biến thành clean OOS.

## 3. Dung lượng và Merkle toàn cây

Tiền đề tăng 15GB không khớp snapshot cùng root/đơn vị:

| Mốc D | Logical bytes | GB thập phân | GiB |
|---|---|---|---|
| V10 | 211765450617 | 211.765451 | 197.221945 |
| V12 | 211767375854 | 211.767376 | 197.223738 |
| V13_before | 211768711272 | 211.768711 | 197.224981 |
| V13_after | 211768731710 | 211.768732 | 197.225000 |

V10 → V12 chỉ +1,925,237 bytes. 211,77 GB ≈197,22 GiB;
sự khác đơn vị/scope không phải 15GB cache phình mới. Jobs/matrices V10–V13 ở E.
JSON giữ delta theo nhóm để truy lại thay đổi thực tế; hai VI permission gaps vẫn unknown.

Đã kiểm toàn bộ 403 cây của 887 cặp directory,
bao phủ đủ 1998 cặp file V12. 106 cặp
có Merkle toàn cây bằng nhau; 0 cây không xác minh được.
Hash gồm mọi file/relative path/size/SHA256 và empty directory, không sample.
Không follow reparse/junction; giữ metadata hardlink và lỗi thay đổi file.
Đây là toàn bộ cây của các candidates V12, không là chứng minh đã tìm hết mọi
duplicate trên cả hai ổ.

**Không xóa bản nào:** các cây bằng nhau thuộc dependency/cache cài đặt, code/vendor
đang dùng hoặc chưa chứng minh đã hết consumer, hay backup chưa rõ canonical/retirement.
Import qua interpreter không bị loại chỉ vì không thấy executable trực tiếp trong cây.
Hash bằng nhau không đủ chứng minh một bản cài đặt là thừa.
Manifest/consumer evidence nằm ở private `directory-dedup.json` và `merkle-trees/`.

| Ổ/scope | Bytes xóa thực | Files xóa | Folders xóa | Delta snapshot bytes |
|---|---|---|---|---|
| D | 0 | 0 | 0 | 20438 |
| E | 0 | 0 | 0 | 19684165 |

Delta snapshot gồm bằng chứng mới, cache/test/process khác; không gọi đó là
physical space được giải phóng. **GB thu hồi được xác nhận: D=0, E=0.** Không đụng
VI WIP, Trader pin, raw prices, frozen attempts hoặc backup duy nhất.

## 4. Auditor, tests, hiệu năng và bàn giao

Auditor scalar/Decimal: **3,165 paths**, **6,330 cost views / 31,650 cash legs**,
0 discrepancies. Kiểm mọi lượt valid của 28 cells, gồm 450
lượt đi qua phút nguồn chưa rõ; giữ nhãn uncertainty. Auditor không import producer
accounting/execution. Cùng implementer và cùng feed: không gọi là người review độc lập.
Không kiểm toán account chưa chạy hoặc khẳng định giá thực thi broker.

**1,091/1,091 tests PASS**, 0 skip; giữ nguyên 1.072 IDs cũ, thêm 19.
Smoke 78 tests; phép đo sau tối ưu: median **0.848599s**, max **1.010735s** trên 10 lần.
9/10 lần dưới 1s. Mục tiêu median đạt, chưa bảo đảm mọi lần đều dưới 1s.
Lô serial cuối median 0.806960s / max 0.864177s.
Thử A/B 5 cặp xen kẽ với runner 2 workers có sẵn; giữ serial vì parallel không
cải thiện ổn định. Giữ đủ cả 2 batch serial và các mẫu parallel trong receipt.
Giữ cả mẫu preflight 1,036s và mẫu 2,318s khi inventory/full IO chạy song song;
không chọn mẫu nhanh nhất để báo. Đã profile thấy WMI qua numpy.testing import;
dùng so sánh nguyên vẹn list/shape/tolerance thay lớp assert gây hardware-query.
Giữ đủ 400 random first-passage queries và tất cả test IDs, không sửa kernel cho tốc độ.
Không áp số đo smoke cho throughput lifecycle/full campaign.

V13 Development mất 16.841s gồm source hash/load, gap index, 28 replays, profiles và write;
khác workload 2.888-cell kernel V12 nên không báo speedup so với 36,9s.

Hậu kiểm: lỗi DirEntry.stat Windows trả inode/device=0 được phát hiện ở fixture
Merkle trước production hash, đã đổi sang Path.stat cho file identity. Không retry
financial batch; report đọc lại artifacts. Numerical attempts/seals V1–V12 giữ nguyên.
Không thêm skill vì chưa có workflow mới cần một source of truth riêng; reuse quant
core/deep_storage và skill hiện có. Không broker/paid/Astra/runtime promotion.

**Bước có cơ sở tiếp theo:** xác minh raw M1/tick cho các phút thiếu của ba nhánh
được chọn trước khi bàn admission tài khoản. Không mở thêm grid, nâng risk hoặc
đổi ngưỡng cadence trong cùng lô để ép qua gate. PR V13 để owner duyệt, không tự merge.
