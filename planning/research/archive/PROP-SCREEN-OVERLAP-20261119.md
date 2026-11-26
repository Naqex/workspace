# Các nhánh dương yếu có bổ sung được cho BASE?

**Gác tổ hợp ở bước đối chiếu sổ.** Sau gộp tín hiệu trùng, có cơ hội
khác BASE và đủ chỗ theo trần stop danh nghĩa. Phần định giá được
chỉ thêm **277–376 USD/năm** theo hai cụm và hai biểu phí. Chưa có
cửa sổ nào chạm thêm mốc 5.000 USD trong phép so tiền đã chốt.
[Phạm vi chọn 19 cấu hình](PROP-SCREEN-MISS-AUDIT-20261119.md).

## Cơ hội trùng và chỗ còn lại

Quy tắc khóa trước phép cộng. Từ 19 cấu hình (2.860 lượt thô),
bỏ alias P0/P1 và các hạn thoát lặp theo thứ tự P0 ưu tiên khi
cùng hạn, rồi chọn hạn ngắn nhất cho cùng tài sản và công thức.
Tám đại diện còn 1.193 lượt. Gộp theo tài sản, giờ quyết định UTC
và chiều được **1.074 cơ hội riêng theo định nghĩa này**. Ưu tiên
hạn ngắn, mode và thứ tự định danh khi một nhóm có nhiều công thức.

- **146/1.074** cơ hội trùng BASE về tài sản, đúng timestamp quyết
  định và chiều. V11 medoid cùng tài sản/giờ/chiều ở **284**, V13
  ở **169** cơ hội. Không có bản trùng cả cấu hình với lựa chọn
  V11 hoặc V13. V23 bỏ nhánh hoặc thêm bộ lọc cho BASE. V26 đổi
  trọng số ba cấu hình BASE, xác nhận bằng danh sách khóa risk.
  Không có sổ tương đương cho đúng tổ hợp tám đại diện.
  [V11](ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115.md) ·
  [V13](PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115.md) ·
  [V23](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.md) ·
  [V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md).
- BASE được ưu tiên ở cùng giờ quyết định trên cùng tài sản.
  Loại **147** cơ hội ở bước đó, gồm 146 trùng chiều. Loại 53
  vì phí. Tiếp theo, 19 gặp vị thế BASE đang mở cùng tài sản
  và 88 gặp vị thế bổ sung đang mở. Còn **767** lượt được cấp
  phần risk tham chiếu.
- Dùng risk 150 USD/vị thế BASE trong sổ tham chiếu, giữ trần stop
  danh nghĩa 1.000 USD và chia đều phần trống tại các entry đồng
  thời, tối đa 150 USD mỗi lệnh. Đỉnh danh nghĩa 600 USD, không
  có lượt phải giảm risk. Có **26 lần BASE vào sau khi vị thế bổ
  sung cùng tài sản đã mở**, nên mô hình cộng sổ không bảo đảm
  ưu tiên BASE ở cấp tài khoản. Đếm xung đột để nhận diện giới
  hạn, giữ đường sổ gốc và không lọc theo kết quả sau khi biết.
  [Quy tắc tài khoản V19](ASYMMETRIC-RECOVERY-V19-PROTOCOL-20261116.md).

## Tiền, tiến độ và lỗ trên sổ tham chiếu

| Cụm | Đã định giá / được cấp risk | Phần tăng thêm đã đo, USD/năm SYM / ASYM | Giả định mỗi lượt chưa có đường lỗ 1,15R, USD/năm SYM / ASYM |
| --- | ---: | ---: | ---: |
| 2018–2020 | 292/347 | +277,14 / +297,55 | −2.885,36 / −2.864,95 |
| 2021–2023 | 340/420 | +375,72 / +375,72 | −4.224,28 / −4.224,28 |

Có **135/767 (17,6%)** lượt chưa định giá được, gồm 94 US500, 21
EURUSD và 20 XAUUSD. Giữ chỗ risk đến hạn đã đăng ký cho các lượt
này. Bảng tiền đo được chỉ cộng **632 lượt có kết quả**. Kịch bản
lỗ 1,15R là độ nhạy xây từ một stop định mức và trần ma sát
15%R. Đây là tình huống giả định đồng thời, không phải dự báo hoặc
cận lỗ. Ngay cả khi không chịu kịch bản đó, ở SYM 135 lượt chưa rõ
phải kiếm trung bình **39,43 và 23,41 USD/lượt** lần lượt ở hai cụm
mới đưa tổng lên 1.000 USD/năm.

So **61 cửa sổ đủ 12 tháng** từ cùng sổ BASE tham chiếu 150 USD,
dùng đỉnh tiền đã chốt để tính khoảng cách tới +5.000 USD:

| Phép so | Cửa sổ giảm / tăng / giữ nguyên thiếu hụt | Trung vị giảm thiếu hụt | Cửa sổ mới chạm mốc |
| --- | ---: | ---: | ---: |
| Phần có giá, cả SYM/ASYM | 54 / 6 / 1 | +881,41 USD | 0 |
| Độ nhạy stop ở phần chưa rõ, cả SYM/ASYM | 13 / 45 / 3 | −317,44 USD | 0 |

Trên phần có giá, cash drawdown từ **1.709,82 lên 2.932,59 USD**
và ngày UTC lỗ tiền đã chốt lớn nhất từ **312,64 lên 353,57 USD**.
Các bảng chưa mô phỏng floating equity, lot/margin, reset Prague,
guard theo pha hay ảnh hưởng khi hai hệ thống tranh risk. Kết quả
vòng 1 thực trong mô phỏng tài khoản không được tính lại lượt này.
[Đối chứng vòng đời BASE](PROP-PAYOUT-REPLAY-DECISION-20261118.md).

**Quyết định:** không mở replay PRIMARY/STRICT mới. Cụm yếu hụt xa
mốc 1.000 USD/năm trong phần đã định giá, mô hình cash không có
cửa sổ chạm mục tiêu thêm và drawdown cash tăng. Đây là chẩn đoán
hậu chọn trên 2018–2023. Tập giá 2024–2026 nằm ngoài phạm vi,
`BASE_GUARD` vẫn `NOT_QUALIFIED`.

Private artifact và verifier nằm ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-screen-overlap-20261119/`.
Protocol SHA256 `328abe04f6f61cbdf422ebb0c6f973cc9afdca9cd1d98d2aef5cb9d937f8c2a4`.
Ledger nén SHA256 `5829d78ed6ded34c22f18ac6961819515f36b998ae3fb7b999853204cd739ff5`.
