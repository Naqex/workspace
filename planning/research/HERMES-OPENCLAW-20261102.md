# Hermes Agent và OpenClaw trong Naqex Workspace

Ngày khảo sát: 02/11/2026. Đây là đề xuất tích hợp, không là acceptance của engine
hay thay đổi quyền giao dịch. Tiếp hướng dài hạn trong
[AI brief](AUTONOMOUS-TRADING-SYSTEM-BRIEF.md); Paperclip hiện sở hữu giao việc,
timeout/cancellation và lịch sử công việc theo [engine contract](../../tooling/ai-engines/README.md).

Bổ sung theo yêu cầu owner: [Ponytail, Superpowers, GSD Core và RTK](CODING-AGENT-ADDONS-20261102.md).

## Kết luận áp dụng

**Giữ kiến trúc hiện có, chưa cài Hermes/OpenClaw vào global hoặc Codex.**
Pilot RD-Agent trên dữ liệu giả lập đã đạt; chi tiết trong
[receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md). Còn vòng finance,
dữ liệu thị trường và native dispatch; chưa có bằng chứng chiến lược đạt.
Nếu cần thêm, chọn từng công cụ cho nhu cầu cụ thể:

| Công cụ | Vai trò | Chỗ phù hợp nếu có nhu cầu |
|---|---|---|
| Hermes Agent | Agent thực hiện việc bằng tools; có memory qua phiên, tạo/cải tiến skills, CLI, desktop, messaging gateway và subagents | Một worker riêng do Paperclip giao việc, nếu benchmark cho thấy làm tốt hơn worker hiện có |
| OpenClaw | Gateway và môi trường vận hành trợ lý qua nhiều kênh chat; có sessions, tools, policies và các agent runtime | Kênh điều khiển/thông báo cho owner qua Telegram hoặc app chat khi thực sự cần |
| Paperclip hiện có | Phân công đội, công việc, approvals, runs và báo cáo | Tiếp tục giữ quyền điều phối workflow nghiên cứu |
| RD-Agent hiện có | Sinh ý tưởng, code và chạy thí nghiệm nghiên cứu dữ liệu/model | Worker nghiên cứu; output còn phải qua kiểm chứng định lượng |

Hai dự án mới đều có nhiều phần giao nhau với nhau và bộ công cụ hiện tại.
Cài cả hai ngay sẽ thêm nơi giữ state/credentials, cấu hình, scheduler và update
mà chưa có tác vụ riêng chứng minh giá trị. Đây là suy luận kiến trúc từ nhu cầu
và source/docs, chưa phải benchmark so sánh khả năng làm việc của các agent.

## Những khả năng đã đối chiếu

### Hermes Agent — Nous Research, MIT

- Upstream mô tả learning loop tạo/cải tiến skills và ghi nhớ kinh nghiệm.
  “Tự cải thiện” ở đây chủ yếu là workflow/skills/memory; không có bằng chứng
  trong khảo sát này rằng nó tự huấn luyện lại trọng số model hay tạo lợi nhuận.
- Có CLI, desktop, messaging gateway, nhiều provider và backend terminal như
  local/Docker/SSH. Chất lượng còn phụ thuộc model, tools, prompt và task.
- Hermes có cả MCP client, plugin MCP server chính thức và ACP; cần phân biệt
  chiều kết nối, tool scope và quyền của từng đường như bảng bên dưới.
- Memory lưu dưới Hermes home/profile và có ghi tự động. Nếu thử nhiều worker,
  dùng profile/home riêng; không nhập toàn bộ Codex memory, settings hoặc keys.
  Skills chỉ được đưa về repo sau review theo policy hiện có.
- Chưa cài/chạy Hermes, chưa đo latency, chi phí, tỷ lệ hoàn thành hay chất lượng
  so với Codex/native Paperclip workers. Không dùng quảng cáo tiết kiệm context
  hoặc số GitHub stars làm acceptance.

