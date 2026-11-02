# Studio: vận hành cho một owner

Ngày khảo sát: 02/11/2026. Đây là quyết định thiết kế; kết quả triển khai và
bằng chứng thuộc [receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Scope vẫn theo [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md): hoàn
thiện hệ thống, chưa tối ưu chiến lược hoặc mở broker execution.

## Kết luận

Giữ Paperclip làm nơi giao việc, xem run và báo cáo; wrapper xác định luồng,
engine xử lý từng bước. Luồng numeric → một lượt Hermes → owner xem phù hợp
với giai đoạn hiện tại. Không thêm agent điều phối, scheduler, framework hay
vòng tự sửa. Hai workflow đang có là fixture hệ thống, chưa là nghiên cứu tự do.

| Phần | Quyết định | Lý do |
|---|---|---|
| Native UI/API/process adapter | Giữ | Tránh tạo bảng task/run và cơ chế hủy thứ hai |
| Contract nhỏ, dữ liệu/hash và báo cáo có provenance | Giữ | Phân biệt engine chạy xong với kết quả đáng tin |
| Một lượt review, owner nhận hồ sơ | Giữ | Có điểm dừng, tránh review qua lại vô hạn |
| Thất bại chỉ hiện ở bước con | Sửa | Parent cần trạng thái lỗi và đường dẫn tới bước cần xử lý |
| Tạo/hủy cả graph | Đã nối control nhỏ trong Trader | Xem mẫu, tạo draft, xác nhận start/cancel; native tasks vẫn thuộc Paperclip |
| Bật lịch tự chạy hoặc thêm CEO agent | Chưa làm | Chưa giải quyết khoảng trống vận hành, có thể tăng lượt model |
| Budget/token accounting | Cần hoàn thiện trước unattended | Process adapter không tự biết token và giá của SDK/gateway |
| Tự retry/model lại để sửa publication | Không dùng | Có thể tính phí hai lần, mất phân biệt inference với delivery |

## Đối chiếu primary source và source đang pin

1. [Process adapter](https://github.com/paperclipai/paperclip/blob/master/docs/adapters/process.md)
   dành cho script/custom runtime chạy một lần; không cung cấp conversational
   session persistence. Khớp cách native process gọi wrapper và engine hiện tại.
2. [Task workflow](https://github.com/paperclipai/paperclip/blob/master/docs/guides/agent-developer/task-workflow.md)
   dùng task/checkout/status/handoff có owner. Không coi agent tự nói xong là
   bằng chứng: wrapper vẫn cần kiểm report và numerical evidence trước bàn giao.
3. [Routines API](https://github.com/paperclipai/paperclip/blob/master/docs/api/routines.md)
   có manual/API trigger, idempotency và coalesce/skip khi đang chạy. Nó tạo
   một execution issue cho một agent, không thay nguyên graph numeric/review/paper
   của project. Native instance hiện không có routine nào.
4. Source pin đang chạy có `experimental.enableCases`; reusable workflows là
   name/prompt, không phải graph interpreter. `doc/plans/2026-10-21-reusable-case-workflows.md`
   ghi graph validation, role binding và workflow authoring UI còn deferred.
   Không bật feature flag/migration chỉ để có thêm một chỗ lưu prompt.
5. [Costs and budgets](https://github.com/paperclipai/paperclip/blob/master/docs/guides/board-operator/costs-and-budgets.md)
   mô tả enforcement trên chi phí được báo về. Worker SDK hiện chưa có đầy đủ
   token/pricing telemetry; số tiền bằng 0 hoặc unknown không chứng minh miễn phí.
   Deadline/concurrency không thay spending cap. Chưa đổi budget của owner.

Tài liệu remote có thể mới hơn pin; quyết định implementation được đối chiếu với
source local. Đặc biệt `server/src/routes/issues.ts` yêu cầu một lý do gỡ chặn
cho blocked transition. Agent chỉ được tự đứng tên `unblockDescriptor.owner`;
không được tự chọn board/user. Wrapper tuân thủ rule này, không nới quyền engine.
Người nhận hồ sơ vẫn có thể là human creator; worker chịu trách nhiệm sửa lỗi.

## Đối chiếu cộng đồng

- [Endless review loops](https://www.reddit.com/r/PaperClip_AI/comments/1ws7f1s/real_q_how_do_you_prevent_agents_from_getting/):
  người dùng phản ánh review qua lại và task bị kẹt; các lời khuyên về watchdog
  hoặc giới hạn loop là trải nghiệm cá nhân, không chứng minh local có cùng lỗi.
  Project giữ một lượt review và không tự mở vòng sửa tiếp.
- [Practical usage](https://www.reddit.com/r/paper_clip_ai/comments/1s7vijw/practical_usage_of_paperclip/):
  nhiều trải nghiệm khác nhau về chia vai trò, handoff và cấu hình. Có cả nội dung
  quảng bá template; không lấy số agent hoặc lời hứa tự vận hành làm chuẩn kiến trúc.

## Luồng vận hành đã chọn

1. Đăng ký câu hỏi, dữ liệu và contract trước khi tạo graph.
2. Xem graph rồi chạy thủ công; không timer tự động.
3. Numeric worker kiểm dữ liệu, chạy và xuất báo cáo; Hermes chỉ nhận nguồn đạt gate.
4. Thành công: summary chờ owner review. Thất bại: summary blocked, có tài liệu
   **Workflow cần bạn xem**, link bước lỗi và mã chẩn đoán; không tự retry.
5. Đọc native run + receipt khi bị ngắt. Native cancellation là trạng thái run;
   receipt còn running sau hard kill không phải success. Không sửa receipt cho đẹp.
6. Nếu kết quả đã có mà delivery lỗi, sửa delivery bằng native API. Chỉ tạo lượt
   engine mới sau khi biết attempt trước đã làm gì. Paper/demo/live có gate riêng.

Không xóa lịch sử lỗi hoặc fork cần thiết. Việc lược bỏ ở đây là gộp nhánh báo
lỗi trùng trong adapter và tránh thêm tầng điều phối chưa có nhu cầu thực tế.

## Bổ sung sau triển khai UI

Control **Quy trình** gọi wrapper allowlist qua local Vite/preview middleware;
không mở shell/proxy chung hoặc sửa Paperclip core. Draft có idempotency token
lưu trước request; mất phản hồi dùng lại token, không tự tạo attempt mới. Start
và cancel tách xác nhận; outcome chưa rõ phải đọc lại native truth trước khi tiếp.

Source pin có thêm rule dedup task theo company/parent/title, không theo project.
Graph vì thế dùng `allowDuplicate:true` cùng idempotency key cho từng task: hai
lần tạo mới độc lập dù cùng tên; retry cùng key vẫn là cùng task. Parent trả về
phải đúng company/project trước khi tạo tiếp children. Đây là sửa wrapper theo
native contract, không sửa cơ chế dedup upstream. Receipt giữ regression thực tế.
