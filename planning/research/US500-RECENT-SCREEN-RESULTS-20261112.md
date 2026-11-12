# US500/M15: mở rộng 8 setup và kiểm dữ liệu gần đến 2026

12/11/2026. **Đã hoàn tất vòng nghiên cứu này; chưa có setup đủ bằng chứng
để đề xuất challenge.** Đã bổ sung 2025 và 2026 đến hết phiên New York 11/11,
không còn chỉ dựa vào 2022–2024. Kết luận này không bác bỏ mọi chiến lược US500.

[PLAN](US500-RECENT-DISCOVERY-PLAN-20261112.md),
[luật/tiêu chí đã khóa](US500-RECENT-SCREEN-PROTOCOL-20261112.md),
[hai sự cố và recovery](US500-RECENT-RECOVERY-AMENDMENT-20261112.md).

## Cách chia dữ liệu

| Khoảng | Dùng làm gì | Đã thực hiện |
|---|---|---|
| 2022–2024 | So sánh ban đầu trên lịch sử đã dùng | Đếm 8 setup; mô phỏng tài chính 4 setup |
| 2025 | Ưu tiên khả năng hoạt động gần hiện tại; dùng để lựa chọn | Đếm 8 setup; mô phỏng tài chính 4 setup |
| 01/01–11/11/2026 | Kiểm tiếp sau khi khóa lựa chọn | Chỉ RS01/RS07, không đọc kết quả 6 setup còn lại |
| 2016, 2020, 2021 | Kiểm sức chịu đựng ở bối cảnh cũ | RS01/RS07, giữ mọi năm và cảnh báo thiếu giá |

2025 đã dùng để lựa chọn nên không gọi là dữ liệu kiểm định mới. Không xác
nhận 2026 là holdout chưa từng xem ngoài project; sau lần này cửa sổ đó đã
được dùng cho hai recipe. Không sửa luật rồi gọi cùng 2026 là kiểm định mới.
Khóa ưu tiên dữ liệu gần trước outcomes: 2025/2026 tối đa 4 điểm kinh tế,
2022–2024 tối đa 2, quá khứ xa tối đa 1; không bắt thắng mọi năm.

## Tám setup và số cơ hội đã đo năm 2025

Đây là **cơ hội đầu tiên mỗi ngày có đủ giá ở thời điểm dự kiến vào**, chưa
phải số lệnh được risk engine chấp nhận. Mỗi tuần quy đổi 5 phiên lịch; giữ
ngày không có cơ hội. Các biến thể liên quan không là 8 lợi thế độc lập.

| Mã | Giải thích đơn giản | Cơ hội 2025 | Mỗi 5 phiên | Tuần trống / 53 | Đã kiểm lời/lỗ |
|---|---|---:|---:|---:|---|
| RS01 | Giá đóng vượt kênh cao/thấp của 20 nến trước | 176 | 3,52 | 0 | 2022–2026 và 3 năm cũ |
| RS02 | Phá kênh, quay lại thử mức vừa phá rồi đi tiếp | 94 | 1,88 | 7 | 2022–2025 |
| RS03 | Vượt đỉnh/đáy phiên thường trước | 190 | 3,80 | 0 | 2022–2025 |
| RS04 | Phá vùng giá 15 phút đầu phiên | 237 | 4,74 | 0 | Chỉ đếm; có parent/control R094 |
| RS05 | Phá vùng đầu phiên rồi quay vào trong: đi ngược cú phá | 101 | 2,02 | 3 | Chỉ đếm; có parent/control R095 |
| RS06 | Hồi rồi vượt lại đường trung bình | 59 | 1,18 | 15 | Chỉ đếm; giữ bằng chứng âm của parent R123 |
| RS07 | Đi quá xa trung bình rồi quay vào vùng bình thường | 219 | 4,38 | 0 | 2022–2026 và 3 năm cũ |
| RS08 | Giá mở lệch phiên trước, nến đầu đi ngược khoảng lệch | 114 | 2,28 | 6 | Chỉ đếm; chưa ưu tiên economic screen |

Không chạy tài chính cả 8 chỉ vì có thể chạy nhanh. RS01/02/03/07 được chọn
trước outcomes theo cơ chế và vai trò đối chiếu; giữ controls và trial history
R001/003/019/094/095/123. RS06 dùng cùng trigger nhưng exit chuẩn hóa khác
parent, không tuyên bố exact rerun. Không thêm lưới MA/ATR/giờ/TP/SL trong lượt này.

