# R085 USDJPY bán sau fix: mở rộng lịch sử không đạt độ bền đã đăng ký

09/11/2026. [Protocol](USDJPY-POSTFIX-EXTENSION-PROTOCOL-20261109.md) và
calendar amendment freeze ở`55fe25d` trước nguồn mới. Hướng này được chọn
sau diagnostic control dương trong[R084](USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md);
không independent discovery, clean OOS hoặc replication paper.

**Gác exact recipe SELL09:56→10:24 Tokyo theo lịch nominal.** Chỉ6/13năm
mở rộng dương sau phí cao, trong khi gate đã đăng ký cần ít nhất10/13 và
cả4block dương. Hai block đầu âm. Lịch phụ cũng không đạt; không đổi giờ,
calendar/fees hoặc thêm SL/risk wrapper để cứu kết quả này.

## Số liệu dễ hiểu

Đơn vị:100.000USD notional cố định/lượt, không account10k, mức risk hoặc
%return. Phí nhưR084: Ask/Bidspread+5USDcommissionRT; chuẩn0/stress0,4pipRT.
JPY PnL quy vềUSD tại exitmid từngrow, không actualbrokerconversion.

| Năm | Lượt lịch chính | Net chuẩn USD | Net cao USD | Vai trò |
|---|---:|---:|---:|---|
|2010|49|+753,82|+529,43|Mở rộng|
|2011|46|+1.216,72|+985,51|Mở rộng|
|2012|48|−930,58|−1.171,75|Mở rộng|
|2013|49|−448,08|−648,33|Mở rộng|
|2014|48|−22,34|−204,24|Mở rộng|
|2015|48|−887,57|−1.046,38|Mở rộng|
|2016|48|+144,35|−32,14|Mở rộng|
|2017|47|+1.104,18|+936,80|Mở rộng|
|2018|49|+166,43|−11,12|Mở rộng|
|2019|49|+267,22|+87,33|Discovery, reuse và không vào gate|
|2020|47|+234,40|+58,42|Mở rộng|
|2021|49|+220,00|+41,46|Mở rộng|
|2022|46|+1.430,15|+1.289,95|Discovery, reuse và không vào gate|
|2023|48|−6,50|−143,24|Mở rộng|
|2024|49|+1.039,46|+909,85|Mở rộng|

Không chỉ cộng hết năm rồi gọi “có edge”:625lượt của13năm mới chỉ còn
+204,25USD sau stress, khoảng+0,33USD/lượt trên100knotional. Gross+9.066,59,
spread3.357,31,commission3.125,00,slip2.380,03USD. Lợi nhuận mô hình còn quá
mỏng so với assumptions chưa phải phí/fill thật. Tổng15năm+1.581,53USD gồm
discovery2019/2022; hai năm chọn hướng đóng góp+1.377,28USD, không phải
bằng chứng kiểm định mới. Các tổng USD/pip được tính perrow riêng.

| Gate chỉ trên13extensionyears | Lịch chính | Lịch phụ chuyển ngày nghỉ |
|---|---:|---:|
| Đủ giá tất cả planned postfixrows | Có | Có |
| Lượt |625|906|
| Năm net stress dương /13 |6|6|
|2010–2013, netUSD|−305,14|−211,86|
|2014–2017, netUSD|−345,96|−280,30|
|2018–2021 bỏ2019, netUSD|+88,75|−434,88|
|2022–2024 bỏ2022, netUSD|+766,60|+1.087,93|
| Tổng net stressUSD |+204,25|+160,90|
| Qua gate nghiên cứu? |Không|Không|

Ngưỡng10/13vàblocktest là heuristic ưu tiên research đã freeze, không chuẩn
thống kê phổ quát hoặc chứng minh mọi strategy lời6/13năm đều vô ích. Kết quả
này không đủ ưu tiên exactrecipe theo mục tiêu đã đặt; không loại cả fixing
family hoặc chứng minh thị trường không có edge. Chưa tính SL/account equity,
daily/overall breach, challenge time-fit/OOS/prospective/ownerhandover.

## Kiểm chứng, dữ liệu và lịch sử sửa

