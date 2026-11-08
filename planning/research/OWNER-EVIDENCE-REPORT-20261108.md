# Báo cáo cho owner: đã làm gì, bằng chứng đến đâu?

Đối chiếu hồ sơ ngày **08/11/2026** theo yêu cầu học và kiểm soát dự án của
owner. Lượt này không chạy backtest mới. Đây là bản tổng hợp có nguồn; các
protocol, kết quả và receipt được dẫn giữ bằng chứng gốc. Báo cáo không là
chứng nhận độc lập hoặc bảng trạng thái runtime đang hoạt động.

## Kết luận trước

- **Phần mềm:** có bằng chứng cho một số đường tính giá, tiền, thời gian và
  khôi phục. Đã tìm/sửa lỗi thật; chưa chứng minh toàn hệ thống không còn lỗi.
- **Nghiên cứu:** đã thử nhiều phiên bản và giữ lịch sử. Việc đóng luật trước
  kết quả, tăng chi phí và kiểm lại nguồn có ích. Chất lượng chuyển ý tưởng
  thành công thức và độ tin cậy của bộ sàng lọc vẫn còn điểm chưa giải quyết.
- **Challenge:** chưa có chiến lược đủ bằng chứng để đề xuất mua challenge.
  Hoàn tất một phép thử hoặc một Goal hữu hạn không có nghĩa đạt mục tiêu này.

## 1. Hệ thống có đang làm đúng điều đã quy định?

| Việc đã làm | Bằng chứng cụ thể | Được kết luận gì? | Chưa được kết luận gì? |
|---|---|---|---|
| Kiểm giá và dữ liệu | Có kiểm hash, thứ tự, thời gian, Bid/Ask, tick grid. Đã phát hiện nguồn US500 có phút được decoder tự chèn, rồi tạo lại phần bị ảnh hưởng bằng nến nguồn và giữ lịch sử cũ | Có kiểm dữ liệu và đã sửa lỗi nguồn được phát hiện | Không chứng minh mọi giờ có đủ dữ liệu hoặc giá có thể khớp tại broker đích |
| Kiểm tiền và chi phí | Đọc lại 624 trường hợp EURUSD, kiểm cash, floating, số lệnh và tách commission/slippage/funding. Có cách tính lại từ giá/lot mà không gọi hàm đang được kiểm | Các phép tính được kiểm khớp trong phạm vi đó | Chi phí giả định không tự thành chi phí lịch sử/tài khoản quỹ đã xác minh |
| Kiểm thứ tự quyết định/khớp | Có fixture chống dùng dữ liệu tương lai, kiểm prefix/restore; các mẫu tick đã so cho thấy tín hiệu và entry khớp. Ví dụ đã mở lại: quyết định lúc 07:00:00.000 UTC, quote entry tới sau 90 ms | Có bằng chứng về timing cho những đường đã kiểm | Không phải toàn bộ code được kiểm toán độc lập hoặc mọi loại tín hiệu đều không thể nhìn tương lai |
| Kiểm mô phỏng nhanh so với tick | Nhóm kiểm tuần 03–07/01/2022 có chênh 0,04–0,24 USD do SL. Asia 2024 có chênh cả năm khoảng 74–77 USD, toàn bộ được quy về stop fills | Đã biết mô phỏng nhanh có thể ghi tốt hơn tick; dùng để ưu tiên nghiên cứu | Không có một mức sai số cố định áp cho mọi năm, tài sản hoặc chiến lược |
| Kiểm khôi phục job nghiên cứu | Đã ngắt/restore bài 442.341 tick; state, quyết định và các file cuối khớp lượt không ngắt. Checkpoint cũ thiếu state bị từ chối | Có resume hoạt động trong trường hợp đã kiểm | Không chứng minh mọi job cũ resume được, hoặc broker/MT5 sẽ khôi phục giống job offline |
| Log/version/lỗi | Có protocol, source/input hashes, trạng thái tiến độ, failure và output riêng. Ví dụ cache không hợp phiên bản đã dừng trước numerical; sau đó chỉ kiểm/tái dùng phần dữ liệu có bằng chứng | Có thể lần ngược những lượt gần đây và phân biệt failed/completed/inconclusive | Hồ sơ đầy đủ không tự chứng minh giả thuyết kiếm tiền đúng |

Nguồn: [sửa dữ liệu US500](INDEX-LONG-EXPLICIT-RESULTS-20261108.md),
[kiểm screen và tiền](SCREEN-CALIBRATION-REPAIR-RESULTS-20261108.md),
[annual tick comparison](H1-NATIVE-SURVIVORS-RESULTS-20261108.md),
[resume](NATIVE-RESUME-REVIEW-20261108.md).

### Một ví dụ owner có thể tự tính

Lệnh mô phỏng EURUSD ngày 02/01/2019, không phải lệnh gửi broker:

