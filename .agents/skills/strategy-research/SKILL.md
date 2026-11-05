---
name: strategy-research
description: Select, specify and implement reproducible Naqex trading hypotheses with prop constraints, causal data and registered experiments. Use for strategy research or experiment design; not status checks, trading lessons or permission to send orders.
---

# Nghiên cứu chiến lược

Chuyển câu hỏi thành thí nghiệm tái hiện được; dùng code/runner đã có.
Kế thừa bằng chứng qua `evidence-continuity` nếu consumer hỗ trợ. Thiếu repo
thì dùng dossier được giao; không bịa command hoặc bắt owner kể lại chat.

## Chọn câu hỏi và ứng viên

- Đọc `planning/CURRENT-CONTEXT.md`, `planning/research/README.md` và PLAN/task
  khi có workspace. Chốt mục tiêu, thị trường, trade tay/semi-auto/auto và quỹ/
  program/phase. Số dư danh nghĩa không là risk budget hay tiền owner sở hữu.
- Lọc nguồn theo quy tắc rõ, cơ chế kinh tế, dữ liệu tái hiện, costs, điều kiện
  hãng và quyền dùng code/data. Case study trade tay không chứng minh bot;
  payout không chứng minh lợi nhuận sau tổng phí hoặc khả năng tồn tại.
- Tách official/paper/community/inference. Kiểm nguồn hiện hành trước quyết
  định nhạy thời gian; không xếp phổ biến/hiệu quả bằng upvote hoặc quảng cáo.

## Đăng ký trước outcome

- Ghi candidate/version, giả thuyết bác bỏ được, baseline, entry/exit/sizing,
  clock/DST/gap policy, cost/risk/program version, metric và tiêu chí dừng.
  Đổi threshold/giờ/logic là trial mới; giữ cả biến thể thất bại.
- Audit availability/consumed data mà không đọc outcome holdout. Tách dev,
  validation/final holdout; overlap windows/cùng họ strategy không tự là độc
  lập. Warmup chỉ lấy từ quá khứ, không tính lợi nhuận warmup.
- Nến đóng mới quyết định, tick fill sau quyết định, Bid/Ask/cost đúng semantics.
  Không bịa nến thiếu, force close cuối mẫu hoặc đặt cost0 để làm đẹp kết quả.
- Logic tín hiệu tách khỏi config luật/risk. Skill không hard-code luật hãng/
  giá hoặc risk owner; thiếu terms/spec/cost ghi unknown/declared scenario.

## Thực thi và bàn giao

- Có repo: đọc `tooling/ai-engines/STRATEGY-WORKFLOW.md` và
  `projects/trader/foundation_v2/docs/FOREX-RESEARCH.md`. Reuse QDM CLI/runner
  opt-in; không biến native fixed fixture thành engine search tùy ý.
- Kiểm timing/accounting/state trước numeric run; dùng `--preflight-only` nếu
  cần kiểm riêng, giữ input/protocol/source hashes và output mới. Preflight
  không là backtest; exit0 không là strategy qualified.
- Job dài có status/log/checkpoint/deadline/một writer. Reconcile trước retry;
  snapshot roundtrip không chứng minh CLIresume nếu chưa hỗ trợ.
  Với workspace, đọc `tooling/ai-engines/OBSERVABILITY.md`: ghi event theo phase/
  counter và failure locations, không log mỗi tick/secret hoặc gọi stale là dead.
- Chuyển exact run/protocol/candidate/evidence locator cho
  `strategy-qualification` qua native dossier; lưu nguồn/giới hạn/trial history/
  next action ngoài chat trước kết thúc. Không tự đổi protocol sau outcome.

Không cấp quyền account/provider/holdout/OrderCheck/OrderSend/mua challenge.
Skill hỗ trợ repo và package Paperclip; process workers không tự đọc Markdown.
Semi-auto cần quyết định người trước outcome và replay lại state; chọn trade
hindsight hoặc cộng PnL riêng của trade nhận không chứng minh human edge.
