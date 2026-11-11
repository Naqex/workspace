# Rà tổng thể chiến lược US500 theo mục tiêu của owner

11/11/2026. **Chưa có ứng viên phù hợp để đề xuất challenge hoặc làm nguồn thu
chính.** Giữ hướng US500/M15/intraday/risk thấp; gác đúng bộ luật R123 hiện tại.
Ít lệnh và thiếu lợi thế sau chi phí là hai vấn đề riêng, không chữa bằng tăng lot.

R123 là bản **MA reclaim**: dùng SMA20/80 nhận hướng, chờ giá hồi rồi đóng nến
vượt lại MA20 cộng/trừ đệm 0,10ATR; có cả BUY và SELL. SL2ATR, thoát khi mất
hướng hoặc đến giờ đóng; không TP cố định. Luật cụ thể giữ ở
[protocol đã khóa](US500-MA-RECLAIM-PROTOCOL-20261111.md), không sửa trong lượt rà.

## Mục tiêu và mức phù hợp hiện tại

Owner chọn US500 chính, M15, tự động, giữ vài giờ trong phiên; hướng tới vốn prop
FTMO CFD 2-Step Standard cả funded, The5ers đánh giá riêng. Thu nhập chính là
mục tiêu dài hạn; mức thu nhập tháng và risk vận hành thật chưa chốt.

| Mặt cần kiểm | Mốc dùng để nghiên cứu | R123 đã đo / điều chưa biết | Kết luận |
|---|---|---|---|
| Sản phẩm, timeframe | US500, M15 | Đúng hướng owner chọn | Giữ hướng, không chứng minh edge |
| Tần suất | Ưu tiên 3–8 lệnh/tuần; thường 0–2/ngày, không quota | 165 lệnh/753 phiên; khoảng 1,05/tuần lịch, 1,10 mỗi 5 phiên; chỉ 11/157 tuần có ít nhất 3 lệnh | Thấp hơn mong muốn |
| Giới hạn cơ hội | So theo cap thật của từng version | R123 chỉ một arm attempt/ngày; tối đa lý thuyết 5 lệnh trong tuần 5 phiên | Với cap này so dải 3–5, không ép đạt 8 |
| Lợi thế sau costs | Kỳ vọng dương và đủ bền, sau đó mới kiểm ngoài mẫu | Tổng chuẩn +4,83 USD; stress −307,03 USD trên ba sổ năm reset 10k | Chưa chứng minh; stress âm cả ba năm |
| Lợi nhuận tháng | So kịch bản 0,5% / 1% / 1,5%; chưa là target owner chốt | Trung bình số học 36 tháng: chuẩn +0,0024%; stress −0,0844% | Không có cơ sở làm mô hình thu nhập |
| Risk một lệnh | Ưu tiên thấp; scenario ≤25 USD/10k ban đầu | Planned stop risk tối đa 24,99744 USD; không tự tăng theo thu nhập | Giữ scenario, chưa chốt live risk |
| Winrate và lời/lỗ | Xem cùng nhau, không ép winrate cao | Chuẩn 47,27%, lời trung bình/lỗ trung bình 1,12; stress 44,24% và 1,02 | Tổ hợp gần hòa vốn hoặc âm |
| Sụt giảm | Equity đầy đủ và luật quỹ đúng phase | Closed-balance peak DD tối đa từng năm 2,11% chuẩn / 2,62% stress; full intraminute equity DD chưa biết | Chưa được gọi là an toàn/pass quỹ |
| Giữ lệnh, giờ chạy | Intraday, bot chạy được ban đêm VN | Giữ trung bình khoảng 2h45 chuẩn; lâu nhất 5h15; đóng trong ngày NY | Hợp kiểu vận hành dự kiến; forward chưa kiểm |
| Prop / ngoài mẫu / vận hành | Profile đúng account, OOS và signal→fill reconciliation | News/closure/spec target, đầy đủ equity compliance, OOS và R123 forward còn thiếu | Chưa đủ challenge |

Các dải tần suất/lợi nhuận là **đề xuất lập kế hoạch của agent**, không phải
ngưỡng quỹ, chuẩn khoa học chung, tiêu chí đã khóa trước các kết quả cũ hoặc
quota runtime. [Planning cadence/thu nhập](DAYTRADING-INCOME-CADENCE-20261111.md)
giữ các giả định và bảng 10/20/30 triệu VNĐ; không tạo một config vận hành mới.

## Tần suất thực sự: không chỉ lấy trung bình

Hai cost scenarios cùng 165 lệnh trên 2022–2024, không phải 330 quan sát độc lập.
Calendar giữ đủ 753 phiên/157 nhóm tuần ISO/36 tháng, kể cả kỳ không giao dịch:

