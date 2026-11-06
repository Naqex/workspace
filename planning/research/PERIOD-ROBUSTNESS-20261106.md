# Kiểm độ bền hai ứng viên — tháng 4–9/2022

## Phạm vi trước khi đọc kết quả

Owner giao tiếp tục sau [review hai ứng viên](SURVIVOR-REVIEW-20261106.md).
Lượt này kiểm lịch sử offline đã đề xuất, không mở final holdout hoặc broker.
Protocol được lưu và hash trước export/kiểm giá mới; registration cuối pin cả
input bytes và numerical source trước mô phỏng. Metadata audit không chứng
minh dữ liệu chưa từng được xem ngoài project: `clean_oos=false`, prior exposure
unverified. Không đổi tham số sau khi thấy kết quả.

Câu hỏi: hai bộ quy tắc hiện tại có còn tạo lợi nhuận sau chi phí trong đoạn
lịch sử tiếp theo Q1/2022, hay evidence hiện tại phụ thuộc hẹp vào thời kỳ?
Đây là kiểm robustness của hai ý tưởng đã chọn, chưa là chứng minh edge.

| Thành phần | Cấu hình khóa |
|---|---|
| Candidates | `eurusd-h4-z20-2-atr14-time6-r025-v1`; `eurusd-h4-utc-range00-08-atr14-r025-v1` |
| Thị trường / tín hiệu | EURUSD, nến H4 đóng, fill tại quote hợp lệ tiếp theo theo Bid/Ask |
| Warmup | 01/02–31/03/2022; ít nhất 81 nến H4 hợp lệ; không tính PnL |
| Evaluation | 01/04–30/09/2022; cuối mẫu exclusive 01/10/2022 UTC |
| Observations | Cutoff exclusive 01/07 và 01/10/2022: 3 và 6 tháng lồng nhau, không độc lập |
| Rules | Entry, initial SL 2 ATR14 và exits gốc; không thêm TP/filter hoặc đổi giờ |
| Account | Initial 10.000 USD, fixed planned 25 USD/lệnh, một vị thế; phanh nội bộ 100 USD/ngày và 500 USD overall |
| Reference | Commission 2,50 USD/lot/side; slippage 0; financing buy 9,3 / sell −0,31 USD/lot |
| Cost stress | Commission như reference; slippage 0,00002/side; financing buy/sell 20 USD/lot |
| Financing calendar | 22:00 UTC ngày thường, thứ Tư ×3; declared counterfactual, không phải historical broker costs |
| Profile | Reuse exact declared FTMO 2-Step Swing 10k profile từ study trước; áp vào 2022, không chứng nhận luật/spec năm 2022 hoặc contract account |
| Clock / data | Quotes/H4 UTC; risk reset Europe/Prague theo DST; giữ gaps/thứ tự/tick grid, không bù giá |
| Cuối mẫu / phase | Không force-close cuối mẫu; native pass → reset account ở H1 kế tiếp trước end; causal indicators tiếp tục, state account cũ archive |
| Thực thi | Hai numerical workers, parallel start; tối đa 6 giờ/worker, 8 giờ/batch; preparation tối đa 30 phút riêng; đây là ceilings, không ETA |
| Recovery | Không auto retry, không mid-scenario resume; dùng lại completed job/scenario chỉ khi bindings/seals khớp |

## Chỉ tiêu và diễn giải đã chọn trước outcome

Primary: net equity của account tại cuối 6 tháng trong cả hai cost scenarios,
đọc cùng tick DD, first breach, native phase status và coverage. Nếu reset phase,
giữ số theo account/vòng và archive riêng; không cộng tiền các vòng thành payout
hoặc một equity curve giả. Flat-cash baseline là equity delta 0 trên initial 10k.

Secondary: snapshot 3 tháng, contribution Q2/Q3 khi cùng một account path,
trade count/exposure/holding, commission/slippage/financing, actual initial
stop-risk và pending/open cuối mẫu. Không yêu cầu mỗi quý phải có lãi; không
chọn winner chỉ theo profit, win rate hoặc số quý dương.

| Kết quả | Quyết định tối đa |
|---|---|
| Lỗi material data/timing/accounting | Dừng/quarantine evidence bị ảnh hưởng, sửa đúng lỗi; không sửa strategy để làm đẹp |
| First breach | Không đủ điều kiện theo profile/config đó; giữ nguyên first-breach evidence |
| Net không dương ở một mức phí | Chưa đủ để promote trong test này; xem nguyên nhân, không loại cả họ chiến lược |
| Net dương cả hai mức phí, không breach | Thêm evidence robustness; review sự tập trung/uncertainty, chưa tự công nhận edge hoặc đủ thi quỹ |
| Chưa đạt phase target | Giữ not-reached; không tăng lot để ép pass hoặc ngoại suy thời gian từ annual mean |
| Thiếu coverage / không giao dịch | Inconclusive; không coi zero breach là pass |

Giữ trial âm và original rules. Mọi đổi risk/TP/SL/indicator sau outcome là trial
mới trên dữ liệu đã consumed. Risk sensitivity và TP2R chưa thuộc lượt này.

## Gates và provenance

1. Bounded JSON metadata audit tại jobs/research roots; không đọc giá hoặc xuất
   outcome trong audit. Kết quả riêng giữ scope, gaps và prior exposure unknown.
2. Kiểm QDM cache identity/availability và instance rảnh; chỉ export hai window
   trên từ cache hiện có, không download/update hoặc mở 2024/2025+.
3. Chuẩn bị quality/H4/tick cache một lần, hash raw/source/runtime, kiểm ordered
   timestamps/BidAsk/grid/date bounds; giữ quality exclusions, không tự sửa giá.
4. Freeze registration JSON mới; bổ sung đúng digest vào registry, giữ source
   numerical không đổi so study trước. Reader/report hỗ trợ đúng horizons [3,6]
   với negative tests; giữ legacy guards và các registration cũ nguyên vẹn.
5. Hai registered CLI preflights không mô phỏng; synthetic six-month cutoff,
   seal/accounting/report và annual compatibility checks đạt trước dispatch.
6. Native batch/supervisor owns processes, receipts, logs, cancellation và
   completed verification; report consumer chỉ công nhận sau seals/accounting.

Output riêng:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-period-robustness-20261106/execution-v1/`.
`preparation.json` và `batch-1/PROGRESS.md` giữ tiến độ; `pipeline.json` giữ phase
và report locator. Source snapshot giữ provenance; chưa là hermetic restore.
Receipt AI hiện có giữ actual state, hashes, commands và quyền tiếp tục.

Không gọi LLM trong replay loop, không OrderCheck/OrderSend, không mua challenge,
không paid provider mới. Kết quả trong declared model không là full firm
certification, calibrated pass probability, broker realism hoặc payout readiness.
