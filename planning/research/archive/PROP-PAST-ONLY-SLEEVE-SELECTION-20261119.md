# Chọn nhánh tại cuối 2020, đo giá trị tăng thêm trong 2021–2023

**Gác phép chọn đại diện F1–F4 theo quy tắc đã khóa.** Không có nhánh nào được
chọn cho EURUSD, XAUUSD hay US500. Cả 11 đại diện đều âm sau phí stress trên
phần đã định giá được ở 2018–2020 và đều có đường giá chưa đủ. Tổ hợp
2021–2023 giữ đúng sổ BASE_GUARD, đóng góp thêm **0 USD** ở cả hai kịch bản
đường giá. Giữ trạng thái **NOT_QUALIFIED**.

## Quy tắc đã khóa trước khi tính

- Dùng registry V11 đã sửa clock và sổ có stop V12 gốc cho EURUSD/XAUUSD.
  US500 dùng V12 sửa làm tròn cent với phí stress gốc. V12 lưu cả cấu hình
  thắng và trượt. Có 912 ô horizon P0 thuộc F1–F4 trước khi bỏ 8 ô cùng công
  thức với BASE. EURUSD F4 vắng theo thiết kế. Dùng mode P0 với stop tự nhiên
  và không TP cứng. Không có recipe/horizon mặc định duy nhất nên lấy ID
  đầu theo thứ tự từ điển, trong các bản gốc có tín hiệu trước 2021. Cả 11
  ID tình cờ cùng horizon 24H. V13 chọn cell sau khi biết sáu năm và có vá
  đường giá, nên danh sách đó nằm ngoài phép chọn.
  [V11](ENSEMBLE-AND-STORAGE-V11-PROTOCOL-20261115.md) ·
  [V12](SL-ACTIVE-ENSEMBLE-V12-PROTOCOL-20261115.md) ·
  [V13](PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115.md).
- Mốc khóa là 01/01/2021 00:00 UTC. Chỉ tính lệnh đã đóng và có deadline
  cộng một phút dự phòng trước ranh giới. Sàn phù hợp là 60 lệnh định giá
  được mỗi năm, sau phí, bước lot và chặn trùng vị thế trong mỗi ứng viên.
  Dùng trần phí 12%/intent và tỷ lệ ma sát/trung vị stop 12%, giữ ít nhất
  50% tín hiệu. Giữ yêu cầu V12 về đường giá đầy đủ, tổng stress dương
  trước và sau lọc, và kỳ vọng sau lọc tối thiểu +0,04R/lệnh. Nếu nhiều
  đại diện cùng qua, chọn số ngày UTC vào lệnh lớn nhất rồi tie-break bằng
  ID. Không thay đại diện khi bản đã khóa trượt.
  [Cổng kiểm định](../../.agents/skills/strategy-qualification/references/validation-gates.md).
- Cả hai cụm đều là Development đã được dự án xem trước đây. Phép tách
  này tránh dùng PnL 2021–2023 để xếp hạng, nhưng chưa có giá trị như một
  holdout sạch. Phí và lot là giả định nghiên cứu. Sổ V12 dùng giá Bid/Ask,
  dữ liệu đường giá của nguồn và stop đã đăng ký. Không áp phí FTMO
  mới cho US500 vào kết quả lịch sử này.

## 2018–2020 · Kết quả chọn

`Ngày tín hiệu` là ngày UTC có ít nhất một tín hiệu thô qua ranh giới thời
gian. `Cấp/định giá` là số lượt qua phí, bước lot và chặn trùng vị thế / số
có đường đầy đủ trong nhóm đó. Ô thiếu giá giữ trạng thái chưa rõ. Net R và
mean R dưới phí stress chỉ tính các lệnh đã định giá được.

| Tài sản · họ | Ngày tín hiệu 18/19/20 | Định giá thô / tín hiệu | Giữ sau phí, trước overlap | Cấp/định giá | Định giá 18/19/20 | Net R | Mean R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EURUSD F1 | 52 / 43 / 51 | 111/146 | 96,6% | 126/95 | 41 / 29 / 25 | −37,95 | −0,399 |
| EURUSD F2 | 232 / 237 / 232 | 588/701 | 58,1% | 365/300 | 138 / 64 / 98 | −130,75 | −0,436 |
| EURUSD F3 | 25 / 32 / 23 | 67/80 | 95,0% | 75/62 | 22 / 28 / 12 | −7,72 | −0,125 |
| EURUSD F4 | — | — | — | — | — | — | — |
| XAUUSD F1 | 43 / 30 / 33 | 85/106 | 44,3% | 41/37 | 3 / 10 / 24 | −5,05 | −0,136 |
| XAUUSD F2 | 220 / 234 / 228 | 533/682 | 31,4% | 191/164 | 13 / 32 / 119 | −36,80 | −0,224 |
| XAUUSD F3 | 20 / 16 / 23 | 46/59 | 47,5% | 26/25 | 0 / 5 / 20 | −6,54 | −0,262 |
| XAUUSD F4 | 153 / 140 / 124 | 330/417 | 48,4% | 202/172 | 15 / 45 / 112 | −30,39 | −0,177 |
| US500 F1 | 0 / 3 / 20 | 8/23 | 87,0% | 19/6 | 0 / 0 / 6 | −4,75 | −0,791 |
| US500 F2 | 137 / 172 / 216 | 143/525 | 26,9% | 127/38 | 5 / 3 / 30 | −0,98 | −0,026 |
| US500 F3 | 1 / 5 / 19 | 9/25 | 92,0% | 21/7 | 0 / 1 / 6 | −1,88 | −0,268 |
| US500 F4 | 19 / 21 / 74 | 66/114 | 87,7% | 100/62 | 10 / 7 / 45 | −10,93 | −0,176 |

