# Risk và prop: giữ đúng nghĩa

Phương pháp, không chứa luật hãng hiện hành hoặc risk budget owner.
Pin rules/terms đúng account/program/phase và ngày hiệu lực.

| Khái niệm | Kiểm gì |
|---|---|
| Drawdown quan sát | Đỉnh→đáy của đúng balance/equity series, coverage/thời gian |
| Giới hạn hãng | Contract threshold, static/trailing, reset/basis/costs; không đồng nhất metric backtest |
| Giới hạn nội bộ | Budget được cấu hình và khoảng đệm; không tự dùng sát ngưỡng hãng |
| Daily / overall | Anchor ngày khác initial/high-water-mark; không reset overall/trial count theo ngày |
| Equity / balance | PnL mở/chi phí theo semantics; balance không đủ cho rule equity |
| Static / trailing | Anchor cố định khác high-water-mark đúng basis/timing/điều kiện ngừng trail |
| Risk mỗi lệnh | Stop-risk + cost/gap assumptions; SL không bảo đảm fill đúng giá |
| Tổng risk account | Positions/pending/reservations/unknown; không chia budget mỗi bot |
| Correlation/exposure | Nhiều ticker/strategy có thể cùng cược một hướng |
| Lợi nhuận owner | Tách simulated capital, payout và mọi phí challenge/retry/subscription |

Rule profile cần version/effective date/provenance, firm/program/phase/size,
loss semantics/timezone, news/holding/SL/EA permissions và target/day/payout.
Thiếu trường liên quan giữ unknown; không dùng default hãng khác.

## Chọn sizing cho ứng viên có bằng chứng

### Contract Core Alpha — Prop Sizing Policy — Exit

| Owner | Inputs / đầu ra tối thiểu | Cửa kết luận |
|---|---|---|
| Core Alpha | Frozen signal/entry/exit rules, known-at/source/cost units; intent/abstain trace và net evidence/dependence/uncertainty | Kỳ vọng dương sau chi phí cần bằng chứng phù hợp; net mẫu dương chỉ provisional. Cadence/sample phải đủ cho câu hỏi và thời gian thu bằng chứng |
| Prop Sizing Policy | Alpha intent + canonical account/phase/equity, daily/overall headroom, positions/pending/reservations, lot/margin và cost/gap allowance → size/reject/pause có reason | Chọn risk/time-fit/buffer theo profile; không tự sửa signal/exit để cứu economics. Phase lấy lifecycle, không tạo state machine cạnh tranh |
| Exit Policy | Frozen SL/TP/time/partial/BE decisions có timestamp và remaining position | Đổi quản lý lệnh là version/trial mới. Primitive partial-close có sẵn không chứng minh exit đó tốt hơn hoặc đúng trong runner này |
| Qualification | Hai phần evidence alpha và account replay, đúng rule/data/model version | Không lấy technical pass, sizing đẹp hoặc simulated target hit thay edge/OOS/authority |

Screen có thể dùng baseline để ước lượng economics sớm, nhưng chưa promote
alpha khi mẫu/precision/cadence không đủ. Một mức risk thấp không là trần
bất biến; không loại candidate chỉ vì baseline return chưa đạt kỳ vọng.
Nếu overlay đổi admissions/fills/account state, phải replay theo thời gian;
không lấy trade list trước overlay làm toàn bộ kết quả mới. Ghi raw intent
và accepted/rejected orders riêng để thấy alpha hay policy gây khác biệt.
Risk halt khác strategy exit: stop-entry và account liquidation phải có
policy/priority đã đăng ký tại execution owner; đóng sau breach không xóa
witness đã xảy ra. Partial/BE không tự được bật như một risk emergency.

Contract test plan và component reuse nằm ở [gap matrix của bước1–2](../../../../planning/research/STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md#gap-matrix-và-test-cases-nhỏ-nhất-cho-bước-3).
Thiết kế không là implementation; chưa tự bật overlay, partial/BE hoặc đổi
risk thật. Giới hạn/taxonomy theo [validation gates](validation-gates.md#nhãn-nguyên-nhân-dừng-và-phạm-vi-bằng-chứng).

Tách hai câu hỏi: tín hiệu có net edge trong model/data đã kiểm không, và
size/risk nào phù hợp mục tiêu với daily/overall headroom? Không loại ứng
viên chỉ vì return ở một baseline risk thấp chưa đáp ứng kỳ vọng. Risk lớn
hơn không tạo thêm mẫu độc lập; cùng trade set và cost tỷ lệ không đổi thì
nhân size không đổi dấu net expectancy. Nếu fixed fees/fee tiers làm thay
cost/unit, cần tính lại economics theo size, không coi đó là edge tự xuất hiện.

1. Giữ signal/entry/exit recipe và definition of R rõ. Risk là budget tiền/
   size; RR là payoff/SL-TP structure. Đổi TP/SL/exit là strategy version mới,
   không coi là chỉ đổi risk. Cố định SL distance rồi đổi size cần sizing version.
2. Sau evidence kinh tế đáng giữ, đăng ký vài sizing policies có lý do trong
   vùng risk nội bộ; so return/time-to-target cùng equity daily/overall DD,
   losing streak/recovery, exposure/correlation, margin/cost/gap/lot rounding.
   Không chọn size lớn nhất vừa lọt historical DD hoặc nhìn mỗi final PnL.
3. Linear R scaling chỉ là ước tính nếu cùng fills/trade set và cost/unit không
   đổi. Fixed fees, compounding, minlot, capacity, rejects và risk brakes có
   thể đổi kết quả/admissions. Khi sizing mới làm đổi path/state, replay
   account từ đầu window; không chỉ nhân toàn bộ equity/PnL cũ với một hệ số.
4. Reuse dữ liệu, indicators và signal trace hợp lệ; không bắt nghiên cứu lại
   từ đầu nếu signal semantics không đổi. Kiểm lại phần sizing/account/prop/
   execution bị ảnh hưởng; validation đã dùng vẫn consumed. Final sizing
   freeze trước fresh/prospective validation, không tune trên final holdout.

Return đáp ứng kỳ vọng chỉ được promote nếu còn buffer trước stress/tail và
drawdown chưa từng thấy, đúng account-wide budget/rule/phase. Biết historical
maxDD không biết được future maxDD; stress/resampling theo dependence khi có
đủ cơ sở, không gọi kết quả mô phỏng là xác suất bảo đảm. Thiếu dữ liệu giữ
unknown. Không tự đổi risk thật/account grant từ đề xuất offline.

Source Naqex khi có workspace:

- `projects/trader/foundation_v2/trading_workspace_v2/semantics/prop_profile.py`:
  versioned evaluator/data blockers, không suy hỗ trợ mọi luật.
- `projects/trader/foundation_v2/trading_workspace_v2/forex_pilot_risk.py`:
  pilot limits riêng, chưa là chứng nhận compliance/intrabar đầy đủ.
- `projects/trader/foundation_v2/trading_workspace_v2/risk_promotion_contracts.py`:
  pure reducer/budget không tự là adapter runtime enforce broker.
- `projects/trader/foundation_v2/api-rust/src/automation_grants.rs`: một owner/
  account, durable attempts/reservations; unknown không release chỉ vì timeout.
  Kiểm consumer send boundary, không suy từ struct/config đã enforce.

Mất quote/kết nối xử lý theo contract; không giả đã flat hoặc SL được broker
chấp nhận. Guard không chứng minh edge và không loại mọi loss tail.
