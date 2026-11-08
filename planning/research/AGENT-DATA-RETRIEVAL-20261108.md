# Dữ liệu và tra cứu cho AI agents — review08/11/2026

## Delta 09/11: dùng trong Goal tìm ứng viên mới

Goal mới đang active; phạm vi task không mở lại Goal ở review gốc bên dưới
là lịch sử ngày 08/11. [NYFX conditional](NY-FX-GAP-SCENARIOS-RESULTS-20261109.md)
và [NASDAQ overnight](NASDAQ-OVERNIGHT-REVERSAL-RESULTS-20261109.md) đã dùng lại
nguồn có seals/review, protocol/code snapshots và các output mới có lineage.
Raw/source cũ không bị rewrite; exact unknown và conditional outcomes giữ riêng.

Lát NASDAQ mới phân biệt predictor thiếu/crossed với gap bằng 0; prior expected
cashsession với last available quote; signal time với fill interval; price
component USD/unit với account USD. Calendar/clock/grid/side/census và false
authority có guards/tests, reviewer Fraction kiểm outcomes độc lập về số học.
Lỗi reviewer v1 và bản sửa v2 được giữ, không sửa pin cũ hoặc rerun numeric.

Đây là củng cố contracts trong pipeline đang dùng, không migration sang một
schema/DB chung cho mọi artifact lịch sử. Catalogue hiện 80 records / 58 policy-
model versions, không 80 independent edges; số lượng cũ trong inventory08/11
bên dưới giữ đúng ngày đo. Metadata/hash giúp truy vết, không chứng minh edge.
Local retrieval vẫn phục vụ tìm tài liệu; numeric đọc artifacts bằng code.
Không có evidence mới cần vector DB, embeddings provider hoặc RAG service.

[Tick normalization/performance](INDEX-TICK-REVIEW-OPTIMIZATION-RESULTS-20261109.md)
thêm explicit integer-grid/UTC-ms/native-volume/ordering/window contracts cho
derived columns, không thay raw. Full fields/M1/locators khớp frozen oracle;
source pins có before-use/final binding và active loop checks. Đây là áp dụng
chuẩn hóa ở consumer thực, không migration lịch sử hoặc format DB mới.

[Full tick view](INDEX-PAPER-WINDOW-TICK-HISTORY-PROTOCOL-20261109.md) áp metadata
theo hour: source identity/UTCms/price-grid/quote-volume units/consumed exposure,
raw/output/proof seals, common-M1 conflicts/missing/extension và archived quote
locators. Source và review có journals riêng; resume kiểm binding trước skip,
không coi directory/file tồn tại là đã verified. R076/R077 revision lineage giữ
trong catalogue thay vì ghi đè negatives. Numerical projections đọc bằng code,
không embedding tick hoặc thêm RAG service. [Results/correction](INDEX-PAPER-WINDOW-RESULTS-20261109.md)
đã review source/economics; full-year quarter omission bị phát hiện/sửa, có
code guard trước PnL, không chỉ metadata/hash. Hai components không đạt netgate.

[Consensus reuse](INDEX-CONSENSUS-RESULTS-20261109.md) kiểm experiment mới trên
parent records đã sealed trong5,32s producer+review, không đọc lại raw16million
ticks. [EU-open pilot](EU-OPEN-SOURCE-PILOT-RESULTS-20261109.md) rebind original
rawUTCday/side cho32nightbars vàfullquarterproofs; source role/clock/basis đổi
thì có admission scope riêng, không suy hashmatch là mọi holdingwindow đã tickproof.

[R075 recovery](US500-OVERNIGHT-REVERSAL-RESULTS-20261109.md) bổ sung reuse
proof lịch sử khi code live đã revision: explicit frozen code/protocol snapshots,
raw/calendar/canonical seals trực tiếp; không sửa old proof hoặc chạy lại data
preparation. Đã rebind 4 source years và kiểm actual NASDAQ row/summary parity
sau khi dùng chung component. Default reader vẫn strict/current; frozen proof
reuse không chứng nhận producer mới. Source/inventory08/11 không được nâng ngày
chỉ vì dependency code đã đổi.


## Review gốc 08/11

