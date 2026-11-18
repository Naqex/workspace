# Rà ứng viên bị bỏ sót giữa sàng lọc và sổ có stop

**Chưa tìm thấy nhánh đủ lý do để chạy thêm sổ 50.000 USD hoặc mua
Challenge.** Trên phần so được, cấu hình bị gác có cụm yếu tốt nhất
chỉ tương đương **137 USD/năm** theo quy ước 150 USD/R, so với mốc
**1.000 USD/năm**. Kết quả của cấu hình đó còn thiếu đường giá.
Kịch bản định giá V13 đã có cho cùng cấu hình chuyển cụm đầu thành âm.

## Phạm vi và độ phủ

Khóa registry V11 đã sửa đồng hồ và V12 đã đối soát cent trước khi
tính lại PnL. Chỉ Development 2018–2023. Bỏ 8 khóa tài sản/công thức/hạn
thoát của hai recipe Gold đã nằm trong BASE. Các mode khác nhau cùng
recipe được tính riêng ở cấp cấu hình và chung ở cấp họ.

| Họ chính | Cấu hình P0/P1 đã có sổ | Có phần giao so được ở hai cụm | Bị gác ở V11 và có phần giao | Trọn cohort, cả hai sổ |
| --- | ---: | ---: | ---: | ---: |
| F1 · Phá biên | 960 | 768 | 764 | 4 |
| F2 · Hồi theo xu hướng | 320 | 256 | 256 | 0 |
| F3 · Phá nén | 472 | 376 | 340 | 0 |
| F4 · Xung lực theo giờ | 760 | 760 | 744 | 0 |
| **Tổng** | **2.512** | **2.160** | **2.104** | **4** |

**4 họ có cặp**, theo 1.256 khóa gốc và hai mode thoát. Bốn cấu hình
trọn cohort đều thuộc F1 trên US500, chỉ hai khóa gốc. 352 cấu hình
đã chạy nhưng thiếu phần giao ở ít nhất một cụm. Trong 2.160 cấu hình
có phần giao, 2.156 còn thiếu kết quả trên một phần tập cơ hội thô.
Đây là census có phạm vi V11–V12, chưa cho mẫu số để tính tỷ lệ bỏ
sót của cả catalogue. [Bản sàng lọc V11](ENSEMBLE-AND-STORAGE-V11-PROTOCOL-20261115.md) ·
[Sổ có stop V12](SL-ACTIVE-ENSEMBLE-V12-RESULTS-20261115.md).

- **F5:** 348 path cells ngoài 12 bản sao recipe BASE có sổ V12.
  Không tìm thấy ma trận markout cấp cơ hội đã lưu để lập cặp đầy đủ.
- **V26:** 115 ô mặc định của sáu họ mẫu nến không có sổ SL/TP-active,
  gồm **91 đã sàng và trượt**, **24 thiếu tick volume**. Sáu ô EURUSD
  MFI đã sàng sau đối soát nguồn là phần con của 91, được tính một lần.
  Các họ này chưa chấm được về bỏ sót kinh tế.
  [Hồ sơ V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md).
- Catalogue13 kết thúc năm 2022, còn các sổ native H1 cũ chỉ phủ các
  lát ngắn hoặc một năm phù hợp. Không ghép hai khoảng khác nhau thành
  cặp sáu năm. Không lấy lại 340 lệnh BASE của hồi quy 18/11 hay phép
  thử sai số coarse/tick 08/11.
  [Catalogue13](EURUSD-CATALOGUE13-RESULTS-20261108.md) ·
  [Native H1](H1-NATIVE-SURVIVORS-RESULTS-20261108.md).

## Hụt ở đâu

Trong **1.228 khóa gốc bị V11 gác**, 985 khóa có ít nhất một cụm gross
yếu ngay sau spread. 241 khóa còn lại có lý do kinh tế về net sau thêm
phí hoặc ở tập qua lọc; hai nhóm kinh tế này phân theo ít nhất một
cụm gross không dương. Có thêm **226** khóa vướng quy mô/giữ mẫu qua
phí, **628** khóa thiếu endpoint và **128** khóa từng vướng cadence
ở luật V10. Các nhóm có thể chồng nhau. V11 không có cổng cadence
riêng cho từng nhánh. Hai khóa bị gác vì lý do phi kinh tế.

