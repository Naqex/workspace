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
