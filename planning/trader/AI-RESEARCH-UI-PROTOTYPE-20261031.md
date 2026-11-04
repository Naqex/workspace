# AI workspace — native Paperclip UI và prototype lịch sử

## Phạm vi owner giao — hoàn thiện hệ thống, 03/11/2026

Owner giao hoàn thiện các khoảng thiếu từ dữ liệu đến vận hành giao dịch, ưu
tiên năng lực hệ thống thay vì lặp pilot hoặc tuning chiến lược. Mục này mở rộng
phạm vi offline/source của pilot bên dưới; Product Plan tiếp tục own sản phẩm,
receipt AI hiện có own trạng thái và bằng chứng. Không tạo thêm progress ledger.
Goal tự tiếp tục của Codex chưa được tạo; không cần Goal để thực thi phần đã giao.

### Kết quả cần đạt

| Lát | Acceptance hệ thống |
|---|---|
| Dữ liệu/spec/cost | Input giữ provenance, cutoff, chất lượng và điều kiện chi phí; không dùng unknown như zero hoặc phí hiện tại như lịch sử đã xác minh |
| Research và backtest | Thí nghiệm pin protocol/source/data/spec/cost và giới hạn engine; kết quả phải được kiểm chứng trước khi dùng cho bước sau |
| Promotion và forward | Handoff có artifact binding, criteria và mode rõ; system fixture không tự thành chiến lược đạt, báo cáo model không cấp quyền |
| Risk admission | Đường tự động có policy đóng băng, scope tài khoản/version, limits và stale/unknown gates trước send; không tự đổi semantics của giao dịch thủ công |
| Execution | Reuse native command idempotency, account/generation fencing, unknown reconciliation và kiểm kết quả broker; không thêm đường gọi SDK bỏ qua native API |
| Paper/forward | Có adapter đúng asset/cost/lot semantics, checkpoint/cursor và state có thể khôi phục; không gọi long-only spot accounting là Forex demo |
| Vận hành | Readiness phản ánh process đang sống nhưng mất phản hồi, degraded/recovery có bằng chứng; backup/restore và stop/restart không gửi lại lệnh không rõ kết quả |
| Trải nghiệm | Khép các chuỗi còn thiếu theo owner audit hiện có, ưu tiên tài khoản/dữ liệu/thực thi và giữ management UI native của Paperclip |

Triển khai theo dependency: nối các contract sẵn có và độ tin cậy runtime →
handoff dữ liệu/kết quả và risk/forward adapter → tích hợp native và kiểm đúng
đường vận hành → quan sát dài ngày trong phạm vi được cấp. Gộp kiểm chứng vào
thay đổi thật, focused trước; không redispatch workflow đã hoàn tất chỉ để
thử báo cáo, không thêm engine/framework/agent khi chưa có capability gap.

### Quyền và giới hạn của lần giao

- Được triển khai source, offline fixtures, tài liệu, phối hợp lane và bảo trì
  local theo standing grant trong Trader AGENTS; giữ dữ liệu/account/runtime
  ownership và rollback. Không có quyền ghi đè WIP của task khác.
- Demo order execution là gate riêng: trước một lượt gửi lệnh cần hợp đồng cụ
  thể gồm demo account, symbols, thời hạn, số lệnh/position, ngân sách rủi ro
  và stop/reconcile. Không dùng quyền thử Exness ngày29/10 cho lượt mới.
- Live/Real, challenge trả phí, provider/OAuth mới, migration dữ liệu owner,
  public deployment và service tự chạy lâu dài giữ gate tương ứng. Tiếp phần
  độc lập an toàn khi gặp gate; không tự điền risk budget của owner.
- Hoàn tất source/offline không đồng nghĩa runtime/broker/soak hoặc whole-product
  acceptance. Tiền lãi và strategy qualification là mục tiêu sau, không là
  tiêu chí ép hệ thống phải tạo kết quả có lời.

**Owner duyệt tiếp 03/11:** triển khai tách quyền Owner/runner tự động; được
migration local sau khi có backup được kiểm chứng. Giữ UI Paperclip native;
runner chỉ vào đường Demo có grant bất biến, ngân sách và account/generation
cụ thể. Quyền này cho phép xây và rollout ranh giới bảo mật, không tự cấp grant,
điền risk budget hoặc gửi lệnh demo/Real. Kiểm auth/grant/risk bằng fixture cách
ly trước; owner DB chỉ migration sau quiesce, backup DB/artifact và rollback.