| Dữ kiện đã đọc lại | Giá trị |
|---|---:|
| Bán tại Bid lúc 07:00:00.090 UTC | 1,14851 |
| Mua lại để đóng tại Ask lúc 13:00:00.115 UTC | 1,14050 |
| Khối lượng / hợp đồng mô phỏng | 0,11 lot / 100.000 đơn vị mỗi lot |
| Lãi trước phí | 88,11 USD |
| Commission khai báo; slippage và funding trong case này | 0,55 USD; 0 và 0 |
| Net trong báo cáo | **87,56 USD** |

`(1,14851 − 1,14050) × 100.000 × 0,11 − 0,55 = 87,56 USD`.

Đã đọc trực tiếp raw ordinals 34.562 và 95.674, không chỉ lấy lại hai giá từ
bảng tổng kết. Ví dụ này kiểm được giá/tiền/thời gian của một lệnh; không xác
nhận lợi thế của chiến lược. Locator gốc nằm trong packet
`execution-v1/eurusd-catalogue13-v1/2019/` và
`execution-v1/fixing-clock-transfer-v1/2019-events.json` dưới private root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.

## 2. Cách tìm và kiểm ứng viên hợp lý đến đâu?

| Câu hỏi owner cần đặt | Thực tế đã làm | Đánh giá hiện tại |
|---|---|---|
| Vì sao chọn các ý tưởng này? | Dùng các họ phổ biến như trend/reversion/ORB/fixing và một số ML. Có nguồn cơ chế; nhiều exact recipes, giờ, SL/exit là project tự cụ thể hóa | Có căn cứ để đặt câu hỏi, nhưng chưa phải tái hiện thành công các chiến lược nổi tiếng hoặc đã pass quỹ |
| Có so công bằng không? | Nhiều bài khóa trước rule, dữ liệu và hai mức chi phí. Hai lượt mới so cùng entry/mask; attribution còn giữ cùng tổng lot và báo cả hai thứ tự phân rã | Có bằng chứng thiết kế công bằng trong những bài đó; không tự chứng nhận mọi bài cũ |
| Có chỉ chọn kết quả đẹp không? | Giữ cả 24 phiên bản FX đã gác, ML thua, control tình cờ lời, thiếu quote, timeout và source correction | Lịch sử gần đây có giữ negative evidence; danh mục chưa phải toàn bộ số ý tưởng từng nghĩ tới hoặc mọi thử nghiệm bên ngoài project |
| Có sửa theo quá khứ rồi gọi là dữ liệu mới không? | Các phiên bản/câu hỏi mới đều ghi lineage và exposure. 2010–2022, 2023–2024 đã xem được ghi là development/robustness đã dùng | Đã phân biệt đúng ở hồ sơ hiện hành; chưa có lợi thế được xác nhận trên clean holdout cho ứng viên challenge |
| Bộ lọc có thể bỏ sót bản tốt không? | Có so một số bản lời/lỗ với tick và giữ nhãn không tự reject cả family. Heuristic số năm dương đã ghi là quy ước chọn workload | **Chưa đo được tỷ lệ bỏ sót.** Không được gọi bộ lọc hoàn chỉnh hoặc chuẩn chung cho mọi chiến lược |
| Có kiểm hợp mục tiêu quỹ không? | Có các đường tick/prop cho Asia và kiểm time-fit/cash của Gold | Đã kiểm một số scope; còn thiếu ứng viên có edge, đúng target costs, validation mới và strategy forward/reconciliation đủ |

Nguồn: [origin/transfer map](STRATEGY-ORIGIN-TRANSFER-REVIEW-20261108.md),
[khung cửa kiểm chứng](../../.agents/skills/strategy-qualification/references/validation-gates.md),
[FX results](EURUSD-CATALOGUE13-RESULTS-20261108.md),
[ML controls](DISCOVERY5-RESULTS-20261108.md).

## 3. Các nhóm đã thử: vì sao giữ hoặc gác?