| Số lệnh trong tuần | Số tuần | Tỷ lệ |
|---|---:|---:|
| 0 | 47 | 29,9% |
| 1 | 66 | 42,0% |
| 2 | 33 | 21,0% |
| 3 | 11 | 7,0% |
| 4 trở lên | 0 | 0% |

588/753 phiên không có lệnh (78,1%). Tháng có 1–10 lệnh, trung vị 4; khoảng
nghỉ dài nhất trong một sổ năm là 26 phiên lịch. Các khoảng này gồm warmup và
quality filtering; không được suy thành máy hỏng/ngắt. Nhóm tuần có tuần biên
không đủ 5 phiên. Nhãn ISO `2025-W01` có thể là phiên 30/12/2024, không có đọc
giá 2025. Lịch nghỉ lễ và cơ hội thực tế cũng làm trần tần suất thấp hơn lý thuyết.

## Tiền lời/lỗ và mức ổn định

Mỗi năm bắt đầu lại 10.000 USD mô phỏng, không external cash flows. Có spread
Bid/Ask trong nguồn; commission 0 là scenario đã khai báo, extra slippage mỗi
fill 0,25 điểm chuẩn / 0,75 điểm stress. Chưa xác nhận tương đương fills/costs
trên tài khoản FTMO của owner. Không cộng tổng thành CAGR hoặc lợi nhuận của
một tài khoản chạy liên tục ba năm.

| Chỉ tiêu | Chuẩn | Stress |
|---|---:|---:|
| Net 2022 | −117,60 USD (−1,176%) | −158,29 USD (−1,583%) |
| Net 2023 | +65,98 USD (+0,660%) | −58,09 USD (−0,581%) |
| Net 2024 | +56,45 USD (+0,565%) | −90,65 USD (−0,907%) |
| Tổng ba sổ reset | +4,83 USD | −307,03 USD |
| Profit factor sau costs | 1,003 | 0,806 |
| Lời trung bình / lỗ trung bình | 19,20 / 17,16 USD | 17,50 / 17,22 USD |
| Net trung bình/lệnh theo planned risk | +0,0010R | −0,0752R |
| Tháng dương / âm | 18 / 18 | 13 / 23 |
| Tháng tốt nhất / xấu nhất | +0,991% / −1,230% | +0,908% / −1,269% |
| Tháng đạt ít nhất +0,5% | 7/36 | 5/36 |
| Tháng đạt ít nhất +1% hoặc +1,5% | 0/36 | 0/36 |
| Chuỗi lệnh lỗ dài nhất ghi nhận trong một sổ năm | 9 | 9 |

Profit factor 1,003 nghĩa tổng tiền lời chỉ nhỉnh hơn tổng tiền lỗ khoảng
0,3%, không phải tài khoản tăng 0,3%. 1R là planned stop risk riêng của lệnh;
R123 không có TP cố định nên tỷ lệ lời/lỗ thực nhận không phải TP/SL đã cài.
Winrate 47% không tự xấu; ở đây mức lời/lỗ kết hợp với costs chưa tạo biên đủ tốt.

Tỷ suất tháng dùng **balance đầu tháng của đúng sổ năm**, giữ cả tháng không
lệnh. Vì mọi lệnh đã đóng intraday và không unresolved cuối sổ, net tháng
được đối soát; điều này không cung cấp đường equity đầy đủ trong tháng.
Trung bình tháng chỉ mô tả mẫu đã xem, không là forecast hay khoảng tin cậy.
2022–2024 đều development đã exposed, chưa G3/OOS. 2025+ vẫn reserved/gated.

## Risk, giờ vận hành và prop fit

Planned risk ≤0,25% **vốn ban đầu** không đồng nghĩa lỗ thực tế luôn ≤0,25%
equity hiện tại: phí, slippage và gap còn ảnh hưởng. Internal daily/account-wide
budgets chưa chốt. Không lấy giới hạn hãng làm mức được phép tiêu hết.

Recorded endpoint equity DD stress lớn nhất 279,06 USD, tương đương **2,79%
của initial 10k**; đây không phải peak-relative DD đầy đủ. Không thay nó cho
daily/overall equity rule hoặc bỏ các biến động giữa các điểm giá đã lưu.

Trong mẫu, entry VN sớm nhất 21:16 ngày của phiên NY, muộn nhất 02:31 hôm sau.
Flat theo model lúc 15:31 NY tương ứng 02:31/03:31 VN hôm sau tùy DST; chưa
chứng minh phù hợp mọi lịch đóng sớm/holiday của broker mục tiêu. Đây là timestamp mô phỏng; thời điểm SL
trong phút chưa phải crossing time đo bằng tick. Owner đã cho biết máy có
thể chạy 24/7; không yêu cầu owner ngồi quan sát suốt đêm. R123 chưa có forward
proof cho restart/disconnect/unknown, nên khả năng chạy máy không thay bằng chứng đó.

Kiểm nguồn chính thức 11/11/2026:

