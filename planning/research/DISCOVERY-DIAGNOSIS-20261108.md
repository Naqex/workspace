# Vì sao chưa có ứng viên challenge? — rà soát 08/11/2026

Owner yêu cầu phân biệt lỗi hệ thống, thiếu sót sàng lọc/kiểm định, chất lượng
hypothesis và thiếu data/thời gian; đồng thời làm rõ nguồn gốc chiến lược.
Goal đang **paused**; lượt này chỉ đọc artifacts/source và research web, không
simulation/train/download market data, không mở holdout hoặc broker authority.
Đây là review cùng agent, không independent certification hoặc full-code audit.

## Kết luận và mức chắc chắn

**Chưa có căn cứ quy nguyên nhân cho một phía hoặc chia tỷ lệ trách nhiệm.**
Bằng chứng mạnh nhất hiện tại: những exact recipes đã thử có economics yếu
hoặc nhạy chi phí; đồng thời discovery/transfer và calibration của screen
chưa đủ tốt để kết luận đã tìm đúng cách hoặc không bỏ sót bản tốt. Chờ lâu
hơn/chạy thêm cùng kiểu không bảo đảm tạo edge.

| Giả thuyết | Đã biết | Chưa biết / quyết định |
|---|---|---|
| Engine lỗi làm mọi strategy thua | Có lỗi dữ liệu US500 padding và timing/recovery đã ghi/sửa; có fixtures, accounting/raw checks và một số tick comparisons | Chưa audit độc lập toàn engine; không khẳng định hết bug, cũng chưa có bằng chứng bug chung gây âm cả24FX |
| Bộ lọc quá khắt khe | Gate9/13 stressyears dương và3bands dương là heuristic, chưa calibrated false-negative rate; coarse không full risk/DD/prop | Không có24FX totalstressdương, nên bỏ gate9/13 thôi vẫn không tạo stress-positive survivor. Không hard-reject family từ coarse |
| Chọn/biến đổi hypothesis chưa tốt | Nhiều bản là adaptation indicator/giờ/exit/SL của project; không exact replication paper;24FX phụ thuộc cùng market/families | Đây là ưu tiên cải thiện có căn cứ, nhưng chưa đo được mức gây mất edge. Cần tách paper mechanism khỏi wrapper trước thêm variants |
| Chỉ thiếu data/thời gian |24FX đã có2010–22;18/24 âm tổng ngay reference,6dương reference nhưng0stress. Gold có aggregate dương; gap probe chỉ21primaryevents | Thêm data hữu ích cho mẫu thưa/uncertainty, fresh validation hoặc regime mới; không mặc định cần nhiều năm hơn cho mọi loser hoặc đủ N sẽ ra winner |
| Chi phí không đúng thực tế | EURUSD observed Bid/Ask có provenance; commission/slippage/funding và historical target contract vẫn declared scenarios | Âm stress là nhạy assumption, không chứng minh âm trên mọi tài khoản thật. Phải bind target costs trước promotion; không hạ phí để cứu outcome |
| Mục tiêu challenge khó hơn có lời | Gold SMA50k retained research nhưng closed-cash evidence chưa đạt target tại checkpoints đã kiểm |3/6/12tháng là diagnostic, không deadline owner đã chốt. Không loại hard chỉ vì chậm hoặc vì không dương mọi năm |

Ưu tiên trên là phán đoán từ evidence, không causal attribution đã được thí
nghiệm kiểm chứng. Kết quả âm có thể vừa do recipe yếu vừa do assumption/model;
chưa kiểm calibration thì không có tỷ lệ bỏ sót đáng tin cậy.

## Lượt đọc lại mới: không chạy backtest

Parent `execution-v1/eurusd-catalogue13-v1` dưới private campaign root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Python stdlib đọc13 `year/result.json`, đối chiếu SHA256 với từng `completed.json`,
kiểm624unique(candidate,scenario,year) và tính lại48candidate-cost totalnet từ
rows bằng Decimal, khớp `summary-review.json`. Không rehash raw ticks hoặc
chạy lại simulator. Command dùng researchPython `-X utf8`, inline read-only.