| Nhóm | Điều đã thấy | Quyết định và lý do |
|---|---|---|
| EURUSD: 24 phiên bản, 13 năm, 2 mức phí | 624 cases; 6 bản tổng dương ở phí chuẩn, 0 bản dương ở phí cao | Gác exact versions. Không phải chỉ do tiêu chí nhiều năm dương khắt khe; không bác cả họ chiến lược Forex |
| Hai model ML thực | Ridge/Forest không đạt; một shuffled control lại dương | Gác hai bản thực, giữ control như nhắc nhở rằng một kết quả dương có thể xuất hiện dù quan hệ tín hiệu bị phá. Chưa định lượng xác suất may mắn từ mẫu này |
| SMA vàng trên 50k | Tổng mô phỏng dương; 10/15 sổ năm dương khi phí cao. Closed cash/time-fit và realism chưa đủ cho challenge | Giữ nghiên cứu, hạ ưu tiên challenge; không tăng risk để ép đạt target |
| Asia→London, native tick | 2023/2024 phí cao còn +18,79/+64,52 USD trên 10k; chưa đạt phase 1 trong những paths đó | Có evidence tick/prop theo scope, nhưng chưa đủ edge hoặc time-fit. Các lượt native này không xóa negative long-history của exact version |
| London, native tick | Reference có kết quả, hai stress jobs timeout | Giữ stress là **chưa hoàn tất**, không suy phần thiếu từ reference |
| US500 | Đã sửa source padding; các recipe đã kiểm chưa qua cửa giữ. Monthly còn thiếu input | Gác hoặc để chưa đủ bằng chứng theo từng bản; không dùng kết quả dữ liệu cũ sai để quyết định |
| Gap cuối tuần | Primary phí cao +25,2 pip năm 2019 nhưng −65,8 pip năm 2022 | Chưa ưu tiên phát triển bot từ probe đó; không đổi giờ/filter để cứu cùng bản |

Nguồn chi tiết: [FX](EURUSD-CATALOGUE13-RESULTS-20261108.md),
[ML](DISCOVERY5-RESULTS-20261108.md), [Gold](GOLD-SMA50K-REVIEW-20261108.md),
[native](H1-NATIVE-SURVIVORS-RESULTS-20261108.md),
[US500](INDEX-LONG-EXPLICIT-RESULTS-20261108.md),
[gap](WEEKEND-GAP-COMPONENT-RESULTS-20261108.md).

## 4. Hai việc mới nhất có làm thay đổi quyết định không?

**Đổi 14:00 sang 14:15:** lựa chọn xuất phát từ khác biệt với nguồn nghiên
cứu, không quét hàng loạt giờ. Đã khóa so sánh trước tính mới. Trên cùng ngày
đủ quote, thêm 15 phút giảm 119 pip năm 2019 và 161,2 pip năm 2022.
**Quyết định:** không đổi exit sang 14:15 để cứu parent. Năm 2019 vẫn giữ một
entry có exit chưa giải quyết; không coi toàn năm đủ dữ liệu.

**SL hay cách chia lot:** trên cùng lệnh và tổng lot, cách chia lot của parent
giúp cả bốn case. Cách thoát theo SL cũ giảm kết quả so với endpoint không SL.
**Quyết định:** chưa có lý do đổi sizing để cứu bản này; cần đo đường giá/rủi
ro trước thiết kế stop mới. Không bỏ SL từ bảng số học đó.

Hai nghiên cứu này có ích vì đã trả lời câu hỏi cụ thể và thay đổi việc nên
làm tiếp. Chúng chưa chứng minh edge: vẫn dùng data đã xem, cùng family, và
phần không SL chưa là portfolio backtest hoặc có drawdown/prop proof.

Nguồn: [clock](FIXING-CLOCK-TRANSFER-RESULTS-20261108.md),
[SL/lot attribution](PRE-ECB-WRAPPER-ATTRIBUTION-RESULTS-20261108.md).

## 5. Những phần mình làm chưa tốt hoặc còn thiếu

- Nhiều báo cáo nhỏ, tên kỹ thuật và số test làm owner khó nắm bản đồ quyết
  định. Từ đây báo theo câu hỏi → phép thử → bằng chứng → giới hạn → quyết định.
- Nhiều recipes là adaptation; có paper/indicator không đủ xác nhận việc
  chuyển sang instrument, timeframe, exit và cost của project giữ được edge.
- Có lỗi thật về dữ liệu và recovery; đã giữ và sửa các lỗi được tìm thấy,
  không được suy ra đã sạch lỗi toàn bộ.
- Review chủ yếu cùng agent bằng code khác. Có oracle/tamper checks, nhưng
  chưa tương đương một kiểm toán độc lập toàn hệ thống.
- Chưa biết error/false-negative rate toàn bộ screen; chưa có fresh validation
  và strategy forward đủ để đề xuất challenge. System demo check không thay
  strategy forward.
- Không có phép đo active research/code time đầy đủ từ đầu; không dùng thời
  gian các job để bịa tổng công sức hoặc chi phí tối ưu toàn dự án.

**Việc tiếp theo có cơ sở:** đo mức giá đi ngược/thuận trước 14:00, đối chiếu
với stop/risk đang có và chất lượng dữ liệu, rồi mới quyết định có đáng thiết
kế một phiên bản stop mới. Chưa mở phép thử đó trong lượt báo cáo này.

Các worker nghiên cứu gần đây đã terminal theo receipts; kiểm process của
các job vừa nêu không thấy còn chạy ở lượt này. Không phải kiểm sức khỏe toàn
bộ app, MT5 hoặc broker. Chưa có ứng viên challenge; không mở holdout/gửi lệnh.
