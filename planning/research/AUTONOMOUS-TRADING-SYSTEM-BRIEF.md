# Hệ thống giao dịch tự chủ — brief hiện hành

Cập nhật: **31/10/2026 (Asia/Saigon)**.
**WORK: DRAFT · REVIEW: DOCUMENTATION-ONLY · DOC: FULL.**
Owner đã giao nghiên cứu kiến trúc/workflow và lưu context. Chưa giao triển khai
hệ thống mới. Brief này giữ mục tiêu, lựa chọn và câu hỏi đang bàn; không là
execution plan, acceptance ledger hoặc hợp đồng cấp quyền giao dịch.

## 1. Mục tiêu và bối cảnh do owner xác nhận

- Mục tiêu dài hạn: tìm kiếm lợi nhuận trên thị trường bằng hệ thống, dùng AI
  để tự động hóa cả nghiên cứu và vận hành giao dịch.
- Trader hiện tại đi theo luồng giao dịch tay tham khảo FXReplay, kết hợp AI chat;
  owner muốn nghiên cứu cách tiến tới hệ thống tự chủ hoàn chỉnh.
- Owner tự đánh giá cảm quan Trader đã hoàn thành khoảng **80% trên nền FXReplay**.
  Đây không phải kết quả audit, phần trăm acceptance toàn sản phẩm hoặc bằng chứng
  sẵn sàng live; các gate hiện hành tiếp tục ở Product Plan/ledger của chúng.
- Ưu tiên nền dài hạn, có thể duy trì và mở rộng. Các lát thực hiện sau này phải
  đóng góp cho kiến trúc đích; tránh làm bản ngắn hạn chỉ để có tính năng.
- Thị trường đầu tiên **chưa chốt**: so sánh Forex/vàng qua MT5 và crypto.
- Nhịp giao dịch **chưa chốt**: owner muốn đề xuất theo tính khả thi. D1/H4 mới
  là khuyến nghị của assistant, chưa là lựa chọn được owner chốt.
- Paperclip, TradingAgents và repo ngoài là đối tượng research/reference/reuse;
  owner chưa yêu cầu cài đặt, tích hợp hoặc chọn một engine cụ thể.

## 2. Lựa chọn A/B — ý muốn dài hạn đã chốt

Ở đây A/B chỉ nói về **đưa phiên bản chiến lược mới vào chạy bằng tiền thật**,
không nói về duyệt từng lệnh hoặc quyền tự nâng tổng ngân sách.

| Chế độ | Ai quyết định đưa chiến lược mới vào chạy? |
|---|---|
| **A — Chờ duyệt** | Hệ thống nghiên cứu và trình bằng chứng; owner quyết định |
| **B — Tự quyết có giới hạn** | Hệ thống tự quyết khi đạt tiêu chí và nằm trong phạm vi owner đã cấp |

**Owner thích B làm đích dài hạn và muốn có thể chuyển sang A khi cần.**
Khả năng chuyển chế độ là yêu cầu thiết kế; chi tiết contract chưa được chốt.
Lựa chọn B trong brief không tự cấp quyền broker/live, vốn, tài khoản hoặc deploy.

Đề xuất để tiếp tục thảo luận, chưa là hành vi đã triển khai:

- Dùng chung pipeline nghiên cứu/kiểm chứng; chính sách duyệt quyết định bước
  phát hành chiến lược. Giữ phiên bản chính sách và lịch sử quyết định.
- B → A: các quyết định phát hành mới chờ duyệt. Chuyển chế độ không tự đóng
  vị thế, hủy lệnh đã gửi hoặc dừng chiến lược đang chạy; quyền vận hành hiện có
  và kiểm soát rủi ro tiếp tục áp dụng. Dừng khẩn cấp là thao tác riêng.
- A → B: chỉ tự quyết trong phạm vi đã cấp; phải kiểm lại bằng chứng, dữ liệu
  và hạn mức hiện hành, không tự chạy hàng loạt đề xuất đang chờ.
- Tranh chấp chuyển chế độ/dispatch và xử lý yêu cầu đang thực thi cần được
  đặc tả trước implementation. Không suy rằng thay một công tắc UI là đủ.

