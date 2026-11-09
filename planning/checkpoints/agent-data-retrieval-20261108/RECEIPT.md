# Agent data/retrieval — 08/11/2026

Scope: local knowledge routing/retrieval; không migrate/xóa data, không sửa
runtime DB, không mở holdout/trading hoặc Goal nghiên cứu chiến lược.
Report owner: [data review](../../research/AGENT-DATA-RETRIEVAL-20261108.md).

## Trước thay đổi

- Current-context64.486B/759lines, receiptAI548.636B/7.170lines.
- Research205files/147Markdown≈1,67MB. Một campaign private≈21,45GB, riêng
  CSV15,80GB/JSON5,50GB; không coi đây là data toàn máy hoặc file có thể xóa.
- Xerj pinned binaryverified; manifest518files đãstale so currentbase526;
  oldallowlist không nhận CURRENT-CONTEXT/research docs. MCP chưa expose
  search tool trong phiên này; không sửa config để giả capability.

## Thay đổi và cách kiểm

- Context hiện hành5.065B, giảm92,1%bytes; full originalsnapshot+sha/base ở
  `planning/archive/2026-11-08-context-storage-review/`.
- Xerj opt-in research docs/3operationsdocs/Forexresearchcontract; CodeGraph
  dùng helper defaultFalse, phạm vi của nó giữ nguyên, chưa reindex graph. Local lexical mode,
  authloopback node hữu hạn của wrapper cósẵn, không service/embedding API mới.
- `test_xerj_research_scope.py` kiểm allowlist/privacy/escape/freshness.
- Skill evidence-continuity sửa nhỏ để giữ currentstate+locator và tra cứu
  đúngsource; không publish package hoặc đổi quyền Paperclip.

## Smoke queries đăng ký trước retrieval

| Query | Nguồn cần thấy trong top5 |
|---|---|
| `R023 primary US stress 2019` | `planning/research/LOCAL-SESSION-RESULTS-20261108.md` |
| `lỗ đúng luật hay lỗi hệ thống` | `planning/research/OWNER-EVIDENCE-REPORT-20261108.md` |
| `PreECB MAE MFE path risk` | `planning/research/PRE-ECB-PATH-RISK-RESULTS-20261108.md` |
| `unknown reconcile broker submission` | `tooling/ai-engines/OPERATIONS.md` hoặc `STRATEGY-WORKFLOW.md` |
| `lossless Parquet tick cache raw hash` | `projects/trader/foundation_v2/docs/FOREX-RESEARCH.md` |

Expected locator là câu hỏi về đúng nguồn, không đo model trả lời đúng hoặc
globalrecall. Giữ cả miss; latency gồm freshness/node startup. Không đổi query
hoặc expectedtarget theo output để làm pass. Rawlogs/manifests ở runtime
benchmark riêng, không đưa vào corpus hoặc commit secrets.

## Kết quả thực tế

Index mới680tracked files, gồm148researchMarkdown; scanmanifest không có
archive/holdout/checkpoints/runtime/rawCSV/JSON/Parquet/DB. Nativeindex hoàn
tất20,4s; sau bổ sung ghi chú backup/CodeGraph vào maintaineddocs thì index
lại19,7s và kiểm cùng bộ queries. Không thay query hoặc expectedtarget.

| Query ID | Expectedsource trong top5 | Rank | Wallseconds lần kiểm cuối |
|---|---|---:|---:|
|session|Có|2|2,283|
|normal_loss|Có|1|2,450|
|path_risk|Có|2|2,397|
|unknown|**Không**|—|2,323|
|cache|Có|5|2,628|

4/5là smokehit rate của bộ nhỏ có chọn trước, không modelaccuracy hoặc
globalrecall. Medianlatency2,397s gồm hashing/freshness/ownednode startup;
không benchmarkso sánh tổng thời gian làm task hoặc tokenbill. Cả5CLIexit0
không biến miss thành pass. Logs giữ cả hai lượt ở
`.runtime/search/benchmark/agent-research-20261108{,-final}/` cùng manifests/
results, không source upload hoặc embeddingprovider được cấu hình.

Miss`unknown`: top hits là code demo_trading/reconciliation và brief cũ,
không operationsowner đã yêu cầu. Nativepinned`search --help` không có path
filter; chưa thêm customranker hoặc đổi sang semanticservice chỉ để pass.
Fallback đã kiểm: `rg -n 'unknown|reconcil' tooling/ai-engines/OPERATIONS.md`
tìm được nguồn, gồm mục Reconcile unknown outcomes before retry. Với thao tác
broker, route thẳng tới operations/grant/ledger theo skill, không tin global
top5 hoặc hồi đáp LLM để cấp quyền. Giữ miss để đánh giá hybrid sau nếu cần.

Validation:

- `python -X utf8 -m unittest discover -s tooling/tests -p test_xerj_research_scope.py -v`:
  5tests đạt, gồmpositive/negative scope và source mới/đổi làm index stale.
- `quick_validate.py .agents/skills/evidence-continuity` và scopedskilllinks:
  hợp lệ,0linkerrors. Maintainerforceaudit0errors/0warnings:
  global12.279B/project10.133of65.536B/reserve55.403B/combined22.412B.
- Canonicalcontext/researchreport/searchguide/receipt/skill links đều đạt;
  snapshotoriginalbytes/hash khớp. Linkssnapshot dùngoriginalbase đã ghi,
  không giả chúngresolve tạiarchive mới.
- Manualread-set: hỏi trạng thái nghiên cứu → currentcontext ghi GoalclosedB
  và trỏownerreport; cần lịch sử mới mởsnapshot. Hỏi brokerunknown → readowner,
  không coi searchresult là permission. Đây là walkthrough cùngagent, chưa
  đánh giá model routing độc lập hoặc toàn hệ thống vận hành.
- Binaryhash pin và finalindexfreshness đạt; không process`xerj.exe` còn chạy
  khi kiểm cuối. Không reindexCodeGraph hoặc claimMCPtool đã expose trong phiên.

Giữ rawdata/financialresults/DB/broker/runtime và unrelatedWIP. Skill chỉ sửa
repo; chưa publish/assign Paperclipnativepackage. Rollback bằng Git cho source/
docs, restorecontext từ byte snapshot; searchindex derived có thể rebuild,
không cần rollback dữ liệu tài khoản hoặc sửa frozenresearchartifacts.
