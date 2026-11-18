# V4_Harvest · Chia đôi suất EURUSD cho GBPUSD có giúp rút được tiền?

**Gác phương án chia suất FX cho mục tiêu Challenge.** B giảm sụt giảm từ
đỉnh khoảng 2,88–3,08 điểm phần trăm, nhưng số mốc qua vòng 1 giảm từ
4 hoặc 6 xuống 2 trên 13. Cả A và B đều có 0 mốc qua vòng 2 và 0 USD
payout mô phỏng. Mọi mốc vẫn chịu bất định đường giá XAUUSD. Giữ
`BASE_GUARD` ở `NOT_QUALIFIED`.

## So sánh đã khóa

| Phần | A · V4_Harvest | B · chia suất FX |
| --- | --- | --- |
| Gold A0 | 200 / 175 / 125 USD theo pha | 200 / 175 / 125 USD |
| EURUSD SAT1 sweep ngày | 200 / 175 / 125 USD | 100 / 87,50 / 62,50 USD |
| GBPUSD S01 sweep ngày | Ngoài danh mục | 100 / 87,50 / 62,50 USD |
| Guard chung | Trần stop mở 800 USD, sàn dự phòng 46.000 USD, dừng lỗ thực hiện ngày 1.000 USD | Cùng guard |
| Thu hoạch | V6 đóng theo lịch hoặc quote tiếp theo đúng mã, 14 ngày, phần trader 80% | Cùng harvester |

Chia đôi suất FX sau throttle của V4. Nếu equity giảm tới mức làm
suất EUR gốc bị chặn ở 150 hoặc 90 USD, mỗi FX ở B chỉ nhận 75 hoặc
45 USD. Suất trống ở một mã không chuyển sang mã kia. Giữ tín hiệu,
stop tự nhiên và deadline của từng sổ. Hai nhánh FX đóng trong ngày.
Mỗi nhánh FX chịu commission 5 USD và slippage 4 USD/lot/vòng, ngoài
spread Bid/Ask. Gold giữ commission và trượt cũ, với swap SYM −40/−40
hoặc ASYM −45/−5 USD/lot/rollover. Hai chế độ giữ lịch tài khoản như V6.
[V4](PROP-COCORE-V4-PROTOCOL-20261114.md) ·
[V6](PROP-V4-HARVEST-V6-PROTOCOL-20261115.md).

Cùng 13 mốc đầu tháng từ 01/2022 đến 01/2023, mỗi sổ kết thúc đúng 12
tháng sau ngày bắt đầu. S02 cung cấp tape đã khóa 2022–2023, gồm 210
lệnh Gold A0, 236 EUR SAT1 và 287 GBP S01. Các trường ảnh hưởng đến tài khoản trong toàn bộ sự kiện Gold/EUR
và manifest các phân vùng tick của A khớp với V4 Development. S01
cho phép cổng chi phí gốc 15%, dùng stop sweep đệm ATR và hạn
20:30 UTC hoặc đóng sớm. Khớp, stop và clock của GBP lấy từ sổ tick
source-v2 đã niêm phong tại S02.

S02 cũ dùng Gold 150 USD, EUR 75 USD và thêm GBP 75 USD lên đối chứng
Gold 150 + EUR 75. Nó dùng cap 500 USD, sàn 46.500 USD, reward 30 ngày
và các mốc có thời lượng khác nhau. Kết quả cộng GBP của S02 không
đo phần EURUSD bị cắt và không trả lời phép chia suất này.
[S02 và audit khoảng trống](/C:/Users/MIIKEY/.codex/worktrees/solo-prop-system/TradingWorkspace/planning/research/SOLO-THREE-ASSET-REPLAY-RESULTS-20261118.md).

## 1. Kế toán tham chiếu trước khi chạy guard

Các dòng dưới giữ nguyên entry, exit và tính lại lot ở mức pha 1.
Đây là phép phân rã sổ giao dịch đã cố định trước admission, chưa áp
mốc chuyển pha hay cạnh tranh risk.

| Năm | EUR toàn suất | EUR nửa suất | GBP nửa suất | Giảm phần EUR | Net tăng thêm của FX |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022 | +768,26 USD | +378,85 USD | +520,81 USD | −389,41 USD | **+131,40 USD** |
| 2023 | +2.120,51 USD | +1.059,59 USD | +2.429,97 USD | −1.060,92 USD | **+1.369,05 USD** |