Sau khi bật stop đúng P0/P1, **19 cấu hình thuộc 12 khóa gốc** dương
hai cụm ở cả SYM và ASYM trên phần V12 định giá được. **0** cấu hình
đạt 20R/cụm ở cả hai mô hình phí, tương đương 1.000 USD/năm nếu quy
mô đúng 150 USD/R. Các con số dưới đây là quy đổi chẩn đoán, chưa
qua số lot thực, cạnh tranh vốn, risk chung hay đường equity quỹ.

| Trường hợp | 2018–2020 | 2021–2023 |
| --- | ---: | ---: |
| Mẫu cao nhất trên phần đo được, Gold F3 NR14 48H P1, số có đường / toàn bộ | 32/59 | 33/45 |
| Markout SYM trên đúng mẫu giao | +2,020R | +3,436R |
| SL-active SYM trên đúng mẫu giao | +2,739R | +2,956R |
| Quy đổi SL-active SYM ở 150 USD/R | +136,94 USD/năm | +147,80 USD/năm |
| V13 C04 định giá theo quote kế tiếp, SYM | −7,111R | +4,962R |

V13 là kịch bản xử lý khoảng trống đã đăng ký, vẫn còn phút chưa
xác minh. Trong **17 cấu hình V13 ngoài BASE**, giá trị lớn nhất ở
cụm yếu hơn qua cả hai phí là **6,828R** (EURUSD F5 H4 quét 10 ngày,
DAY P0), tương đương **341,42 USD/năm**, cũng dưới mốc 1.000. Trong
bốn cấu hình V12 trọn cohort, cấu hình có cụm yếu tốt nhất vẫn
**−1,116R** ở cụm 2021–2023. [Hồ sơ xử lý đường giá V13](PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115.md).

## Quyết định và đối soát

Không dùng thêm suất replay chẩn đoán. Bốn họ đã có cặp, và sổ V13
đã cho biết hướng xử lý gap không đưa những ca dương gần nhất tới
quy mô cần. V26 vẫn chưa đo lợi nhuận theo luật thoát gốc. Ưu tiên
ca có đồng thời đường giá đủ ở hai cụm và bằng chứng kinh tế theo
risk đã khóa trước khi dành tài nguyên cho replay. Đóng góp tăng
thêm so BASE **chưa đo**, vì không có nhánh đạt cổng độc lập. Đối
chứng BASE hiện qua cả hai vòng trong 12 tháng ở **0/61** cửa sổ;
`BASE_GUARD` vẫn `NOT_QUALIFIED`.
[Tiêu chí và sổ đối chứng 50k](PROP-PAYOUT-REPLAY-DECISION-20261118.md).

Đối chiếu hash ma trận V10/V11/V12, 10 trường nhận dạng cho cả
1.256 khóa, bảng phân rã gross/phí/trượt giá/swap và số cơ hội
được, thiếu, qua phí. V12 dùng M1/H1, có Ask proxy ở Gold/EUR và
US500 làm tròn cent theo quy tắc đã niêm phong. Bài này dùng lại
mô hình đó. Giá 2024–2026 không nằm trong phép đo.

- Artifact private `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-screen-miss-audit-20261118/`.
- Protocol SHA256 `d3f568cdfbe678af09cf51f3162775123f97e5deda94468b9edba52589d5f8c9`.
- Kết quả nén SHA256 `4568ecb3cd512f02d534fe1d0b04c1fa24039f4c8753bd4bfae00d01e9fefc89`.
- `pair-audit.py` và `verify-pairs.py` chạy thành công. Verifier
  đọc lại kết quả đã lưu và đối soát số đếm, phân rã cơ hội, cổng
  kinh tế, hai receipt V13/V26 và hash.
