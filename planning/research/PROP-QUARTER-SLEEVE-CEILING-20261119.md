# BASE_GUARD · trần cải thiện khi bật/tắt từng nhánh theo quý

**Gác thử bộ lọc quý.** Ngay cả khi biết trước quý nào có lãi
trên sổ cố định, PRIMARY 2018–2020 chỉ thêm **942,80 USD/năm**,
hụt **57,20 USD/năm** so với mốc 1.000 USD/năm đã khóa. Điều kiện
để chạy luật dựa trên bốn quý vừa đóng không đạt. Giữ
`BASE_GUARD` ở `NOT_QUALIFIED`.

Mỗi ô là một quý UTC × một nhánh F3/F4/F5. Nhận hoặc bỏ toàn bộ
entry của ô. Quý được xác định tại thời điểm vào lệnh, giữ giá
thoát cũ nếu vị thế sang quý tiếp theo. Cả bốn sổ có 340 lệnh và
không có lệnh cắt ranh quý. Cả 72 ô được xét, trong đó ba ô rỗng
ở cụm đầu. Dùng lot gốc tính từ 150 USD risk, phí SYM_FLAT và
làm tròn cent. Bật/tắt chỉ ảnh hưởng lệnh mới nên không phát sinh
phí đóng vị thế. Không chuyển risk từ nhánh tắt sang nhánh khác.
V23 từng bỏ F3 hoặc đổi bộ lọc, V26 đổi trọng số. Hai phép cũ
không thử luật bật/tắt theo quý.
[V23](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.md) ·
[V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md).

## Trần so với luôn bật

Tắt mọi ô có tổng ròng âm là lựa chọn tối đa khi đã biết trước
kết quả. OHLC và OLHC cho cùng số liệu trong từng kịch bản.

| Tập | Kịch bản | Luôn bật, USD cộng dồn | Biết trước, USD cộng dồn | Tăng thêm, USD/năm | Lệnh bỏ / tổng · trong đó lệnh thắng |
| --- | --- | ---: | ---: | ---: | ---: |
| 2018–2020 | PRIMARY | +1.400,80 | +4.229,19 | **+942,80** | 75/147 · 22 |
| 2021–2023 | PRIMARY | +2.177,06 | +5.547,83 | +1.123,59 | 94/193 · 31 |
| 2018–2020 | STRICT | +901,45 | +4.127,15 | +1.075,23 | 75/147 · 21 |
| 2021–2023 | STRICT | −2.094,35 | +3.848,51 | +1.980,95 | 120/193 · 35 |

Trong PRIMARY 2018–2020, 19 ô bị tắt. Cụm đầu tránh **4.269,05
USD** tiền lỗ và bỏ **1.440,66 USD** tiền thắng trong chính các
ô đó. Phần tăng thêm mỗi năm lần lượt là **313,46 USD từ F3**,
**252,61 USD từ F4**, **376,72 USD từ F5**. Cụm sau tắt 20 ô và
bỏ 1.799,37 USD tiền thắng.

STRICT có trần tăng thêm lớn hơn một phần vì sổ luôn bật có
nhiều lỗ hơn để loại. Dùng chính danh sách bật/tắt biết trước
của PRIMARY lên STRICT, mức tăng cụm sau còn **1.281,09 USD/năm**
so với **1.980,95 USD/năm** nếu được chọn lại bằng kết quả STRICT.
Cụm đầu giữ +1.075,23 USD/năm. Cả hai danh sách đều là phản thực
có lợi nhuận tương lai.

## Quyết định và kiểm chứng

Luật khóa để dùng nếu qua trần là nhìn PnL tiền đã chốt của từng
nhánh trong bốn quý đã kết thúc, theo sổ quan sát PRIMARY OLHC
luôn ghi nhận mọi cơ hội. Tổng dương thì bật, thiếu lịch sử
thì giữ BASE. Đã lưu luật, chưa chạy vì điều kiện trần không
đạt. Không chạy replay tài khoản, risk/DD theo pha hay payout.
Trần chỉ áp dụng cho phép chọn quý trên bốn sổ cố định này.
Giá 2024–2026 không nằm trong đầu vào. [Sổ đối chứng 50k](PROP-PAYOUT-REPLAY-DECISION-20261118.md).

Đối soát 1.360 dòng theo bốn kịch bản bằng phép tính Decimal
riêng cho khối lượng, cent, phí, kỳ rollover và tổng từng ô.
Artifact private tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-quarter-sleeve-ceiling-20261119/`.
Protocol SHA256 `7d47c52743c69ddf334cb2204eba8c9474268ee56d8289010cae0cb3d1a9176e`.
Ledger SHA256 `199eb062d3686707f0da1b2663cbb10f74c0730eb90dfe9c67672f376346ff75`.
