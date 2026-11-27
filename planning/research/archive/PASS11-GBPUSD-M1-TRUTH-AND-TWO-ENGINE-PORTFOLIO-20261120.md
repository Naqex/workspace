# Pass 11 · GBPUSD London ORB trên M1 và kiểm định hai động cơ

**GBPUSD_FAILED_M1_CHECK**. Development 2018–2024 đã có exposure.
[Protocol đăng ký trước](PASS11-GBPUSD-M1-TRUTH-PROTOCOL-20261120.md) tại `98068c8`.

## 1. Nguồn và độ phủ

Dùng QDM CLI 125.2692, symbol riêng `GBPUSD_PASS11_QUARANTINE` và
export theo từng năm UTC. Cache QDM thô đứng ngoài nghiên cứu. Tick
được kiểm clock trước khi đọc giá, rồi tổng hợp Bid/Ask và midpoint
thực theo từng phút vào Parquet/Zstd. Khe được giữ nguyên.
Tổng **204.491.282 tick** và
**2.608.982 M1 có quote**.
Timestamp cuối `2024-12-31T21:59:59.120000+00:00`.
Có **0** record từ 01/01/2025 qua cổng.
Update gặp HTTP 429 ở đuôi tháng 11/2026. Cả bảy export 2018–2024
hoàn tất sau đó và qua kiểm clock. Không tiếp tục tải phần đuôi.

| Năm | Tick | M1 | Đủ 541 phút | A nhận | A chưa replay | B có giá | B không giá |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 26.510.095 | 373.306 | 258 | 0 | 0 | 1 | 2 |
| 2019 | 30.615.058 | 372.936 | 256 | 0 | 0 | 3 | 2 |
| 2020 | 32.293.308 | 374.198 | 259 | 0 | 0 | 1 | 2 |
| 2021 | 20.382.321 | 371.585 | 252 | 3 | 0 | 5 | 1 |
| 2022 | 43.751.475 | 372.615 | 253 | 0 | 0 | 7 | 0 |
| 2023 | 28.956.623 | 371.874 | 252 | 1 | 0 | 6 | 1 |
| 2024 | 21.982.402 | 372.468 | 257 | 1 | 0 | 2 | 2 |
| **Tổng** | — | — | 1787 | 5 | 0 | 25 | 10 |

