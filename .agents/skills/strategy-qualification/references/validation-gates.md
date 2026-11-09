# Cửa kiểm chứng: bằng chứng nào cho phép kết luận gì?

Áp dụng từng cửa theo stage, không bắt research ban đầu có đủ mọi điều kiện của
broker execution. Nguồn/đối chiếu hiện hành ở
[audit khung validation](../../../../planning/research/STRATEGY-VALIDATION-FRAMEWORK-20261105.md).
PLAN/protocol và receipt vẫn own scope/outcomes; bảng này own phương pháp review.

| Cửa | Bằng chứng cần | Kết luận tối đa |
|---|---|---|
| G0. Thiết kế trước kết quả | Cơ chế giả thuyết, exact rules/baseline/cost/risk, consumed map/split, main metrics/stop/decision và bản freeze có thời điểm đáng tin | Được chạy đúng experiment đã đăng ký; hash nội dung riêng không chứng minh timing |
| G1. Dữ liệu/code/timing | Kiểm ordering/gaps/timezone/BidAsk; chỉ dùng dữ liệu đã có tại decision, fill sau decision; case tính tay/oracle đơn giản và regressions độc lập với helper bị kiểm | Implementation có bằng chứng trong scope đã kiểm; còn gap thì nêu rõ |
| G2. Simulation assumptions | Spread/commission/slippage/financing/lot/margin, stress/gap/delay, equity/cash và cuối mẫu đúng semantics, nguồn và giới hạn assumptions | Kết quả dưới assumptions đó; chưa suy broker fills hay prop compliance |
| G3. Edge ngoài mẫu | Freeze trước window chưa used, trial history gồm failures/variants, sample/exposure/dependence/regimes/uncertainty, selection-aware assessment khi đủ assumptions | Review robustness/edge; PnL dương hoặc một Sharpe threshold không tự pass |
| G4. Prop-specific | Đúng firm/program/phase/size/version, reset/DST/daily/overall equity, first breach, entry rules, sample coverage, cost/permissions | Prop-fit trong phạm vi profile đã kiểm, không đồng nhất internal budgets với luật hãng |
| G5. Forward/reconciliation | Shadow/demo đúng code/config; đối chiếu signal→order→fill/cost/risk, disconnect/restart/unknown handling, dữ liệu live theo quyền riêng | Bằng chứng vận hành và model-vs-broker gap; chưa bảo đảm lợi nhuận tương lai |
| G6. Authority | Account/scope/budget/grant còn hợp lệ và gate của execution owner | Được thực thi đúng phạm vi, không do research report tự cấp |

Trước validation research: cần G0, G1 và G2 có assumptions rõ, không nợ lỗi
material; chưa đủ realism thì chỉ được kết luận ở mức scenario. Trước đề xuất
shadow/demo cho strategy: review thêm G3/G4 theo mục tiêu, nêu remaining gaps.
Mọi gửi lệnh cần G6 riêng; system demo test không tự chứng minh strategy edge.

## Cách báo cáo

Mỗi cửa ghi stage applicability, status **đã kiểm trong scope / chưa kiểm /
không đạt / chưa đủ bằng chứng**, locator/version và bước sửa nhỏ nhất. Tool
`strategy_evidence.py inspect` chỉ kiểm artifact invariants/bindings; đọc
`review_checks`, không suy từ exit0/hash match thành preregistration, causality,
OOS, independent review hoặc broker realism. Không biến user labels thành proof.

- Lỗi code/clock/data → invalidate/quarantine run bị ảnh hưởng, sửa và kiểm
  case lỗi rồi rerun phần cần. Không loại luôn ý tưởng hoặc sửa parameters cho đẹp.
- Thay rules sau khi nhìn validation → trial mới; window đã nhìn là consumed,
  không còn final unseen holdout cho bản đó. Giữ negative/abandoned variants.
- Sample/precision/coverage thiếu → inconclusive, không mặc định0 hoặc pass.
- Có material bug hoặc vi phạm xác minh → reject evidence/version liên quan.
- Eligible next-stage review cần bằng chứng cho đúng stage, chưa là authority.

Đừng chọn một con số Sharpe/số trades/p-value làm tem chuẩn chung. PBO/DSR/
resampling cần trial/dependence/distribution assumptions phù hợp; chúng không
sửa được lookahead, dữ liệu sai hoặc chi phí hư cấu. Walk-forward không là bắt
buộc cho mọi fixed strategy; purge/embargo chỉ áp khi cấu trúc samples/labels cần.

## Khi exact run dừng vì thiếu giá

Không mặc định phải khôi phục cả archive trước khi chọn việc tiếp theo. Có thể
đăng ký một sensitivity model riêng để hỏi uncertainty có làm đổi ưu tiên
nghiên cứu không; giữ exact unknown và protocol cũ. Đây không là permission
bỏ gap, tự đóng vị thế hoặc chấp nhận dữ liệu không đạt G1/G2.

- Nêu giả định có thể bác bỏ: ví dụ hidden prices nằm trong same-side H1
  envelope và protective execution theo model không rejection. Kiểm envelope
  chứa observations đã có; điều đó chưa chứng minh không có quote/outlier mất.
- Bao gồm mọi nhánh SL/TP/survival/gap có thể theo giả định, account costs và
  eligibility trên toàn cash interval. Thiếu terminal/source hoặc các nhánh
  làm đổi entry eligibility mà chưa mô hình hóa thì giữ inconclusive.
- H1 có thời gian trước entry không xác định được thời điểm chạm barrier;
  dùng retrospective bound không được đưa tương lai vào entry/size. Outer
  bounds có điều kiện không là confidence interval/xác suất pass đã hiệu chỉnh.
- Khóa tiêu chí trước outcome mới, so unaffected trades với exact baseline
  và kiểm bằng arithmetic/path khác. Kể cả hai đầu bound bằng nhau vẫn ghi
  conditional; không sửa actual-state/unknown/edge/prop verdict thành pass.
  Upper bound âm có thể giảm ưu tiên đúng recipe theo protocol, không bác bỏ
  cả family hoặc chứng minh mất giá đã được khôi phục.

Provenance: [R065 bounds](../../../../planning/research/NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md)
và [R066](../../../../planning/research/NASDAQ-NOISE14-RESULTS-20261109.md) đã có
registered models, full Fraction reviews và retained exact unknowns. Đây là
hai cases cùng agent/provider, không universal fidelity certificate.
