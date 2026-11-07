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
| Hạn thi prop, minimum days, inactivity, giữ lệnh, payout và thời gian đạt vốn | [Time-fit, kiểm05/11](PROP-FIRM-FIT-20261102.md#thời-gian-challenge-và-độ-phù-hợp-chiến-lược--kiểm-lại-05112026); lifecycle offline đã có, firm-specific/payout/live gaps còn mở |
| Time-fit 3/6/12 tháng, dates/source/input/cost binding | [Execution 2023](TIME-FIT-EXECUTION-20261106.md), [registered JSON](TIME-FIT-HISTORICAL-20261106.json); [thiết kế](TIME-FIT-REGISTRATION-20261106.md); trạng thái ở receipt AI |
| Annual2023 hoàn tất, giữ/loại5version, proof và việc sau batch | [Kết quả/hậu kiểm06/11](TIME-FIT-RESULTS-20261106.md); source `bbc7c60e`,5/5verified; hai survivors chưa edge/prop-qualified |
| Hai survivors: tick DD, native prop lifecycle, exit oracle và annual dispatch | [Protocol06/11](PROP-PATH-SURVIVORS-20261106.md), [frozen binding](PROP-PATH-SURVIVORS-20261106.json); receipt AI giữ run state, không mở holdout/broker |
| Hai ứng viên tốt ở đâu/yếu ở đâu; quý, phí, sizing và chọn phép kiểm tiếp | [Review survivors06/11](SURVIVOR-REVIEW-20261106.md); cả hai inconclusive; review-only, chọn period robustness trước risk/TP |
| Bước tiếp sau review: hai rules không đổi trên Q2–Q3/2022 | [Period protocol06/11](PERIOD-ROBUSTNESS-20261106.md), [frozen registration](PERIOD-ROBUSTNESS-20261106.json); actual state/hashes/preflight/dispatch ở receipt AI; không clean OOS |
| Period batch đã xong chưa, giữ ứng viên nào, công việc tiếp theo | [Kết quả/hậu kiểm period06/11](PERIOD-RESULTS-20261106.md);2/2jobs/8rows verified, Z-score tạm gác, UTC range inconclusive; offline stream handoff ở receipt, chưa broker/OOS |
| Mở rộng danh mục, ba rules mới, screen nhanh không giả portfolio PnL | [Discovery round3,07/11](DISCOVERY-ROUND3-20261107.md);8implemented/2directions deferred; feasibility probes rồi tick review, actual status ở receipt |
| Kiểm tiếp UTC nguyên bản trên2024, giữ2025+đóng | [Protocol UTC07/11](UTC-VALIDATION-20261107.md); historical validation/prior exposure unverified, chưa clean OOS hoặc authority broker; receipt giữ freeze/dispatch/outcomes |
| Snapshot terms FTMO/The5ers cho time-fit | [PROP-TERMS-SNAPSHOT-20261106](PROP-TERMS-SNAPSHOT-20261106.md); FTMO sơ bộ đủ, The5ers còn account/program pin |
| Forex/prop simulation, QDM và chi phí | [Forex pilot](FOREX-PROP-PILOT-20261102.md); [QDM CLI](../../projects/trader/docs/quantdatamanager.md) |
| Luồng nghiên cứu, review và promotion | [AI research workflow](AI-RESEARCH-WORKFLOW-20261101.md); [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope hiện hành |
| Kiến trúc tự chủ dài hạn | [Autonomous trading brief](AUTONOMOUS-TRADING-SYSTEM-BRIEF.md); kiểm ngày/quyết định owner trước dùng |
| Studio/Paperclip native UI và ownership | [Studio operations research](STUDIO-OPERATIONS-20261102.md); [operating guide](../../tooling/ai-engines/OPERATIONS.md) giữ quy trình |
| Long-running demo, recovery, replay và vận hành | [Demo foundations, 04/11](DEMO-LONG-RUN-FOUNDATIONS-20261104.md); run state/receipt mới nhất do AI plan dẫn |
| Codex `blocked by policy` | [Chẩn đoán 05/11](CODEX-POLICY-BLOCK-20261105.md); phân biệt config trên đĩa và policy hiệu lực |

Chưa thấy chủ đề thì dùng `rg` trong thư mục/project liên quan; chỉ mục chưa
liệt kê toàn bộ research. Cập nhật bản chủ đề đang có trước khi thêm file mới.
Quy trình lưu/kế thừa ở [context lifecycle](../CONTEXT-LIFECYCLE.md#kế-thừa-research-chẩn-đoán-và-kiểm-chứng).
