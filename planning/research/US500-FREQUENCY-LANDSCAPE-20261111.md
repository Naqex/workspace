# US500/M15: tần suất, độ đều và độ dễ tự động hóa

11/11/2026. Owner yêu cầu nghiên cứu riêng tần suất trước khi chọn tiếp.
**Ưu tiên tìm cơ chế có khoảng 3–5 lệnh mỗi tuần đủ 5 phiên, luật rõ và ít
phụ thuộc thao tác tay.** Đây là đề xuất phân bổ nghiên cứu, không quota, chuẩn
quỹ, ngưỡng tối ưu đã chứng minh hoặc thay đổi cap/risk của strategy đang lưu.

## Những gì đã đo: cùng sản phẩm, tần suất rất khác

Đã đọc lại **180 financial books của 30 rule versions**, không chạy backtest
mới: R094/R095, 27 bản R096–R122, R123; 2022–2024 development đã exposed.
Hai cost scenarios có entry timestamps giống nhau, không cộng thành hai mẫu.
Lịch giữ 753 phiên, 157 nhóm tuần ISO (có tuần biên/nghỉ lễ) và 36 tháng.

| Bộ luật | Lệnh / 3 năm | Mỗi 5 phiên lịch | Tuần không lệnh | Tháng ít nhất / trung vị / nhiều nhất | Đọc đúng kết quả |
|---|---:|---:|---:|---:|---|
| R094 phá biên đầu phiên | 677 | 4,50 | 0/157 | 16 / 18 / 23 | Nhịp khá đều trong mô hình; chưa đủ edge và còn held gaps |
| R095 phá biên rồi quay lại range | 269 | 1,79 | 23/157 (14,6%) | 4 / 7 / 13 | Cơ hội ít hơn do phải chờ thêm một sự kiện |
| R123 hồi rồi vượt lại MA | 165 | 1,10 | 47/157 (29,9%) | 1 / 4 / 10 | Khá đều theo năm nhưng không đều theo tuần/tháng |
| R120 pullback MA40/160 | 15 | 0,10 | 142/157 (90,4%) | 0 / 0 / 2 | Quá thưa cho vai trò daytrading chính đang tìm |
| Cả nhóm 27 bản pullback A/B/C | 13–32 **mỗi bản** | 0,086–0,212 mỗi bản | Xem JSON từng version | Xem JSON từng version | Nhiều biến thể không tạo nhiều cơ hội độc lập |

Mỗi bộ trong bảng đều có cap một attempt/ngày. R094 có 152/157 tuần đạt ít
nhất 3 lệnh; R095 có 34, R123 có 11, R120 có 0. Khoảng không có entry dài nhất
trong một sổ năm: lần lượt 2 / 10 / 26 / 146 phiên. Đây là khoảng trong lịch
mô hình, **gồm warmup/data blocks**, không phải chỉ ngày hợp lệ nhưng không setup.

Ví dụ quan trọng: R123 có 58/50/57 lệnh qua ba năm, nhìn tổng năm khá ổn;
nhưng gần 30% tuần trống và tháng chỉ 1–10 lệnh. Không dùng annual average
để hứa tháng nào cũng có cơ hội như nhau.

R094/R095 có held paths chưa biết (1/3/1 và 0/1/0 theo năm). Bảng đếm entries
đã ghi trong mô hình, không chứng minh state/entry tiếp theo nếu phần giá thiếu
diễn biến khác. Không tự coi unknown thành ngày thị trường không có tín hiệu.
Ngay cả R123 đủ held M1 coverage cũng chưa có target broker/news/forward proof.
Không lấy cadence đẹp để phục hồi verdict kinh tế của R094 hoặc các bản đã gác.

Nguồn: [opening screen](US500-M15-OPENING-SCREEN-RESULTS-20261111.md),
[27 bản multiframe](US500-MULTIFRAME-FULL-TABLE-20261111.md),
[R123 fit](STRATEGY-FIT-REVIEW-20261111.md). JSON audit mới giữ đủ từng tháng,
quý và weekly distribution của cả 30 bản, không chỉ bốn dòng đại diện.

## Nhóm nào dễ nhiều/ít cơ hội, dễ code đến đâu?

Bảng dưới là **suy luận theo cấu trúc luật**, không thống kê tần suất trung
bình của tất cả bot trên thị trường. Ngoài những bản đo ở trên, chưa có cơ sở
gán số lệnh/tuần cho một tên chiến lược. “Dễ code” nghĩa dễ định nghĩa/kiểm
tín hiệu; để giao dịch tin cậy vẫn cần fills, risk, restart và reconciliation.