## Lời/lỗ gần đây: nhìn đúng phần đã biết

Vốn mỗi sổ năm reset **10.000 USD**, planned stop-risk tối đa **25 USD/lệnh**
(0,25% vốn đầu năm, chỉ giả định offline). Bid/Ask đã có spread; commission 0
là kịch bản chỉ số đã khai báo, chưa phải xác nhận chi phí tài khoản FTMO.
Slippage adverse 0,25/0,75 điểm **mỗi fill** cho reference/stress. M15 ra
quyết định sau đóng nến, vào phút sau; stop 2 ATR, đóng trong ngày, không TP cố
định. NautilusTrader 1.231.0 dùng native order/matching/cash; M1 stop-envelope
chưa tái hiện đường đi tick thực tế.

**Bảng sau chỉ là tổng của các lệnh có đủ M1 trên đường giữ lệnh, ở phí cao.**
Không là lợi nhuận toàn bộ chiến lược: không bỏ lệnh thiếu giá khỏi verdict.

| Setup | 2025: lệnh / thiếu đường giá | Phần đủ dữ liệu 2025 | 2026: lệnh / thiếu đường giá | Phần đủ dữ liệu 2026 |
|---|---:|---:|---:|---:|
| RS01 phá kênh | 176 / 1 | −253,83 USD | 155 / 4 | −80,75 USD |
| RS02 phá rồi thử lại | 94 / 1 | −28,33 USD | Chưa chạy | Chưa đo |
| RS03 phá đỉnh/đáy phiên trước | 190 / 3 | −541,90 USD | Chưa chạy | Chưa đo |
| RS07 quay về trung bình | 219 / 4 | −650,04 USD | 202 / 5 | −947,46 USD |

Lợi nhuận **toàn kỳ vẫn N/A** cho các sổ trên. Chỉ 31 phút thiếu trong lịch
cash 2025 và 77 phút trong 2026 cũng có thể chạm đúng lúc đang giữ lệnh.
Raw decoder/hash khớp không chứng minh nguồn không mất giá; không điền giá
giả, đóng lệnh giả hoặc lấy modeled PnL thay full-known PnL.

Để tra assumptions: modeled closed net của 2025 lần lượt RS01 −232,04;
RS02 −8,36; RS03 −512,95; RS07 −746,75 USD. Đây là **kết quả mô hình có đường
giá chưa biết**, không dùng để chọn winner hoặc chấm điểm lợi thế.
2026 RS01 reference modeled +16,26 nhưng stress −122,61 USD; cả hai vẫn N/A
toàn kỳ. Không gọi đây là edge bị phí ăn hết khi chưa giải quyết uncertainty.

Không recipe nào có sổ stress 2025 full-known đủ điều kiện lựa chọn. Theo
fallback **đã khóa trước**, RS01/RS07 được kiểm 2026 và năm cũ chỉ để chẩn đoán,
không phải hai winner. Các phần đủ dữ liệu ở 2016/2020/2021 của hai recipe
cũng âm; source gaps nhiều nên không công nhận exact full-period verdict.

## Điểm tự đánh giá và trạng thái kiểm định

Rubric /10 là công cụ ưu tiên nghiên cứu, không phải xác suất pass quỹ.
Readiness và economics tách riêng; điểm kỹ thuật không bù edge chưa biết.

| Setup | Điểm đạt / phần có thể đánh giá | Phần chưa đủ bằng chứng | Kết luận |
|---|---:|---:|---|
| RS01 | 3 / 3 | 7 điểm kinh tế chưa chấm được | Chưa chứng minh edge; cần rõ đường giá và cost sensitivity |
| RS02 | 2 / 3 | 7 điểm kinh tế chưa chấm được | Cadence dưới mốc 2/5 phiên; gần hòa vốn modeled không là pass |
| RS03 | 3 / 3 | 7 điểm kinh tế chưa chấm được | Nhiều cơ hội, phần đủ dữ liệu vẫn yếu; không ưu tiên mở rộng ngay |
| RS07 | 3 / 3 | 7 điểm kinh tế chưa chấm được | Phần đủ dữ liệu âm ở cả hai năm gần; giảm ưu tiên exact recipe |

3/3 ở đây chỉ là 2 điểm kiểm source/timing/cash trong scope mô hình và 1 điểm
cadence. **Không quy đổi 3/3 thành 10/10 hoặc 100% đạt.** RS04/05/06/08 chưa
có economic run của phiên bản này nên không tự chấm như đã backtest.