- [FTMO news](https://ftmo.com/en/faq/can-i-trade-news/): Standard funded chịu
  hạn chế execution ±2 phút quanh một số tin; SL/TP cũng tính execution;
  US500.cash nằm trong nhóm chịu tác động tin USD. Challenge/Verification và
  Swing có ngoại lệ. Intraday không tự giải quyết news compliance.
- [FTMO holding](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/):
  không được giữ qua market break >2 giờ trong scope không được miễn; không
  phải cấm mọi overnight. Giờ/holiday phải kiểm đúng instrument/platform.

R123 chưa có đầy đủ các cửa này. The5ers cần profile riêng; không gắn kết quả
FTMO vào The5ers. Chưa mua challenge hoặc gửi lệnh broker từ báo cáo này.

## Đối chiếu để không nhầm nhiều lệnh với có lợi thế

| Bộ luật đã thử | Tần suất gần đúng mỗi 5 phiên | Evidence hiện có | Ý nghĩa |
|---|---:|---|---|
| [R094 opening breakout](US500-M15-OPENING-SCREEN-RESULTS-20261111.md) | 4,5 | 677 entry; modeled stress sum −1.144,62 USD; full annual PnL N/A do held gaps 1/3/1 unresolved theo năm | Đủ nhịp quan sát nhưng chưa có edge/coverage đầy đủ |
| [R120 MA40/160](US500-MULTIFRAME-FULL-TABLE-20261111.md) | 0,1 | 15 lệnh/3 năm; stress +48,87 USD | Ít mẫu, chưa chứng minh lợi thế |
| [R123 MA reclaim](US500-MA-RECLAIM-RESULTS-20261111.md) | 1,1 | 165 lệnh; chuẩn gần hòa vốn, stress âm | Cả cadence và economics chưa phù hợp |

Không chọn R120 vì dương hoặc đưa R094 trở lại vì nhiều lệnh. Không cộng các
biến thể cùng họ/cost scenarios thành nhiều nguồn lợi thế độc lập.

## Quyết định và bước tiếp

1. **Giữ US500/M15/intraday và ưu tiên risk thấp.** Bộ khung này đủ cụ thể để
   nghiên cứu tiếp; chưa được chứng minh là lựa chọn tối ưu hoặc có lợi nhuận.
2. **Giữ R123 parked**, không tăng risk/cap, không quét lại MA/TP/SL/giờ để cứu.
   Không có financial trial hoặc đổi verdict lịch sử từ lượt rà này.
3. Ý tưởng tiếp theo phải đăng ký cơ chế trước; kiểm nhịp cơ hội rẻ và cost
   sensitivity nhỏ trước deep validation. Với cap 1/ngày dùng 3–5/tuần làm ưu
   tiên tìm kiếm; không loại máy móc mọi edge ít lệnh. Nếu đổi cap, đó là
   version/risk contract mới, không phải sửa con số trong báo cáo.
4. Chỉ ứng viên có cơ sở kinh tế mới đi tiếp uncertainty/OOS → đúng prop
   profile → forward/reconciliation → owner handover. Không suy thu nhập hoặc
   xác suất pass từ 165 lệnh; chưa có cơ sở tính thời gian đạt challenge.

## Evidence và kiểm chứng của lượt rà

Private base: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`.

- Input: `us500-ma-reclaim-cost-screen-v1/`: 9 books/reviews/seals, manifest,
  admitted frozen NYSE calendar. Không đọc thêm raw prices hoặc simulate.
- Output hiện hành: `us500-strategy-fit-review-v2/result.json`, source snapshot
  và input hashes; 9 books checked, review wall 0,246 giây. Chưa đo riêng thời
  gian code/docs/Git, không gọi toàn task mất 0,246 giây.
- Giữ v1: label min/max clock VN trước đó sắp theo giờ chữ nên sai thứ tự khi
  qua nửa đêm. v2 dùng giờ + day offset so với ngày phiên NY; **mọi metric
  ngoài clock labels của cả 9 books giữ nguyên**, không financial rerun.
- `review_us500_strategy_fit.py`: saved-ledger reviewer; 10 focused tests đạt,
  gồm mẫu số tháng/peak DD, no-trade periods, invalid capital→unknown,
  unresolved/open→unknown, cash/duplicate/calendar rejection, boundary ns và
  VN midnight wrap. Không rerun 40 native tests khi native source không đổi.
- Catalogue giữ **123 records / 88 policy-model versions / 53 native**.
  Correctness evidence có scope; self/separate-code-path review không là
  independent feed/human audit hoặc chứng nhận toàn hệ thống.

Không cần thêm engine, skill, service hay financial run để tính các chỉ số này.
Workflow qualification/evidence-continuity hiện có đủ route; reuse ledgers giúp
các lượt sau đối chiếu mục tiêu mà không chạy lại backtest.
