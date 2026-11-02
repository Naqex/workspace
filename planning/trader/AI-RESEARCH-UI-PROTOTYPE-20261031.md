# AI workspace — native Paperclip UI và prototype lịch sử

## Hướng hiện hành — owner tự setup,01/11

### Lát tiếp nối hiện hành — Forex/prop offline, 02/11

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
