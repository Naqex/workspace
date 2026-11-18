# BASE cần thêm lợi thế bao nhiêu để hoàn tất hai vòng trong 12 tháng?

**Mức +1.000 USD/năm chỉ tạo thêm một cửa sổ hoàn tất ở PRIMARY và không
tạo cửa sổ mới ở STRICT. Cả hai đều chưa có payout mô phỏng trong 12 tháng
ở mức này.** Để phần lớn cửa sổ hoàn tất ở cả hai cách xử lý gap, mốc
đã thử đầu tiên là **+7.500 USD/năm quy chiếu**. Đó là +0,625R/lệnh
ở 40 lệnh/năm hoặc +0,417R/lệnh ở 60 lệnh/năm với 1R quy chiếu là
300 USD. Đây là phép đo độ nhạy bằng lệnh giả định. Chưa có cơ chế thật
nào trong hồ sơ đạt và duy trì các con số này ở tần suất tương ứng.

## Phép thử

Khóa trước hai nhịp 40 và 60 cơ hội/năm, lịch weekday 05:00–05:05 UTC,
cùng thứ tự thắng/thua trong từng nhịp cho mọi mức lợi thế. Mỗi khối 10
cơ hội có 5 thắng và 5 thua theo thứ tự SHA256 định trước, không chọn
theo kết quả của BASE. Tăng lợi thế bằng cách nâng giá thoát giả định của
nhóm thắng. Nhóm thua chạm stop 50 pip, khoảng −1,054R sau phí.
Có một mốc giá đi ngược trước khi đóng. Bỏ các khung 5 phút đụng đường
hoặc sự kiện BASE đã lưu, không dời sang ngày thuận lợi. Các lệnh
EURUSD giả định dùng chính module khớp và tính phí BASE. Cổng nhận lệnh
có thể từ chối. Chỉ lệnh đã đóng mới đóng góp PnL.

Dùng đúng 61 mốc tháng UTC từ 01/2018 đến 01/2023. Mỗi sổ chạy đến đầu
tháng cùng tên năm sau, loại trừ timestamp cuối. Giữ sổ 50.000 USD,
profile BASE_GUARD và phí V19 SYM_FLAT (friction 100 là stress gốc,
chưa cộng surcharge 150). Mức risk yêu cầu ban đầu theo pha là 300 /
262,50 / 187,50 USD. Giữ cách tăng theo cushion đã có ở Pha 1,
hạ risk khi sụt vốn, lot làm tròn xuống, trần stop mở 2%, reserve nội
bộ, reset Prague, giới hạn lỗ ngày 5% và lỗ tĩnh 10%, yêu cầu bốn ngày
giao dịch, đích +10% / +5% và reset vốn khi đổi pha.

Payout mô phỏng chỉ xảy ra sau Pha 2, khi sổ Funded đã flat, có lợi nhuận
và đủ thời gian chờ theo V19. Payout đầu chờ từ lệnh Funded đầu tiên
tối thiểu 14 ngày, chia 80% trong mô hình, chưa tính phí mua/retry,
thuế hoặc vận hành. Mọi sổ được tính đến đúng hạn 12 tháng, kể cả sổ
chưa chạm mốc. [Sổ V19](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md).

## Số cửa sổ đạt mốc trong 12 tháng

Mỗi ô là **qua Vòng 1 / qua cả hai vòng / có payout đầu**, trên 61
cửa sổ. PRIMARY và STRICT giữ nguyên đường BASE tương ứng. Dòng
`BASE` không thêm lệnh. Dòng 0 USD vẫn nhận lệnh theo phân phối 5/5
đã khóa và kỳ vọng 0R ở risk cố định. Risk thích ứng và lệnh thực nhận
làm `0R` đầu vào khác kết quả ròng thực hiện.