**Giữ cách lưu theo từng loại dữ liệu; tối ưu cửa tra cứu trước, chưa thêm
vector DB hoặc RAG service mới.** Project đã có local retrieval nhưng corpus
cũ bỏ research và index đã stale. Context hiện hành còn trộn nhiều trạng thái
lịch sử; đó là hai vấn đề đã quan sát, chưa cần phỏng đoán thiếu embedding.
Task này không mở lại Goal tìm chiến lược, không đổi raw/DB/frozen evidence.

## Dữ liệu đang được lưu như thế nào?

| Loại | Vị trí/cách lưu | Cách agent nên dùng |
|---|---|---|
| Source, rules, schema và workflow | Git workspace và repo sản phẩm; skills/Markdown/code, commit/lockfiles | Đọc đúng owner/version; `rg` hoặc source search, không suy codepass thành edge |
| Knowledge nghiên cứu | `planning/research/`:205files,147Markdown, khoảng1,67MB ở lúc kiểm | Index chủ đề → kết luận/nguồn/giới hạn → artifact được dẫn; giữ negative/superseded evidence |
| Danh mục chiến lược | Catalogue JSON+Markdown:53records/41versions, cùng owner | Python đọc JSON để lọc ID/role/state; không xem số records là independentedges |
| Giá gốc, cache, kết quả | Private research artifact tree trênE:, CSV/JSON/Parquet, source snapshots và manifests/hashes | Code đọc đúng input/cost/rule/version; không dùng văn bản RAG tính PnL hoặc chọn giá |
| Tiến độ và phục hồi | Per-attempt progress/events/logs, result/review/checkpoint | Reconcile producer/terminal/bindings; không coi file tồn tại là đã hoàn tất |
| App/task state | Trader và Paperclip có PostgreSQL/storage owner riêng theo operations docs | Native API/ledger/UI giữ authority; không làm bản sao search DB thành task state |
| Context cho agent | `planning/CURRENT-CONTEXT.md`; receipt lịch sử và plan riêng | Chỉ lấy trạng thái hiện hành và đường đọc tiếp; không nạp mọi log vào prompt |

