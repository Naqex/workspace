# Báo cáo cho owner: đã làm gì, bằng chứng đến đâu?

**Hậu kiểm cập nhật10/11:** xem [mục12](#12-làm-lâu-nhưng-chưa-có-kết-quả-hậu-kiểm-delivery-ngày1011)
và [đối chiếu cộng đồng mục13](#13-cộng-đồng-có-gặp-ngưỡng-này-không-đối-chiếu1011).
Owner đã xóa app Goal; task hiện tại là phân tích/báo cáo, chưa chạy nghiên cứu
mới. Các trạng thái active/paused và kết thúc đợt08/11 trong receipts là lịch sử.

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

**Cập nhật sau khi owner giao thực thi:** phép đo đã xong tại
[báo cáo đường giá](PRE-ECB-PATH-RISK-RESULTS-20261108.md). Đã kiểm 519 ngày,
đối chiếu raw cho 8 đường giá mẫu và tính lại số học toàn bộ. Nếu giả định
chưa cắt lỗ và giữ lot cũ, có đường giá lỗ giữa phiên hơn 5R dù cuối phiên
có thể lời. Giữ bản cũ ở trạng thái gác; không bỏ hoặc nới SL từ kết quả này.

### Toán và thống kê được ghép vào lộ trình thế nào?

Owner hỏi tiếp08/11: nên tiến tới mục tiêu hay thêm xác suất/thống kê/toán.
Khuyến nghị là dùng chúng ngay trong các cửa ra quyết định, không tạo thêm
một chiến dịch xây framework hoặc grid search. Lượt này chỉ khảo sát/tư vấn.

| Bước | Phép phân tích có ích | Giới hạn cần giữ |
|---|---|---|
| Trước thay stop | Đo adverse/favorable excursion, phân phối đường giá và các đuôi lỗ; liên hệ với lot/risk đã đăng ký | Lời cuối phiên không chứng minh chịu được lỗ giữa phiên; observed extrema không là bảo đảm broker fill |
| Đánh giá tín hiệu | Net expectancy và khoảng bất định, contribution theo giai đoạn và ít lệnh lớn | Chưa đủ mẫu/assumptions thì inconclusive; không dùng một con số winrate/Sharpe để chứng nhận |
| Kiểm độ nhạy | Một số thay đổi nhỏ có cơ chế, khóa trước kết quả, tính lại sizing khi đổi stop | Không tối ưu hàng trăm tham số trên cùng data rồi chọn đẹp nhất |
| Kiểm selection | Giữ toàn trial/variants/exposure ngay; xem xét DSR/PBO khi return panels và assumptions phù hợp | Chưa có một DSR/PBO đáng tin của toàn catalogue; không tính từ vài annualtotals hoặc ép số variants thành independenttrials |
| Trước challenge | Dữ liệu chưa dùng để thiết kế, native path/prop, prospective demo và reconciliation; resampling/scenarios nếu thích hợp | Monte Carlo không tạo dữ liệu độc lập mới, không sửa data/fill sai và chưa là xác suất pass đã hiệu chỉnh |

Project đã có `tooling/ai-engines/forex_uncertainty.py`: circular block bootstrap
theo các nhóm tuần, lấy chung indices cho pairedcandidate/cost, xuất khoảng95%
có điều kiện cho meanclosedR. CLI hiện chỉ nhận verified flat annualcoarsebooks
2023/2024, dùng planned25USD; output ghi `selection_adjusted=false`, không
futureedge/passprobability, không sửa longregime/tails/simulationerror. Không
đem nguyên công cụ này áp vào pip/constantlot component2019/2022 hoặc gọi là
toàn hệ thống đã có thống kê chuẩn. Code arithmetic/source checks đã có cũng
không thay kiểm định kinh tế.

Nguồn phương pháp đọc/đối chiếu08/11:
[QuantConnect research guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
về hypothesis/OOS;
[Bailey et al.,PBO2015](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
về selection khi thử nhiều cấu hình;
[Bailey/López de Prado,DSR2014](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)
về selection/non-normality. Đây là căn cứ chọn phương pháp, không chứng minh
code hoặc ứng viên của project đã đạt các phương pháp đó.

Các worker nghiên cứu gần đây đã terminal theo receipts; kiểm process của
các job vừa nêu không thấy còn chạy ở lượt này. Không phải kiểm sức khỏe toàn
bộ app, MT5 hoặc broker. Chưa có ứng viên challenge; không mở holdout/gửi lệnh.

## 6. Chưa biết trade tay có vận hành bot được không?

**Có thể. Nhưng nếu không hiểu bot, bạn khó giám sát và dễ sửa sai thứ.**
Đây là khuyến nghị vận hành; không yêu cầu bạn phải trade tay có lãi hay đọc
hết code. FTMO nêu trader vẫn chịu trách nhiệm về objectives/risk dù thuật
toán thực thi; QuantConnect tách riêng rủi ro chiến lược, vận hành và lỗi code.
Nguồn đã đọc ngày 08/11/2026:
[FTMO](https://ftmo.com/en/blog/what-is-algorithmic-trading-and-how-to-use-it-for-the-ftmo-challenge/),
[QuantConnect](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/risks).

| Chỗ chưa hiểu | Rủi ro thực tế | Cách bàn giao trong project |
|---|---|---|
| Bot vào/thoát vì sao | Tin nhầm code chạy đúng nghĩa là có lợi thế | Thẻ chiến lược và ví dụ quyết định → giá → lệnh/khớp → tiền, có cả lỗi và kết quả xấu |
| Lỗ đúng luật khác lỗi ở đâu | Tắt bot sau vài SL, nới stop hoặc tăng lot để gỡ | Ví dụ lời/lỗ/sự cố; đối chiếu phân phối và tiêu chí review đã đăng ký |
| Mỗi lệnh/tài khoản chịu bao nhiêu | Nhầm số dư danh nghĩa là vốn mình có thể mất | USD/R, phần đệm lỗ còn lại của cả tài khoản, gap/slippage và tổng phí owner chịu |
| Mất mạng/AI/PC thì sao | Gửi lặp, hoặc tưởng tắt app là đã đóng lệnh | Diễn tập demo: ngừng vào lệnh, kiểm vị thế/SL tại broker, đối soát kết quả chưa rõ trước khi tiếp tục |
| Điều kiện quỹ/phiên bản nào | Bot vi phạm rule dù có lời | Xác định đúng program, rules/config version và kiểm điều kiện hiện hành trước challenge |

**Thẻ minh họa từ bản đang gác, không khuyến nghị trade:**
`eurusd-h1-pre-ecb02ny-14berlin-atr14x1p5-r025-v1` bán EURUSD theo lịch
02:00 New York vào weekday khi đủ dữ liệu/khởi tạo. Thoát theo SL 1,5 ATR14
hoặc lịch 14:00 Berlin nếu chưa thoát; chia lot theo ngân sách rủi ro cũ.
Tên preECB **không có nghĩa chỉ trade ngày ECB họp**: source `fixing_entry`
là lịch weekday. Cơ chế kỳ vọng theo giờ vẫn là giả thuyết; kiểm tra phí
hiện tại chưa chứng minh lợi thế. Chưa có bot đạt chuẩn challenge để bàn giao;
bạn không cần học thuộc ví dụ này như một chiến lược đã được chọn.

**Ví dụ giả định:** tài khoản 10.000 USD × 0,25% = 25 USD = 1R dự kiến.
Ba lệnh SL đúng luật có thể là −75 USD trong mô hình đó; chưa đủ kết luận
lỗi hoặc mất lợi thế. Ngược lại, vào nhầm tài khoản hoặc thiếu SL bảo vệ
theo policy là sự cố dù lệnh đang lời. SL không bảo đảm lỗ thực tế dừng đúng
25 USD; phải tính cả phí, gap và trượt giá theo từng trường hợp.

Qualification skill đã có nhánh bàn giao: thẻ chiến lược + ba ví dụ (lời,
lỗ, sự cố) + diễn tập khôi phục trên demo + owner giải thích lại. Trạng thái
hiện tại là **prepared_not_demonstrated**: đã chuẩn bị, chưa quan sát bạn
diễn giải hoặc thao tác; không tự ghi bạn đã hiểu. Walkthrough của agent chỉ
kiểm nội dung/routing: bàn giao thì đọc reference và ghi phần còn thiếu;
hỏi tiến độ thì không bắt học trade tay hoặc chạy lại toàn bộ audit. Chưa
kiểm bằng model hay owner độc lập. Không tạo UI, ledger hoặc quyền mới.

## 7. Có đang tìm một thứ không tồn tại không?

Đối chiếu nguồn ngày 08/11/2026. **Có bằng chứng cho việc nghiên cứu giao dịch
hệ thống và khả năng nhận payout; chưa có bằng chứng rằng project sẽ tìm ra
bot đáp ứng toàn bộ mục tiêu của owner.** Không đổi “chưa chứng minh” thành
“không tồn tại”, cũng không suy “có người làm được” thành “mình chắc chắn làm được”.

| Mệnh đề | Bằng chứng | Giới hạn |
|---|---|---|
| Giao dịch có quy tắc có thể có lợi nhuận | [AQR nghiên cứu trend following, 2017](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing) và [quỹ AQMIX đang vận hành](https://funds.aqr.com/funds/aqr-managed-futures-strategy-fund): lịch sử mô phỏng và lịch sử quỹ thực là hai loại bằng chứng khác nhau. Trang AQMIX ngày kiểm ghi annualized10yr5,43% tại30/10/2026, inception05/01/2010 | Đa tài sản/futures, tín hiệu độc quyền và điều kiện tổ chức; không chứng minh recipe EURUSD/CFD của project có edge, phù hợp prop hoặc lặp lại được trong tương lai |
| Payout prop không chỉ là khái niệm | [FTMO công bố payout](https://ftmo.com/en/blog/we-pay-millions-in-payouts-to-our-ftmo-traders/), bài viết có số liệu tới2023/đầu2024 và mô tả người nhận nhiều kỳ | Dữ liệu do hãng công bố, không phải kiểm toán độc lập trong lượt này; không có phân tách manual/auto, tổng phí/thất bại và mã chiến lược để xác minh khả năng tái lập |
| Làm nhiều bot và kiểm nhiều bước vẫn có thể thất bại | [FTMO Big Algo Test](https://ftmo.com/en/blog/a-big-test-of-algo-trading-does-it-work/): hãng mô tả triển khai91systems từ01/04/2018, sau một năm lỗ12.530USD trên100.000USD, drawdown17,6% | Một thử nghiệm cũ do hãng báo cáo; không phải tỷ lệ thất bại toàn ngành hay bằng chứng mọi bot đều thua. Các nhận định chắc chắn về robust/diversify/reverse trong bài không phải chuẩn project tự động chấp nhận |
| Có bot phù hợp đúng mục tiêu owner? | Hồ sơ project hiện chưa có ứng viên đủ bằng chứng | Chưa định lượng được xác suất tìm ra hoặc xác suất pass/payout của owner. Thêm test, code hoặc thời gian không tự tạo edge |

**Cách hiểu mục tiêu:** có lợi thế sau chi phí → đường lỗ chịu được trong
đúng luật quỹ → tiến độ đạt target có ích → vận hành/tuân thủ → payout sau
tổng phí. Một chiến lược có lời dài hạn vẫn có thể không hợp drawdown/clock/
holding rules hoặc quá chậm. Một lần pass/payout chưa chứng minh lợi thế bền
vững: còn may mắn, lựa chọn chỉ khoe người thắng và tổng chi phí đã mất.
Không dùng số dư danh nghĩa funded làm tiền owner thực nhận.

Với một ứng viên cụ thể, bằng chứng cần nối đủ: giả thuyết/công thức và code
khớp; dữ liệu/fill/cost/accounting đúng trong scope; kiểm trên dữ liệu chưa
dùng để chọn/sửa rule và ghi toàn trial history; kết quả/rủi ro không chỉ nhờ
ít lệnh hoặc một giai đoạn; account-wide equity/prop path; prospective demo
và đối soát; cuối cùng payout thực sau tổng phí. Không bước nào chứng minh
chắc chắn tương lai. Không tính pass probability bằng cách đếm các biến thể
đã thử hoặc từ payout aggregate không rõ denominator.

**Quyết định:** tiếp tục từng câu hỏi hữu hạn khi kết quả có thể làm đổi lựa
chọn; chấp nhận gác hypothesis hoặc kết luận chưa tìm được trong phạm vi đã
thử. Không nghiên cứu vô hạn chỉ vì đã đầu tư công sức, không nới risk để
buộc ra winner và không biến mục tiêu thành lời hứa sẽ tìm ra. Lượt này chỉ
đọc hồ sơ và nghiên cứu nguồn, không mở numeric/holdout/broker hoặc Goal mới.

## 8. Quyết định kết thúc đợt Goal theo đầu ra B — 08/11/2026

**Chưa tìm được ứng viên đủ bằng chứng để đề xuất challenge. Kết thúc đợt tự
động hiện tại và chuyển hướng chuẩn bị đầu vào nghiên cứu tốt hơn.** Đây là
đầu ra B đã được owner cho phép trong Goal/campaign; không phải C1/C2 đã đạt,
không phải chứng minh chiến lược phù hợp không tồn tại.

Lượt Goal trước là progress thực: admission hai hypotheses, triển khai và
kiểm R023, commit a84a2fa/c0fe917. [Kết quả](LOCAL-SESSION-RESULTS-20261108.md)
giữ đầy đủ primary/context/control, dữ liệu thiếu, source và review. Lượt
hiện tại đối soát toàn bộ danh mục và các artifacts làm căn cứ, không mở thêm
giá hoặc chạy lại backtest.

### Đã xem xét đủ những gì trong danh mục hiện tại?

Mỗi hồ sơ chỉ nằm trong một dòng dưới; tổng **53 hồ sơ / 41 policy versions**.
Các versions cùng họ, controls và cost scenarios không là lợi thế độc lập.

| Nhóm | Hồ sơ | Kết luận trong phạm vi hiện tại | Điều gì có thể làm đổi quyết định? |
|---|---:|---|---|
| FX rules đã code |19, gồm24versions|0/24 tổng stress dương trên13annual books theo assumptions đã đăng ký; giữ gác, không bác bỏ cả họ | Cơ chế khác rõ hoặc lỗi material được chứng minh, không chỉ đổi ngưỡng để cứu |
| ML và shuffled controls |4|Hai model thật không đạt; control dương không là candidate | Giả thuyết/labels/execution phù hợp hơn và kiểm selection; không train lại để tìm số đẹp |
| Gold đã code |6|SMA50k còn là research survivor; chưa challenge-ready, các bản khác giữ negative | Signal/fill oracle, target costs và equity path đủ tin cậy; xét lại time-fit bằng protocol phù hợp |
| Index đã code |7|Source correction vẫn cho kết quả yếu hoặc thiếu input; monthly chỉ32/132months đủ điều kiện | Dữ liệu source/clock/contract phù hợp recipe, không padding hoặc bỏ năm thiếu |
| Price components R023/24/25 |3|Các primary không đạt tiêu chí giữ của từng phép thử; chưa là bot có risk/SL | Hypothesis mới có cơ sở; không chọn lại side/giờ/calendar sau outcome |
| R019 retest |1|Có thể code/test về kỹ thuật nhưng chưa chọn exact recipe đủ cơ sở để ưu tiên chi tiếp | Mức giá, entry, invalidation/expiry có lý do và cách so baseline; không yêu cầu paper phải chứng minh sẵn mọi rule |
| R020 fixing có điều kiện |1|Clock, lot/SL attribution và path risk đã trả lời; chưa có điều kiện/invalidation mới được chốt | Điều kiện causal có input hợp lệ và lý do kinh tế; không nới stop bằng hindsight |
| R010 volatility variant |1|Phụ thuộc baseline monthly còn vấn đề source/clock; không tự tạo edge | Baseline input được nhận trước, sizing tách rõ tác động và trial mới |
| R026 hedge cuối tháng |1|Fixture một ngày của proxy không đủ long-history, adjusted return, relative-equity mapping và benchmark calendar | Pin những inputs này và khác biệt với paper trước PnL; không đổi thành trade lịch vô điều kiện |
| News |2|Chưa có consensus/actual/revisions/timestamps point-in-time được kiểm | Bộ dữ liệu hợp lệ và recipe causal cụ thể; không dùng dữ liệu đã sửa sau tin |
| Carry/value/cross-section |7|Thiếu funding/vintages hoặc panel nhiều thị trường đồng bộ và method admission | Đầu vào phù hợp và costs/contract; chỉ có series giá hay factor index chưa đủ |
| Risk modifier R036 |1|Quản lý rủi ro không là nguồn edge độc lập | Có baseline đáng giữ rồi mới đo sizing sensitivity |

**Vì sao chọn dừng tại đây?** Trong các lựa chọn đã rà, chưa thấy phép thử
kế tiếp đủ rõ về cơ chế, dữ liệu và khả năng làm đổi quyết định để tiếp tục
tự động chi công sức. Thử R019 vẫn khả thi về kỹ thuật; tải/chuẩn hóa dữ liệu
cho R026 hay multi-market cũng có thể làm thành một chiến dịch khác. Chọn
chưa làm lúc này là đánh giá giá trị nghiên cứu, không giả chúng bị cấm hoặc
đã được chứng minh không hiệu quả. Không lấy việc đã tốn nhiều công sức làm
lý do chạy tiếp và không dừng vì một giới hạn token giả định.

Gold cần giữ cách hiểu riêng: mẫu bắt đầu tháng1 chưa có checkpoint closed
profit đạt target trong12tháng; điều đó không loại mọi rolling start hoặc
horizon dài hơn. Owner chưa chốt deadline cá nhân;12tháng không được biến
thành hạn cứng mới. [Review Gold](GOLD-SMA50K-REVIEW-20261108.md) giữ bản dương
làm nghiên cứu, nhưng không đủ để mua challenge. Không nhân quy mô vốn hoặc
tăng risk để làm nó có vẻ đã đạt target.

### Completion audit của đúng đầu ra B

| Yêu cầu Goal | Bằng chứng đã kiểm | Trạng thái |
|---|---|---|
| Đợt hữu hạn đã đăng ký trước outcomes | Admission hai hypotheses/source a84a2fa; R019 defer và R023 price probe, không thêm policy | Đã hoàn tất đúng đợt |
| Tính toán, kiểm và sửa lỗi trong scope |8fixtures,3.114Fraction event-cost checks,12summary rows,24raw links; lỗi assert format sửa trước numeric; catalogue readiness counts đã đối soát | Đạt trong scope đó, không whole-system certification |
| Kế thừa và giữ negatives/log/timing |13actual result seals/624unique FX cases đọc lại; local/source/result/event/fixture bindings, Gold30books/prefix binding, index/monthly review artifacts được kiểm | Có evidence; không rerun simulator |
| Xét lựa chọn còn lại trước khi dừng | Coverage12nhóm phía trên,53IDs không trùng/thiếu và41distinct versions | Đã rà danh mục hiện có; không exhaustive search mọi chiến lược có thể tồn tại |
| Bàn giao quyết định, giới hạn, mở lại | Mục này, báo cáo kết quả và current-context/index | Đủ cho quyết định dừng đợt, không đủ cho challenge |
| Giữ authority/data gates | Lượt review không simulation/network price/broker calls, không đọc2025+, không process nghiên cứu còn chạy khi kiểm | Không mở quyền mới |
| Tách B khỏi A | C1 chưa đạt; cleanOOS, nativeprop/targetcost, strategyforward và owner thao tác vẫn chưa đủ bằng chứng | Không đề xuất mua hoặc chạy challenge |

Private audit `execution-v1/goal-opportunity-review-v1/review.py`,manifest,
result/progress giữ cách phân nhóm và các kiểm tra. ResultSHA:
`d2c92b453dabdf17d378e6ca037d25f65337153d004907fe00e543d368420600`.
Review2,147s,0simulation/newprice/network/broker calls; cùng agent, không
independent audit. Nó kiểm coverage/bindings và đọc lại các tổng đã có,
không chứng nhận mọi kết quả cũ là đúng hoặc screen không bỏ sót chiến lược.

Giới hạn còn lại không bị xóa: declared costs chưa thành target-broker
history, coarse không full tick/prop path, nhiều mẫu đã exposed, selection
và global false-negative rate chưa được định lượng, các gaps/unknowns đã nêu
vẫn còn. Những phần này ngăn promotion, không phải thành tích đã hoàn tất.

Không dừng vì FTMO cấm bot: [FAQ hiện hành](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/)
cho phép algorithmic/EAs trong điều kiện của hãng. [2-Step](https://ftmo.com/en/2-step-challenge/)
vẫn ghi10%/5%,daily5%/overall10% và unlimited khi kiểm08/11; một candidate
có lời vẫn phải đáp ứng profile/terms cụ thể. Không dùng rule của FTMO thay
The5ers hoặc tự mua tài khoản để bỏ qua thiếu evidence.

### Mở lại theo điều kiện nào?

Ưu tiên **một** hướng có thay đổi đầu vào rõ: method có quy tắc tái hiện được,
đủ gần instrument/horizon/cost thực tế và có dữ liệu hợp lệ; hoặc hoàn tất
input admission đang thiếu cho một cơ chế như R026. Trước chi thêm compute,
ghi khác biệt với các bản đã thử, dữ liệu nào sẽ được dùng, cách bác bỏ,
chi phí/thời hạn đợt và điều kiện giữ/gác. Không cần học trade tay có lãi
trước; không tạo skill/framework/model mới như điều kiện thay thế edge.

Nếu review khác tìm thấy lỗi material trong source/fill/cost, sửa và kiểm lại
đúng phần bị ảnh hưởng theo quy trình sẵn có. Chỉ xem holdout khi có survivor
và protocol/quyền riêng; không mở dữ liệu mới chỉ để tiếp tục tìm kết quả đẹp.
Mọi mở lại giữ mục tiêu vốn quỹ/risk thấp và quyền broker/account/payment
riêng. Hiện không đăng ký job hoặc automation chạy tiếp sau khi Goal kết thúc.

## 9. Đúc kết09/11: vì sao chưa có ứng viên, dữ liệu đã đủ lớn chưa?

Owner yêu cầu phân tích sau khi tạm dừng Goal. Chỉ đọc lại kết quả, không
backtest/fetch giá hoặc tiếp tục discovery. Chưa đủ bằng chứng challenge khác
với đã chứng minh không chiến lược nào có thể đạt challenge.

| Phát hiện | Bằng chứng cụ thể | Giới hạn / bài học |
|---|---|---|
| Economics sau phí là trở ngại rõ | Catalogue13:24FXversions×13years×2costs=624cases,6versions tổng chuẩn dương nhưng0stress tổng dương | Không chỉ do year/block gates khắt khe; chỉ loại exact recipes/assumptions, không cảForex |
| Có lời vẫn có thể mỏng/chậm | R056continuous10k/25USDplannedrisk:3.171closedtrades/2010–22,stressnet+1.078,12USD toàn13năm,2/4blocks âm | Không dùng tổng dương làm khả năng đạt target hoặc ngoại suy thời gian pass |
| Survivor còn concentration/time-fit | Gold50k:15annualbooks/220stressclosedtrades,10/15years equity dương;0/15books có checkpoint closedcash+5k trong năm | Không exhaustive rollingstarts, chưa fullprop; năm nhiều nhưng số trade không lớn, vài winner đóng góp nhiều |
| Chuyển ý tưởng sang CFD có thay đổi quan trọng | Origin/transfer review:indicator,clock,horizon,SL/sizing,ETF/futures→CFD/funding/universe khác nguồn | Có paper không xác nhận projectrecipe; cần giảm khoảng cách method trước chi compute |
| Engineering đã có lỗi thật | Sourcepadding; reviewer bỏQ2/Q4; gap/stopmodel khácnative | Sửa affectedscope và giữ failures; chưa whole-system independent audit; không thể quy toàn bộ negatives cho bugs |
| Bộ lọc có unknowns | Một số recipes có gates đòi cácblocks/years dương; chưa đo globalfalse-negative rate | Các ngưỡng là researchpriority heuristics, không luật quỹ hoặc chuẩn thống kê chung; không hạ hồi tố để cứu losers |
| Dữ liệu nhiều chưa thành validation mạnh | 80records/58policy-modelversions gồm controls/variants; nhiều window consumed; mới nhất chỉ2019/2022 | Không80independentstrategies hoặc nhiều proof độc lập; cần alignedreturns/selection/untouchedvalidation đúng stage |

Nguồn: [FX624](EURUSD-CATALOGUE13-RESULTS-20261108.md),
[R056](PRE-ECB-SESSION-RISK-RESULTS-20261108.md),
[Gold](GOLD-SMA50K-REVIEW-20261108.md),
[transfer](STRATEGY-ORIGIN-TRANSFER-REVIEW-20261108.md),
[source correction](INDEX-PAPER-WINDOW-SOURCE-CORRECTION-20261109.md),
[catalogue](STRATEGY-CATALOGUE-20261107.json),
[R080](US500-EU-OPEN-COMPONENT-RESULTS-20261109.md).

### Quy mô: tách raw observations khỏi bằng chứng độc lập

| Nguồn / phạm vi theo receipts đã có | Quy mô | Đánh giá đúng |
|---|---|---|
| EURUSD evaluation2010–2022 |325.614.557ticks,13năm | Đáng kể cho research cá nhân và loại exactFXversions; không325triệu trade hoặc marketregimes độc lập |
| Gold2010–2024 |5.399.878M1rows,15năm;SMAstress220closedtrades | Dài về lịch sử, sampletrades của exactstrategy vẫn tương đối hạn chế và phụ thuộc |
| US500/NASDAQclosing scope |16.080.264jointticks/1.996instrument-hours/998asset-days | Dày tại cửa sổ cuối phiên2019/2022, khôngfull15yearintraday hoặc998ngày độc lập giữa hai chỉ số |
| NewEU-openR080 |499plannedwindows,439resolved,60unknown |2019coverage76,71%,2022=99,20%; không đủfullannualpath chỉ vì có fullcalendarfiles |
| Freshvalidation/targetexecution | Chưa candidate đủcleanOOS+prop+strategyforward | Đây mới là phần thiếu để promote, không phải thiếu thêm millions ticks trùng cùngwindow |

Các phạm vi trên khác asset/window/format và có overlap; không cộng thành
unique globaldataset hoặc cập nhật inventory toàn máy. Rawvolume không chứng
minh effective sample size; chưa tính một con số effectiveN đáng tin cho cảcampaign.

**Đánh giá của mình:** dự án đã có nền nghiên cứu đáng kể, nhưng chất lượng
giả thuyết/transfer và bằng chứng sau phí đang hạn chế kết quả hơn compute.
Đã dành nhiều công cho reliability/performance; tiếp tục đổi tên indicator/
giờ hoặc tăng số batch trên cùngdata không tự tạo nhiều cơ hội kinh tế mới.
Đây là chẩn đoán có căn cứ, chưa attributionthống kê mọi failure thành tỷ lệ%.

Nếu owner tiếp tục: chọn ít cơ chế khác nhau có method/input gần đúng sảnphẩm,
kiểm gross→spread→fees→funding/slip trước wrapper đắt; phân biệt economicfail,
dataunknown và prioritygatefail. Với borderlinecases, review thiết kế bộlọc
trước outcomes mới thay vì relabel parent; chỉ survivor mới qua validation
chưa dùng/nativeprop/prospective. Không ưu tiên tải bulk, đổiGPU/RAG hoặc chạy
thêm biến thể chỉ vì dễ làm. Đây là khuyến nghị, **chưa dispatch khi Goalpaused**.

[QuantConnect research guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
đã đọc lại09/11: hypothesis trước tuning, lưu ý overfitting khi dùng lặp cùng
data và giữ OOS. Không áp các heuristic counts trên trang làm chứng nhận
hoặc ngưỡng loại universal cho catalogue của project.

## 10. Edge và cơ hội khác nhau: giải thích cho owner09/11

Lượt tư vấn tiếp theo, Goal vẫn paused. Đây là cách phân loại để định hướng,
không protocol mới, statistical independence certificate hoặc quyền chạy tiếp.

**Edge** là lợi thế có căn cứ khiến kỳ vọng lợi nhuận sau chi phí dương trong
những điều kiện xác định. Net dương trong một backtest chỉ là ước lượng có
thể do may mắn, selection hoặc mô hình sai; chưa đủ xác nhận edge. Không cần
thắng từng lệnh hoặc mọi thị trường. Phần bù cho rủi ro khó chịu cũng có thể
tạo expected return nhưng không tự là alpha hoặc hợp giới hạn lỗ của quỹ.

Ví dụ giả định: win45%, trung bình thắng50USD/thua25USD trước phí, tổng chi
phí chưa trừ2USD/lệnh: expectancy=0,45×50−0,55×25−2=6,75USD/lệnh. Chưa dự báo
100lệnh sẽ lời675USD hoặc chứng minh những tham số đó tồn tại trong project.
Nếu lấy average win/loss đã net thì không trừ cùng chi phí lần nữa.

Không có số loại edge cố định. Bảng dưới chia theo cơ chế kiếm tiền, có thể
giao nhau; không phân loại theo tên indicator/model hoặc coi mỗi hàng có edge.

| Cơ chế giả thuyết | Ví dụ / trạng thái project | Độ phù hợp ban đầu với mục tiêu |
|---|---|---|
| Trend/momentum | SMA/Donchian/breakout: tiếp diễn chuyển động; đã thử nhiều adaptations | Có thể tự động hóa, nhưng ít winner lớn/whipsaw cần kiểm; chưa qualified |
| Mean reversion | RSI/IBS/Z-score: mất cân đối tạm thời rồi hồi lại | Có thể tự động hóa; chi phí và lỗ đuôi khi thị trường chạy một chiều quan trọng |
| Dòng tiền/sự kiện có cấu trúc | Fixing, tái cân bằng, phản ứng tin; đã thử một số clock proxies, news inputs còn thiếu | Đáng xét khi có causal mechanism/calendar/input; clock-only không chứng minh flow |
| Relative value | Tài sản liên quan lệch nhau rồi hội tụ; fixed FX/metal formation chưa đạt | Có thể giảm một phần directional exposure, nhưng thêm basis/breakdown/two-leg costs và data requirements |
| Carry/risk premia | Nhận lợi tức/phần bù giữ rủi ro | Cần đúng sản phẩm; CFDswap có thể khác underlyingcarry; holding/tail risk có thể không hợp prop |
| Execution/liquidity | Lợi thế giá khớp hoặc cung cấp thanh khoản | Không ưu tiên với bot MT5 retail hiện tại; chưa có hạ tầng/venue access hoặc measured advantage tương ứng |

Đây là taxonomy của bản tư vấn, không sáu nhóm học thuật duy nhất. Ví dụ
[AQR2015](https://www.aqr.com/insights/research/journal-article/understanding-style-premia)
chia style premia thành value/momentum/carry/defensive: axis khác, không proof
cho CFD recipes của project. AI/ML là phương pháp khai thác thông tin;
backtest nhanh/log chuẩn là năng lực nghiên cứu; cả hai chưa tự tạo edge.

### Cơ chế khác không tự là lợi nhuận độc lập

SMA20/80 và Donchian20 có thể cùng long EURUSD khi USD yếu; thêm GBPUSD cũng
có thể tăng cùng USD exposure. Trend và reversion là hai giả thuyết khác, nhưng
phải đo synchronized net returns, positions/factor exposure, losing periods
và joint drawdown trước nói diversifying. Correlation thấp ở một mẫu không
chứng minh independence hoặc giữ được trong stress. Không cộng riêng những
trade được chọn để thay chronological portfolio/account-wide risk replay.

Ưu tiên breadth theo cơ chế trước, depth bằng một số variants có lý do sau.
Biến thể dùng kiểm sensitivity/robustness hoặc sửa assumption có căn cứ;
không bị cấm, nhưng phải có lineage/trial count và freeze trước outcomes mới.
Mỗi hypothesis cần trả lời: lợi nhuận dự kiến đến từ đâu, input nào biết lúc
quyết định, khi nào cơ chế mất tác dụng, và còn gì sau tổng phí. Không gọi
proposed family là proven edge hoặc gán probability pass từ expectancy riêng.

Loại nghiên cứu hiện tại (rules, price/time/flow proxies, khung không cần tốc
độ cực cao) phù hợp năng lực bot/data của project ở mức định hướng. Những exact
versions đang có chưa chứng minh đủ edge/prop fit. Next recommendation vẫn là
ít cơ chế tái hiện tốt, bám đúng instrument/horizon trước thêm biến thể, không
all-family search, tăng risk hoặc bỏ results/gates cũ. Chưa thực thi khi paused.

### Challenge có chi phí giao dịch

Nguồn chính thức đọc09/11:

- [FTMO infrastructure FAQ](https://ftmo.com/en/faq/how-does-the-ftmo-technical-infrastructure-work/):
  mô phỏng evaluation có commissions theo symbol và execution delay; slippage
  có thể hai chiều. Exact phí/spec phải kiểm theo account/platform/symbol.
- [The5ers spreads/commissions FAQ](https://the5ers.com/faqs/what-are-the-spreads-and-commissions/),
  trang cập nhật22/07/2026: Forex4USD/lot roundtrip, indices commission0,
  metals/oil/crypto theo tỷ lệ; spread và swap vẫn có. Không extrapolate một
  spread công bố lúc bình thường thành spread cố định mọi thời điểm.
- [FTMO25/09/2025 announcement](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
  là lịch sử rate change, không tự nâng thành current-account fee verification.

Phí giao dịch mô phỏng tác động PnL tài khoản; phí mua challenge là khoản tiền
owner trả riêng. Commission0 không bằng totalcost0. Khi đã dùng Bid/Ask cho
fill thì không trừ spread lần hai; fee/funding/slippage phải đúng semantics.

## 11. Chỉ tham gia lúc có lợi và nghiên cứu market mechanics09/11

Owner dùng ví dụ1→10 để hỏi vì sao không chỉ giao dịch đoạn có edge. Diễn
giải có hai khả năng, chưa mặc định owner muốn chọn winners hồi tố: chọn
điều kiện trước entry, hoặc dừng khi đạt mốc lời. Không backtest mới/không
resume Goal trong lượt tư vấn này.

- Edge là expected net advantage có điều kiện, không bảo đảm sau đúng10lệnh
  phải dương. Một sample dương/âm ngắn chưa chứng minh kỳ vọng tương ứng.
- Rule conditional có thể hợp lý ngay cả khi unconditional rule âm. Ví dụ
  giả định20%opportunities thuộcA có expectednet+3USD,80%thuộcB−2USD: giao
  dịch tất cả có expectednet−1USD/opportunity; chỉ chọnA có thể+3USD/selected
  trade nếu nhận diệnA bằng thông tin có sẵn trước entry và ước lượng đúng.
  Không phải actualproject numbers hoặc đảm bảo nhận diện đượcA.
- Biết lúc nào nên đứng ngoài là một phần policy. Regime/session/spread/news
  eligibility là hypotheses cần cơ chế, data known-at và đăng ký trước new
  outcomes; không quét filters trên cùngdata rồi gọi subgroup đẹp là newOOS.
- Stoptrading ở target/profit/dailybudget là rule có thể kiểm để phù hợp prop.
  Nó có thể thay pass/survival paths; không tự biến mọi âm-expectancy process
  thành positiveedge. Phải giữ cả paths không chạm target, lỗ/vi phạm trước
  target, costs và actualnextopportunities; không chọn điểm dừng sau khi xem.
- Đính chính: không phải mọi bản đều totalnegative. R056 và GoldSMA có tổng
  dương dưới assumptions riêng, nhưng chưa qualification; giữ lý do khác nhau.

### Đang thử gì, khung nào?

| Phạm vi theo protocols/results đã đọc | Khung tín hiệu/nguồn | Giai đoạn |
|---|---|---|
| EURUSD catalogue24versions | H1/H4 rules, observedBidAsk/ticksource; một số native survivors kiểm tick | Longscreen2010–2022; có các follow-up2023/24 đã consumed, không mặc định mọi version fulltick |
| XAUUSD/Gold | H4trend/reversion/session rules; M1→H1/H4/coarse và nguồn khác tùy study | Longscreen/review2010–2024; SMA50k evidence cóannualresets, không continuous account |
| US500/NASDAQ100 adaptations | Chủ yếuM1cashsession signals, một H4SMA probe; closingwindow tick checks riêng | Nhiều cơ chế mới chỉ2019/2022development; khôngfullhistorymọirecipe |
| GBPUSD/AUDUSD; silver | FXH1pricecomponents; metalsrelativeformation | FXsource2010–24 cógaps; formation/source không equivalent fullbot/propqualification |
| R080 mới nhất | FixedUS500EU-open, M1Open23:31→03:31NewYork, khôngVIXcondition |2019/2022consumed,439/499resolved; giữ60unknown |

M1/H1/H4 là độ dài nến1phút/1giờ/4giờ, không mặc định thời gian giữ lệnh.
Tick là từngquote update; test granularfills khác timeframe quyết định. Nhiều
study cùng asset/year/source overlap, không cộng thành independent evidence.
Own2025+ vẫn đóng; không bó hẹp mọi nghiên cứu vàoEURUSD hoặc mộtkhung duy nhất.

### Cơ chế vận hành thị trường: có căn cứ để đổi trọng tâm nghiên cứu

Nên đặt cause/effect và đúng data/product trước indicator recipes; điều này
bổ sung phương pháp chứ không thay netcost/OOS/prop checks. Project đã thử
một số fixing/open-close hypotheses, nhưng nhiều rule còn là price/time proxy,
chưa quan sát actualsignedflow hoặc institutionalinventory.

Primary summaries đọc lại09/11:

- [BankofCanada2021-48](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/):
  FXfixing drifts/reversals trong sample gắn orderimbalances, clientdemands
  theo timezone và dealerinventory. Cung cấp cơ chế để đặt hypotheses, không
  xác nhận netCFDrecipe hoặc hiện tại vẫn giữ effect sau costs.
- [NYFed150](https://www.newyorkfed.org/research/staff_reports/sr150.html):
  stoploss clusters liên quan positivefeedback/pricecascades; historical
  evidence, không chứng minh bot thấy được stopmap từ nến hoặc mọi breakout lời.
- [BISMarketsCommittee13/2020](https://www.bis.org/publications/fx-execution-algorithms-and-market-functioning):
  executionalgos giúp matching/liquidity efficiency nhưng có executionrisks.
  Bot của tổ chức có thể chỉ tối ưu khớp một order đã quyết định, không phải
  model dự đoán direction hoặc mộtalpha riêng. AI là công cụ, chưa lợi nhuận.

Khuyến nghị kế khi owner thực sự giao thực thi: map ai mua/bán→vìsao/phải
giao dịch khi nào→dấu hiệu quan sát trước entry→chi phí/rủi ro ai chịu→điều
kiện effectmất→một registered causalrule/abstentionrule. So unconditional
baseline và negativecontrols trên cùng lịch/cost rồi mới validation chưa dùng.
Không tìm thêm bulkdata/AI mới hoặc bỏ oldnegative evidence chỉ từ ý tưởng.

## 12. Làm lâu nhưng chưa có kết quả: hậu kiểm delivery ngày10/11

**Kết luận:** đã tạo được năng lực nghiên cứu và kết quả loại/chưa đủ bằng chứng,
nhưng chưa tạo được đầu ra owner cần: một chiến lược đủ cơ sở xét challenge và
sau đó payout bền vững. Không nên gọi toàn bộ thời gian là vô ích, cũng không
nên lấy số test/file/job hoàn tất để nói mục tiêu thu nhập đã gần đạt. Chẩn đoán
hiện tại là cả economics chưa thuyết phục lẫn cách ưu tiên/phân phối công việc;
không chỉ cần đợi lâu hơn hoặc chạy nhiều hơn.

Owner cho biết đã phát triển project 2–3 tháng. Lượt này đọc lại context,
catalogue JSON, campaign, báo cáo tiền/nguồn/transfer và benchmark; không chạy
backtest mới hoặc audit toàn bộ các repo/phiên chat từ đầu. Không có timesheet
active coding/research/review/rework hoàn chỉnh nên **chưa biết bao nhiêu giờ
hoặc bao nhiêu phần trăm đã lãng phí**. Git timestamps/commit counts và worker
seconds không thay thời gian công sức hoặc chi phí cơ hội.

### Đầu ra nào đã có, đầu ra nào chưa?

| Lát | Bằng chứng kế thừa đã đối chiếu | Giá trị / giới hạn |
|---|---|---|
| Dữ liệu và correctness | Sửa source padding, kiểm raw/quote/timing, đối soát cash/floating/cost, giữ failure và version | Giảm nguy cơ chọn bot từ số sai; chưa phải toàn hệ thống được kiểm toán độc lập |
| Reliability và performance | Có resume bounded; benchmark Q1/2023 5×2 scenarios hoàn tất 1.800,48s và semantic golden parity | Có tài sản dùng lại; không đem job khác workload so để tuyên bố speedup, không tạo edge |
| Bề rộng nghiên cứu | Catalogue hiện có 93 unique IDs, 47 records có implementations với 58 entries; 39 records mang role variant, 9 versions là controls | Không 93 bot hoàn chỉnh hoặc 93 ý tưởng độc lập; 45 records chưa account policy và 1 risk component |
| Economics | FX24versions×13years×2costs =624cases;6versions tổng reference dương,0stress tổng dương | Nhiều exact recipes không đủ biên dưới assumptions đã khai báo; không thể chỉ đổ cho bộ lọc khắt khe |
| Kết quả có vẻ khả quan | Gold SMA50k còn research survivor; R088 component net dương nhưng event-control gate không đạt | Giữ đúng vai trò và remaining gaps; không gọi mọi bản đều lỗ hoặc tự promote |
| Kết quả theo mục tiêu owner | Chưa challenge-qualified; chưa strategy forward/reconciliation và payout evidence của ứng viên được chọn | Chưa có cơ sở lập ngân sách sinh hoạt từ hiệu suất project hoặc hứa ngày kiếm được tiền |

Counts kiểm trực tiếp từ [catalogue JSON](STRATEGY-CATALOGUE-20261107.json);
không biến nhãn `implemented` thành passed edge. Timing/parity ở
[engineering review](ENGINEERING-REVIEW-Q1-20261105.md), FX ở
[624-case results](EURUSD-CATALOGUE13-RESULTS-20261108.md), recovery/correctness
theo các locators mục1. Không recheck toàn private raw/receipts trong lượt này.

### Nguyên nhân, xếp theo ưu tiên thay đổi cách làm

Thứ tự dưới là đánh giá định tính có căn cứ, **không phải tỷ trọng thống kê**:

| Ưu tiên | Vấn đề | Bằng chứng và tác động | Điều cần thay đổi |
|---|---|---|---|
| 1 | Exact hypotheses/transfer chưa đủ biên kinh tế | Paper/indicator đã đổi instrument, horizon, entry/exit, SL và funding; FX nhiều bản gross mỏng hoặc âm | Ưu tiên ít cơ chế tái hiện được trên sản phẩm/chi phí khả dụng; kiểm original→adaptation và cost headroom trước bot wrapper |
| 2 | Công việc dàn trải, đóng nhiều lát nhỏ nhưng chưa đóng một đường ứng viên | Catalogue tăng bằng variants, components, source admission; vẫn chưa có ứng viên qua chuỗi economics→validation→prop→forward | Đợt tới phải có shortlist hữu hạn và câu hỏi quyết định; không mở cơ chế tiếp chỉ vì vừa đóng một source/job |
| 3 | Economics mô phỏng chưa gắn đủ với tài khoản đích | Gold/funding/spec còn unknown; chi phí declared không phải measured target costs | Phân biệt thất bại kinh tế dưới scenario, thiếu dữ liệu và fail priority heuristic; giải quyết gap làm đổi verdict thay vì thêm framework |
| 4 | Có rework kỹ thuật thật | Source padding, reviewer bỏ quarter, recovery và stop/fill khác coarse đã có hồ sơ | Giữ regression/reuse; chỉ sửa affected scope, không làm lại study không đổi hoặc hứa toàn hệ thống sạch lỗi |
| 5 | Độ tin cậy screening chưa được đo đầy đủ | Có bounded coarse/tick checks nhưng chưa global false-negative rate; year/block gates là heuristic ở vài studies | Review borderline theo quy tắc khóa trước outcome mới; không yêu cầu mọi strategy lời mọi năm, không đổi hồi tố old verdict |
| 6 | Báo cáo làm owner thấy hoạt động nhiều nhưng không thấy tiến gần đích | Nhiều technical names, counts và checkpoints; mục5/9 đã thừa nhận khó nắm bản đồ | Báo số ứng viên tiến/lùi stage, lý do và blocker; số test/ticks/commit là bằng chứng phụ |

Chi phí có tác động được đo, nhưng không giải thích mọi thất bại:
[FX attribution](SCREEN-CALIBRATION-REPAIR-RESULTS-20261108.md) trong stress có
15/24 tổng closed gross dương **sau embedded spread**, còn2/24 sau commission/
slippage và0/24 net equity gồm funding/floating. Đây là cùng study, không24
edges độc lập hoặc attribution nhân quả mọi thất bại. Không cộng lại spread,
không hạ phí để tạo winner khi chưa có nguồn target hợp lệ.
[R091 cost headroom](COST-HEADROOM-DIAGNOSTIC-20261109.md) cho thấy spread đã
lớn hơn mid-price gross; [R093](OPTIONS-WEEK-RESULTS-20261110.md) năm2022 âm
trước phí. Ngược lại, R088 net dương không chứng minh riêng FOMC gây ra edge.

**Phần agent cần chịu trách nhiệm:** kiểm soát phạm vi và báo cáo theo kết quả
chưa đủ tốt; đã để activity kỹ thuật che khoảng cách tới mục tiêu kinh tế.
Việc sửa bug/risk là cần thiết, nhưng không đủ lý do tiếp tục tối ưu mọi thứ.
Chưa có bằng chứng rằng chỉ do bug mà tất cả chiến lược thua, hoặc bộ lọc đã
loại mất một winner cụ thể. Không thể bảo đảm đổi cách tổ chức sẽ tìm ra edge.

### Đề xuất đợt tiếp theo — chưa dispatch trong lượt báo cáo

1. Chốt một bảng shortlist tối đa3 hypotheses khác nhau về cơ chế, có input và
   cost khả dụng, kế thừa negatives/lineage. Đây là giới hạn quản lý workload
   đề xuất, không số lượng đủ chứng minh thị trường có cơ hội. Không mặc định
   Gold là core, FOMC là edge hoặc khôi phục loser không có evidence mới.
2. Với từng hypothesis, ghi một blocker quyết định và phép thử nhỏ nhất có thể
   thay đổi việc giữ/loại. Thiếu nguồn material thì defer có điều kiện; economics
   không đạt thì gác exact version; đủ cơ sở mới thiết kế full account policy.
3. Dồn phần kiểm đắt vào ứng viên tốt nhất còn lại: target costs/spec→causal
   equity/risk→validation→prop-specific→strategy forward. Đây là các stage,
   không bắt chạy một lượt mọi thứ hoặc mở holdout/broker để hoàn tất checklist.
4. Kết thúc đợt bằng review shortlist: có bản đủ đề xuất stage kế, hoặc chưa có
   và lý do cụ thể. Không tự mở vòng vô hạn; kết thúc một đợt âm không phải hoàn
   thành C1/C2. Báo thời gian còn thiếu dự kiến riêng, không hứa deadline có edge.

Study mới tuân [recent-first](STRATEGY-VALIDATION-FRAMEWORK-20261105.md#ưu-tiên-dữ-liệu-gần--quyết-định-của-owner-ngày-10112026):
2022–24 vẫn exposed/unverified,2025+ reserved; không mở data mới chỉ từ bản audit.
[Portfolio](PORTFOLIO-RESEARCH-AND-ADMISSION-20261110.md) chưa có aligned panel/
shared-account proof; chưa xây optimizer để che thiếu hypotheses khả dụng.
Không thêm skill/RAG/GPU/framework: các skills hiện có đã mô tả workflow, thiếu
đang nằm ở evidence và ưu tiên thực thi. Đây là self-review có đọc nguồn khác,
chưa một independent audit hoặc kiểm chứng lại toàn campaign.

## 13. Cộng đồng có gặp ngưỡng này không? Đối chiếu10/11

**Có các trường hợp gần giống, không có căn cứ từ chúng để ước lượng tỷ lệ phổ
biến, thời gian trung bình vượt qua hoặc bảo đảm owner sẽ thành công.** Đã mở
bài gốc và phần bình luận liên quan ngày10/11. Đây là convenience sample từ
Reddit, có self-selection, survivorship/reporting bias và có thể quảng cáo;
không xác minh danh tính, code, broker statements hoặc lợi nhuận từng người.
Các case khác futures/options/crypto, chưa cùng FTMO/The5ers và hồ sơ tài chính
của owner. Không dùng thời gian họ kể để hứa lịch đạt mục tiêu cho project.

| Case trực tiếp đã đọc | Họ gặp gì / đã làm hoặc rút ra gì? | Giới hạn |
|---|---|---|
| [6 tháng full-time,17 chiến lược MNQ/NQ](https://www.reddit.com/r/algotrading/comments/1spd5nf/6_months_full_time_on_algo_17_strategies_dead_on/) | Có tick/L2 và custom Rust, chuyển sang Nautilus để giảm viết lại; vẫn không chứng minh edge. Tác giả nói sửa lookahead làm WR84%→53%. Bình luận đề xuất tìm cơ chế, tính phí sớm và theo dõi thời gian bác bỏ ý tưởng | Không có follow-up kiểm chứng họ đã kiếm được tiền. Không lấy WR/p-value/nhận định NQ của tác giả làm chứng nhận hoặc quy luật thị trường |
| [Developer viết bot options7tuần](https://www.reddit.com/r/algotrading/comments/1otf3wg/built_my_own_algorithmic_options_trading_tool/) | Backtest có vẻ tốt, khi live phải sửa liên tục và nhận ra chưa tính slippage; tác giả nhận định nên reuse framework thay vì tự xây tất cả | Đây là bài kể thất bại và hỏi hướng sửa, không một giải pháp đã được đo thành công; options khác CFDprop |
| [Thảo luận AI trong algotrading](https://www.reddit.com/r/algotrading/comments/1sn0yyg/has_ai_actually_helped_your_algo_trading_workflow/) | Một commenter tự kể1,5năm dùng AI vẫn chưa lời, chuyển sang quan sát cơ chế của ví on-chain; người khác thấy AI hữu ích cho code/visualization/loại ý tưởng | Chưa xác minh kết quả sau đổi hướng. Không nhận claims Python luôn leakage, Rust ngăn leakage hoặc AI không bao giờ tạo hypothesis như fact |
| [Infrastructure vs alpha](https://www.reddit.com/r/algorithmictrading/comments/1vu8bu4/infrastructure_vs_alpha_generation_bottleneck_in/) | Chủ bài nói framework/execution gần xong nhưng không có OOSedge; comment đề xuất bắt đầu từ ai phải giao dịch, khi nào, vì sao và điều gì cản arbitrage | Tác giả hẹn thử và báo lại; chưa evidence đã thoát bottleneck. Có comments tự nhận thành công nhưng không hồ sơ kiểm chứng |

Đáng giữ cả phản biện: trong thread17strategies, một commenter đề xuất cứu
subgroup có lời nhỏ; chủ bài đọc lại và cho biết lợi nhuận bị một winner chi
phối, bỏ winner thì âm. Đây là lời kể hữu ích để đặt câu hỏi concentration,
không tái tính thống kê gốc. Một commenter khác nói intradayprop3–4lệnh/tuần
đã live khoảng1tháng, đồng thời thừa nhận còn quá sớm để gọi đáng tin. Không
lấy lời này làm recipe hay hiệu suất FTMO/The5ers đã xác minh.

### Đối chiếu nguồn chính thức và điều áp dụng

[QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide),
đọc10/11, khuyến nghị giả thuyết nhân→quả trước code, nhận diện overfitting và
giữ OOS. Chỉ reuse các nguyên tắc; không áp các bảng30/70backtests,16hours hoặc
số parameters như ngưỡng khoa học chung. Case platform không chứng minh mọi
workflow/data của project đã đúng. Bài [FTMO Big Algo Test](https://ftmo.com/en/blog/a-big-test-of-algo-trading-does-it-work/)
đã đọc lại:4tháng phát triển,91systems triển khai01/04/2018, sau1năm lỗ12.530USD
trên100.000USD vàDD17,6%, theo hãng tự báo cáo. Đây là case lịch sử đã có ở mục7,
không mẫu đại diện ngành/luật quỹ hiện tại. Không nhận các claims về xác suất
lệnh độc lập hoặc đảo chiều loser thành winner trong bài làm bằng chứng.

**Diễn giải cho project:** tìm và chứng minh expectednetedge hiện là nút thắt
khó nhất đang thấy, dựa trên mục12/catalogue, không một thứ hạng khó đã đo cho
toàn ngành. Engineering có acceptance hữu hạn cho từng hành vi; giả thuyết
kinh tế có thể không tồn tại hoặc không đủ mạnh trên sản phẩm/chi phí/quyền
truy cập này. Sau đó còn duy trì edge, execution/risk và payout/counterparty;
không nói vượt bước này là xong hoặc tỷ lệ kiếm tiền đã biết.

Bài học áp dụng ở mức đề xuất: kiểm cơ chế và netcost trước wrapper đắt; dùng
AI để code/đối chiếu/quan sát thay vì lấy output làm proof; reuse nền hiện có;
ghi thời gian tới quyết định và điều kiện mở lại. Không áp deadline2tuần của
commenter thành automaticreject và không quét filters để cứu subgroup đã xem.
Các lời khuyên đơn giản hóa/thêmfilters/đổi market trái nhau; chỉ một registered
experiment mới cho biết chúng có giúp exactrecipe của mình không. Chưa đổi
shortlist/risk/protocol, chạy backtest, mởholdout hoặc kết nối/gửi lệnh. Existing
skills đủ workflow; không thêm framework/skill từ một lượt đọc cộng đồng.