Nguồn: [repository](https://github.com/NousResearch/hermes-agent),
[memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory),
[MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp),
[ACP](https://hermes-agent.nousresearch.com/docs/user-guide/features/acp).
HEAD quan sát: `557254faa24ef5d86f67595c4c64dc61644d0f68`.

### Hermes trong project hay nối thẳng Codex?

| Đường nối | Thực chất | Quyết định hiện tại |
|---|---|---|
| Paperclip → Hermes worker | Agent riêng, profile/home/workspace riêng; trả artifacts theo contract, Paperclip giữ dispatch/retry/cancel | Chỗ phù hợp để thử khi có một job riêng chứng minh lợi ích; chưa triển khai |
| Codex → Hermes MCP | Gọi conversation bridge và một allowlist tools, không phải chạy toàn bộ Hermes agent trong Codex | Chỉ thêm khi cần capability mà tools hiện có chưa đáp ứng |
| Hermes → Codex app-server | Hermes làm giao diện/session wrapper, Codex thực thi turn | Upstream mô tả optional/beta; thay ownership runtime, chưa áp dụng |

Phát hiện bổ sung: plugin chính thức **mcp-serve 1.0.0**, MIT,
Hermes >=0.22.0, catalog pin `6389dd08c1e485db708688c69e42c2b7a7360f4e`.
Lệnh hiện hành `hermes mcp-serve` thay `hermes mcp serve` đã tách khỏi core.
Mặc định expose list/read/events/send/approval bridge của profile. `--tools`
mới thêm web/browser/vision/image/skills/TTS, tùy provider được cấu hình.
Không expose terminal/files/process/kanban/delegation. Đọc hội thoại và gửi
tin dùng quyền của profile; cài MCP không tự cấp quyền gửi tin cho agent.

Đường MCP công khai này không tự chuyển memory/self-improvement của Hermes
sang Codex. Đường app-server là chiều ngược lại, có thể ghi managed global Codex
config và migrate plugins/MCP; không phải cài thêm một skill trong chat hiện tại.
Chưa cài Hermes, chưa thêm MCP/config hay benchmark worker. Khuyến nghị project
scope trước là quyết định kiến trúc, chưa là kết quả đo Hermes tốt hơn Codex.

Nguồn: [plugin MCP server](https://hermes-agent.nousresearch.com/docs/plugins/mcp-serve),
[catalog pin](https://github.com/NousResearch/hermes-official-plugins/tree/6389dd08c1e485db708688c69e42c2b7a7360f4e/mcp-serve),
[Codex app-server runtime](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/codex-app-server-runtime.md).
Phía Codex hỗ trợ STDIO và project-scoped MCP config theo
[OpenAI MCP docs](https://learn.chatgpt.com/docs/extend/mcp); có đường cấu hình
không đồng nghĩa plugin đã được nối hoặc chạy thành công trong phiên này.

### OpenClaw — MIT

- Gateway kết nối các kênh chat với sessions/agent tools. Có đường native Codex
  app-server để điều khiển phiên Codex; ACP dùng cho external harness phù hợp.
- Có MCP server chính thức: `openclaw mcp serve`. Nó nối tới Gateway và expose
  conversation/message/history/events cùng một số thao tác approval. Đây là
  khả năng phù hợp để Codex làm việc với kênh chat đã cấu hình.
- Generic MCP client dùng polling tools; thông báo push riêng của Claude không
  tự chứng minh hoạt động với Codex. Phải smoke-test client/runtime thật.
- Sandbox thực thi cần bật/cấu hình; tài liệu ghi mặc định tắt. Gateway vẫn chạy
  trên host. Khi thử phải giới hạn tools, filesystem mounts và người gửi; không
  tự nối broker, thêm quyền duyệt hoặc bật outbound messaging.
- Chưa cài/chạy OpenClaw, chưa nối tài khoản chat hay thêm MCP vào Codex. Có hỗ
  trợ giao thức không có nghĩa nó đã được tích hợp vào workspace.

Nguồn: [repository](https://github.com/openclaw/openclaw),
[MCP server](https://docs.openclaw.ai/cli/mcp/serve),
[ACP và native Codex](https://docs.openclaw.ai/tools/acp-agents),
[sandbox](https://docs.openclaw.ai/gateway/sandboxing).
HEAD quan sát: `7cce68feca197b3f3d2e98528031f7cfe9fd38f9`.

Tài liệu so sánh Hermes trên website OpenClaw là quan điểm upstream OpenClaw,
tham chiếu snapshot cũ; không dùng nó làm kết luận độc lập về độ an toàn hoặc
chất lượng hiện tại của Hermes.

## Điều kiện thử sau này

| Nhu cầu xuất hiện | Lát thử nhỏ | Chỉ giữ khi |
|---|---|---|
| Cần một worker nghiên cứu/coding có skills qua nhiều phiên | Hermes với home/profile và workspace riêng, cùng một model và bộ task với incumbent | Output đúng, kiểm chứng độc lập đạt; đo cả thời gian/chi phí, lỗi và khả năng resume |
| Muốn giao việc/xem kết quả từ Telegram hoặc kênh chat khác | OpenClaw với một kênh và allowlist owner; ưu tiên đọc trạng thái trước | Đúng người, đúng task/state; reconnect/cancel không gửi lặp hoặc mở quyền ngoài dự kiến |
| Muốn coding agent tìm source/docs tốt hơn | Dùng `rg`, Xerj, CodeGraph, Context7 đã có | Không thêm gateway/agent loop cho khả năng đã đáp ứng |

Nếu adopt, scope ở `projects/integrations/` và runtime riêng, pin source/license
theo `upstream-integrations`. Paperclip tiếp tục giữ một owner cho dispatch,
retry và cancellation; worker/gateway không tự chạy lịch trùng nhau. Global chỉ
xét khi đã chứng minh lợi ích qua nhiều project độc lập.