Nhóm A có tối đa 5 phút thiếu rời rạc, giữ bốn mốc phiên và bước
nhảy Bid/Ask hai đầu ≤0,2 pip. Loại khỏi mẫu mở rộng nếu khe nằm gần
fill/exit hoặc cắt cạnh đang active. Nhóm B gồm khe lớn, khe thiếu
mốc phiên hoặc ngày không có quote. B được báo coverage, không gán
lãi/lỗ 0. Cache thô có thể chứa dữ liệu ngoài giai đoạn thử nghiệm.
[Giới hạn QDM update](https://strategyquant.com/forum/topic/qdmcli-exe-update-resume-ohne-uberschreiben/).

## 2. GBPUSD · giữ nguyên London ORB

Hộp 08:00–09:00 London, OCO đến trước 13:00, SL cạnh đối diện,
hard flat 17:00, không swap. Trigger và thanh lý dùng đúng Bid/Ask.
Base gồm phí 5 USD/lot và slip 0,20 pip mỗi chiều. Hai mức stress
chỉ cộng thêm 0,50 hoặc 1,00 pip tại entry. Stop cùng phút entry
được xử lý bảo thủ. OHLC M1 giữ được biên nhưng không xác định chính
xác thứ tự tick trong một phút. R dùng khoảng cách stop cấu trúc.

### Mẫu chặt

| Năm/cụm | H1 Pass 10 · R | M1 Base · R | M1 +0,50 pip · R | M1 +1,00 pip · R |
| --- | ---: | ---: | ---: | ---: |
| 2018 | +47,86 | +13,08 | +8,04 | +3,01 |
| 2019 | +4,68 | +22,17 | +16,45 | +10,73 |
| 2020 | +57,10 | +19,63 | +15,35 | +11,08 |
| 2021 | +10,83 | -5,50 | -10,67 | -15,84 |
| 2022 | +51,48 | +28,26 | +23,89 | +19,52 |
| 2023 | +13,96 | -11,87 | -17,27 | -22,67 |
| 2024 | -4,67 | -37,67 | -45,38 | -53,08 |
| A | +109,64 | +54,88 | +39,85 | +24,82 |
| B | +71,60 | -26,77 | -49,42 | -72,07 |
| Tổng | +181,24 | +28,11 | -9,57 | -47,26 |

| Mức phí | Lệnh | Năm dương | BUY R | SELL R | Top 10 / tổng R lệnh thắng | R bỏ Top 10 | Floating DD R | Dưới đỉnh (tháng) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base | 1762 | 4/7 | +59,55 | -31,44 | 7,3% | -51,42 | 54,11 | 29,21 |
| +0,50 pip | 1762 | 4/7 | +41,54 | -51,11 | 7,3% | -88,80 | 67,31 | 30,59 |
| +1,00 pip | 1762 | 4/7 | +23,53 | -70,78 | 7,4% | -126,18 | 92,00 | 55,83 |

**173 ngày H1 chạm hai cạnh, Stress +0,50.** 172/173 ngày
qua cổng đường giá và 172 có lệnh. Net **-158,17R**.
Có 161 SL, 9 lệnh lãi,
0 phút chạm hai entry và 0
phút có entry và SL. Trường hợp còn thiếu là 29/03/2024,
thiếu 10 phút và xếp Nhóm B.
Trong riêng 2024, 23 ngày hai cạnh
đóng góp -25,66R. So khác nguồn
native H1 FTMO và QDM M1, nên chênh lệch trên ngày ghép gồm cả
cách đo giá và thứ tự khớp.

**2024.** Trên 233 ngày cả H1/M1 có lệnh,
H1 đạt -13,92R và M1 đạt
-19,72R ở Stress +0,50.
Có 3 ngày lệch chiều, 0 ngày chỉ
H1 có lệnh, 23 ngày chỉ M1 có lệnh trên tập đủ giá.
Cổng Stress +0,50 của mẫu này: **RỚT**.

### Mẫu chặt + Nhóm A

| Năm/cụm | H1 Pass 10 · R | M1 Base · R | M1 +0,50 pip · R | M1 +1,00 pip · R |
| --- | ---: | ---: | ---: | ---: |
| 2018 | +47,86 | +13,08 | +8,04 | +3,01 |
| 2019 | +4,68 | +22,17 | +16,45 | +10,73 |
| 2020 | +57,10 | +19,63 | +15,35 | +11,08 |
| 2021 | +10,83 | -8,65 | -13,91 | -19,17 |
| 2022 | +51,48 | +28,26 | +23,89 | +19,52 |
| 2023 | +13,96 | -11,99 | -17,41 | -22,82 |
| 2024 | -4,67 | -32,13 | -39,87 | -47,62 |
| A | +109,64 | +54,88 | +39,85 | +24,82 |
| B | +71,60 | -24,50 | -47,30 | -70,09 |
| Tổng | +181,24 | +30,38 | -7,45 | -45,28 |

| Mức phí | Lệnh | Năm dương | BUY R | SELL R | Top 10 / tổng R lệnh thắng | R bỏ Top 10 | Floating DD R | Dưới đỉnh (tháng) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base | 1767 | 4/7 | +64,05 | -33,67 | 7,2% | -49,15 | 48,69 | 29,43 |
| +0,50 pip | 1767 | 4/7 | +45,97 | -53,42 | 7,3% | -86,67 | 64,51 | 55,83 |
| +1,00 pip | 1767 | 4/7 | +27,90 | -73,17 | 7,4% | -124,20 | 90,02 | 55,83 |

**173 ngày H1 chạm hai cạnh, Stress +0,50.** 172/173 ngày
qua cổng đường giá và 172 có lệnh. Net **-158,17R**.
Có 161 SL, 9 lệnh lãi,
0 phút chạm hai entry và 0
phút có entry và SL. Trường hợp còn thiếu là 29/03/2024,
thiếu 10 phút và xếp Nhóm B.
Trong riêng 2024, 23 ngày hai cạnh
đóng góp -25,66R. So khác nguồn
native H1 FTMO và QDM M1, nên chênh lệch trên ngày ghép gồm cả
cách đo giá và thứ tự khớp.

**2024.** Trên 234 ngày cả H1/M1 có lệnh,
H1 đạt -8,44R và M1 đạt
-14,22R ở Stress +0,50.
Có 3 ngày lệch chiều, 0 ngày chỉ
H1 có lệnh, 23 ngày chỉ M1 có lệnh trên tập đủ giá.
Cổng Stress +0,50 của mẫu này: **RỚT**.

## 3. Danh mục và quyết định Pass 12

GBPUSD rớt cổng Stress +0,50 đã đăng ký. Track 3 giữ đóng,
vì kết quả ghép danh mục sẽ dùng một nhánh chưa qua kiểm M1.
Giữ USDJPY Pass 7B/8 làm mốc. Không dùng +1h hay thay SL để
cứu recipe và chưa có căn cứ mở mô phỏng Challenge Pass 12.

## 4. Kiểm chứng

Bộ quant đầy đủ 1.503 test đạt, 0 skip, 0 lỗi.
Lần xuất JSON đầu gặp kiểu số NumPy không serialize được. Đã chuyển
index và risk thành kiểu Python ở nguồn và kiểm lại serialization.
Dùng lại Parquet đã qua SHA, giữ các lần xuất dở riêng. Kiểm tính
lại cash, net R và tổng trên từng bậc phí từ ledger.
Giá holdout từ 01/01/2025 giữ khóa, OrderSend = 0, pin Trader
và WIP VI Dubber được kiểm lại trước commit. SHA256 tính trên
bytes blob Git xuống dòng LF. Dữ liệu và ledger raw nằm ngoài Git.