G0: rules/cost/risk/split/selection đã freeze ở commit `66660b6`; sửa bug và
recovery riêng `0c6ceb8`, `5c922f8`, không tuning outcome. G1/G2: đã kiểm
source, accounting và clocks trong scope nhưng full paths và broker realism
còn thiếu. G3: chưa chứng minh edge/clean OOS. G4: chưa đủ target prop/news/
intraminute equity. G5/G6: chưa forward strategy/không cấp broker authority.
Review bằng Fraction tách implementation engine nhưng cùng agent; chưa có
người hoặc feed thứ hai xác nhận độc lập. JSON giữ monthly distribution,
BUY/SELL, known wins, concentration và scope/dependence; không áp IID hoặc
tạo xác suất pass từ mẫu này. Tháng 11/2026 là một phần tháng, không đưa
tháng 12 chưa xảy ra vào thống kê cadence hoặc gán nó là tháng 0 cơ hội.

## Research bổ sung và điều rút ra

- [LEAN opening breakout source](https://github.com/QuantConnect/Lean/blob/master/Algorithm.CSharp/OpeningBreakoutAlgorithm.cs)
  đã có trong thư viện pin của workspace: reuse kiến trúc/luật rõ, không lấy
  demo làm bằng chứng lợi nhuận US500.
- [QuantConnect ORB stocks-in-play](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/),
  đọc lại 12/11: setup đi kèm chọn cổ phiếu có volume bất thường. Không chuyển
  thành “mọi ORB đều tốt” hoặc sao kết quả stock universe sang một CFD US500.
- [Intraday ETF momentum](https://www.quantconnect.com/research/15348/intraday-etf-momentum/),
  đọc lại 12/11: nghiên cứu chuyển động đầu phiên/liên hệ cuối phiên có cơ chế
  và ví dụ code. Họ này đã có negative lineage trong campaign; không đổi tên
  rồi chạy lại như ý tưởng hoàn toàn mới.
- [QuantConnect research guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
  và [Bailey et al., PBO](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf),
  kiểm 12/11: càng thử/chọn nhiều trên cùng dữ liệu càng cần xét selection bias.
  Đây là lý do giới hạn 4 economic recipes rồi khóa 2 trước 2026; không suy
  8 hay 12 là số setup tối ưu chung.
- [NYSE calendar](https://www.nyse.com/trade/hours-calendars), kiểm 12/11:
  dùng giờ cash/lịch nghỉ làm proxy nghiên cứu; chưa là spec CFD FTMO.

**Đề xuất:** giữ US500/M15 và ưu tiên gần hiện tại, nhưng dừng tuning rộng
trên 2025/2026 vừa xem. **Đã inventory** RS01/RS02 năm 2025: mỗi recipe có
một lệnh unresolved, cùng thiếu đúng phút **04/04/2025 11:02 New York**.
RS01 SELL vào 10:16, RS02 SELL vào 10:31; không phải hai lỗi nguồn độc lập.
JSON `us500-recent-missing-path-inventory-v1.json` bind book/source hashes;
chỉ đọc lại lịch sử đã dùng, không fetch/impute/đổi verdict. Bước tiếp là xem
có phục hồi phút này từ nguồn đã được phép hoặc nguồn tick đáng tin không,
và đăng ký trước cách đối chiếu. RS02 chỉ
là câu hỏi chi phí/data đáng xem, chưa là shortlist hoặc cho phép đọc 2026.
Nếu cần đo RS02 trên 2026, phải đăng ký study mới và ghi rõ lựa chọn sau khi
đã xem 2025; không gọi đó là validation chưa đụng tới. Với đúng RS03/RS07,
giảm ưu tiên thay vì tiếp tục quét tham số. Không bác bỏ toàn family.

**Delta kiểm tiếp 12/11:** [tick gap probe đã xong](US500-RECENT-GAP-RESULTS-20261112.md).
23.875 ticks trong đúng một giờ; target11:02NY cũng không có tick, 118 M1
overlap hai side khớp. Chưa sửa được bằng endpoint này; giữ hai lệnh unknown,
không rerun hoặc tự ffill. Tiếp kiểm khả năng nguồn đã có/bounds có đăng ký.

## Giải thích setup và điểm chung cho owner

Setup là tình huống giá được mô tả rõ để bot biết khi nào xét giao dịch.
Một strategy đầy đủ còn cần cách vào/thoát, cắt lỗ, khối lượng, phí và giờ chạy.

RS01/02/03/04/06 thử **giá tiếp tục theo hướng vừa thể hiện**: khác nhau ở
mức giá dùng làm mốc và có chờ hồi/xác nhận thêm không. RS05/07/08 thử
**giá quay lại sau khi đi lệch một vùng/mức tham chiếu**. Đây là các giả thuyết,
không phải bot biết trước đoạn nào sẽ tiếp diễn hoặc đảo chiều.

Ví dụ giả định: biên trên một vùng là104, ATR=1 thì đệm0,10ATR=0,10 điểm.
RS01 chờ nến đóng trên104,10 để xét BUY. RS02 chờ cú phá đó rồi một nến sau
chạm lại vùng quanh104 và đóng trở lên ngoài đệm. RS05 dùng **vùng đầu phiên
riêng**, chờ phá lên rồi nến sau đóng lại trong vùng để xét SELL. Giữ đúng mốc
khác nhau; không đồng nhất kênh20nến với vùng15phút đầu phiên. Hình minh họa
chỉ dừng ở tín hiệu, không vẽ diễn biến tương lai có lời.

Tất cả dùng giá US500/BidAsk theo cash-clock nghiên cứu, M15 đã đóng, luật số
học rõ và tối đa một trigger đầu/ngày cho mỗi recipe. BUY/SELL đều có; không
martingale/thêm lot để gỡ. Chưa có H1 bias bắt buộc chung; RS06 dùng SMA20/80
trên M15. ATR là đơn vị đo độ dao động để đặt đệm/stop, không tự là tín hiệu
BUY/SELL. Rule rõ giúp tái hiện/check code, chưa chứng minh có edge.

Bốn economic recipes dùng chung risk cap25USD/10k, stop2ATR, vào phút sau,
chi phí reference/stress và exit trong ngày; RS07 có thêm thoát khi về mean20.
Đây là điều kiện so sánh thử nghiệm, chưa khẳng định tối ưu cho từng family.
Bốn recipe chỉ đếm cơ hội chưa được coi đã chạy toàn strategy lời/lỗ.
RS01/RS02 chung parent, RS04/RS05 chung range; gặp cùng phiên có thể phụ thuộc
nhau, nên không cộng số mẫu hoặc gộp PnL thành portfolio độc lập.

## Reliability, thời gian và nơi lưu

Giữ **56 sổ**: 48 financial và 8 null controls, tất cả có source/input/signal/
seal và arithmetic review; không đếm cost pairs là samples độc lập.
Development dùng lại 23 sổ, historical dùng lại 14; tổng 37 sổ giữ nguyên byte.
19 sổ retained còn lại mới chạy trong lượt recovery; golden replay 1 sổ là
kiểm parity riêng. Hai failure giữ nguyên. 38 focused tests theo các suite
(8 setup + 5 recent runner + 20 core + 5 multiframe runner) đạt; đây không là
toàn bộ tests sản phẩm hoặc chứng nhận edge.

| Phase | Thời gian đã đo | Cách đọc |
|---|---:|---|
| Import 2025–2026 | 564,44 giây | Lượt trước trong cùng study, native source cache được giữ |
| So raw/native và tạo source proof | 40,06 giây | Source-only, chưa đánh giá strategy |
| Golden actual 2022/RS01 | 10,10 giây | Load + replay + toàn artifact parity trừ nhãn trace |
| Development v2: 36 sổ | 80,72 giây | 23 reuse/re-review, 13 mới |
| Confirm 2026: 5 sổ | 23,32 giây | Chỉ fixed diagnostic controls |
| Historical v2: 15 sổ | 20,75 giây | 14 reuse/re-review, 1 mới |
| Failed development v1 | ≥115,69 giây | Lần lỗi nhãn log, không mất 23 sổ |
| Failed historical v1 | ≥71,98 giây | Lần Windows lock, không mất 14 sổ |
| Research/code/review/docs toàn task | Chưa đo riêng | Không cộng các phase chồng thời gian thành wall toàn quy trình |

Không cần GPU/engine mới cho workload này. Sửa root cause và reuse đã tránh
chạy lại toàn bộ. Không còn numerical job hoặc controller lock.

Private evidence tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`:
`us500-recent-development-v2`, `us500-recent-confirm-v1`,
`us500-recent-history-v2`, `us500-recent-final-review-v1.json`;
source/admitted/cache và failed attempts giữ nguyên. Review final kiểm lại
seals, source/input bindings, metrics, selection parent và census. Chỉ chấp
nhận exact writer-only source delta đã ghi recovery contract; không sửa pin cũ.