### Kiểm độ bền trước vận hành Demo — owner giao 04/11/2026

Ưu tiên kiểm chặt bằng code production cùng fixture trước, rồi vận hành Demo
có quan sát để tìm lỗi môi trường thực. Không chờ 1–2 năm để kiểm logic thời
gian; không coi hai năm mô phỏng là hai năm uptime. Nhiều máy dự phòng để sau.

- Reuse runner/native receipts và backup helpers để kiểm: thời hạn theo UTC/
  offset, crash trước/sau intent và fill, lỗi ghi checkpoint, mất phản hồi,
  reconcile nhiều lần không gửi trùng; checkpoint/dữ liệu phục hồi không làm
  sống lại quyền đã thu hồi/hết hạn.
- PostgreSQL disposable: committed ledger qua crash thật và restore; so row
  counts/hash và chạy lại native admission trên dữ liệu đã hồi phục. Không dùng
  DB owner làm chaos target. Chỉ tăng workload để trả lời rủi ro cụ thể.
- Regression cần thiết vào CI hiện có; dùng receipt AI hiện hành để ghi nguồn,
  phạm vi, thất bại và kết quả. Không thêm engine, scheduler hoặc ledger mới.
- Sau gate offline, kiểm runtime Demo theo điều kiện dừng/cảnh báo và authority
  cụ thể. Đọc/quan sát không mở grant hay OrderSend. Backup ngoài máy, kênh gửi
  cảnh báo, task tự khởi động lâu dài hoặc giao dịch mới cần cấu hình/quyền đúng
  phạm vi trước khi bật; chưa có thì báo rõ, không tự chọn cloud/tài khoản mới.

Owner trả lời tiếp04/11: chưa có đích backup ngoài máy/kênh cảnh báo; hoàn tất
local trước. Hai phần external này để sau, không là quyền chọn provider mới.
Owner sau đó xác nhận G là ổ rời nhưng giao tiếp phần hệ thống, để việc backup
ổ rời/cloud lại khi cần; chưa bật copy, retention hoặc lịch backup mới.

### Tiếp nguồn dữ liệu forward — owner giao tiếp 04/11

Sau khi khép lỗi snapshot/clock, tiếp nguồn quote có thể khôi phục: reuse native
API/owned worker và identity/generation/terminal lock để đọc lịch sử tick theo
đoạn có giới hạn. Consumer ghi đoạn bất biến cùng provenance/hash trước cursor,
resume kiểm prefix và đọc lại đoạn cuối; lỗi, đổi nguồn hoặc broker sửa đoạn đã
ghi phải chặn tiến tiếp. Kiểm offline crash/network/disk/concurrency và một lượt
đọc Demo ngắn, không gửi lệnh hoặc chạy chiến lược. Requested-range cursor không
là bằng chứng đủ tick, source watermark, forward profitability hoặc 24/7 uptime.
Không cài daemon, lịch, UI quản lý hoặc state quyền giao dịch song song; continuous
forward/coverage qualification vẫn là acceptance riêng. Receipt AI giữ kết quả.

### Phiên forward shadow có giám sát — owner duyệt tiếp 04/11

Owner giao làm tiếp phiên hữu hạn: nối nguồn observed vào ứng viên H4 cố định,
quy tắc chất lượng/đóng nến rõ, Rust quản lý start/stop/deadline/recovery, rồi
kiểm một lượt chỉ đọc có gián đoạn và báo cáo native Paperclip. Không tuning,
fill/P&L giả, OrderCheck/OrderSend, lịch tự boot hoặc service 24/7 mới.

Reuse capture/provenance và owned-process Job hiện có. Requested cursor không
thành watermark: chỉ đưa giờ được yêu cầu đầy đủ, qua thời gian chờ và đọc lại
không đổi vào shadow; gap vượt chính sách chặn thay vì tạo nến. Quality vẫn là
mẫu quote quan sát, không chứng nhận đủ tick. Giờ đầu/cuối chưa đủ giữ partial;
thiếu warmup thì báo warming_up, không ép tín hiệu. Python giữ reducer/SDK path,
Rust giữ lifecycle hữu hạn; checkpoint vận hành không thay task/run Paperclip.
Receipt AI giữ source/offline/runtime và giới hạn acceptance riêng.

## Hướng hiện hành — owner tự setup,01/11

