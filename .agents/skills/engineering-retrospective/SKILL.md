---
name: engineering-retrospective
description: Review completed screening or validation batches and costly failures, then verify bounded quality, reliability or performance improvements. Use for post-run engineering learning; not status checks, trivial edits or strategy selection.
---

# Hậu kiểm và cải tiến kỹ thuật

Biến một đợt chạy có ý nghĩa thành bằng chứng, việc sửa cụ thể và cách làm tốt
hơn cho lượt sau. Kích hoạt sau job tốn thời gian, sự cố đáng kể/tái diễn hoặc
owner yêu cầu review tổng thể; không full-audit sau mọi command/commit.
Sau một đợt screening/kiểm nghiệm có kết quả mới, làm lượt hậu kiểm gọn khi
đóng batch; chỉ profile/benchmark phần có dấu hiệu hoặc lợi ích cụ thể. Không
lặp audit cùng artifact không đổi hay buộc phải tìm ra một tối ưu mới mỗi lần.
Với strategy research, đọc [hậu kiểm lượt nghiên cứu](references/research-runs.md)
để phân biệt cải tiến kỹ thuật với đổi mô hình mô phỏng hoặc đổi chiến lược.

## Đọc đúng bằng chứng

- Nhận scope/acceptance từ PLAN và receipt hiện hành; đối soát worker còn chạy
  trước khi sửa source/runtime đang dùng. Kế thừa theo
  [evidence continuity](../evidence-continuity/SKILL.md).
- Đọc source/config/input/version pins, terminal, logs, failures, attempts và
  artifact/result liên quan. Tách correctness, reliability, performance, UX/AX,
  maintainability và delivery; không lấy run pass làm whole-product acceptance.
- Đo thời gian theo phase, throughput, CPU/RAM, retry/rework, cache/reuse và
  phần việc người phải làm khi evidence có sẵn. Ghi unknown khi chưa đo;
  không đồng nhất wall time, CPU time, quota LLM và tiền.

## Chọn cải tiến có ích

1. Lập bảng lát hệ thống → hiện trạng/bằng chứng → vấn đề/giả thuyết → hành động
   nhỏ nhất → ưu tiên và cách xác nhận. Có cả quyết định giữ nguyên/để sau.
2. Lỗi đã thấy dùng [evidence debugging](../evidence-debugging/SKILL.md);
   giữ case hồi quy của transition thực tế. Trước lượt đắt, kiểm nhanh nhánh
   handoff/complete/failure/cancel/reuse bị tác động thay vì lặp full study.
3. Chậm dùng [fullstack performance](../fullstack-performance/SKILL.md):
   phase timing chỉ khoanh vùng, profile mới quy được chi phí cho function.
   Đối chiếu output trước timing; tách cache hit/partial miss/new workload.
   Chỉ claim speedup của workload đã đo. Không bỏ validation/risk để chạy nhanh.
4. Reuse job đã verified khi bindings còn đúng; rerun phần affected. Checkpoint
   chỉ là resume khi đủ state/input/cursor và đã kiểm uninterrupted equivalence.
   Native workflow ownership theo [Studio operations](../studio-operations/SKILL.md).
5. Xếp ưu tiên theo ảnh hưởng correctness, công sức lặp, thời gian tiết kiệm và
   độ phức tạp/bảo trì. Chọn lát kế tiếp hữu hạn; dừng khi đủ acceptance hoặc
   chưa có cải tiến được chứng minh. Không mở vòng agent tự tối ưu vô hạn.

## Lưu bài học ở đúng owner

- Bug/hành vi → code và regression; cách vận hành → runbook; quyết định thiết kế
  → ADR/decision owner hiện có; workflow lặp không hiển nhiên → skill/reference.
  Không chép raw incident logs hoặc cùng một rule vào mọi lớp.
- Dùng [skill maintenance](../../../docs/development/SKILL-MAINTENANCE.md) khi
  tạo/sửa/gộp/retire. So reuse/callers trước; instruction không thay code guard.
- Lưu bảng review, số đo/baseline, quyết định, nguồn, giới hạn và bước tiếp vào
  receipt/artifact owner; index chỉ trỏ tới đó. Ghi rõ manual walkthrough,
  source-confirmed, measured hoặc actual runtime verification.
- Khi chốt một tối ưu hoặc thay cách làm, đối chiếu [nhật ký quyết định](../../../tooling/ai-engines/STRATEGY-WORKFLOW.md#nhật-ký-quyết-định-để-kiểm-lại-việc-tối-ưu-và-chọn-chiến-lược):
  lý do trước đo → baseline/delta → kết quả trước/sau → kiểm parity/giới hạn →
  giữ/bỏ và rollback locator. Giữ cả tối ưu thất bại; source/data semantics
  hoặc phạm vi đổi thì không gọi là speedup cùng độ đúng. Ghi thiếu evidence
  thay vì bịa số đo hoặc bắt chạy lại batch không đổi chỉ để điền bảng.
- Skill thực thi khi agent có lượt làm việc; không là daemon hay quyền tự nâng
  package/model/engine, đổi risk, sửa holdout hoặc cấp broker authority. Repo
  skill không chứng minh native Paperclip/Hermes loader đã nhận hoặc dùng nó.

Khởi đầu thực tế: [review Q1](../../../planning/research/ENGINEERING-REVIEW-Q1-20261105.md).
Risk/edge/prop qualification vẫn thuộc
[strategy qualification](../strategy-qualification/SKILL.md), không thuộc speed review.
