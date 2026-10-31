# Đội agents cho nghiên cứu giao dịch

Khảo sát: **31/10/2026**. **ĐỀ XUẤT, CHƯA ÁP DỤNG CẤU HÌNH**.

Owner giao đọc docs và kinh nghiệm cộng đồng để chọn cách tổ chức đội phù hợp.
Tài liệu này bổ sung [brief kiến trúc](AUTONOMOUS-TRADING-SYSTEM-BRIEF.md), không
thay acceptance/receipt, không cấp quyền chạy engine hoặc giao dịch. UI trước,
backend/services sau vẫn là thứ tự hiện hành; UI audit rộng tiếp tục pause.

## 1. Khuyến nghị

Khởi đầu bằng **3 agent: Điều phối → Nghiên cứu + Kiểm chứng độc lập**.
Paperclip quản lý công việc; RD-Agent và TradingAgents là engine được gọi theo
nhiệm vụ, không nhân đôi toàn bộ vai trò của chúng thành nhân sự Paperclip.

| Agent / tên kỹ thuật đề xuất | Trách nhiệm | Kết quả bàn giao |
|---|---|---|
| Điều phối nghiên cứu / `research-lead` | Chuyển mục tiêu owner thành đề tài có phạm vi, giao việc, theo dõi blocker, tổng hợp kết luận | Đề bài, kế hoạch thử, báo cáo ngắn cho owner |
| Nghiên cứu chiến lược / `quant-researcher` | Nghiên cứu giả thuyết, viết candidate, chạy thử trên phần dữ liệu được cấp | Code, giả thuyết, nhật ký tất cả lượt thử, artifact có phiên bản |
| Kiểm chứng độc lập / `validation-reviewer` | Xem timing/data/code và kết quả bộ đánh giá; yêu cầu bổ sung hoặc chặn chuyển bước | Kết luận đạt / không đạt / thiếu bằng chứng / lỗi, kèm lý do |

`research-lead` là đầu mối của owner; hai agent còn lại báo cáo hành chính cho
lead. Quan hệ quản lý không cho lead quyền sửa kết quả kiểm chứng, bỏ qua gate
hoặc tự cấp quyền dùng tiền. Tính độc lập đến từ quyền dữ liệu/công cụ và policy
bảo vệ kết quả, không chỉ từ một prompt hay dùng model khác.

Sau khi có chiến lược và adapter demo đạt yêu cầu mới bổ sung **Vận hành demo**:
theo dõi phiên bản đã được phép, sức khỏe run và đối soát; quyền gửi lệnh nằm ở
dịch vụ execution riêng. Việc phát triển Trader là lane kỹ thuật riêng theo
task, không trộn vào đội nghiên cứu thị trường thường trực.

Đây là lựa chọn kiến trúc cho giai đoạn đầu, chưa là kết luận 3 agent luôn tối
ưu. Chỉ tách thêm vai trò khi job thật cho thấy thiếu chuyên môn, quá tải context
hoặc cần kiểm chứng song song; đo thời gian, lỗi và chất lượng artifact trước.

## 2. Cộng đồng có gì và nên học gì?