| Nhóm ý tưởng | Nguồn cơ hội / độ đều dự kiến | Độ dễ viết tín hiệu bot | Mức ưu tiên theo riêng cadence/code |
|---|---|---|---|
| Phá biên đầu phiên (ORB) | Có range mới mỗi phiên; tối đa một cú đầu tiên nếu cap1/ngày; không đảm bảo ngày nào cũng có entry | Cao: giờ, high/low, close xác nhận rõ | Cao để nghiên cứu cơ chế theo phiên; exact R094 vẫn gác |
| Đi theo chuyển động trong ngày ở giờ cố định | Có một thời điểm đánh giá mỗi phiên; filters có thể làm nhiều ngày không trade | Cao: clock + return trước decision + exit rõ | Cao về khả năng đo; các recipe close-momentum cũ không tự chạy lại |
| Pullback theo xu hướng, ít điều kiện rõ | Chỉ có khi vừa có hướng vừa có hồi; dễ dồn lệnh vào một loại thị trường | Cao nếu dùng MA/ATR/nến đóng; thấp hơn nếu “zone đẹp” chưa định nghĩa | Trung bình–cao nếu có cơ chế mới; audit cơ hội trước PnL |
| Cắt MA / phá kênh intraday nhiều lần | Cho phép xét nhiều cơ hội trong phiên; đi ngang có thể tạo chuỗi tín hiệu đảo liên tục | Cao, nhưng cần cooldown/rearm/cap rõ | Dùng làm baseline hoặc nghiên cứu có kiểm soát; không ưu tiên số lệnh tối đa |
| Quay về trung bình theo band/RSI | Có thể lặp lại trong ngày đi ngang; thị trường chạy một hướng có thể ít entry hoặc nhiều entry xấu | Cao nếu rule số học rõ | Dự phòng để đối chiếu; không đổi ưu tiên xu hướng của owner |
| VWAP pullback/reversion | Phụ thuộc session anchor và volume; tên VWAP không tự quyết định nhiều/ít lệnh | Trung bình: phải có nguồn volume phù hợp và clock đúng | Để sau khi xác minh data; tick-volume proxy phải đặt tên riêng |
| Phá giả / breakout-retest / cấu trúc nhiều bước | Phải có chuỗi sự kiện; càng thêm bước càng dễ mất cơ hội, nhưng cap setup đầu có thể làm quan hệ không đơn điệu | Trung bình; pivot/zone/expiry/confirmation phải causal | Thấp hơn nếu mục tiêu trước mắt là nhịp đều, không bác bỏ cả họ |
| Theo tin/sự kiện hiếm | Dồn quanh lịch sự kiện; đều theo lịch kiểm không đồng nghĩa đều số trade | Khó hơn về known-at, news feed, execution và rule quỹ | Chưa ưu tiên làm lane thu nhập chính đơn lẻ |
| Scalping nhiều lần / market making | Có thể rất nhiều order/fill, dễ đếm trùng một cơ hội; phụ thuộc spread/latency/queue | Viết tín hiệu đơn giản có thể dễ, mô phỏng/vận hành đúng khó | Không mở lane này chỉ để tăng số lệnh cho US500/M15 |