### Ưu tiên hiện hành — hoàn thiện hệ thống AI, 02/11

Owner làm rõ: chưa muốn dành thời gian tối ưu chiến lược; ưu tiên hệ thống AI
và workflow vận hành. Đề xuất validation2023 trước đó được gác lại. Giữ nguyên
candidate EURUSD/H4, dữ liệu đã dùng và kết quả đã lưu làm fixture kỹ thuật;
không tuning, tìm candidate mới hoặc mở thêm dữ liệu để chứng minh lợi nhuận.

Lát tiếp theo: nối workflow Forex offline qua cơ chế native Paperclip đã có,
reuse QDM CLI, runner và worker phản biện hiện có. Bắt đầu từ luồng owner nhìn
được trên UI: giao nhiệm vụ → chuẩn bị dữ liệu → mô phỏng → phản biện → báo cáo.
Đối chiếu implementation/evidence hiện có trước khi sửa; bổ sung đúng mắt xích
còn thiếu, không chạy lại toàn bộ pilot crypto hoặc tạo engine/UI song song.

Acceptance hệ thống:

- Một nhiệm vụ dẫn được tới đúng input/spec/config/output bằng run ID và hash;
  kết quả hiển thị trong native task/report của Paperclip nhúng trong Trader.
- Bước sau chỉ nhận output hợp lệ của dependency đã thành công; nguồn thiếu,
  lỗi, sửa hash hoặc hủy phải chặn handoff và hiển thị hành động tiếp theo rõ.
- Owner xem được tiến độ, kết quả/lỗi và hủy; retry có kiểm tra trạng thái để
  không tạo worker trùng hoặc làm mất lịch sử lượt trước. Dùng cơ chế khôi phục
  đã có, ghi rõ phần nào chỉ hỗ trợ chạy lại và phần nào tiếp tục từ checkpoint.
- Một lượt fixture offline xuyên suốt và các failure/cancel checks cần thiết
  chứng minh luồng; kiểm latency/resource theo bottleneck đo được, không mở
  benchmark hoặc refactor rộng khi chưa có vấn đề thực tế.
- Source, runtime, workflow/provider và strategy qualification có bằng chứng
  riêng trong receipt hiện có. Workflow đạt không đòi fixture phải có lãi và
  không mở demo orders/live, scheduler hoặc quyền dùng tiền.

Thứ tự: rà luồng hiện có và biểu diễn trên UI → nối điểm thiếu → kiểm một lượt
xuyên suốt → xử lý lỗi vận hành còn lại. Không cần thêm repo/engine chỉ để đủ
thành phần. Phát triển/đánh giá chiến lược là giai đoạn tiếp theo, có giao việc
và tiêu chí riêng. [Receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md)
giữ trạng thái và bước tiếp; mục này chỉ giữ scope/acceptance.

Điểm tiếp tục sau pilot02/11: mục **Workflow Forex native xuyên suốt** trong
receipt. Hoàn thiện cách owner tạo mẫu/hủy cả graph qua UI bằng khả năng native
trước; không chạy lại pilot đã thành công hoặc coi task review là duyệt paper.

### Studio — điều khiển quy trình, 02/11

**Owner điều chỉnh02/11:** dùng thẳng UI native Paperclip trong **Studio → Đội AI**;
bỏ dialog/nút Quy trình và HTTP bridge ngoài để tránh hai UI quản lý cùng task.
Trader chỉ giữ phần nhúng, preference và kết nối. Helper CLI giữ contract riêng
của graph, kiểm dữ liệu giữa engine, đối soát receipt và hủy cả nhóm bước.
Receipt mục **Studio: điều khiển workflow từ UI** giữ lịch sử lát đã thực hiện;
mục **Studio: vận hành native, đối soát run/receipt** ghi thay đổi thay thế và
kiểm chứng hiện hành. Không chạy lại model chỉ để kiểm UI.

Thứ tự tiếp theo cho hệ thống:

1. Hoàn thiện visibility về quota/chi phí và kết quả chưa xác định; đối soát
   native run/receipt trước mọi retry. Chi phí chưa biết phải hiện unknown.
2. Chỉ thêm lịch chạy khi đã có giới hạn số lượt/chi phí, chống chạy trùng,
   khôi phục sau restart và đường dừng được kiểm chứng. Lịch hiện vẫn tắt.
