# C2: đã bắt nến chèn và sửa phép đo R025; chưa sửa hết các sách US500

**Continuation đã hoàn tất:** [long source correction/results](INDEX-LONG-EXPLICIT-RESULTS-20261108.md)
đã kiểm views2013–2024,24RSI/preclosebooks và monthly admission. Các dòng
"long books còn chờ" bên dưới là checkpoint trước continuation, không là
trạng thái hiện hành. C1/C2 tổng thể vẫn còn native/tick/targetprop/OOS gaps.

**Lỗi nguồn đã xác nhận, có đường đọc mới và hồi quy.** Thư viện tự thêm nến
flat/volume0 vào phút raw response bỏ qua. Vì vậy, một export có hash và đủ
timestamp vẫn chưa chứng minh có quan sát nguồn ở mọi phút. Correction này
phân biệt được chúng; chưa là xác nhận mọi backtest US500 đã sạch hoặc có edge.
[Protocol](INDEX-EXPLICIT-SOURCE-CORRECTION-20261108.md) giữ cách sửa trước
outcome. Commit `4ee6fbb` thêm source-only và reviewer; `bc74072` thêm mask
Bid/Ask cho từng metric. Không sửa installed library hoặc source Trader.

## Tái hiện trên dữ liệu thật

[Fixture được đăng ký](FX-FIXING-PROXY-DATA-PREFLIGHT-20261108.md):03/01/2023,
ba instruments × Bid/Ask. Sáu requests hoàn tất11,308s, hai raw cache hits và
bốn URL fetch; không broker, model hoặc2025+.

Các counts dưới đây **giống nhau ở cả Bid và Ask** trong fixture này:

| Instrument | Nến native export | Nến raw liệt kê | Nến thư viện chèn | Nến chèn trong390phút cash |
|---|---:|---:|---:|---:|
|EZU ETF Eurozone|1260|379|881|11|
|SPY ETF Mỹ|1260|390|870|0|
|EURUSD|1440|1429|11|0|

EZU/SPY là proxy, chưa tái hiện Total Market Indices của paper. Cả ba có giá
nguồn ở phút20:59UTC dùng làm endpoint kiểm fixture; chưa chứng minh toàn
lịch sử, corporate actions, giá điều chỉnh, lịch fixing hoặc quyền khớp.

Đường mới `getCachedM1(...,{sourceCandlesOnly:true,...})` chỉ giữ timestamps
raw liệt kê và phát hash/count qua `onSourceProvenance`. Giá vẫn do native
decoder đọc. Native default giữ để tái hiện lịch sử; so cả sáu exports khớp
exact với bản cũ. Không lấy điều kiện volume0 làm bộ lọc: một nến nguồn có
volume0, kể cả flat, vẫn được giữ. Unknown không trở thành giá hợp lệ.

Node cache-only integration chặn `fetchBuffer`:0 network attempts,0,619s.
Reviewer Python riêng dựng lại giá/volume từ integer deltas và kiểm source
timestamps/side/coverage:0,235s, khớp toàn fixture. Đây là hai code paths trong
cùng agent, chưa là independent human/model sign-off.

## Sửa đúng phần bị ảnh hưởng của R025

Giữ [outcomes native-expanded trước sửa](US500-TURN-OF-MONTH-COMPONENT-RESULTS-20261108.md).
Đối chiếu3140 raw cache responses với các endpoints cũ:9408 endpoint-sides
được nguồn liệt kê,10 là padding, không thiếu raw provenance. Mười điểm thuộc
ba ngày; không đổi calendar/strategy/risk/cost hoặc chọn ngày theo lãi/lỗ.

| Ngày | Điểm không có nến nguồn | Xử lý |
|---|---|---|
|09/03/2020|Bid/Ask cashopen và09:32 entry|Cash decomposition và mua/bán trong phiên thành unknown|
|16/03/2020|Bid/Ask cashopen và09:32 entry|Tương tự; không dùng nến chèn làm giá mở|
|05/08/2024|Bid/Ask09:32 entry|Chỉ phép đo mua/bán thành unknown; Bidopen/close thật vẫn dùng cho decomposition|

Giữ nguyên1507/1510 daily rows. Chỉ ba ngày bị ảnh hưởng được tính lại và các
summary được tổng hợp lại; không chạy backtest portfolio hoặc đọc lại full M1
để rerun strategy. Bid quyết định cash/close; Ask quyết định entry. Không loại
CTC chỉ vì một side không dùng đến thiếu nguồn. Synthetic predecessor Bid
không được dùng để tạo return của ngày kế tiếp.

