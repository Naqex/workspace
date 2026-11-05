---
name: evidence-continuity
description: Reuse and update research, diagnostic, decision and validation evidence across Naqex sessions and agent handoffs. Use for research, substantive findings or resuming related work; not trivial Q&A, translation or copy-only edits.
---

# Kế thừa và cập nhật bằng chứng

Giữ kết quả hữu ích ngoài chat để lượt sau tiếp tục từ bằng chứng đã có.
Quy trình và nơi lưu theo [vòng đời context](../../../planning/CONTEXT-LIFECYCLE.md#kế-thừa-research-chẩn-đoán-và-kiểm-chứng).
Skill này quản lý việc lưu/kế thừa; không thay phương pháp research, debugging,
kiểm thử hoặc quyền thực thi của task.

## Trước khi làm

1. Tìm đúng owner từ yêu cầu, [current context](../../../planning/CURRENT-CONTEXT.md)
   và PLAN/task liên quan. Research bắt đầu ở [chỉ mục](../../../planning/research/README.md),
   rồi `rg` câu hỏi, lỗi, contract hoặc tên công cụ trong nguồn được dẫn.
   Không đọc toàn archive hoặc mở lại toàn bộ nguồn web để bắt đầu.
2. Đối chiếu kết luận cũ với câu hỏi hiện tại: scope, ngày kiểm, phiên bản,
   input/code/runtime và giới hạn bằng chứng. Phân biệt nguồn chính thức,
   tự thuật cộng đồng, suy luận và kết quả thực thi. Không biến khuyến nghị
   của agent thành quyết định của owner, hoặc tài liệu thành runtime acceptance.
3. Reuse phần còn đúng; chỉ research/test lại phần đổi, còn thiếu hoặc mâu thuẫn.
   Thông tin dễ đổi hoặc high-stakes phải kiểm nguồn hiện hành trước khi dùng
   để hành động. Nguồn không truy cập được thì ghi chưa xác minh, giữ bằng chứng
   lịch sử đúng ngày; không tự nâng ngày kiểm lên hôm nay.

## Trước khi kết thúc hoặc bàn giao

4. Cập nhật artifact do owner hiện có quản lý: câu hỏi, kết luận và trạng thái
   quyết định, nguồn/bằng chứng, scope/version/ngày kiểm, giới hạn và phần cần
   kiểm lại. Giữ kết quả âm, giả thuyết bị bác và lỗi chưa giải quyết. Với test
   ghi command, baseline, kết quả và locator; không chép raw log/secret vào context.
5. Ghi delta và lý do đổi; đánh dấu kết luận cũ bị thay thế bằng link tới phần
   mới. Sửa cả nguồn đang dẫn agent tới kết luận thiếu/sai; không chỉ thêm một
   tài liệu mới mà để hướng dẫn hiện hành mâu thuẫn. Giữ protocol/attempt đã
   freeze và receipt lịch sử nguyên vẹn khi cập nhật interpretation.
6. Thêm link ở chỉ mục/context nếu là chủ đề mới hoặc đổi cách resume; không
   append một recap vào mọi file mỗi lượt. Bàn giao bằng link/section/revision,
   việc chưa biết và bước tiếp. Kiểm local links và đọc thử từ entrypoint.

Nếu chỉ xác nhận lại mà không có delta, cập nhật ngày kiểm tại nguồn phù hợp
kèm nguồn thực sự đã kiểm; không tạo báo cáo mới. Nêu trong trả lời nơi đã lưu.
Paperclip, process worker và Hermes có loader khác nhau: cung cấp evidence
packet bằng đường được consumer hỗ trợ; file/skill trong repo không chứng minh
catalog đã cài, agent đã đọc hoặc worker đang chạy đã nhận instruction mới.