**Điểm chặn chính là kinh tế trên phần có giá.** EURUSD F2 đủ nhịp ở cả ba
năm nhưng lỗ 130,75R. Mười đại diện còn lại thiếu nhịp ở ít nhất một năm.
Năm đại diện cùng trượt tỷ lệ giữ mẫu và quy mô stop. Độ phủ thô dao động
27,2%–83,9%. Hạ sàn nhịp một mình vẫn cho cùng danh mục rỗng. Mẫu đã đo
không đủ để kết luận mọi cấu hình trong từng họ đều lỗ.

## 2021–2023 · So cùng ngân sách rủi ro

BASE dùng sổ V19 OLHC PRIMARY và STRICT. Hai sổ định giá cùng danh tính
lệnh theo hai cách xử lý nguồn. Dùng 150 USD risk stop định mức/lệnh, lot
theo adapter V15 và phí SYM_FLAT của V14. Trần stop mở chung là 1.000 USD,
đỉnh đã dùng 300 USD theo định mức. Sổ gồm 193 lệnh trên 180 ngày vào,
172 lệnh có đường nguồn và 21 có bất định đường giá. Tổng risk stop sau
làm tròn lot là 28.329,54 USD cộng dồn qua các lệnh. Không có nhánh bổ
sung nên không phát sinh tranh chỗ, lệnh bị chặn hay tiền từ lệnh mới.
[Đối chứng V19](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md).

| Năm đóng UTC | Lệnh / đủ đường nguồn | Net PRIMARY | Net STRICT | Cash DD PRIMARY / STRICT | Phần tăng thêm |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 51/39 | +272,06 USD | −2.245,55 USD | 755,92 / 2.586,57 USD | 0 USD |
| 2022 | 66/62 | −686,13 USD | −1.513,68 USD | 1.322,23 / 1.513,68 USD | 0 USD |
| 2023 | 76/71 | +2.591,13 USD | +1.664,88 USD | 749,17 / 1.035,85 USD | 0 USD |
| **Cả cụm** | **193/172** | **+2.177,06 USD** | **−2.094,35 USD** | **1.688,91 / 4.313,01 USD** | **0 USD** |

Cash DD cả cụm theo đường liên tục. DD từng năm quy về đầu năm. Sau khi
bỏ ba lệnh lời nhất cả cụm, còn **−254,79 USD PRIMARY** và **−4.526,20 USD
STRICT**. Ngày UTC lỗ tiền đã đóng lớn nhất là **305,56 USD** ở cả hai view.
Đây là tiền từ sổ đóng lệnh với giả định đã ghi, gồm cách V19 định giá
đường bất định. Daily Loss của quỹ và floating drawdown cần replay equity.

Trong 25 cửa sổ đủ 12 tháng bắt đầu theo đầu tháng, **0/25** chạm mốc đỉnh
cash +5.000 USD ở mỗi view. Cửa sổ gần nhất vẫn thiếu **2.260,01 USD PRIMARY
/ 3.141,01 USD STRICT**. Trung vị còn thiếu **4.313,04 / 4.919,29 USD**.
Các cửa sổ dùng cùng giai đoạn và chồng lấn. Mốc 1.000 USD/năm cho nghiên
cứu thêm và mức quy chiếu 7.500 USD/năm vẫn thiếu toàn bộ phần tăng thêm.
[Độ nhạy qua hai vòng đã đo riêng](PROP-TWO-PHASE-SENSITIVITY-20261119.md).

## Quyết định và bằng chứng lưu

Dừng tại cửa sổ chọn. Không cần chạy lại account runner vì sổ đối chứng và
sổ kết hợp đồng nhất theo từng lệnh. Lượt này không có kết quả Challenge
hoặc payout mới. Không mở giá 2024–2026. Khác với phép overlap trước, không
chọn nhánh từ danh sách dương toàn Development.
[Chẩn đoán overlap](PROP-SCREEN-OVERLAP-20261119.md).

Private receipt tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-past-only-sleeve-selection-20261119/`.

| Bằng chứng | SHA256 |
| --- | --- |
| `registration.md` | `dec40d6618216578932abf12baccafc1c22356b86e2a5ab1db0015857cb3c3ee` |
| `representatives.json` | `75d1c4310b1268db21ae003547eefadd4b1cc70e087162432ac17f2b5188d280` |
| `selection-freeze.json` | `fe92f445d4fc5282c3fd539c975e2d6c41d9fc1580834b0bca204d1869734583` |
| `ledger.private.json.zst` | `d022c8a40d93d3ac2b247a0a00db6802fcd6d100e7f5d220dde875f0534af951` |

Kiểm hash nguồn và receipt, giải nén đối chiếu khóa chọn và sổ đánh giá,
đối chiếu danh tính PRIMARY/STRICT, đếm lại năm và cộng tiền chính xác
đến cent. Lượt preflight đầu phát hiện registry V12 chứa thêm F5. Đã lọc
đúng bốn họ trước khi xuất danh sách hoặc đo PnL. Quy tắc không đổi.