3. Sau đó mới xét nghiên cứu tự chủ trong phạm vi đăng ký. Tối ưu chiến lược,
   qualification và paper/demo/live là những acceptance riêng, chưa khởi động.

### Bằng chứng nền — Forex/prop offline, 02/11

Owner đã đăng nhập FTMO demo; thông số EURUSD được đọc/pin. Contract mục10
đăng ký chạy lại hai tuần và mở development quý I/2022, cả hai đã hoàn tất;
validation/holdout chưa đọc. Python offline có timed cash events, phí theo lot,
entry sau decision và stop từ actual fill. Kết quả, code/input/spec hashes và
giới hạn ở receipt; chưa là strategy/Prop qualification. Các đoạn tiếp sau giữ
lịch sử những lát trước, không phải trạng thái hay thứ tự thực thi hiện hành.
Các mô tả capability/phạm vi bên dưới giữ lịch sử của các lát trước;
không dùng chúng để chạy lại probe hoặc thu hẹp quyền dữ liệu owner vừa duyệt.

Owner đã chuyển ưu tiên sang Forex major/MT5, FTMO 2-Step Swing làm chuẩn mô
phỏng. Hoàn thành lát nhỏ: đăng ký [contract nghiên cứu](../research/FOREX-PROP-PILOT-20261102.md)
trước outcome Forex, reuse Prop domain của Trader và kiểm balance anchor độc
lập với equity. EURUSD/H4/10.000 USD và risk25 USD là giả định offline của
agent, chưa là lựa chọn tài khoản/risk budget tiền thật do owner duyệt.
[Receipt hiện có](../checkpoints/ai-integrations-20261031/RECEIPT.md) giữ source/test
results và lượt export M1/tick ngày03/01/2022 qua
[QDM CLI đã có](../../projects/trader/docs/quantdatamanager.md). Tick Bid/Ask đã
kiểm format; cost/spec còn thiếu cho Forex runner, chưa backtest outcome, workflow dispatch, UI preset
hoặc rollout; không tự mở trial/challenge/broker.
Bổ sung02/11: owner cho phép tải toàn bộ tick EURUSD vào cache QDM để reuse;
CLI đã tải xong cache và export chỉ03/01/2022 (65.215 ticks), giữ15 phút không
có quote để review. Risk guard25/100/500 USD đã có source candidate và focused
tests; chưa nối runner/runtime. Probe BUY/SELL baseline/stress đã đối soát
accounting trên giờ development đăng ký. Lượt đầu dùng terminal valuation;
lượt tiếp đã có queued causal exit với proof/JSON restart, đối soát lại4 scenarios.
Lát này còn PARTIAL ở broker spec/cost, timed financing và H4 runner;
bằng chứng/source revision/cách resume ở receipt AI được dẫn trên.
Quyền tải cache không mở quyền phân tích validation/holdout.
Các workflow crypto bên dưới giữ lịch sử và không là adapter Forex.

### Lát được giao tiếp — workflow crypto spot nối tiếp, 02/11

Owner đã chọn ưu tiên crypto và giao triển khai workflow spot: nghiên cứu →
RD-Agent/Quant Lab → Hermes phản biện → owner xem kết quả. Dùng native tasks,
parent/dependency wakeup của Paperclip; giữ đội và UI gốc. Lượt kiểm tích hợp
dùng lại contract BTC/ETH D1 cố định đã có, không tune hoặc coi dữ liệu cũ là
holdout mới. Một lần chạy lại phục vụ kiểm handoff, không tìm số đẹp hơn.

Acceptance: tạo graph idempotent; bước phản biện chỉ đọc đúng output/hash/run
thành công của dependency; dữ liệu sửa/lỗi/cancel chặn bước sau trước inference;
báo cáo nguồn và kết quả hiển thị trong Trader. Parent chờ owner review, paper
giữ NOT_RUN và không mở broker/live/lịch. Kiểm lifecycle/cancel và failure bằng
fixture offline; một real workflow qua Gemini đủ để xác minh đường tích hợp.
Source/research qualification/paper acceptance tiếp tục ghi riêng trong receipt
owner hiện có. Không cần thêm agent, engine hay vá Paperclip core.

