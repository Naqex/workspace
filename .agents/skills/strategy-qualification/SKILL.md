---
name: strategy-qualification
description: Review Naqex strategy evidence for correctness, out-of-sample robustness, prop fit and a justified next stage. Use after research/backtest/shadow/demo; not strategy discovery, status checks or automatic trading approval.
---

# Kiểm định và quyết định bước tiếp

Đánh giá đúng scope; có thể loại hoặc chưa đủ bằng chứng, không mặc định phải
tìm winner. Đọc [risk/prop](references/risk-and-prop.md) khi đánh giá quỹ.

## Đọc bằng chứng

1. Bind candidate/code/data/cost/rule versions, cutoff/split, task/run/attempt
   và protocol. Dossier tự đủ hoặc link artifact truy cập được; thiếu thì ghi
   gap. Có repo đọc `tooling/ai-engines/STRATEGY-WORKFLOW.md` và dùng
   `strategy_evidence.py inspect`. Tool chỉ kiểm artifact invariants/binding.
2. Correctness trước profitability: causal timing, quality, fills/costs,
   accounting, risk/position/pending/end-of-sample. Lỗi material chưa giải
   quyết thì không promote. Source mới khác pin không xóa kết quả lịch sử;
   nó làm kết quả cũ chưa chứng minh source mới.
3. Xem net return cùng drawdown, tail losses, losing streak, recovery, trade
   count, exposure/turnover và contribution của ít trade. Unrealized equity
   không là tiền rút. Không lấy một ngưỡng Sharpe/số trade làm chứng nhận.

## Độ bền và khả năng áp dụng

- Kiểm OOS/holdout thực sự chưa dùng, trial count, sensitivity, cost/data/
  delay/gap stress. Walk-forward/MonteCarlo/DSR/PBO chỉ khi assumptions/số liệu
  phù hợp; không ép mẫu nhỏ pass hoặc thêm metric chưa có consumer.
- Tách overlap windows, cùng tín hiệu cost scenarios và biến thể cùng họ;
  tỷ lệ pass mô phỏng không là xác suất đã hiệu chỉnh.
- Theo quỹ/program/phase riêng: reset clock/DST, daily/overall equity headroom,
  first breach, days-to-target, survival/payout/fees. Thiếu intrabar hoặc rule
  engine chưa hỗ trợ thì unknown; không gắn tên hãng khác vào kết quả có sẵn.
- Manual/semi-auto: decision timestamp/reason trước outcome, missed trades/
  latency và replay lại portfolio state. Dừng sự cố/risk khác veto tín hiệu.
- Concurrent research khác concurrent execution. Kiểm account-wide budget,
  positions/pending/unknown và lock tại execution owner; không nhân budget
  bằng cách tạo nhiều phiên/grant cho một account.

## Kết luận và bàn giao

Tách correctness, edge, prop fit, operations và authority, mỗi trục có scope/
bằng chứng/unknown. Một trục đạt không làm trục khác đạt.

- `reject`: lỗi/vi phạm được xác minh hoặc không đạt tiêu chí đăng ký.
- `inconclusive`: thiếu mẫu/nguồn/coverage/OOS; chỉ bước nhỏ giải quyết bất định.
- `eligible_for_next_stage_review`: đủ cho đúng bước đề xuất, chưa là permission,
  auto promotion hoặc bảo đảm lợi nhuận.

Paperclip own task/report/decision; artifacts giữ numbers/provenance; promotion
reducer/grant hiện có giữ quyền thực thi. Reuse quyền đã có nhưng kiểm còn hiệu
lực đúng account/scope; không tự cấp mới hoặc sửa ledger để tự pass. Báo cáo
không là lệnh gửi broker.