Ở mức pha 2, tiền tham chiếu sau chia tăng 101,20 / 1.166,10 USD cho
hai năm. Ở mức Funded là 68,27 / 817,65 USD. Các số này chưa tính điều
kiện nhận payout. Bỏ ba giao dịch lời nhất riêng ở mỗi nhánh FX được
chia, EUR nửa suất còn −1.280,39 / −662,06 USD, GBP nửa suất còn
−1.133,76 / +24,70 USD ở mức pha 1. Đây là độ nhạy mô tả trên từng
sổ, không xóa lệnh trong A/B thực.

EUR và GBP cùng có tín hiệu vào ở 73/88 ngày năm 2022/23. Có
66/75 cặp vị thế chồng thời gian, 0 timestamp vào cùng mili giây.
Sự chồng lấn làm phép cộng sổ riêng chưa đủ để suy kết quả tài khoản.
Trong 26 lần chạy A, EUR thực dùng trung vị 198,56 USD ở pha 1 và
148,80 USD ở pha 2 sau throttle và làm tròn. Trong B, EUR dùng khoảng
98,90–98,94 / 87,07–87,10 USD và GBP khoảng 98,44–98,47 / 86,43 USD,
tùy swap. Gold dùng chính sách cũ, số tiền phát sinh khác khi pha,
equity hoặc tập lệnh khác. Đỉnh tổng stop mở tối đa quan sát
785,53 USD ở A và 783,73 USD ở B. Chặn sàn nội bộ trên 13 mốc giảm
350→147 lượt SYM và 498→145 lượt ASYM. Đó là lượt xét lệnh qua các
sổ chồng lấn, chưa là số tín hiệu riêng.

## 2. Vòng đời tài khoản trên đúng 13 cửa sổ

| Sổ / swap | Qua P1 | Qua P2 | Có payout đầu / USD trader | Trung vị P1 trong nhóm đạt | Còn thiếu trung vị P1 / P2 ở nhóm dừng tại pha đó |
| --- | ---: | ---: | ---: | ---: | ---: |
| A · SYM | 4/13 | 0/13 | 0/13 · 0 USD | 256,35 ngày | 6.327,59 / 6.087,23 USD |
| A · ASYM | 6/13 | 0/13 | 0/13 · 0 USD | 226,85 ngày | 7.306,33 / 6.447,87 USD |
| B · SYM | 2/13 | 0/13 | 0/13 · 0 USD | 300,35 ngày | 5.672,26 / 1.360,79 USD |
| B · ASYM | 2/13 | 0/13 | 0/13 · 0 USD | 292,35 ngày | 5.317,66 / 1.126,83 USD |

Cả 13 mốc ở mỗi sổ hết thời gian nghiên cứu trước khi đạt payout.
Số ngày tới P2 và payout đầu đều chưa quan sát được. Có 0 đường
Funded riêng biệt, không có dòng tiền trader để gộp. Số dư thiếu
tính theo mục tiêu số dư của chính pha đang dừng. Chênh giữa hai
trung vị P2 chịu ảnh hưởng của tập mốc đi được tới P2.

Ví dụ đối chiếu đúng mốc **01/2023** mà cả hai sổ qua P1. SYM thiếu
P2 từ 4.714,85 USD (A) xuống 1.659,15 USD (B). ASYM từ 3.357,67
xuống 1.411,36 USD. Ngày qua P1 khác nhau. Bắt đầu P2 sớm hơn cho
cả ba nhánh một tập lệnh khác, nên mức giảm thiếu hụt gồm cả hiệu
ứng thời điểm, Gold và hai nhánh FX. Mốc 12/2022 chỉ B qua P1.
B đánh mất ba mốc P1 riêng của A ở SYM và năm mốc ở ASYM.
Kết quả 13 cửa sổ chồng lấn không phải xác suất.

| Sổ / swap | Equity DD đỉnh–đáy | Lỗ dưới vốn đầu | Lỗ ngày theo Prague | Breach thấy được | Mốc vướng đường XAU / khoảng mỗi mốc |
| --- | ---: | ---: | ---: | ---: | ---: |
| A · SYM | 14,468% | 7,901% | 1,341% | 0/13 | 13/13 · 23–76 |
| A · ASYM | 14,276% | 7,936% | 1,280% | 0/13 | 13/13 · 23–76 |
| B · SYM | 11,588% | 7,999% | 1,339% | 0/13 | 13/13 · 48–80 |
| B · ASYM | 11,197% | 7,932% | 1,278% | 0/13 | 13/13 · 48–80 |