Đơn vị bảng dưới là **bps giá ròng trung bình/phiên**, không%lãi tài khoản.

| Giai đoạn | TOM chuẩn/cao | REST chuẩn/cao | Đủ TOM/REST cho tradable | Tiêu chí cũ |
|---|---:|---:|---:|---|
|2019–2021|+1,1293/−1,8692|+1,8661/−1,1057|144/608|Không đạt|
|2022–2024|+6,2720/+4,0545|−2,5293/−4,7431|143/608|Đạt|

Admission từng năm còn đủ cả nhóm/metrics. Quyết định không đổi: **không ưu
tiên bot R025**, vì không đạt cả hai giai đoạn/mức phí. Không suy đây là
hard reject cả calendar family hoặc xác suất kiếm lời ngoài mẫu.

| Phần việc | Thời gian đo | Giới hạn |
|---|---:|---|
|Bind raw + sửa affected rows/summary|66,422s wall;41,891s CPU|Phần lớn là lần đầu kiểm nguồn3140 cache responses|
|Reviewer độc lập code path|33,390s|Integer timestamp/price, float log/mean, masks/counts/criteria khớp|
|Fixture cache-only native/source-only parity|0,619s|Sáu requests, không có network fallback|
|Fixture Python raw/coverage review|0,235s|Không gọi Node mask helper đang kiểm|

Reviewer kiểm1510 rows,9408 source endpoint-sides,1507 rows reuse và bắt case
chèn lại entry synthetic. Không dùng thời gian này làm speedup của native
tick engine hoặc hiệu năng một annual study. Lần sau nên reuse source view
đã kiểm theo hash; chưa có canonical quarterly source-only export cho các
sách US500 khác nên không tuyên bố đã loại bỏ toàn bộ công việc lặp.

## C2 tại checkpoint trước quarterly gate (đã được cập nhật ở phần tiếp)

| Lát | Trạng thái hiện tại | Việc tiếp theo |
|---|---|---|
|Source-only loader|14 Node tests;7 Python raw-provenance tests đạt|Opt-in cho output mới; default expanded chỉ là historical scenario|
|R025 endpoints|9 component tests;actual corrected review đạt|Không chạy lại để benchmark hoặc thay tiêu chí|
|Noise14/first→last30, RSI/preclose, monthly US500|Đã kiểm số học trên expanded views; source-padding impact chưa đánh giá toàn bộ|Ưu tiên tạo canonical paired explicit view từ cache, kiểm signal/fill/range và rerun đúng affected books|
|Gates của reader|Checkpoint ban đầu mới đo timestamp sau decode|Đã được thay bằng proof gate ở mục quarterly bên dưới; legacy vẫn chỉ là expanded-view scenario|
|R026 fixing|Transport proxy dùng được nhưng còn clock/calendar/currency/corporate-action gaps|Đợi source correction trước numeric protocol; không tải10markets|
|QDM Forex/Gold|Không đi qua decoder này|Không invalidate hoặc rerun vì lỗi của pipeline khác|

Nến được nguồn liệt kê vẫn chưa là quote độc lập hoặc giá thực thi được.
Chưa pass C1/C2, không mở holdout/broker hoặc làm yếu validation. Existing
research skill đã cập nhật reference; không tạo skill/provider/framework mới.