ORB có upstream implementation thật trong
[LEAN](https://github.com/QuantConnect/Lean/blob/master/Algorithm.CSharp/OpeningBreakoutAlgorithm.cs).
[Nautilus quickstart](https://nautilustrader.io/docs/latest/getting_started/quickstart/)
minh họa indicator cập nhật theo bar/event; tài liệu latest hiện là 2.x,
không dùng API đó thay pin 1.231.0 của các books hiện có. Những ví dụ này chứng
minh có thể viết luật thành code, không chứng minh tần suất/edge trên CFD US500.

## Bao nhiêu là nên ưu tiên cho owner?

| Nhịp bình quân trên tuần đủ 5 phiên | Cách phân bổ nghiên cứu đề xuất |
|---|---|
| Dưới 1 lệnh | Ít phù hợp làm lane intraday/thu nhập chính duy nhất; có thể giữ ý tưởng tốt cho vai trò khác |
| 1 đến dưới 3 | Xét có chọn lọc nếu có cơ sở kinh tế mạnh; cần chấp nhận nhiều tuần vắng và thu thập mẫu lâu |
| **3–5** | **Ưu tiên tìm kiếm hiện tại**: nhịp vừa, tương thích thiết kế cap1/ngày, dễ quan sát theo nhiều phiên |
| Trên 5 đến 10 | Cần nhiều hơn một entry/ngày ở một số phiên; version/cap/account-wide budget mới, không tự mở |
| Trên 10 | Không mặc định tốt hơn; đòi kiểm kỹ turnover/costs, cụm lệnh cùng ngày và execution |

3–5 không phải ngưỡng có edge. Có chiến lược ít lệnh nhưng lời tốt; có bot đều
mỗi ngày nhưng đều thua. Không loại hồi tố theo bảng này hoặc chỉnh rule chỉ
để chạm dải. Thu nhập cần kiểm riêng lợi thế, vốn, drawdown và reward, không
được suy từ số lệnh. Dải campaign3–8 cũ vẫn là preference rộng; current
cap1/ngày không thể đạt8 trong tuần5phiên. Planning owner vẫn ở
[cadence/income](DAYTRADING-INCOME-CADENCE-20261111.md).

## Đo “đều” bằng gì ở những lượt tiếp theo?

1. Báo cả mean/median, khoảng phân bố mỗi tuần/tháng; giữ kỳ không có lệnh.
   Không chọn mẫu số chỉ gồm ngày đã trade hoặc tháng thuận lợi.
2. Đo % tuần không entry, chuỗi phiên vắng dài nhất, quarterly counts và nhịp
   rolling13tuần trên development để thấy chậm dần/dồn theo mùa. Không đặt
   một ngưỡng tuần trống “chuẩn khoa học” khi chưa có dữ liệu hỗ trợ.
3. Tách **giờ được đánh giá → setup → confirmed signal → risk/cap-admitted
   entry → fill**. Một setup lặp 5 nến, một order có partial fills hay nhiều
   lệnh cùng đợt giá không là 5 cơ hội độc lập.
4. Tách 0 vì không setup khỏi data unavailable/warmup/news/risk cap/outage;
   báo coverage riêng. Audit này chỉ có calendar và entry trace, **chưa có
   đủ reason-by-day của mọi version**, không tự điền nguyên nhân.
5. Kiểm qua nhiều quý/regime, hai chiều và đúng clock/DST. Độ đều của số lệnh
   khác độ đều lợi nhuận; nhiều entry phụ thuộc nhau không tự làm winrate
   ước lượng chính xác như cùng số quan sát độc lập.

## Research bổ sung và giới hạn áp dụng

Các nguồn kiểm 11/11/2026, phần suy luận/đề xuất ở trên là của agent:

- [Graczyk & Queirós, intraday seasonalities](https://arxiv.org/abs/1810.12099):
  nghiên cứu cổ phiếu DJIA 2003–2014 cho thấy hoạt động trong phiên có cấu trúc
  theo giờ và cấu trúc này thay đổi theo thời kỳ. Không giả định mọi M15 hoặc
  mọi năm có cùng mật độ cơ hội; không ngoại suy số trade sang CFD.
- [Baltussen và cộng sự, JFE2021](https://academicweb.nd.edu/~zda/intramom.pdf):
  nghiên cứu intraday momentum ở nhiều futures, liên hệ hedging demand. Có cơ
  sở nghiên cứu cơ chế theo thời điểm, không phải bằng chứng mọi trend bot có
  edge. [CFD adaptation first→last cũ](US500-CLOSE-MOMENTUM-RESULTS-20261108.md)
  đã âm ở assumptions đăng ký; không gọi recipe đó mới hoặc tự chạy lại.
- [LEAN scheduled events](https://www.quantconnect.com/docs/v2/writing-algorithms/scheduled-events):
  clock/consolidator/event sequence và live-vs-backtest timing cần kiểm; chỉ
  viết một giờ vào code chưa chứng minh entry đúng lúc.
- [MetaQuotes volume types](https://www.mql5.com/en/docs/constants/indicatorconstants/prices):
  phân biệt tick volume và trade volume. VWAP cần chốt đúng input, không lấy
  bất kỳ trường volume nào rồi coi là dữ liệu giao dịch tập trung tương đương.
- [FTMO news](https://ftmo.com/en/faq/can-i-trade-news/):
  lịch tin hạn chế execution với Standard funded khác Challenge/Verification;
  US500 chịu một số tin USD. Cadence trước news gate chưa là cadence vận hành
  cuối. Lượt này chưa áp news gate hoặc tái tính lợi nhuận.

Không có nguồn trên chứng minh3–5/tuần là tối ưu chung. Nguồn web bổ sung lý do
đo theo clock/regime/data; số lệnh trong bảng đầu đến từ project, không từ bot
quảng cáo, ví dụ nhiều cổ phiếu hoặc extrapolation số nến.

## Kết quả, quyết định và evidence

Ưu tiên cơ chế **theo phiên, luật số học ít bước**, vừa có khả năng lặp qua nhiều
ngày vừa tái hiện được bằng bot. Chưa chọn recipe mới hoặc phục hồi ứng viên
đã gác. Không tự chuyển M5/M1, tăng cap/risk hoặc mở nhiều sản phẩm để đủ quota.
Tiếp theo khi owner chọn nhóm: admission ý tưởng theo mechanism/lineage → đếm
cơ hội và phân rã filter trước outcome → economic screen nhỏ → kiểm sâu đúng gate.

Artifact private:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/us500-frequency-landscape-v1/`.
`audit.py` + `result.json` giữ script/hash, inputs, all30versions và metrics.
Native books được kiểm seal/book/review/manifest; opening books có prior reviews
và current hashes, không gọi chúng là native-sealed. Entry timestamps đối soát
reference/stress cho90 annual pairs; calendar/order/dailycap/period sums,
known totals677/269/165, R123weeklydistribution và13–32 range đã kiểm.
Đây là same-agent descriptive audit, không independent code/feed review.

Wall2,118giây là đọc/kiểm/tính sổ đã có, không gồm research/docs/Git. 0financial
replays, 0newstrategytrials; catalogue giữ123records/88policy-modelversions/
53native. Không đọc2025+, không broker/provider/account changes. Không cần
engine/dependency/skill mới: reuse workflow và calendar/book evidence đã có.