| Diagnostic | Reference | Cost-stress |
|---|---:|---:|
| Annual books / candidates |312 /24|312 /24|
| Candidate tổng13books dương |6|0|
| Entry fills cộng các books |56.469|56.469|
| Margin rejections |0|0|
| Skipped minimum lot |0|0|
| Books không có fill |0|0|

Hai costs không là independent samples; cùng số fills không chứng minh cùng
quantities/fills/net. Tổng13annualresetbooks không continuous account, CAGR
hoặc annual return. Không thể giải thích batch này bằng “risk0,25% làm không
vào được lệnh”. Không suy những counts này cho Gold/US500 hoặc mọi account.

Nguồn outcomes: [624cases](EURUSD-CATALOGUE13-RESULTS-20261108.md),
[Gold review](GOLD-SMA50K-REVIEW-20261108.md),
[US500 correction](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md),
[R024 component](WEEKEND-GAP-COMPONENT-RESULTS-20261108.md).

## Chiến lược của mình từ đâu?

| Nhóm | Thành phần quen thuộc/nguồn | Phần project tự cụ thể hóa |
|---|---|---|
| Donchian, SMA, RSI, Bollinger, Z-score, ORB, prior-day levels | Họ indicator/trend/reversion/level phổ biến; paper/definitions là context | Lookback20/80, H1/H4, ATR/SL, clocks/exit và cách kết hợp thành exactpolicy |
| Fixing/session | Nghiên cứu BoC/SNB về flow và thời điểm | EURUSD đơn lẻ, H1 approximation, giờ và SL/holding riêng; không paper portfolio replication |
| Gold/US500 adaptations | Trend, daily reversion, intraday momentum có cơ chế tham khảo | Instrument/source/clock/cost/recipe thay đổi; không chuyển thẳng evidence từ futures/equities sang CFD |
| ML | Ridge/Forest đã train trong Discovery5, cộng2shuffled controls | Features/labels/training/entry/SL workflow của project; hai real policies không được giữ |

Đây là **AI hỗ trợ thiết kế/code các giả thuyết từ họ chiến lược đã biết**,
không toàn bộ do AI phát minh mới, không chép một bot nổi tiếng đã có
verified challenge record. Numerical rules không gọi LLM mỗi lệnh; ML ở đây
là model đã train, không đồng nghĩa model ngôn ngữ.53records/41versions không
41independent edges; controls không ứng viên để chọn khi tình cờ dương.

Bằng chứng trực tiếp: [Discovery4](CHALLENGE-DISCOVERY-ROUND4-20261108.md)
ghi8recipes không exact replication; [Discovery6](SESSION-DISCOVERY6-20261108.md)
liệt kê khác biệt với paper; [Discovery7](ORB-DISCOVERY7-20261108.md) ghi H1
breakout là adaptation chậm; [ML results](DISCOVERY5-RESULTS-20261108.md);
[catalogue/source limitations](STRATEGY-CATALOGUE-20261107.json).

## Điểm cần sửa trong cách tìm và kiểm, trước batch rộng khác

1. **Tách replication khỏi adaptation.** Chọn một cơ chế có nguồn rõ và
   dữ liệu phù hợp. Lập bảng original→project (asset, horizon, entry/exit,
   stops, costs, universe). Tái hiện phần thực sự có dữ liệu/quyền dùng,
   ghi proxy/missing; chỉ sau đó thay một thành phần có lý do. Không lấy việc
   RSI/SMA nổi tiếng làm prior evidence rằng exactrecipe có edge. Không tự mở
   holdout/account/provider để ép replication.
2. **Kiểm độ tin cậy của screen ở vùng ảnh hưởng quyết định.** Đăng ký trước
   một nhóm nhỏ gồm bản near-zero định giữ và bản định gác, thêm path có gap/
   stop; so cùng input/cost bằng native tick, tìm nguyên nhân từng lệch.
   PilotQ1 chỉ4rules×2costs, coarse−tick+0,04→+0,48USD, thiên lạc quan do SL;
   không là annual error bound. Giữ fixtures có kết quả tính tay dương/âm,
   sai BUY/SELL/clock/cost bị bắt; không đòi historical benchmark bắt buộc lời.
   Shared helpers/parity chưa là fully independent oracle.