**Kết quả:** [NAQ-20](http://127.0.0.1:17860/NAQ/issues/NAQ-20) có research
NAQ-21 và phản biện NAQ-22 nhận tự động qua native dependency. Đã sửa lỗi bàn giao
thiếu human review path bằng fixture NAQ-24, không gọi lại model; parent hiện
`in_review` giao Board, paper NAQ-23 vẫn blocked/NOT_RUN. Receipt giữ run lỗi gốc,
recovery và giới hạn browser; chưa là chiến lược đạt hoặc toàn bộ AI autonomy.

### Tiếp tục 02/11 — kiểm ứng viên cũ và mức sẵn sàng dùng tiền

Owner hỏi hệ thống đã kiếm tiền được chưa và giao tiếp tục. Lát này kiểm lại
Donchian100/50 + vol30% đã có trên snapshot BTC/ETH cũ, không tìm tham số, gọi
model hoặc mở holdout/broker. Contract ghi trước đánh giá; kết quả là chẩn đoán
dữ liệu đã xem, không phải qualification. Tái hiện rồi sửa lỗi đơn vị timestamp
ở quality audit Quant Lab; reissue manifest từ đúng CSV/hash cũ, giữ lịch sử.

Kết quả và giới hạn trong [báo cáo owner](../checkpoints/ai-integrations-20261031/STRATEGY-READINESS-20261102.md)
và receipt cùng thư mục; bản đọc đã đăng vào tài liệu NAQ-20, parent vẫn chờ
owner, paper NOT_RUN. Bước sau ưu tiên kiểm giá khớp/accounting thực tế và tiêu
chí rủi ro trước forward paper; không thêm engine hay coi lợi nhuận backtest là
quyền dùng tiền thật. Lỗi timestamp đã có focused regression, chưa phải audit
toàn bộ Quant Lab hoặc toàn sản phẩm.

### Bổ sung 02/11 — Hermes như worker tùy chọn

Owner duyệt giữ native workers và thử thêm Hermes. Acceptance: profile riêng,
Gemini qua gateway project, một task phản biện hồ sơ NAQ-6 so với cùng model/input
gọi trực tiếp; kiểm memory qua lượt mới, đăng native document và hủy SDK đang chờ
bằng fixture offline. Không thay engine số liệu, không mở broker/holdout/lịch.
Thực thi qua SDK Hermes + native process của Paperclip; CLI của release hiện hành
tự mở daemon nên không chọn làm đường worker. [Guide](../../tooling/ai-engines/hermes.md)
giữ setup/boundaries; [receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md)
giữ benchmark, lỗi đã gặp và giới hạn. Không suy rộng pilot thành toàn bộ autonomy.

### Lát được giao tiếp ngày 02/11 — một workflow nghiên cứu có dữ liệu thật

Owner giao triển khai cả luồng: snapshot lịch sử cố định → một factor RD-Agent
→ Quant Lab kiểm chứng → native Paperclip hiển thị báo cáo. Dùng contract nhỏ
`crypto-momentum-3d-v1`, BTC/ETH spot khung ngày, một candidate, không tune theo
OOS. Đây là lựa chọn fixture kỹ thuật để chứng minh workflow, chưa chốt thị
trường/vốn cho hệ thống dài hạn. Không mở protected holdout hoặc broker/demo/live.

Acceptance: snapshot có nguồn/hash/cutoff và quality preflight; factor khớp
oracle/causal checks; Quant Lab so cash/buy-hold cùng timing/cost và chronological
OOS/stress; Paperclip giao việc, hủy được và giữ native report/provenance qua
reload. Source/test, real provider run, native dispatch và strategy qualification
ghi riêng trong [receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Không cần thêm UI hoặc engine. Worker chỉ mở sau focused checks, không scheduler.

**Kết quả 02/11:** workflow đã hoàn tất qua native task
[NAQ-6](http://127.0.0.1:17860/NAQ/issues/NAQ-6), gồm 2.922 nến BTC/ETH,
một candidate Gemini, RD-Agent kiểm factor và Quant Lab đánh giá bốn cửa sổ
OOS cùng chi phí/stress. Native cancel đã kiểm riêng, báo cáo giữ qua reload
trong iframe Trader. Candidate chưa đủ điều kiện chuyển sang demo; worker hiện
idle, timer off. Các dòng paused/chưa nối bên dưới mô tả thời điểm trước đó;
[receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md#0211--workflow-market-factor-qua-native-paperclip)
giữ kết quả, giới hạn và bằng chứng hiện hành.

### Bổ sung sau owner giao nối engine,01/11

Owner đã giao triển khai TradingAgents trước rồi RD-Agent, và chọn **các model
Gemini** cho lượt chạy thực tế; key Opus5.5 trước đó đã hết hạn. Scope mới cho
phép tạo worker engine qua API gốc của Paperclip, không thay agent do owner tạo.
Native process adapter giữ dispatch/cancellation; wrapper giới hạn input, dùng
API upstream engine và trả báo cáo về tài liệu công việc trong UI Paperclip.

Acceptance lát tiếp: một yêu cầu phân tích được giao đúng worker → model Gemini
qua gateway project → báo cáo VI và provenance trong công việc; chặn input sai,
không chạy lại outcome chưa rõ và không có broker execution. Source/fixture,
Paperclip dispatch và model success phải có bằng chứng riêng trong receipt owner
hiện có. Không đồng nhất báo cáo phân tích với backtest/chiến lược đạt.

Owner đã cho phép cài runtime RD-Agent ngày 02/11. Package và container smoke
đã đạt trên WSL2 Ubuntu 24.04 + Docker Engine riêng; chi tiết trong
[runtime guide](../../tooling/ai-engines/rd-agent-runtime.md) và receipt hiện có.
Trước workflow thị trường bên trên, pilot factor giả lập ngày 02/11 đã đạt: một candidate Gemini chạy qua upstream
workspace/evaluators trong Docker, oracle và kiểm tra nhân quả đạt. Worker tiếp
tục paused tại thời điểm pilot; lúc đó còn data adapter thị trường, vòng finance
và native dispatch trước khi mở worker. Không chạy code sinh trên host Windows; pilot chưa là bằng chứng
chiến lược có lợi nhuận. Recipe và evidence theo runtime guide/receipt bên trên.
Hướng dẫn adapter: [engine jobs](../../tooling/ai-engines/README.md).

Các đoạn cleanup/tự setup sau đây giữ lịch sử trước phần bổ sung này.

Owner yêu cầu lưu kết quả test, dọn đội/config/custom UI mẫu và giữ Việt hóa.
Đã dùng API upstream dọn company pilot Naqex AI cùng dữ liệu thử; instance không
còn company. Đã bỏ ResearchTeamPreview và bản vá adapter Windows phục vụ pilot;
giữ localization, bridge ngôn ngữ, static embedding và fix giữ navigation/state.
Gateway project17852 đã dừng/phục hồi override; tài khoản project giữ nguyên.

Owner tự tạo organization → project → một agent qua UI gốc; chỉ giao task sau
khi runtime Test Environment đạt. Không tự provision lại. Native Copilot trong
bản pin bị giới hạn production ACPX trên Windows; Antigravity pending upstream.
MCP có sẵn nhưng cần authenticated deployment/public origin/experimental gate
và OAuth; instance local hiện chưa cấu hình, không đổi auth trong lượt cleanup.

[Hướng dẫn và nghiên cứu](../../tooling/paperclip/README.md),
[kết quả pilot và cleanup](../checkpoints/ai-integrations-20261031/RECEIPT.md)
giữ bằng chứng/giới hạn. UI audit rộng tiếp tục pause. Các mục sau là lịch sử.

## Lịch sử mở rộng UI — 01/11

Đã mở rộng bản dịch VI/EN sang các trang/menu/dialog chuyên sâu của fork bằng
catalog i18next riêng. Trang Agents có **Xem đội và nhiệm vụ mẫu**: sơ đồ ba
vai trò và một nhiệm vụ nghiên cứu để owner duyệt, chưa provision agent/job.
Source Paperclip `11d41b6`; runtime local đã cập nhật cùng revision, giữ DB.
Phạm vi kiểm chứng và giới hạn nằm trong mục ngày01/11 của
[receipt tích hợp](../checkpoints/ai-integrations-20261031/RECEIPT.md).

Tại thời điểm lát UI này, còn cần review trước khi cấu hình agents, provider và
contract chạy job engine. Các mục31/10 dưới đây
giữ lịch sử, không thay coverage và trạng thái mới trong receipt.

## Lát localization tiếp nối — 31/10

Đã nối VI/EN từ Trader preview tới native Paperclip bằng preference message
kiểm origin/source; đổi ngôn ngữ giữ document, bản nháp và search. Fork dùng
i18next namespace `workspace` riêng, giữ locale upstream và tên/nội dung do
người dùng nhập. Phạm vi hiện tại: navigation desktop/mobile, account actions,
task breadcrumb/search/empty/create và trường chính của new-task dialog.
Đây là bản dịch từng phần; filters/composer settings và các trang khác còn EN.

Browser preview5218: 9 cases trên1920/1440/390px; source review độc lập;
focused unit/component, UI typecheck và build đã kiểm. Token gate toàn fork
còn106 lỗi upstream, không thêm lỗi so với pin cũ. Receipt chi tiết nối vào
`planning/checkpoints/ai-integrations-20261031/RECEIPT.md`.
Chưa cấu hình agents/provider hoặc chạy engine job. UI audit rộng vẫn pause;
tiếp theo hoàn thiện các luồng UI cần dùng và cấu hình company/roles cho owner
review trước khi nối job. Root gitlink Trader vẫn giữ baseline để tránh đưa WIP
audit vào lát integration; host feature checkout được ghi ở receipt.

## Lát adoption được owner giao — fork, source và AI environment

Issue: [Naqex/workspace#6](https://github.com/Naqex/workspace/issues/6).
Owner chọn fork Paperclip gốc, RD-Agent, TradingAgents và LangGraph; giao thực
hiện fork/tích hợp và rà skill dài hạn. Thứ tự UI trước engine vẫn áp dụng.

Acceptance lát nền source/runtime:

- Paperclip có fork Naqex và upstream remote riêng; giữ revision đã kiểm chứng,
  không tự nhảy lên master mới nhất khi tạo fork.
- Source ngoài dưới `projects/integrations/`, giữ submodule/layout/license; RD-Agent
  được pin source. LangGraph giữ là dependency TradingAgents, Quant Lab giữ nguyên.
- Paperclip đang nhúng vẫn hoạt động sau chuyển đường dẫn; giữ nguyên company,
  dữ liệu, cổng và preference sidebar. Backup và rollback được ghi trước cutover.
- Hướng dẫn gần source, một skill repo cho workflow upstream đã được thực hiện;
  không tạo skill nghiên cứu AI từ luồng chưa chạy hoặc thay global config.
- Kiểm topology/đường dẫn, dependency/import và native browser phù hợp với thay đổi.

Lát này không chứng minh RD-Agent/TradingAgents đã chạy job model hay toàn vòng
autonomy. Các lát nối engine sau phải có contract job thực tế, authority cho
dispatch/retry và evidence riêng; không khai agent chạy được chỉ vì đã clone source.
Checkpoint của lát này: `planning/checkpoints/ai-integrations-20261031/RECEIPT.md`.

## Lát được giao tiếp theo — native Paperclip

Owner xác nhận nối UI gốc và lưu source trong `projects/`. Đã tích hợp submodule
upstream `projects/paperclip` tại pin `42fd568cf8f588334cacc6004aa23aff54daa52b`,
giữ source nguyên bản. Trader mở AI→Paperclip bằng iframe toàn vùng nội dung;
rail bên ngoài giữ lựa chọn của owner, bên trong dùng điều hướng và dialogs gốc. Dữ liệu
Paperclip có instance riêng; chưa nối engine nghiên cứu/giao dịch.

[Setup/runtime boundaries](../../tooling/paperclip/README.md).
Evidence/source/runtime và các giới hạn được giữ trong receipt
`projects/trader/foundation_v2/evidence/paperclip-ui-20261031/RECEIPT.md`.
Implementation ban đầu ở Trader `98a0871b`, điều chỉnh port/sidebar ở `18e9348d`; gitlink Trader của root
chưa nâng vì HEAD hiện tại còn chứa lịch sử ngoài phạm vi tích hợp này.
Owner yêu cầu tách cổng khỏi app Windows: Paperclip hiện dùng API17860/DB17861/
HMR27860; CLIProxyAPI managed giữ17852, không chạm instance Windows8317.
`foundation_v2/local-services.json` trong Trader giữ cấu hình dùng chung;
`docs/LOCAL-SERVICES.md` và receipt `PORTS-SIDEBAR.md` giữ hướng dẫn/bằng chứng.
Preview owner tại
`http://127.0.0.1:5218/?workspace=tenant-a&view=ai&area=ai&section=paperclip&lang=vi`.
Các đoạn phía dưới giữ lịch sử quyết định/prototype, không thay trạng thái mới.

## Điều chỉnh hướng sau owner review, 31/10

Owner yêu cầu thiết kế UI từ tổng thể vào chi tiết: khung workspace → điều
hướng → UI upstream → các hành trình trading riêng. Ưu tiên nhúng UI gốc
Paperclip như cách Trader nhúng CLIProxyAPI; không tiếp tục dựng các màn quản
lý công việc/agents riêng để thay thế Paperclip.

Prototype `5aafd680` bên dưới giữ làm bản khám phá workflow, chưa được owner
chấp nhận làm giao diện đích. Build/browser receipt của prototype không chứng
minh Paperclip đã tích hợp. UI audit rộng vẫn pause.

Lát tiếp theo đề xuất: Trader giữ điều hướng cấp sản phẩm; khu AI dành vùng
nội dung cho Paperclip với điều hướng nội bộ của chính nó. Khi ở khu này, thu
gọn điều hướng Trader để tránh hai sidebar đầy đủ cạnh nhau. Chốt khung và
chuyển qua lại trước khi làm màn nghiên cứu riêng hoặc nối engine.

Nguồn kiểm tra: [repo upstream](https://github.com/paperclipai/paperclip),
[server](https://github.com/paperclipai/paperclip/blob/master/server/src/app.ts),
[API client](https://github.com/paperclipai/paperclip/blob/master/ui/src/api/client.ts)
và [MIT license](https://github.com/paperclipai/paperclip/blob/master/LICENSE).
UI gọi `/api` trên origin của Paperclip, nên hướng thử đầu là iframe nguyên
ứng dụng tại origin local riêng; không copy riêng bundle vào origin Trader.
Đây là đánh giá từ source, chưa xác nhận iframe/auth bằng runtime. Cần pin
revision và kiểm framing headers, login/cookies, điều hướng, sự kiện và layout
trên đúng bản chạy trước khi kết luận tương thích.

UI gốc cần API/storage của Paperclip để hoạt động; chạy instance local phục vụ
review UI là một lát riêng với dữ liệu riêng và không tự giao việc cho agent.
Chưa cài/chạy instance hoặc nối trading engine từ lần điều chỉnh này. Không
đặt tối ưu hiệu năng giả định thành điều kiện chặn; mount khi mở lần đầu và
giữ state nếu phù hợp, đo bottleneck thật sau. Ẩn UI không có nghĩa dừng agents.

## Scope prototype lịch sử

Owner giao ngày31/10: làm UI trong Trader trước để review workflow; backend và
services chỉ tiếp sau feedback. Owner cho phép thử CLIProxyAPI/Gemini, nhưng lát
UI này không cần gọi model. Brief kiến trúc: [autonomy](../research/AUTONOMOUS-TRADING-SYSTEM-BRIEF.md).

## Phạm vi

- Khu AI có mục Nghiên cứu, dùng shell và design system hiện có.
- Danh sách có tìm kiếm/lọc; chi tiết có quy trình, thử nghiệm và nhật ký.
- Dialog tạo bản nháp với mục tiêu, data/baseline mẫu và giới hạn số lần thử.
- Trạng thái mẫu: đang chạy, hoàn tất/chờ review, thiếu bằng chứng, lỗi và dừng.
- Quyết định demo chỉ là preview; không tạo run, gọi broker hoặc ghi DB.
- State lưu local theo workspace, có báo lỗi lưu và khôi phục mẫu có xác nhận.

UI phải ghi rõ dữ liệu minh họa; không dùng metric giả như bằng chứng nghiên cứu.
Reuse LegacyModal, FxSelect, SearchInput, AppIcon, palette và compact controls.
Giữ VI–EN, dark/light, keyboard/focus và layout desktop/mobile. Không resume
owner-system audit đang pause hoặc stage WIP của nó.

## Kiểm chứng và bàn giao

Build ở output riêng; browser journey trên UI hiện hành với API fixture/deny
cho writes và external traffic. Kiểm create→reload, search/filter, tabs,
stop/decision preview, empty/error, Escape/focus và mobile/light. Review ảnh
thực tế. Receipt source/build/fixture tách khỏi backend/provider acceptance.

Trạng thái/evidence và hướng mở preview giữ trong receipt tại
`projects/trader/foundation_v2/evidence/ai-research-ui-20261031/`.
Source checkpoint trong repo Trader: `5aafd680`.
[Preview UI riêng](http://127.0.0.1:5218/?workspace=tenant-a&view=ai&area=ai&section=research&lang=vi).
Owner xem prototype trước khi giao lát backend/services. Plan này chỉ own scope,
không đóng Product Plan/U/Y/W hoặc cấp quyền live.