| Lợi thế quy chiếu mỗi năm | Net R/lệnh đầu vào · 40 / 60 | PRIMARY 40 | STRICT 40 | PRIMARY 60 | STRICT 60 |
|---|---:|---:|---:|---:|---:|
| BASE | — | 6 / 0 / 0 | 3 / 0 / 0 | 6 / 0 / 0 | 3 / 0 / 0 |
| 0 USD, có thêm lệnh | 0 / 0 | 7 / 0 / 0 | 6 / 0 / 0 | 9 / 0 / 0 | 3 / 0 / 0 |
| +1.000 USD | 0,083 / 0,056 | 8 / 1 / 0 | 8 / 0 / 0 | 17 / 1 / 0 | 12 / 0 / 0 |
| +3.000 USD | 0,250 / 0,167 | 42 / 6 / 5 | 27 / 4 / 4 | 44 / 7 / 3 | 25 / 5 / 1 |
| +5.000 USD | 0,417 / 0,278 | 60 / 18 / 10 | 48 / 11 / 8 | 60 / 25 / 18 | 44 / 16 / 12 |
| +7.500 USD | 0,625 / 0,417 | 61 / 59 / 52 | 54 / 46 / 36 | 61 / 58 / 51 | 55 / 41 / 35 |
| +10.000 USD | 0,833 / 0,556 | 61 / 61 / 60 | 61 / 52 / 51 | 61 / 61 / 61 | 58 / 50 / 49 |
| +15.000 USD | 1,250 / 0,833 | 61 / 61 / 61 | 61 / 61 / 60 | 61 / 61 / 61 | 61 / 59 / 58 |

- **+1.000 USD.** Hai nhịp cùng giúp một cửa sổ PRIMARY mở 01/2023
  hoàn tất, lần lượt ngày 11 và 18/12/2023 UTC. Đây là một cửa sổ
  duy nhất khi gộp hai nhịp. Trung vị phần lệnh bổ sung ghi nhận là
  +1.134,71 đến +1.305,74 USD, tùy nhịp và đường BASE. Vì vậy nhãn
  1.000 USD là quy chiếu trước sizing, không phải tiền cố định bơm vào
  từng sổ. Ở mức này cả 61/61 cửa sổ chưa có payout.
- **Các mức giữa +5.000 và +7.500 USD.** Khoảng tham chiếu là
  **+0,42–0,63R/lệnh** ở nhịp 40, hoặc **+0,28–0,42R/lệnh** ở nhịp
  60. Đầu dưới đủ tạo thêm một số ca. Đầu trên là mốc đầu tiên trong
  lưới đã khóa có hơn nửa số sổ hoàn tất hai vòng và nhận payout trong
  cả PRIMARY/STRICT cho từng nhịp. Chưa đo điểm chuyển chính xác giữa
  hai mốc. Các con số nhạy với thứ tự lời/lỗ, thời điểm vào, cách chia
  năm và rủi ro khả dụng.
- **Thời gian tính cả nhóm chưa hoàn tất.** Từ ngày mở đến mốc hoặc
  cuối cửa sổ, lấy trung bình cả 61 sổ. BASE và mức 0 USD có
  **365,2 ngày** cho Vòng 2 và payout. Ở +7.500 USD, kết quả như sau.

| Đường BASE và nhịp | Chưa qua hai vòng | Chưa có payout | Ngày tới hai vòng / payout, trung bình tính cả sổ chưa tới | Payout đầu mô phỏng, trung bình tính cả sổ 0 USD |
|---|---:|---:|---:|---:|
| PRIMARY 40 | 2/61 | 9/61 | 268,6 / 291,9 | 190,64 USD |
| STRICT 40 | 15/61 | 25/61 | 292,6 / 317,0 | 83,93 USD |
| PRIMARY 60 | 3/61 | 10/61 | 271,7 / 296,2 | 177,91 USD |
| STRICT 60 | 20/61 | 26/61 | 298,8 / 316,1 | 145,59 USD |