### Khởi đầu nghiên cứu và điều kiện dùng tiền — owner đã đồng ý

Phân biệt **phạm vi nghiên cứu** với **quyền phát hành chiến lược dùng tiền thật**;
không dùng cùng nhãn A/B cho hai chiều này trong các phần giải thích tiếp theo.

- AI được tìm cả ý tưởng mới ngoài các trường phái owner đã biết ngay từ đầu;
  owner vẫn có thể giao đề tài cụ thể. Mỗi đợt nghiên cứu giới hạn phạm vi và
  ngân sách, rồi mở rộng theo bằng chứng; chưa chốt con số hoặc thị trường.
- Khởi đầu: có dữ liệu đáng tin → mốc so sánh đơn giản → AI tìm cách cải thiện.
  Mốc so sánh là công cụ đánh giá, không mặc định là chiến lược để dùng tiền thật.
- Giai đoạn đầu chỉ **mô phỏng và tài khoản demo của broker**. Mô phỏng tính kết
  quả trong môi trường kiểm soát; demo giúp quan sát luồng dữ liệu/lệnh qua broker.
  Kết quả mô phỏng, demo và tiền thật phải ghi riêng, không coi chất lượng khớp
  lệnh demo là bằng chứng tương đương live.
- Owner chỉ muốn dùng tiền thật khi đã có chiến lược tốt. Tiêu chí cụ thể cho
  chữ "tốt" còn cần thống nhất; kết quả backtest đẹp riêng lẻ chưa đủ để kết luận.
- Bước tiền thật ban đầu chờ owner duyệt sau khi có bằng chứng. Đích dài hạn vẫn
  là tự quyết trong phạm vi được cấp và chuyển được về chờ duyệt khi cần.
- Đây là quyết định về lộ trình/thiết kế. Chưa chạy mô phỏng/demo, kết nối tài
  khoản, đặt lệnh hoặc cấp quyền live trong cuộc trao đổi này; các thao tác đó
  cần scope và quyền thực thi tương ứng khi triển khai.

## 3. Khung kiến trúc để nghiên cứu tiếp

Giả thuyết → kiểm chứng → phiên bản được phép chạy → vận hành → giám sát → cải tiến.

- Vòng nghiên cứu: AI đề xuất, viết code/tạo mô hình trong môi trường cô lập,
  chạy thí nghiệm và học từ cả kết quả đạt lẫn thất bại.
- Vòng vận hành: chạy chiến lược được phép, kiểm soát danh mục/rủi ro,
  thực thi và đối soát trạng thái broker/exchange.
- Trader là ứng viên giao diện điều hành; Quant Lab và TradingAgents có tài sản
  để reuse. Đây là hướng nghiên cứu, chưa chốt module/engine hoặc bằng chứng tích hợp.
- AI, ML và bot có thể cùng tham gia. Số agents hoặc độ phức tạp không chứng minh
  lợi thế giao dịch; cần so baseline, chi phí và kết quả ngoài mẫu/forward.

## 4. Reuse tài liệu hiện có

| Tài liệu | Vai trò và cách dùng |
|---|---|
| [Nền AI chung, 23/10](AI-WORKSPACE-ARCHITECTURE-2026-10-23.md) | Kiến trúc AI runs, worker, provider/admission và ownership. Giữ làm baseline hạ tầng; không coi lựa chọn LangGraph là đã chốt trading engine |
| [Money engine, 27/09](../checkpoints/workspace-next-stage/MONEY-ENGINE-ARCHITECTURE-2026-09-27.md) | Tham khảo risk, reconciliation và promotion; đây là packet lịch sử PREP_ONLY, gồm cả nhánh doanh thu sản phẩm ngoài scope lần này |
| [Autonomy feasibility, 28/09](AUTONOMY-2-YEAR-FEASIBILITY-2026-09-28.md) | Tham khảo recovery/vận hành vắng chủ; các giả định thời gian và hoàn cảnh cũ không tự áp cho brief dài hạn hiện tại |
| [Product Plan Trader](../trader/PRODUCT-COMPLETION-PLAN.md) và [current scope](../trader/CURRENT-SCOPE-20261029.md) | Tiếp tục giữ phạm vi và acceptance Trader; brief này không sửa trạng thái các gate |