| Nguồn | Điểm hữu ích | Giới hạn khi áp vào workspace |
|---|---|---|
| [Paperclip Team Catalog](https://docs.paperclip.ing/guides/org/team-catalog/) | Có mẫu leader–builder–checker; preview trước khi tạo đội, chọn runtime khi cài | Mẫu phần mềm chưa có kiểm chứng chiến lược giao dịch |
| [ClawTeam Capital](https://github.com/paperclipai/companies/tree/main/clawteam-capital) | Portfolio Manager, 5 analyst và Risk Manager; phân tích nhiều góc nhìn | Thiên về tổng hợp ý kiến đầu tư; chưa đủ vòng phát hiện chiến lược, OOS và execution |
| [ClawTeam Research Lab](https://github.com/paperclipai/companies/tree/main/clawteam-research-lab) | Phân chia nghiên cứu tài liệu, phương pháp, thí nghiệm và tổng hợp | Không sao chép mục tiêu tối ưu tham số hàng loạt; trading cần giới hạn thử và bảo vệ dữ liệu kiểm chứng |

Hai mẫu ClawTeam tự khai v0.1.0/MIT, được sinh từ ClawTeam và còn nhắc cơ chế
mailbox của ClawTeam. Đây là tài liệu tham khảo vai trò; chưa xác nhận import
trọn gói tương thích bản Paperclip đang pin. Không có bằng chứng độc lập trong
những nguồn đã đọc rằng cài mẫu này tạo được chiến lược có lợi nhuận.

Hai kinh nghiệm vận hành đáng áp dụng:

- [Issue #4027](https://github.com/paperclipai/paperclip/issues/4027): operator
  báo timer thức dậy nhiều khi chưa có bảo vệ chi phí. Issue đã đóng dạng trùng;
  bản pin hiện có idle-skip và daily caps. Bài học là kiểm tra policy thực tế,
  không suy rằng lỗi báo trước đây còn tồn tại nguyên trạng.
- [Issue #4985](https://github.com/paperclipai/paperclip/issues/4985): người xây
  đội trading báo output JSON bị bọc bằng văn xuôi. Đây là báo cáo về adapter/
  phiên bản của họ, chưa tái hiện ở đây. Kết quả chuyển bước phải được code
  validate theo schema; câu “đã kiểm chứng” do agent viết không phải bằng chứng.

## 3. Phân công cho các engine đã chọn

| Thành phần | Công việc đúng vai trò | Khoảng trống cần xử lý |
|---|---|---|
| Paperclip | Task, người chịu trách nhiệm, phụ thuộc, lịch sử, approvals và giới hạn run | Chưa có hợp đồng job nghiên cứu và quyền chuyển sang demo của workspace |
| RD-Agent | Vòng giả thuyết → triển khai → thử → feedback bên trong job nghiên cứu | Finance Quant mặc định dựa Qlib; chưa có job Linux hoặc data adapter MT5/crypto được chấp nhận ở đây |
| TradingAgents | Phân tích tin tức/thị trường, phản biện giả thuyết khi đề tài cần | Không cần gọi mọi analyst cho mỗi thử nghiệm; Risk Manager LLM không thay bộ giới hạn rủi ro bằng code |
| Quant Lab | Tính kết quả theo quy tắc cố định, timing/chi phí, benchmark và provenance | Nền hiện tại là crypto spot D1, không short/leverage; chưa đủ để mô phỏng Forex/MT5 |
| LangGraph | Trạng thái và bước chạy bên trong engine dùng nó | Không dựng thêm tầng quản lý đội song song với Paperclip |

Nguồn engine: [RD-Agent Finance Quant](https://rdagent.readthedocs.io/en/latest/scens/quant_agent_fin.html),
[TradingAgents](https://github.com/TauricResearch/TradingAgents),
[quy tắc Quant Lab hiện tại](../../projects/quant-trading/AGENTS.md).
Thị trường và timeframe đầu tiên vẫn chưa được owner chốt. Reuse bộ đánh giá
hiện có không tự biến crypto D1 thành lựa chọn mặc định cho sản phẩm.

## 4. Một công việc đi qua đội như thế nào?

1. **Chốt đề bài:** lead ghi giả thuyết, thị trường, dữ liệu biết đến thời điểm
   nào, baseline, chi phí, phạm vi tham số và điều kiện dừng. Chưa có dữ liệu
   đáng tin thì giao job kiểm tra dữ liệu trước, chưa tìm chiến lược.
2. **Nghiên cứu:** researcher dùng dữ liệu phát triển/validation được cấp;
   RD-Agent làm vòng thử bên trong. TradingAgents chỉ được gọi nếu có câu hỏi
   phân tích cụ thể. Ghi mọi lượt thử kể cả thất bại, tránh chỉ giữ kết quả đẹp.
3. **Đóng băng candidate:** lưu code hash, engine/model/config, dataset snapshot,
   split và cost model; bộ đánh giá chạy phiên bản này theo policy đã cố định.
4. **Kiểm chứng:** reviewer kiểm data leakage/look-ahead, phí/slippage, độ ổn định,
   so với baseline, overfit/underfit và khả năng tái lập. Thiếu dữ liệu hoặc ít
   giao dịch là “thiếu bằng chứng”, không ép thành đạt hay không đạt.
5. **Báo owner:** lead tổng hợp kết quả và bước tiếp. Quyền thử demo là quyết định
   riêng sau bằng chứng; bước dùng tiền thật ban đầu vẫn cần owner duyệt.

Train dùng để phát triển, validation hỗ trợ lựa chọn trong phạm vi định trước;
final holdout được giữ riêng và chỉ mở theo policy đã chốt. Nếu đã xem holdout
rồi sửa candidate theo nó, lần chạy đó trở thành một phần quá trình nghiên cứu,
không tiếp tục gọi cùng tập ấy là kiểm chứng độc lập. Agent nghiên cứu không
được đọc dữ liệu/metric chi tiết của holdout qua log, tool hoặc shared folder.
Data split cũng không loại hết tri thức tương lai mà LLM có thể đã học khi
pretraining; phân tích lịch sử có tin tức cần provenance/cutoff và giới hạn rõ.

Paperclip giữ mỗi task một assignee; tách task nghiên cứu và kiểm chứng, khai
báo blocker rõ. Parent/subtask chỉ biểu thị cấu trúc, không tự tạo dependency.
Paperclip own dispatch/retry/cancel cấp job; engine own vòng thử nội bộ có giới
hạn. Resume phải đối soát job ID trước khi tạo lại, tránh chạy trùng thí nghiệm.

## 5. Cấu hình khởi đầu đề xuất

Đây là mục tiêu cấu hình cho lát triển khai sau, **không phải YAML đã import**.
Tách setup/review đội khỏi quyền thực thi; tạo agent có thể phát sinh onboarding
run nên phải kiểm tra hành vi wake trước khi ghi cấu hình.

| Hạng mục | Đề xuất |
|---|---|
| Ngôn ngữ | Trao đổi/báo cáo owner bằng VI; giữ tên code, schema, model ID và metric chuẩn |
| Timer | Tắt chạy theo khoảng thời gian lúc đầu; chỉ chạy task được giao khi mở execution có chủ đích |
| Đồng thời | 1 run/agent; 1 job nghiên cứu toàn đội trong pilot để dễ truy vết |
| Phạm vi thử | Mỗi đề tài khởi đầu tối đa 3 candidate; baseline không tính candidate; mọi biến thể tham số vẫn tính một lượt thử |
| Retry | Tối đa 2 lần retry lỗi kỹ thuật; kết quả yếu không là lỗi kỹ thuật. Sửa theo review phải tạo revision và tính vào giới hạn thử |
| Dừng | Hết phạm vi thử, timeout, thiếu data/tool, lỗi lặp hoặc không có artifact mới thì dừng và báo blocker |
| Quyền | Không tự tuyển agent, sửa kết nối/model/runtime/skill, mở tool hoặc thay policy/holdout/tiêu chí đánh giá |
| File/tool | Lead chỉ task và báo cáo; researcher viết vùng candidate; reviewer đọc candidate và gọi bộ đánh giá được kiểm soát |
| Vốn | Không broker key hoặc quyền live trong đội nghiên cứu; quyền demo/execution được cấp riêng sau này |

Số candidate/retry là mặc định thử nghiệm **đề xuất**, không là tiêu chí chứng
minh chiến lược tốt. Timeout, daily run caps và ngân sách cụ thể cần định theo
job/provider được qualification; không bịa số USD khi chưa đo chi phí thực tế.

Source pin hỗ trợ `runtimeConfig.heartbeat` với `enabled`, `intervalSec`,
`wakeOnDemand`, `maxConcurrentRuns`, `skipTimerWhenNoActionableWork`,
`maxDailyRuns`, `maxDailyCostCents`. Tắt timer không chặn on-demand wake. Giới hạn
1 job toàn đội và số candidate/retry nội bộ là contract của integration cần
làm thêm, không được coi đã có chỉ vì đặt giới hạn heartbeat.

Docs/source cũng cho thấy standard agents được cấp mặc định quyền cấu hình
agent, tạo skill và quản lý connections/tools; tắt riêng `canCreateAgents` là
chưa đủ. Cần kiểm direct grants, quyền kế thừa, self-config/wake và tool/run
policy; xác minh cả thao tác bị từ chối. Prompt cấm thao tác không thay được
quyền API/filesystem. Không mặc định low-trust sandbox chạy được trên Windows.
Tham chiếu: [Agents](https://docs.paperclip.ing/guides/org/agents/),
[permission defaults tại pin](../../projects/integrations/paperclip/doc/agent-permission-defaults.md).

Budget Paperclip dựa cost events được báo cáo. Engine gọi model bên trong phải
gửi cả token/chi phí về run tương ứng. Số tiền 0 hoặc thiếu cost events không
chứng minh không tiêu quota/chi phí; cần cả giới hạn lượt thử, thời gian và token
ở engine. Owner từng cho phép thử Gemini thoải mái không có nghĩa cho phép
vòng lặp vô hạn hoặc bật lịch chạy nền thường trực.

## 6. Model, CLIProxyAPI và artifacts

Chọn model theo năng lực thực tế: lead cần phân rã/tổng hợp, researcher cần code
và tool use, reviewer cần phát hiện lỗi và giải thích bằng chứng. Chưa chốt tên
model trước khi kiểm route, schema/tool use, timeout và resume trên fixture.
Reviewer có thể dùng model khác để giảm lỗi chung; điều đó không tự bảo đảm
tính độc lập hoặc độ đúng của phép tính.

[Docs custom model providers](https://docs.paperclip.ing/connectors/custom-model-providers/)
và source pin khớp: Responses API đi với Codex; Messages API với Claude;
Chat Completions với OpenCode/Hermes. Gemini CLI dùng đường kết nối native,
không đơn thuần nhận URL OpenAI-compatible. Với CLIProxyAPI cần qualification
đúng giao thức và model ID; không chọn adapter chỉ vì tên model là Gemini.
Chọn connection rõ trên agent, không thay tài khoản mặc định toàn Windows.
Port/path tiếp tục theo [registry hiện hành](../../projects/trader/foundation_v2/local-services.json),
không tạo registry mới hoặc đụng standalone CLIProxyAPI ngoài project.

Artifact bàn giao đề xuất gồm `job_id`, `candidate_id`, code/dataset/config hash,
data cutoff, split/cost version, seed, engine/model ID, toàn bộ thử nghiệm,
metric, trạng thái và đường dẫn evidence. JSON/schema sai → lỗi contract; process
exit 0 → chỉ kết thúc process; chỉ artifact hợp lệ mới được đưa sang đánh giá.
Giữ artifact ngoài context chat để thay engine hoặc model vẫn tiếp tục được.

Process/HTTP adapters là cách nối worker, không thay được hợp đồng job dài:
submit, status, artifact, cancel và đối soát resume. Paperclip HTTP adapter không
phải ô để dán trực tiếp chat-completions endpoint rồi gọi đó là một agent.

## 7. Những gì đã xác minh và bước triển khai tiếp

Đã đọc docs online, community templates/issues và đối chiếu source local ngày
khảo sát. Pin đã đọc: Paperclip `e123c2b`, RD-Agent `484776c2`, TradingAgents
`ecaafe5`; Git/catalog tiếp tục là nguồn revision chính, không nâng upstream.
Chưa benchmark topology/model, import template, chạy RD-Agent hoặc xác nhận
profitability; lần nghiên cứu này không thay runtime, permissions hay agents.

Lát tiếp phù hợp: cho owner xem **sơ đồ 3 vai trò + một đề tài mẫu** ngay trong
UI Paperclip, cùng quyền/cách dừng dự kiến; chưa tự bật automation. Sau review,
thực hiện một job offline có artifact thật để qualification đường giao việc,
ngắt/resume và kiểm chứng. Chỉ khi quan sát được luồng lặp hữu ích mới đúc kết
skill vận hành; không tạo skill mới từ một workflow chưa chạy.

Nguồn bổ sung để triển khai đúng bản pin:
[YAML editor contract](../../projects/integrations/paperclip/doc/agent-configuration-yaml.md),
[execution semantics](../../projects/integrations/paperclip/doc/execution-semantics.md),
[heartbeat policy parser](../../projects/integrations/paperclip/server/src/services/heartbeat/queue.ts),
[AI connections](../../projects/integrations/paperclip/doc/connections/AI-CONNECTIONS.md).