Ở +7.500 USD số lệnh bổ sung chấp nhận trung vị là 39 / 40 ở nhịp
40, và 58 / 59 ở nhịp 60, theo PRIMARY / STRICT. Không có breach
trong mô hình. Worst daily ở bốn cấu hình này là 2,18%, worst static
5,66% và peak-to-valley tối đa 14,68%. Mức đỉnh xuống đáy có thể
lớn hơn lỗ tính từ vốn đầu vì đỉnh equity đã tăng. Đường bổ sung còn
lý tưởng: một spread cố định, cùng stop, lãi/lỗ theo hai mức và không
có lệnh song song BASE trong 5 phút. Ngay cả khi cô lập entry, việc
đổi pha, sizing và harvest làm số entry BASE đổi ở 39–49/61 cửa
sổ tại +7.500 USD. Các mốc mở tháng chồng lấn nên số đếm mô tả
lịch sử giả định, chưa cho xác suất tương lai.

## Ưu tiên nghiên cứu

Giữ **+1.000 USD/năm** để xét có đáng bỏ công replay, và dùng khoảng
**+5.000–7.500 USD/năm quy chiếu** để đánh giá mức đóng góp có thể làm
đổi mục tiêu hai vòng trong 12 tháng. Không nâng trạng thái BASE_GUARD
khỏi `NOT_QUALIFIED` từ phép thử này. Giữ nguyên mốc 12 tháng do chủ
dự án đặt.

- Phần đã định giá của tám nhánh bổ sung chỉ thêm **277–376 USD/năm**
  ở risk tham chiếu 150 USD, còn 135/767 lượt thiếu đường. Chọn nhánh
  BASE theo quý bằng kết quả biết trước cũng chỉ thêm **942,80 USD/năm**
  ở cụm PRIMARY yếu, trên sổ tham chiếu. Hai số này cho biết bậc độ lớn;
  cách tính lot, rủi ro và thời điểm khác phép thử vòng đời ở trên.
  [Tổ hợp nhánh cũ](PROP-SCREEN-OVERLAP-20261119.md) ·
  [Trần chọn quý](PROP-QUARTER-SLEEVE-CEILING-20261119.md).
- Sổ Development 150 USD của V23 có EURUSD F5 **+0,130R trên 194 lệnh**
  và Gold F4 **+0,101R trên 83 lệnh** qua sáu năm. Mức này thấp hơn
  đòi hỏi của kịch bản 40/60. Nếu giữ quanh +0,10–0,13R/lệnh, chỉ riêng
  quy đổi +7.500 USD ở risk 300 USD đã cần khoảng **193–250 lệnh thực
  nhận/năm** trước khi tính hiệu ứng V19. Hướng đáng sàng lọc là cơ chế
  có tần suất cộng thêm đã đối soát giữa các tài sản và nguồn tín hiệu
  khác BASE. Trước khi thử PnL, đếm cơ hội thực nhận lịch sử sau khi trừ
  trùng và ma sát. Chưa có ứng viên đủ bằng chứng để chạy bước đó trong
  lượt này. [Sổ phân rã V23](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.md).

## Bằng chứng

Chỉ mở gói Dev OLHC PRIMARY/STRICT nén của V19 và receipt gốc, không đọc
giá 2024–2026. Dùng nguyên `BlockTape.walk`, `V19Account` và
`cost_bindings(100)`. Đối chứng không thêm lệnh khớp từng admission,
close, daily mark, phase transition, payout và breach trước hạn ở 122
sổ gốc (3.474 và 3.477 lệnh được nhận). Kiểm đường tiền đến cent cho
sổ flat và đối soát riêng file kết quả theo 1.830 lượt sổ, 9 hash đầu
vào, count/risk/reward. 34 focused tests V18, V19 và ledger oracle đạt.
Bằng chứng local
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-two-phase-sensitivity-20261119/`.

| Artifact | SHA256 |
|---|---|
| `registration.md` | `117edc900b746924cc0963cdc86b7d04f022322d0a57272e76b6f10f5f5d8f6e` |
| `sensitivity.py` | `d15a497317bf96ed313b647e7766d7dcc590929dafcaa57060e08522509548a5` |
| `two-phase-sensitivity.json.zst` | `5db59ec535bd3e9d4534394c42a579eaeb407b0d2d7a91170f712d1b4e2efc50` |