3. **Tách tín hiệu, wrapper và ma sát.** Chẩn đoán contribution gross sau
   embedded spread, commission, slippage, funding, delay/SL/time exit. Gross
   Bid/Ask không phải frictionless alpha. Reference→stress thay cả sizing/cost
   có thể đổi quantities/path, nên không trừ hai totals rồi quy hết cho phí.
   Diagnostic không tạo bản trade“bỏ phí” có quyền promote.
4. **Tách kinh tế và challenge fit.** Trước hết có net expectancy/uncertainty
   hợp lý, sau đó đánh giá DD/headroom/time-to-target3/6/12tháng ở risk hiện có.
   Heuristic nhiều năm dương chỉ ưu tiên workload, không tiêu chuẩn ngành hay
   veto mọi chiến lược theo regime. Không thêm regime filter hậu nghiệm mà
   tiếp tục gọi cùng trial; cũng không tăng lot để tạo lợi thế.
5. **Chỉ thêm trials/data để trả lời câu hỏi cụ thể.** Đếm families/versions/
   exposure, không lấy624cases làm624independent discoveries. Fresh validation
   và prospective forward phải có gate riêng. Không grid search vô hạn,
   không chờ đủ một số năm hoặc đủ số strategies sẽ tự ra winner.

Đây là khuyến nghị sau review, chưa thực thi calibration/replication mới.
R019 vẫn chưa freeze/code/numeric; không dispatch theo report khi Goal paused.
Khi resume, review priorities này trước nối R019 tự động. Không rewrite
frozen protocols, historical outcomes hoặc source pins. Không tạo skill mới:
workflow thuộc strategy-research/qualification/engineering-retrospective đã có;
chưa có thực nghiệm mới để đúc thêm universal rule.

## Đối chiếu nguồn bên ngoài — đã đọc08/11/2026

| Nguồn | Điều hỗ trợ và giới hạn |
|---|---|
|[QuantConnect research guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)|Khuyến nghị bắt đầu từ central hypothesis, tránh tạo lý thuyết theo outcome. Các mốc số backtests/giờ của hãng là hướng dẫn, không áp thành statistical guarantee hoặc deadline mới của project.|
|[Bailey et al.,2015,PBO](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)|Thử nhiều cấu hình trên dữ liệu hữu hạn gây selection/overfit; holdout đơn lẻ không giải quyết toàn bộ. Không dùng paper này để tuyên bố project đã có PBO hoặc bật CSCV máy móc.|
|[AQR,2017,trend following](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf)|Nghiên cứu monthly,67markets,1/3/12month signals và portfolio sizing. Không xác nhận SMA20/80H4 trên một CFD hoặc prop pass-rate.|
|[BoC2021-48](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/)|Cơ chế currency drift/reversal quanh benchmarkfixing trên interdealer FX; không exact H1bot của project.|
|[NYFed125](https://www.newyorkfed.org/research/staff_reports/sr125.html)|Orders clustered quanh levels/roundnumbers hỗ trợ cơ chế, không chứng minh prior-day level+ATR recipe.|
|[FTMO2-Step](https://ftmo.com/en/2-step-challenge/)|Trang hiện hành:target10%/5%,daily5%/overall10%,4days,unlimited. Không hard deadline3/6/12months; không xác nhận target executioncosts.|
|[Reddit:17strategies/6months](https://www.reddit.com/r/algotrading/comments/1spd5nf/6_months_full_time_on_algo_17_strategies_dead_on/)|OP tự thuật nhiều phương pháp/data/code vẫn chưa chứng minh edge. Minh họa sự khó, không tỷ lệ thất bại đại diện, audited trackrecord hoặc xác nhận methodology của OP.|
|[Reddit:algotradingjourney](https://www.reddit.com/r/algotrading/comments/1hpyqcb/tell_me_your_algotrading_journey_what_worked_for/)|Ý kiến trái chiều; có người thiên về replicate/hiểu existingideas rồi innovate, có người dùng generatedportfolio. Claims lợi nhuận không verified; không làm bằng chứng chọn bot hoặc tool.|

Không tìm được từ các nguồn này một tỷ lệ chiến lược bị loại hoặc số trial/
tháng/năm bảo đảm thành công có thể áp cho project. Community có selection,
marketing và reporting bias. Đây là synthesis có giới hạn, không khảo sát
đại diện hoặc bằng chứng rằng một lời khuyên Reddit sẽ tạo edge.