Metadata scan của **một campaign** private
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1`:
21CSV≈15,80GB;12.946JSON≈5,50GB;479logs≈55,1MB;3.343source-snapshotPY≈44,0MB;
1Parquet≈30,8MB, cùng các files nhỏ khác. Tổng xấp xỉ21,45GB, dùng decimalGB.
Đây không phải inventory toàn máy/DB hoặc tỷ lệ file có thể xóa. JSON lớn có
thể chứa results/decisions/cache/evidence có consumer; chưa đo duplicatebytes,
không suy số files thành dữ liệu thừa. Không thay retention hoặc xóa dữ liệu.
Git giữ code/docs và pins, không tự backup DB/private artifacts. Tên thư mục
`BACKUP-TRADINGWORKSPACE` không chứng minh đã có bản sao độc lập hoặc restore
đạt; task này không nối cloud/ổ mới hoặc chạy migration/backup dịch vụ.

Trader đã có lossless, source-bound Parquet tick cache và H1 summaries trong
[Forex research](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md).
Giữ raw+hash/schema/order/grid/producer/runtime checks; không convert toàn bộ
CSV chỉ để đổi format, không sửa binding cũ. Parquet hay SQL phục vụ tính toán;
embeddings phục vụ tìm tài liệu, hai việc khác nhau.

## Findings và thay đổi thực hiện

| Finding đo được | Thay đổi | Điều được giữ |
|---|---|---|
| Current-context64.486B/759lines chứa cả Goalactive/paused/complete cũ | Compact thành cửa hiện hành5.065B, giảm92,1%bytes; snapshot nguyên bytes+hash ởarchive | Mọi lịch sử và relative-link base gốc; PLAN/ledger/gates/WIP không đổi |
| ReceiptAI548.636B/7.170lines | Để lịch sử tại owner, route tới đúngsection; chưa compact receipt | Không rewrite anchors, command hoặc frozen receipts đang có caller |
| Xerj có binary pin đãverified nhưng index518files đãstale; allowlist cũ526files,0research | Opt-in researchMarkdown/current-context/lifecycle và3operations docs; phạm vi mặc định củaCodeGraph giữ nguyên | Lexical local, không remote embeddings, không sửa global MCP config hoặc mở service nền |
| Need raw/DB/holdout exclusion |5focused regression tests cho scope, escapes và freshness | Không CSV/Parquet/resultJSON/receipt/archive/.env/DB trong research scope; tênholdout không index |

Snapshotcontext: `planning/archive/2026-11-08-context-storage-review/`,manifest
ghi originalbase`planning/`, source là bytes trên đĩa, SHA
`52829108a4509146e61cd39e6ab3b53d0d1d26b143cbd3ceef42d0122adad20b`.
Không coi relative links trong snapshot đã di chuyển là resolve ở vị trí mới.
Canonical mới có links đúng; không đọc archive để bắt đầu một task thường.

## RAG có cần thiết không?

RAG là lấy thông tin liên quan rồi đưa vào context cho model. Không bắt buộc
phải có vector DB: workflow `tìm → đọc nguồn → trả lời có bằng chứng` hiện có
đã là retrieval cho agent. CLI Xerj đang dùng lexical mode, chưa semantic
embedding. Session này chưa expose MCP search; CLI là capability được kiểm,
không suy có stanza config nghĩa tool đã có trong mọi phiên/Paperclip worker.

| Nhu cầu | Chọn hiện tại | Khi nào nâng cấp? |
|---|---|---|
| ID/file/code/error chính xác | `rg`, catalogue JSON, đọc source | Chưa có lý do thay bằng vector search |
| Tìm quyết định/research khi không nhớ file | Xerj local trên maintained docs, đọc lại status/date/source | Nếu benchmark câu hỏi thật cho thấy miss vì paraphrase/đa ngôn ngữ, thử hybrid lexical+embeddings có eval |
| Lọc/so sánh nhiều kết quả số | Python và JSON/Parquet hiện có | SQL/DuckDB read-only view khi có query workload được đo; index chỉ là derived, không ledger mới |
| Papers/docs tăng nhiều | Giữ citations, section/clock/scope, supersession và admission roles | Chọn corpus/metadata/chunking trước; chỉ thêm reranking/vector khi thực sự tăng retrieval quality |
| Nhớ quy trình và quyền | AGENTS/skills/native grant/ledger | RAG không thay permission, schema validation hoặc execution owner |

Không embedding từng tick, toàn source snapshots hoặc tất cả logs. Không
tự upload dữ liệu nghiên cứu/trading lên dịch vụ embedding, tạo account/key,
paid provider, watcher hoặc database mới. Chưa có bằng chứng retrieval tốt
hơn sẽ tạo lợi thế giao dịch hoặc sửa được data/fill/model assumptions sai.

## Đánh giá khả năng dùng thật và duy trì

Xác nhận index mới và một tập câu hỏi đã chọn trước khi query; giữ cả miss,
latency gồm node startup/freshness và locator thật, không chỉ ảnh chụp hoặc
claim từ upstream. Tập nhỏ chỉ là smoke evaluation, không globalrecall hoặc
so sánh đầy đủ với semanticRAG. Receipt riêng ở
[agent-data-retrieval checkpoint](../checkpoints/agent-data-retrieval-20261108/RECEIPT.md).

Index sinh lại từ tracked allowlist; khi sửa/tạo doc thì index lại hoặc dùng
`rg`, không hạ freshnessguard. Compact context dùng skill evidence-continuity
và archive policy đã có; không tạo thêm skill/framework quản lý knowledge.
Repo skill sửa không chứng minh loader Paperclip đã nhận nội dung mới.

Nguồn primary đối chiếu08/11:
[Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
về giữ context có chọn lọc/tra cứu theo nhu cầu;
[Contextual Retrieval](https://www.anthropic.com/research/contextual-retrieval)
về mất ngữ cảnh khi chunk và kết hợp lexical với semantic;
[DuckDB Parquet](https://duckdb.org/docs/extensions/parquet)
về đọc cột/filter pushdown;
[SQLiteFTS5](https://www.sqlite.org/fts5.html) là lựa chọn lexicalindex khi có
nhu cầu, không lý do cài thêm lúc đã có Xerj. Số liệu nhà cung cấp không tự
áp cho project; receipt của project mới xác nhận capability trong scope.