| Lát | Kết quả / giới hạn |
|---|---|
| Calendar trước quotes | Official265holidays2010–2024; independent enumeration/bisect khớp toàn bộ mapping.1.045uniondays,906new và139discovery |
| Crossyear guard | Generatorv1 dừng trước quotes vì05/01 có thể về năm trước; failure giữ,0outcomes. V2 amendment trước source: actualexecutionyear/globaldedup, giữnominalmappings;05/01/2014→30/12/2013 và05/01/2020→30/12/2019 không doubletrade |
| Source mới |1.812day-side fetches,0cachehits/0failure/retry events;2.484.956native bars/2.480.516explicit,4.440padding không dùng làm observed source |
| Fullraw/native/math |12.402.580new OHLCV field checks bằngFraction so explicit/native; reuse1.899.620accepted R084 checks qua hash, không decode lại139old days |
| Roles | Postfix29minutes×2sides đủ cả1.045days. Prefix diagnostic có3ngày thiếu1minute:20/06/2014,25/05/2020,30/12/2021; giữunknown,24controlbooks annualN/A, không ảnh hưởng primarypostfixgate |
| Financial |240books/140.960cashfield checks; perrow direct-side oracle so midpoint producer, exactgross/spread/fee/slip/USD/pip/counts/strictN/A/null |
| Discovery parity |32oldbooks ledger và totals khớp nguyên vẹn R084; không tạo trial mới từ phép reuse |
| Preflight/regression |8checks gồm calendar/crossyear/Olympicholidays/unknown/null/discovery exclusion;9syntheticmutations và1actualcash mutation bị validator từ chối |
| Authority |Consumer network-denied;0broker/modelcalls,khôngholdout2025+,newpaidprovider/account/EA/migration hoặcexecution |

Cùng agent và provider, arithmetic oracle khác công thức; không independent
reviewer/feed, actualfill/PIT-bankcalendar certificate. Source-price ownership
và protocol không cấp broker authority. Không mua challenge từ kết quả này.

## Thời gian và hậu kiểm kỹ thuật

| Phase | Wall time thực đo | CPU / nhận xét |
|---|---:|---|
| Newsource |1.026,211s ≈17phút06s|93,703s CPU;inter-completion intervals có bốn đoạn33–49s, không retry; chưa profile network/disk riêng |
| Preflight+binding trong consumer |20,891s|Gồm synthetic review trước numerics và kiểm nguồn |
| Fullnewsource review/roles |274,955s ≈4phút35s|Không fetch lại hoặc re-review old139days |
| Compute+cashreview+parity+mutations |5,103s|Không account/SL simulation |
| Consumer tổng |300,950s ≈5phút01s|238,141s CPU, gồm serialization;phase rounding có residual nhỏ |
| Source+consumer |1.327,161s ≈22phút07s|Không research/code/Git; các thời gian đó chưa đo |

Không coi đây là22phút chờ thị trường hoặc cần soak1–2năm; đây là thu/kiểm
lịch sử mới. Đã giữ fullsource proof; lần sau inputs/consumer semantics không
đổi có thể reuse acceptedartifact/hash thay download/fullreview. Chưa claim
fullnext-run speedup khi chưa có consumer mới để đo. Source chậm hơn forecast
13phút ban đầu, không che sai số dự kiến; deadline30phút vẫn đủ.
Riêng pacing cấu hình300ms sau mỗi1.812request đã tương đương khoảng9phút04s
(tính theo config, không phase timer riêng); không quy toàn bộ wallwait cho
server/mạng hoặc gaming. Reuse dữ liệu giúp tránh cả pacing lẫn fetch lần sau.

Hai vấn đề quan sát không làm restart job: đọc progressfile đúng lúc ghi có
thể nhận snapshot chưa hoàn chỉnh; đối chiếu latest complete event/PID thay
coi worker chết. Finalevent in full Fraction block totals quá dài: rawresult
vẫn nguyên, dùng `summarize-jpy-postfix-v1.py` để đọc số gọn. Giữ frozenrunner
v1 và snapshots, không sửa pins để làm đẹp log. Khi cần controller lượt sau,
chỉ in counters/verdict/rounded display, giữ exact Fraction trongartifact;
observability skill/reference đã có rule này, không thêm manager/skill mới.

Không lỗi material được phát hiện trong scope đã kiểm; calendar guard đã bắt
vấn đề trước quotes. Không có lý do đổi GPU/Rust/engine hoặc rerun unchanged
history. Source/review là chi phí lần đầu, tiếp theo ưu tiên reuse proof.

## Lưu và tiếp tục

Private base `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/jpy-postfix-calendar-v1/failure.json`,calendar-v2/preflight/source/
component-v1 giữ inputs/code/protocol snapshots, config/raw/native/seals,
records/ledger/report/progress/events. Source và consumer đã terminal/reviewed,
không còn job. RowsSHA
`77834b4e0b59a4c0c5c7064846ff800a4a23f040810983848531121dcb563c86`;
resultSHA `6d918b8c04df80b0ee1435dd6855ecbe9a57470e0a83ab99a38a3bcffe1402db`;
reviewerSHA `32fef5602b4aad26d213d5046b7b97ef28904c5829cecdd4982d0a6496a3eb32`.

Catalogue85records/58policy-modelversions/25native/9controls. R085 là related
pricecomponent, không accountpolicy mới. R084primaryfailure và followupflags
giữ nguyên; R085 không qua gate, không sửa R084 thành winner. Goal C1/C2active,
chưa challengecandidate. Lát tiếp [residual-reversion admission](RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md),
method/data/cost trước recipe; không giờ/fee/dategrid cứu Tokyo recipe.