Kiểm môi trường AI sau cập nhật reference: maintainer0errors/0warnings;
global12279B, project10133/65536B, reserve55403B, combined22412B. Skill
structure và local links đạt;12tài liệu được kiểm link, catalogue vẫn53records/
41policy versions. Validator ở product venv thiếuPyYAML nên chạy bằng bundled
Python có sẵn và đạt; không cài package hoặc đổi encoding/config. Trigger
manual walkthrough dùng case decoder padding hiện tại và phân biệt status-only
không cần đọc source; chưa forward-test routing bằng một model độc lập.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/fixing-proxy-fixture-v1` + `prepare-fixing-proxy-fixture-v1.cjs`.
- `execution-v1/fixing-proxy-source-view-v1`: raw/cash review và native parity;
  `review-fixing-source-view-v1.cjs`, `review-fixing-proxy-fixture-v2.py`.
- `execution-v1/us500-turn-month-source-correction-v1`: source masks/receipts,
  corrected daily/result/independent-provenance-review-v1/source-snapshot;
  `review-turn-month-source-correction-v1.py`, `check-turn-month-source-correction-v1.py`.

Các workers của correction đã terminal; giữ raw, logs, source snapshots và
attempts. Lỗi base float ở probe đầu được tái hiện bằng regression: chỉ chuẩn
hóa nhiễu biểu diễn cực nhỏ về integer units, vẫn chặn off-grid có ý nghĩa.

## Lượt tiếp: canonical quarterly views và reader gate

[Protocol riêng trước thực thi](INDEX-EXPLICIT-QUARTERLY-PREFLIGHT-20261108.md)
và code `a2a3358` bổ sung tool `explicit_m1_view.py`, proof/reader gate, và
study CLI yêu cầu source proof. Kết quả đã kiểm của lượt chuẩn bị:

| Năm | Nến cũ/nến explicit paired mỗi side | Phút cash có giá nguồn/dự kiến | Phiên thiếu phút nguồn | Prepare/review/Node oracle,s |
|---|---:|---:|---:|---:|
|2022|435596/341682|97698/97710|4|53,703/16,774/12,402|
|2023|434687/332236|97032/97140|9|57,265/20,914/15,877|
|2024|439334/335016|97678/97740|9|57,110/21,205/15,755|

Counts removed padding gộp hai side:187828/204902/208636. Trong đúng ba năm
này không có unpaired explicit rows; journal rỗng vẫn được seal. Không suy
hai side luôn đồng bộ: synthetic test có side thiếu giữ journal và không
invent counterpart. Native-expanded coverage trước sửa là2022:97710,
2023:97094,2024:97740; tất cả chưa là coverage nguồn.

Batch data có ownership/deadline/CANCEL/status,2022 chạy trước và qua reader+
native oracle rồi mới mở hai workers2023/24. Wall toàn batch187,218s; timers
year có overlap nên không cộng thành thời gian thực. Node chặn fetchBuffer,
không ghi cache; so toàn giá trị/order/source mask và journals với Python,
khớp exact,0 network attempts. Native library cùng provider vẫn không là feed
độc lập. Missing raw/code/input/proof change không được fallback hoặc gọi0.

**Reader/CLI gate đã chạy thật:** legacy input bị chặn trước simulation,
không tạo `reference.json` hoặc terminal numerical result. Source proof được
bind producer/validator/protocol/calendar/raw/parent/seals/journals/counts;
giả nhãn source-only hoặc sửa raw/proof/output bị reject.6 integrationtests,
8 provenance tests,5 reader tests và25 strategy/cost/reviewer tests đạt.
Một asymmetric fixture đầu tiên có Bid>Ask nên bị validator chặn; sửa đúng
giá fixture để vẫn kiểm side-missing, không nới negative-spread guard.

Private `execution-v1/us500-explicit-source-v1/`: source snapshots, mỗi năm
manifest/result/proof/quarters/unpaired/reader/native-oracle và logs. Parent
data/books giữ nguyên. Source producer/reader mới làm old proof chưa chứng
minh current source; không sửa proofhash lịch sử để reuse. `legacy-gate-review`
giữ expected failure. Data controller26276/launcher26484 đã terminal.

### Nhật ký quyết định của lát sửa này

| Quyết định | Vì sao / kỳ vọng trước đo | Baseline → bản mới | Bằng chứng và phạm vi |
|---|---|---|---|
|Phân loại là sửa data semantics|Native decoder tự chèn phút; đủ timestamp chưa là quote nguồn|Expanded unfiltered view → explicit paired source view, giữ mọi giá nguồn|Counts/raw/price parity phía trên; không gọi đây là tối ưu tốc độ hoặc đổi strategy|
|Chặn CLI trước numerical|Tránh lặp false source-coverage acceptance|Old reader chỉ seals/schema → proof bắt buộc cho run mới|Actual legacy expected rejection trước simulation; old source snapshots dùng để tái hiện|
|Chạy lại affected book trọn|Missing quote có thể đổi warmup/range/entry/fill và state sau đó|Sáu commission0 books cũ → attempts mới cùng rules/risk/cost|Không chỉ xóa vài trade/sửa PnL; numerical results chỉ ghi sau reviewer đạt|
|Giữ lịch sử để owner kiểm lại|Owner yêu cầu08/11 có log đủ kiểm chọn/đổi/tối ưu đúng không|Protocol/results/engineering review và catalogue hiện có|Workflow đã thêm baseline→delta→before/after→verdict/rollback; không tạo tracker/UI khác|

### Sáu sách đã tính lại và kiểm delta

`execution-v1/us500-source-corrected-books-v1` hoàn tất6books/18scenarios và
6arithmetic/source reviews,126,390s; delta review chỉ đọc2,125s. Controller22600/
launcher11404 đã terminal. Original books/source snapshots vẫn được giữ.

| Policy/năm | Chuẩn cũ → mới,USD | Stress cũ → mới,USD | Entries cũ → mới mỗi scenario |
|---|---:|---:|---:|
|Noise14/2022|+251,67 → +251,67|+181,19 → +181,19|156 →156|
|Noise14/2023|−61,74 → −40,36|−158,16 → −135,92|153 →151|
|Noise14/2024|−72,35 → −66,19|−156,91 → −150,81|147 →147|
|Firstlast30/2022|−301,27 → −280,50|−562,28 → −477,21|235 →180|
|Firstlast30/2023|−380,64 → −81,84|−751,67 → −278,70|218 →120|
|Firstlast30/2024|−239,11 → −202,95|−619,79 → −429,77|234 →141|

Đây là annual accounts riêng10k, không CAGR hoặc tài khoản liên tục. Noise
tổng annual net chuẩn/stress+145,12/−105,54USD; firstlast−565,29/−1185,68USD.
Cả hai **vẫn không đạt triage đã khóa**. Không giữ vì kết quả bớt âm; không
đổi ngày/rules/risk/cost hoặc chọn một năm đẹp để promote.

Delta reviewer so source snapshots và AST từng numerical function của noise:
không đổi logic; common financial dependencies và firstlast/book vẫn exact.
Metadata candidate/cost/risk/leverage/scenarios giữ nguyên. Chỉ orchestration/
reader/source proof đổi. So toàn decisions/trades/cash/open/pending/gaps, không
chỉ net; manifests/scenarios/reviews đều rehash. Đây là same-agent code review,
chưa human/model độc lập.

Reviewer mới cũng đọc lại một legacyactual bookNoise2022 không resimulate;
số học vẫn đạt nhưng ghi `native-expanded-unverified`, không tự nâng historical
acceptance hoặc xóa gaps bị decoder che. Receipt
`legacy-expanded-compatibility-review-v1.json` ở correctedbatch giữ kiểm này.

- Noise bỏ30/30/29 decision times theo từng năm; các decision còn chung
  timestamp có nội dung exact. Gaps trước bị padding che nay ghi4/45/2 events
  mỗi scenario. Những gap này vẫn chưa có intrabar path, không dùng positive
  net2022 để chứng nhận native tick/risk.
- Firstlast bỏ55/98/93 decision times; decision chung exact. Rule vốn yêu cầu
  đủ cash range cho ATR, nên thiếu nến nguồn làm không đủ inputs và giảm entry.
  Không thêm filter kiếm lời sau outcome hoặc tự bịa daily range.
- Null controls vẫn0 entries/0PnL; tất cả books cuối mẫu không open/pending.
  Full arithmetic/source checks không chứng minh target broker/prop/OOS.

Thời gian numerical batch cũ86,05s → mới126,39s **không là speedup**. Input
semantics và source gates đã đổi; việc rehash raw proof trong mỗi reader/review
có chi phí. Data prep187,218s tách riêng; không cộng year timings overlap hoặc
gọi cache-only correction là download. Cần profile mới trước tối ưu proof reuse;
không bỏ source/cost/risk validation để nhanh hơn.

Nhật ký delta có cấu trúc ở `source-input-delta-review-v1.json`: old/new run
locators, hashes, financial state, counts, changed/removed decisions, reasons,
verdict và source-code parity. `source-snapshot/delta-review-v1.py` giữ exact
reviewer. Workflow đã ghi quy tắc tối ưu/chọn/đổi phải giữ baseline→delta→test→
before/after→decision, gồm cả failures. Chưa có phần mềm tự suy mọi quyết định
đúng chỉ từ log; traceability giúp owner/agent sau kiểm lại bằng chứng.

**Phần còn lại:** RSI/preclose/monthly long books chưa được correction toàn bộ;
trước khi dùng chúng tiếp phải tạo nguồn explicit tương ứng và kiểm đúng phần
bị ảnh hưởng. Native index tick/risk/target cost, cleanOOS và prospective
evidence vẫn còn thiếu. C1/C2 còn mở; không broker/2025+ hoặc strategy mới.
