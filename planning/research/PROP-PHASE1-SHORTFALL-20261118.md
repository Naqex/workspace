# BASE_GUARD còn cách mục tiêu vòng 1 bao xa sau 12 tháng?

18/11/2026. **Trong 55/61 cửa sổ chưa qua vòng 1 ở kịch bản chuẩn, mức
thiếu trung vị là 4.929,17 USD trên sổ 50.000 USD.** F3 kéo lùi lợi nhuận
nhiều nhất trong kịch bản chuẩn. F5 chịu tác động lớn nhất khi giả định
đường giá thiếu bất lợi. Giữ BASE_GUARD làm đối chứng và dành một lượt
Stage‑0 kế tiếp cho một cơ chế có nguồn lợi nhuận khác. [Lộ trình](PROP-SYSTEM-ROADMAP.md)

## Số tiền còn thiếu

Đọc sổ V19 đã lưu và đối soát từ trước. Mỗi sổ bắt đầu vào đầu một tháng
UTC, chạy từ 01/2018 đến mốc khởi đầu cuối cùng là 01/2023 để đủ đúng
12 tháng trong Development. Mốc đo cuối là đầu tháng cùng tên năm sau,
loại trừ chính timestamp đó. Số dư mục tiêu của vòng 1 trong mô hình là
55.000 USD. Cả hai kịch bản dưới đây dùng cùng biểu phí và chính sách
rủi ro BASE_GUARD. PRIMARY dùng đường giá mô phỏng chuẩn, STRICT dùng
giả định chạm stop bất lợi ở các khoảng thiếu. [Bằng chứng V19](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md)

| Kịch bản | Qua vòng 1 | Qua cả hai vòng | Chạm giới hạn lỗ | Trung vị số dư nhóm chưa qua | Thiếu P25 / trung vị / P75 | Số cửa sổ chưa qua dưới 50.000 USD |
|---|---:|---:|---:|---:|---:|---:|
| PRIMARY | 6/61 | 0/61 | 0/61 | 50.070,83 USD | 4.482,80 / **4.929,17** / 5.339,77 USD | 25/55 |
| STRICT | 3/61 | 0/61 | 0/61 | 49.129,40 USD | 5.082,50 / **5.870,60** / 7.775,62 USD | 44/58 |

Thiếu ít nhất/nhiều nhất là 683,84/7.424,97 USD trong PRIMARY và
614,14/8.856,37 USD trong STRICT. Chỉ **2/55** cửa sổ PRIMARY ở trong
tầm 2.000 USD, và **4/55** ở trong tầm 3.000 USD. Cửa sổ chưa qua
PRIMARY có trung vị 54 lệnh đóng. Mức thiếu điển hình **4.929,17 USD**
tương đương 9,86 điểm phần trăm của vốn ban đầu, hay khoảng 410,76 USD
mỗi tháng nếu trải đều theo phép chia số học.

| Năm mở sổ | Số cửa sổ đủ 12 tháng | Qua vòng 1, PRIMARY / STRICT | Thiếu trung vị trong nhóm chưa qua, PRIMARY / STRICT |
|---|---:|---:|---:|
| 2018 | 12 | 5 / 2 | 4.340,42 / 4.646,89 USD |
| 2019 | 12 | 0 / 0 | 5.453,23 / 5.944,04 USD |
| 2020 | 12 | 0 / 0 | 4.727,68 / 5.618,27 USD |
| 2021 | 12 | 0 / 0 | 5.035,89 / 8.613,52 USD |
| 2022 | 12 | 0 / 0 | 4.784,80 / 5.837,09 USD |
| 2023 | 1 | 1 / 1 | — |

Các cửa sổ tháng liền nhau dùng lại nhiều lệnh. Tỷ lệ trên mô tả lịch
sử Development; cỡ mẫu độc lập nhỏ hơn 61. Sổ 01/2023 là cửa sổ duy nhất
mở năm 2023 có đủ 12 tháng trong phạm vi này.

## Phần hụt đến từ đâu?

Lấy PnL ròng thực ghi trong sổ, theo đúng lot và chi phí của từng lệnh,
rồi ghép mỗi lệnh về nhánh nguồn. Cộng PnL từng nhánh vào 50.000 USD để
khớp số dư vòng 1. Các cột đếm âm và đóng góp đều chỉ xét nhóm chưa qua
của từng kịch bản.

| Nhánh | PRIMARY: PnL TB / cửa sổ | PRIMARY: cửa sổ nhánh âm | STRICT: PnL TB / cửa sổ | STRICT: cửa sổ nhánh âm |
|---|---:|---:|---:|---:|
| EURUSD F5 — đảo chiều sau quét biên | +398,87 USD | 27/55 | −831,95 USD | 43/58 |
| XAUUSD F3 — phá vùng co hẹp | **−669,35 USD** | **45/55** | −533,95 USD | 44/58 |
| XAUUSD F4 — động lượng theo giờ | +502,02 USD | 19/55 | +299,70 USD | 26/58 |
| **Cộng** | **+231,55 USD** | | **−1.066,20 USD** | |

