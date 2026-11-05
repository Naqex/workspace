# Tra cứu research đã có

Đọc tài liệu chủ đề trước, chỉ kiểm lại phần đổi/còn thiếu. Đây là chỉ mục chọn
lọc, không là danh sách task hoặc chứng nhận tài liệu còn đúng tới hiện tại.
Mỗi tài liệu giữ ngày kiểm, nguồn, giới hạn và điều kiện refresh của chính nó.
Các mục cũ chưa được re-audit khi tạo chỉ mục ngày 05/11/2026.

| Câu hỏi / từ khóa | Nguồn hiện có |
|---|---|
| Đã dùng dữ liệu nào; không nhớ đã xem2023; khóa/đánh giá bài kiểm Q1/2023 | [Audit và protocol Q1/2023,05/11](PROP-HISTORICAL-ROBUSTNESS-20261105.md); [registration pins](PROP-HISTORICAL-ROBUSTNESS-20261105.json); đã thực thi, numbers/recovery thuộc [receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md) |
| Làm sao biết test chiến lược đúng; version/reuse, quant workflow, overfit, OOS và validation gates | [Framework audit05/11](STRATEGY-VALIDATION-FRAMEWORK-20261105.md); [agent gates](../../.agents/skills/strategy-qualification/references/validation-gates.md) |
| Hậu kiểm chất lượng/kỹ thuật/performance; học từ run; Hermes learning loop | [Engineering review Q1,05/11](ENGINEERING-REVIEW-Q1-20261105.md); [skill hậu kiểm](../../.agents/skills/engineering-retrospective/SKILL.md) |
| Log/status/debug/recovery; có cần OpenTelemetry/collector? | [Observability guide](../../tooling/ai-engines/OBSERVABILITY.md), source check05/11; dùng native/stdlib hiện có trước backend mới |
| Workflow strategy, qualification, preflight/report và skill management | [Workflow công cụ/skills](../../tooling/ai-engines/STRATEGY-WORKFLOW.md); [quản lý skills](../../docs/development/SKILL-MAINTENANCE.md) |
| MCP/tools FTMO, The5ers, TradingView; open-source MT5/Pine; quyền/account | [Khảo sát công cụ cho agent, 05/11](PROP-AGENT-TOOLS-20261105.md) |
| Triển khai pullback-trend, UTC range breakout; hướng auto có giám sát | [Protocol round2, 05/11](PROP-STRATEGY-ROUND2-20261105.md); không thay round1 đã freeze |
| Trade tay, bán tự động, auto; kinh nghiệm cộng đồng; EA prop; FTMO/The5ers; AQR/GSAM | [Bằng chứng chiến lược và mức tự động hóa, 05/11](PROP-AUTOMATION-AND-STRATEGY-EVIDENCE-20261105.md) |
| Chọn ứng viên, protocol, consumed data, OOS, holdout và cost stress | [Đợt chiến lược prop đầu tiên](PROP-STRATEGY-ROUND1-20261105.md); kết quả run thuộc receipt được protocol dẫn tới |
| Chọn quỹ/chương trình theo vốn và rủi ro | [Prop firm fit, 02/11](PROP-FIRM-FIT-20261102.md); refresh giá/luật trước quyết định mua |
| Forex/prop simulation, QDM và chi phí | [Forex pilot](FOREX-PROP-PILOT-20261102.md); [QDM CLI](../../projects/trader/docs/quantdatamanager.md) |
| Luồng nghiên cứu, review và promotion | [AI research workflow](AI-RESEARCH-WORKFLOW-20261101.md); [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope hiện hành |
| Kiến trúc tự chủ dài hạn | [Autonomous trading brief](AUTONOMOUS-TRADING-SYSTEM-BRIEF.md); kiểm ngày/quyết định owner trước dùng |
| Studio/Paperclip native UI và ownership | [Studio operations research](STUDIO-OPERATIONS-20261102.md); [operating guide](../../tooling/ai-engines/OPERATIONS.md) giữ quy trình |
| Long-running demo, recovery, replay và vận hành | [Demo foundations, 04/11](DEMO-LONG-RUN-FOUNDATIONS-20261104.md); run state/receipt mới nhất do AI plan dẫn |
| Codex `blocked by policy` | [Chẩn đoán 05/11](CODEX-POLICY-BLOCK-20261105.md); phân biệt config trên đĩa và policy hiệu lực |

Chưa thấy chủ đề thì dùng `rg` trong thư mục/project liên quan; chỉ mục chưa
liệt kê toàn bộ research. Cập nhật bản chủ đề đang có trước khi thêm file mới.
Quy trình lưu/kế thừa ở [context lifecycle](../CONTEXT-LIFECYCLE.md#kế-thừa-research-chẩn-đoán-và-kiểm-chứng).