Các giới hạn iteration đầu trong research 23/10 tiếp tục được đọc trong scope
hạ tầng AI khi đó; không dùng chúng để loại trước hướng nghiên cứu AI tự viết
chiến lược hoặc kiến trúc dài hạn đang được bàn. Thay đổi implementation vẫn cần
plan/contract và quyền tương ứng. Không khởi động lại plan/worker cũ từ brief này.

## 5. Nguồn ngoài đã khảo sát trong cuộc trao đổi 31/10

Đây là bản đồ reference từ README/docs/paper; chưa chạy engine hoặc benchmark
các ứng viên với cùng workload. Chưa có căn cứ xếp hạng lợi nhuận hay chốt stack.

| Nguồn | Phần đáng nghiên cứu/reuse |
|---|---|
| [RD-Agent](https://github.com/microsoft/RD-Agent), [Qlib](https://github.com/microsoft/qlib) | AI nghiên cứu factor/model, vòng lặp thí nghiệm định lượng |
| [Freqtrade/FreqAI](https://www.freqtrade.io/en/stable/freqai/) | Luồng crypto có ML, backtest/dry/live và tái huấn luyện |
| [NautilusTrader architecture](https://nautilustrader.io/docs/latest/concepts/architecture/), [LEAN](https://github.com/QuantConnect/Lean) | Trading engine, ranh giới data/risk/execution và vận hành theo sự kiện |
| [FinRL-X](https://github.com/AI4Finance-Foundation/FinRL-Trading) | Contract tỷ trọng danh mục nối chiến lược với thực thi |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents), [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Workflow phân tích tài chính bằng agents |
| [Paperclip](https://github.com/paperclipai/paperclip) | Quản lý mục tiêu, công việc và đội agents; cần phân biệt với trading engine |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Temporal activities](https://docs.temporal.io/activity-definition#idempotency) | Workflow có trạng thái/phục hồi; retry không tự bảo đảm broker effect chỉ xảy ra một lần |
| [Nghiên cứu LLM look-ahead bias](https://aclanthology.org/2026.emnlp-main.510/) | Kiểm soát việc mô hình có thể biết kết quả lịch sử từ pretraining |

Refresh đúng version, license, capability và platform trước khi chọn engine;
không đọc danh sách này như quyền cài/chạy toàn bộ.

## 6. Điểm tiếp tục cuộc trao đổi

Owner muốn giải thích **từng phần nối tiếp như giảng bài**, ngắn, có ví dụ;
không liệt kê toàn bộ framework/kiến trúc trong một lượt. Có thể hỏi một câu
khảo sát khi câu trả lời ảnh hưởng thiết kế. Đây là preference cho cuộc trao đổi
kiến trúc, không tự cập nhật tiến độ khóa học trong education/.

Đã trao đổi phần 1: B dài hạn, chuyển được về A. Phần 2 đã chốt AI được tìm ý
tưởng rộng từ đầu, triển khai nghiên cứu theo phạm vi nhỏ; có data và baseline
trước khi đánh giá cải thiện. Owner xác nhận giai đoạn đầu chỉ mô phỏng/demo,
có chiến lược tốt mới xét tiền thật. Tiếp phần 3: giải thích ngắn cách nhận biết
chiến lược "tốt" bằng kiểm chứng, sau đó hỏi từng tiêu chí khi cần. Không hỏi lại
mục tiêu, thị trường, nhịp giao dịch hoặc lựa chọn đã trả lời như thể chưa biết.

Các điểm còn mở, hỏi lần lượt khi tới phần liên quan: tiêu chí đạt của chiến lược,
phạm vi quyền tự quyết, ngân sách/vốn/rủi ro, thời gian owner có thể giám sát,
thị trường/nhịp giao dịch cuối cùng và cách xử lý sự cố. Chưa đặt con số thay owner.