Còn 148 khoảng quote XAUUSD riêng biệt đã biết qua sổ S02, lặp gần
giờ nghỉ New York. Chưa miễn trừ lịch bảo trì lịch sử. Các con số
equity lấy trên mô hình mark từ quote quan sát và quote gần nhất
của mã còn mở. Điều đó không kiểm được phần biến động giữa hai quote
thiếu. Không thấy breach theo đường mô phỏng, chưa chứng nhận giới
hạn Daily hoặc Overall ngoài phần quan sát được. B còn một lệnh
Gold mở ở cutoff của mốc 02/2022 trong mỗi swap. Equity cuối
50.753,68 USD SYM và 51.124,13 USD ASYM. Vị thế giữ right-censored
và không dùng giá sau cutoff để ép đóng hoặc cập nhật DD.

## 3. Phản chứng và quyết định

GBP S01 giai đoạn 2018–2020 trên sổ H1 V25 cùng họ, thoát lúc 20:00 UTC,
lỗ **30,2048R** trên 412 lệnh. Kiểm 20:30 trước đây chỉ có cận và
phần lịch chưa xác định. Ngay cả khi áp cực trị thuận lợi nhất vào
các ngày đã có cận, workbook còn **−0,7339R** trước 19 ngày vướng
lịch. Cận rộng qua cả 19 ngày còn dư địa, nên đây là đối chiếu
bất lợi chứ chưa phải kết quả tick ở đúng mốc 20:30. V26 giữ quyết
định gác việc đưa S01 vào BASE. V6 đã công bố EUR SAT1 âm trong cả
2025 và 2026 YTD ở lần đánh giá trước. Lượt này chỉ dùng báo cáo
đã công bố để đối chiếu, không mở tape, partition hay container giá
2024–2026.
[V25](CORPUS-ISOLATION-V25-RESULTS-20261118.md) ·
[Clock S01](PROP-GBP-S01-EXIT-CLOCK-20261119.md) ·
[V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md) ·
[Snapshot V6](PROP-V4-HARVEST-V6-RESULTS-20261115.md).

B cải thiện mức rơi từ đỉnh và rút ngắn khoảng thiếu P2 ở mốc ghép
01/2023, nhưng hiệu ứng chưa thành lượt qua hai vòng hoặc payout.
Số mốc qua P1 giảm ở cả hai swap, lỗ dưới vốn đầu còn sát trần vận
hành 8%, và GBP chưa có bằng chứng tốt giai đoạn sớm hơn. Dừng áp
dụng phép chia này vào Challenge. Cả hai cấu hình đều chưa qua
cổng danh mục. Không có sổ P2 độc lập đúng phạm vi để dùng cho diễn
giải. Bảng trên dùng chính P2 sau khi vượt P1 ở từng mốc.

## Đối soát

Kiểm SHA256 nguồn Development và sổ S02, khớp toàn bộ 446 event A
với sổ gốc, đối chiếu 236 dòng EUR đến cent ở 150 USD. Khớp
5.182 lệnh vào và 5.182 lệnh đóng trước Funded ở 26 sổ A với
V4 Development. Hai sổ A bắt đầu 01/2023 có cùng cutoff và khớp
cent, chuyển pha, guard và DD. Tái dùng state machine V6. Adapter
private thêm rank GBP và chọn quote kế tiếp đúng mã khi harvest,
đồng thời giữ cutoff từng sổ để tránh trộn giá cuối traversal vào
sổ đã hết hạn. Ba focused tests adapter và 11 tests V6 đạt.
Verifier Decimal đối chiếu 52 phương trình số dư, phí, reset khi
qua pha, 13 mốc mỗi tổ hợp, và giữ 148 gap đã công bố.

Private evidence ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-v4-harvest-fx-split-20261119/`.

| Bằng chứng | SHA256 |
| --- | --- |
| `registration.md` | `9154b26693417d9e5681c3dd939c9b4a2e2cc188876aae2cf32dffe9c703dca8` |
| `A-accounts.private.json.zst` | `cdb064342baa70df63057262b3f01434b7df41ebddde0158553b82cf5c534d8d` |
| `B-accounts.private.json.zst` | `680815bbeda7ec4f9e426807af906f3e714824393e99bdb945928986d1315e35` |
| `summary.json` | `eaadb425b1666f466b826c1ca5671eabd168dbfe66089c3697b554c83d5f2b4a` |
