# Lịch sử gần, tuổi thọ edge và trade tay so với bot

Đối chiếu nguồn10/11/2026 theo câu hỏi owner: trading là thu nhập chính thì nên
ưu tiên2022→nay hay lịch sử dài, thị trường đổi sau bao lâu, trade tay có dễ
hơn bot và nên học tài liệu nào. Research/documentation only; chưa mở giá,
holdout, backtest, sửa rules/risk/selection hoặc giao dịch.

## Quyết định hiện có và đề xuất phải phân biệt

[Recent-first policy](STRATEGY-VALIDATION-FRAMEWORK-20261105.md#ưu-tiên-dữ-liệu-gần--quyết-định-của-owner-ngày-10112026)
đã ưu tiên từ2022 cho study mới, không đòi thắng mọi năm/thị trường. Đây vẫn là
quyết định hiện hành; không sửa verdict của các studies2019/2022 đã freeze.
Tính tới10/11/2026,2022→nay gần5năm, nhưng owner preference không chứng minh
2022 là structuralbreak hoặc đây là độ dài tối ưu. Các studies2022–24 đã exposed/
unverified;2025+ vẫn reserved/gate riêng, câu hỏi research không tự cấp quyền mở.

Tách độ rộng universe/cơ chế, số năm lịch sử, và yêu cầu lời mọi giai đoạn.
Một strategy conditional có thể đứng ngoài khi không phù hợp; điều kiện phải
biết trước entry và có evidence mới. Dữ liệu cũ giúp kiểm tail/failure modes,
không được dùng tổng lợi nhuận cũ che recent weakness. Thu nhập chính cần cả
relevance hiện tại lẫn khả năng chịu gián đoạn, không chỉ curve gần đây đẹp.

## Bằng chứng về thay đổi và tuổi thọ

| Nguồn primary đã mở | Kết quả / scope đọc được | Giới hạn diễn giải |
|---|---|---|
| [McLean/Pontiff, Journal of Finance2016](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365), publisher abstract |97predictors cổ phiếu; portfolio returns thấp hơn26% ngoài mẫu và58% sau publication so với in-sample; chênh32điểm được tác giả gắn publication-informed trading | Không58%strategies chết, khônghalf-life theo năm, không tỷ lệ áp cho Forex/CFD hoặc challenge. Chưa đọc fulltext trong lượt này |
| [AQR2017 century trend-following](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing), author summary |Tái dựng time-series momentum nhiều asset về1880; bằng chứng cơ chế trend có thể tồn tại qua lịch sử dài | Không xác nhận SMAH4mộtasset của project, brokerfunding hay lời mỗi năm. Landing summary, không re-audit full paper mới |
| [Capponi et al., arXiv2512.23596v2](https://arxiv.org/abs/2512.23596v2), abstract13/08/2026 |Nêu tradeoff model complexity/training-window: lịch sử dài tăng mẫu nhưng có thể gồm regimes lỗi thời; nghiên cứu dự báo cổ phiếu Mỹ | Preprint, không chuẩn số năm chung hoặc engine đã kiểm cho project. Training window khác evaluation window và monitoring window |

Không có căn cứ trong các nguồn này để quy một chu kỳ3/5/10năm áp mọi thị
trường. Cơ chế, cấu trúc phí/thị trường, cạnh tranh và thông tin có thể đổi khác
nhau. Dài hơn không mặc định tốt hơn; recent hơn không tự đại diện tương lai.

## Cách chia vai trò dữ liệu — khuyến nghị, chưa protocol mới

| Vai trò | Khoảng bắt đầu cân nhắc | Cách dùng và giới hạn |
|---|---|---|
| Screening/robustness gần |3–5năm liên tiếp khả dụng;2022→nay là mốc có thể bắt đầu | Kiểm các cơ chế/thời kỳ trong mẫu và uncertainty. Không fixedtrainlength hoặc cleanOOS mặc định |
| Độ phù hợp gần |12–24tháng mới nhất trong phạm vi được cấp | Xem contribution, cost/headroom và drawdown gần; không chọn subgroup/year sau khi thấy PnL |
| Theo dõi prospective |3–6tháng là mốc review vận hành có thể cân nhắc | Thời gian không tự đủ chứng minh edge; cần trade/event count, dependency và reconciliation |
| Stress lịch sử |Trước2022 chọn lọc theo câu hỏi/cơ chế | Giữ tails/negative evidence; không bắt mọi năm xanh, không chạy fullhistory lại khi artifacts reuse được |

Các cửa sổ overlap, không ba mẫu độc lập và không tuyên bố statisticalpower đủ.
Mốc prospective không yêu cầu đợi đủ3–6tháng mới kiểm code/fill hoặc sửa sự cố;
kiểm vận hành ngay khi có observations, chỉ kết luận evidence trong scope.
Ví dụ giả định12cơ hội/năm thì5năm chỉ60cơ hội trước dependency; không ép đủ
mẫu bằng thêm ticks. Nhiều giao dịch intraday vẫn có chung position/regime.
Freeze windows, criteria, split/exposure trước outcomes; nếu so độ dài windows
thì ghi như model-selection trials, giữ validation chưa dùng phù hợp. Không
chọn3thay5năm chỉ để bỏ đoạn lỗ hoặc dùng holdout quyết định lookback.

Đổi regime nhận biết tại thời điểm quyết định khác gắn nhãn hindsight năm
thuận/nghịch. Bot có thể có eligibility/retrain/adaptive rules nếu được thiết
kế và kiểm causal; không mặc định bot cố định vĩnh viễn, trade tay tự thích nghi
đúng hoặc strategy phải cùng tham số mọi thị trường. Chưa thiết kế mode mới.

## Trade tay, bot và bằng chứng profitable

[Barber/Lee/Liu/Odean, author manuscript04/2013, abstract vàpp1–5](https://escholarship.org/content/qt7k75v0qx/qt7k75v0qx_noSplash_3d906c8711715d87ac95573cda3fbc7d.pdf):
full Taiwan exchange1992–2006, xếp trader theo năm y rồi kiểm y+1; dưới1% tổng
daytraders có reliably positive abnormalreturns netfees. Tác giả có bằng chứng
một nhóm nhỏ có skill/persistence, cùng dấu hiệu informationaladvantage. Không
nói không ai kiếm được tiền; không gọi mọi người lãi một năm là có edge.
Không extrapolate tỷ lệ sang FTMO/The5ers hiện tại, cũng không biến đây thành
controlled manual-vs-bot study: dataset là trader-level, không gán chắc phương
thức thực thi từng người. BảnPDF là author manuscript, không nhầm ngày crawl
với năm sample/publication.

[AQR Systematic vs Discretionary,3Q2017](https://www.aqr.com/insights/research/alternative-thinking/systematic-vs-discretionary),
landing summary đọc lại: phân tích manager-level cho rằng không nhóm nào vốn
dĩ tốt hơn và có thể bổ sung nhau. Không botMT5retail, randomizedtrial, current
passrates hoặc chứng minh chính owner có manualedge.

Diễn giải kỹ thuật: người có kinh nghiệm có thể dùng context chưa viết thành
luật; đưa thành bot đòi formalize inputs/decision/exit/execution. Bot hỗ trợ
consistency và đo lường nhưng vẫn cần tín hiệu khả dụng. Trade tay cũng có
bias, hindsight, cảm xúc và khó replay; lời kể/ảnh payout không full economic
record. Không có evidence ở đây cho kết luận bot luôn khó profitable hơn tay.
Manual/semi-auto muốn so phải lưu decision/override trước outcome, giữ baseline
và replay accountstate theo [automation research](PROP-AUTOMATION-AND-STRATEGY-EVIDENCE-20261105.md).

## Tài liệu để owner hiểu và kiểm agent

Đã kiểm trang/mục lục/mô tả nguồn chính thức; không tuyên bố đọc toàn văn sách
hoặc xem trọn lecture. Tài liệu học phương pháp, không promise profitable EA.

| Thứ tự đề xuất | Nguồn | Nội dung ưu tiên |
|---|---|---|
|1|[MIT Andrew Lo: Efficient Markets II–III](https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/pages/video-lectures-and-slides/efficient-markets/)|Video miễn phí2008, English/transcript; behavioral finance và adaptive markets. Học khái niệm, không đánh giá trading conditions2026 |
|2|[Ernie Chan: Quantitative Trading,2nd/revised edition](https://www.wiley-vch.de/en?isbn=9781394378043&option=com_eshop&title=Quantitative+Trading&view=product)|Publisher có TOC/samplechapter; ưu tiênch2FishingforIdeas,ch3Backtesting,ch5Execution,ch6Risk,ch7RegimeChange. Không áp Kelly hoặc code mẫu thành riskquỹ chưa duyệt |
|3|[Robert Carver: Systematic Trading](https://www.harriman-house.com/authors/robert-carver/systematic-trading/9780857194459)|Rules, fitting, sizing, costs và discretionary trong systematicriskframework; sách2015, phương pháp không chứng minh recipes còn edge hiện tại |

Khuyến nghị bắt đầu video vàch2–3Chan; Carver bổ sung risk/portfolio sau. Chưa
kiểm bản dịch tiếng Việt hoặc subViệt của đúng edition/video, không phát tán
ebook không có quyền hoặc yêu cầu mua nhiều tài liệu ngay. Không mở course hay
thay education progress chỉ vì đề xuất readinglist. Sources abstract/landing/
TOC đủ cho kết luận giới hạn này, chưa đủ áp phương pháp mới vào numericalcore.