F3 là khoản kéo lùi lớn nhất ở 29/55 cửa sổ PRIMARY chưa qua. Mức lỗ
trung bình 669,35 USD chỉ chiếm khoảng 14% mức thiếu trung bình 4.768,45
USD. Kể cả triệt được phần lỗ F3 trong phép cộng tĩnh, khoảng thiếu vẫn
còn lớn. Bỏ một nhánh có thể thay đổi risk, thứ tự và lệnh được nhận.
V23 đã thử bỏ F3 và giữ BASE_GUARD ở lần xét chuyển tiếp.
[Thử loại F3 của V23](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.md)

So trên **cùng 55 cửa sổ** chưa qua ở cả hai kịch bản, STRICT làm phần
thiếu tăng trung vị **1.320,87 USD**. PnL trung bình của F5 giảm **1.423,36
USD** ở phép so này. Mức nhạy dữ liệu của F5 vẫn là vấn đề cần giải quyết
khi có nguồn mới. Ngay cả PRIMARY cũng còn xa mục tiêu 12 tháng.
[Mười khoảng thiếu ưu tiên](PROP-N1-RESULTS-20261118.md#2-khoảng-thiếu-giá-nào-có-thể-đổi-kết-quả-base_guard)

## Yêu cầu cho một ứng viên bổ sung

1. **Vai trò.** Tạo thêm PnL sau phí ở những cửa sổ BASE_GUARD yếu. Chọn
   một cơ chế và một tài sản có dữ liệu phù hợp, với giả thuyết có thể
   kiểm tra và khác ba nhánh hiện hành. Dùng năm/tháng yếu để đánh giá
   độ bổ sung sau khi khóa cơ chế, tránh biến bảng trên thành lịch bật
   tắt tín hiệu. Hạn mức ở lượt tiếp theo là một cấu hình.
2. **Cửa rẻ nhất.** Đăng ký đúng một chân trời chính, nguồn, giờ, chi phí
   và stop tự nhiên trước khi đếm hoặc xem PnL. Giữ sàn 40 tín hiệu thô
   và 99% mẫu định giá mỗi năm. Ở từng năm Development, markout net
   stress trung bình phải dương và ít nhất bằng phí stress trung bình.
   Giữ ma sát/SL trung vị tối đa 12% và ít nhất 50% mẫu thô qua cap 12%.
   Kết quả Nhịp 1 cho thấy đạt số đếm vẫn có thể trượt kinh tế.
   [Cổng Stage‑0](../../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen)
3. **Đo quy mô trước khi ghép.** 4.929 USD là khoảng thiếu trung vị,
   không phải yêu cầu một nhánh tự lấp hết. Ví dụ, nếu có 40 lệnh thực
   vào trong 12 tháng và mỗi lệnh dùng đúng 300 USD risk, tự lấp toàn
   bộ khoảng đó đòi hỏi khoảng +0,41R ròng mỗi lệnh. Đây là phép quy
   đổi theo risk cố định, chưa xét trần rủi ro mở, biến động sizing
   hay việc ứng viên làm thay đổi lệnh khác.
4. **Chỉ replay khi qua Stage‑0.** So BASE_GUARD và danh mục ghép trên
   đúng 61 mốc UTC với cùng ngân sách rủi ro. Đo số qua vòng 1, chênh
   tiền thiếu trên cùng các cửa sổ, thời gian tới đích, daily/overall
   drawdown và độ nhạy khi một ít lệnh thắng lớn bị bỏ. Khóa tiêu chí
   trước replay. Ưu tiên cải thiện ở nhiều nhóm năm bắt đầu, và kiểm
   sensitivity STRICT trước khi xem xét dữ liệu ngoài Development.

**Quyết định.** Dùng một suất Stage‑0 cho vai trò trên sau khi có card cơ
chế và nguồn. Bài đo này hoàn tất yêu cầu cho ứng viên. Công thức kế
tiếp chưa được chọn và chưa sinh thêm kết quả tín hiệu.

## Kiểm chứng và tái lập

[Script](../../tooling/ai-engines/prop_phase1_shortfall.py) đọc bốn sổ
V19 đã audit và danh sách lệnh theo block. Không chạy replay, đọc file
quote hoặc mở giá 2024–2026. Hai thứ tự OHLC/OLHC cho cùng 61 kết quả ở
mỗi kịch bản. Các mốc đo đều flat theo sổ. Kiểm sum PnL, mốc qua vòng 1,
cash bridge và giá trị từng dòng. Giải nén và đối soát SHA256 gốc/nén
cùng 12 hash đầu vào. 34 bài kiểm thử V18, V19 và kiểm toán sổ đã qua.
Kiểm thêm fixture hụt vốn, đã qua vòng 1, có PnL đóng trong kỳ và có vị
thế chạm ranh giới cuối kỳ.

Bằng chứng theo từng cửa sổ nằm ở
`execution-v1/prop-phase1-shortfall-20261118/749687b9be70/phase1-windows.json.zst`.
SHA256 manifest `b219559dd2be48c237efb3c3ee3021b92248429af619f05c5a7a9b82b4fda8b4`.
