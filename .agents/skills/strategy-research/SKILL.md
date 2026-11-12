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
- Trước study mới, đối chiếu chỉ dẫn mới nhất của owner với task/stage và
  baseline. “Tiếp tục” không tự cho phép thay cơ chế hoặc timeframe chỉ vì
  bản cũ thưa/lỗ. Đổi hướng thành đề xuất rõ trước numeric; owner đã cho phép
  mở rộng thì ghi scope mới và đăng ký trial, không dùng guard này để chặn.
- Với setup nhiều tầng, tách hypothesis/bias/zone/setup/trigger/risk/entry/exit
  và thời điểm biết. Không dùng bản thiếu filter làm bằng chứng cho bản có
  filter; semantic gap cần giải quyết trước khi diễn giải PnL hoặc sửa thêm.
- Lọc nguồn theo quy tắc rõ, cơ chế kinh tế, dữ liệu tái hiện, costs, điều kiện
  hãng và quyền dùng code/data. Case study trade tay không chứng minh bot;
  payout không chứng minh lợi nhuận sau tổng phí hoặc khả năng tồn tại.
- Tách official/paper/community/inference. Kiểm nguồn hiện hành trước quyết
  định nhạy thời gian; không xếp phổ biến/hiệu quả bằng upvote hoặc quảng cáo.

## Đăng ký trước outcome

- Khi tối ưu, chọn hoặc đổi hypothesis: ghi lý do/kỳ vọng và parent baseline
  trước đo; phân biệt sửa lỗi, đổi data semantics, đổi strategy và tối ưu giữ
  nguyên semantics. Dùng [nhật ký quyết định](../../../tooling/ai-engines/STRATEGY-WORKFLOW.md#nhật-ký-quyết-định-để-kiểm-lại-việc-tối-ưu-và-chọn-chiến-lược)
  trong protocol/results owner hiện có; giữ cả fail/cancel/abandoned, không
  tạo log/ledger khác chỉ cho agent. Sửa rule hoặc assumption kinh tế sau khi
  xem outcome là trial mới, không sửa lại bản freeze để giấu lịch sử.
- Ghi candidate/version, giả thuyết bác bỏ được, baseline, entry/exit/sizing,
  clock/DST/gap policy, cost/risk/program version, metric và tiêu chí dừng.
  Đổi threshold/giờ/logic là trial mới; giữ cả biến thể thất bại.
- Audit availability/consumed data mà không đọc outcome holdout. Tách dev,
  validation/final holdout; overlap windows/cùng họ strategy không tự là độc
  lập. Warmup chỉ lấy từ quá khứ, không tính lợi nhuận warmup.
- Nến đóng mới quyết định, tick fill sau quyết định, Bid/Ask/cost đúng semantics.
  Không bịa nến thiếu, force close cuối mẫu hoặc đặt cost0 để làm đẹp kết quả.
- Khi thêm loader/timeframe hoặc gặp lệch coverage/extrema, dùng
  [source transformations](references/source-transformations.md) trước PnL;
  checksum/schema không chứng minh raw quotes được bảo toàn.
- Logic tín hiệu tách khỏi config luật/risk. Skill không hard-code luật hãng/
  giá hoặc risk owner; thiếu terms/spec/cost ghi unknown/declared scenario.

## Thực thi và bàn giao

Khi dùng/port mẫu từ LEAN, NautilusTrader, Backtesting.py, Backtrader hoặc
VectorBT, đọc [native engines](references/native-engines.md) để phân biệt
full-framework use, code port và parity; reuse runtime/pin có sẵn.

Với policy có huấn luyện/model pack, đọc [ML policies](references/ml-policies.md)
trước tạo labels/splits/inference. Không cần nhánh này cho rules cố định hoặc
chỉ hỏi tiến độ.

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
- Đóng batch screening/kiểm nghiệm có kết quả mới: dùng
  [engineering-retrospective](../engineering-retrospective/SKILL.md) để hậu kiểm
  gọn và sửa phần có evidence; không rerun batch không đổi hoặc tuning rules
  chỉ vì muốn lần nào cũng có một cải tiến.

Không cấp quyền account/provider/holdout/OrderCheck/OrderSend/mua challenge.
Skill hỗ trợ repo và package Paperclip; process workers không tự đọc Markdown.
Semi-auto cần quyết định người trước outcome và replay lại state; chọn trade
hindsight hoặc cộng PnL riêng của trade nhận không chứng minh human edge.
