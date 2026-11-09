# Bài kiểm tiếp theo: giữ quy tắc, đổi giai đoạn lịch sử

Đăng ký05/11/2026, sau audit metadata và trước export/đọc giá của bài kiểm mới.
Scope do [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) quản lý;
trạng thái/bằng chứng nằm ở [receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md).
[Registration JSON](PROP-HISTORICAL-ROBUSTNESS-20261105.json) giữ các pin cụ thể.
Đây là protocol thí nghiệm, không tạo tracker hoặc quyền giao dịch mới.

## Kết luận audit và cách gọi đúng

Owner trả lời **không nhớ rõ** đã từng xem/backtest năm2023–2024 hay chưa.
Audit chỉ đọc JSON metadata có tên/size trong phạm vi khai báo; không export
giá từ QDM, không mở CSV giá hoặc PnL của một window mới. JSON được parse
toàn file trong giới hạn2MiB, nhưng bỏ qua price/outcome collections khi tìm
date pairs, chỉ xuất dates/path/schema/hash. Đây không phải chứng minh mọi
byte trong metadata đều không có outcome hoặc mọi loại artifact đã được đọc.

Inventory nhận diện2.397file metadata,43records có date windows. Các window
Forex nhận diện được nằm trong12/2021 và01–03/2022.130coverage gaps đều là
directory links trỏ ra ngoài root đang quét, đã được prune thay vì đi theo.
Một target có thể thuộc root khác được quét riêng; số gaps không là số lượt
backtest bị thiếu. File ngoài allowlist, records không nhận diện format và
lịch sử ngoài filesystem vẫn là giới hạn. **Không tìm thấy record2023 không
chứng minh2023 chưa dùng.** Cache availability cũng không chứng minh exposure.

| Vùng | Nhãn sử dụng từ nay | Có thể kết luận gì? |
|---|---|---|
| Warmup12/2021, developmentQ1/2022 | Đã consumed | Phát triển/so sánh hệ thống; không là test mới |
| 2023–2024 | Prior exposure unverified | Có thể kiểm độ bền lịch sử với nhãn rõ; không gọi clean/unseen OOS |
| 2025→cutoff | Giữ đóng trong bài này; exposure chưa xác minh | Chưa tự nhận là final holdout sạch |
| Dữ liệu phát sinh sau một lần freeze có kiểm soát | Ứng viên prospective test | Cần cutoff, thu thập và protocol riêng trước khi dùng để chọn/sửa rules |

QDM CLI metadata đã xác nhận EURUSD_TICK_TW có cache2003-05-05→2026-11-01,
517.750.341records. Chỉ dùng `symbols`; không download/update hoặc mở app.
Trước chạy phải export đúng cache window, hash/validate CSV mới; cache range
không bảo đảm coverage/tick quality của từng ngày. Không sửa/sort/dedup/fill
để ép quality pass. Runtime QDM đang có ở checkout cũ vẫn được reuse, source
sản phẩm authoritative vẫn là `projects/trader`.

## Khóa phạm vi trước outcome

| Phần | Quyết định đã khóa |
|---|---|
| Câu hỏi | Các bộ quy tắc đã đăng ký còn tạo kết quả dương sau chi phí ở một quý lịch sử khác không? |
| Vai trò dữ liệu | `historical_robustness`, prior exposure `unverified`; `clean_oos=false` |
| Giai đoạn tính kết quả | 01/01–31/03/2023, UTC, gồm cả ngày không có tick hợp lệ |
| Warmup | 01/11–31/12/2022; tối thiểu81nến H4 hợp lệ, không tính PnL warmup |
| Vì sao chọn ngày | Quý đầu theo thứ tự lịch của vùng validation dự kiến trước đây; chưa xem outcome để chọn quý |
| Vì sao warmup2tháng | Giữ cùng history cho cả5bản và tránh thiếu81nến hợp lệ khi lịch nghỉ/gap làm giảm số nến; không dùng warmup để xếp hạng |
| Ứng viên | Giữ cả5bản Donchian/SMA/Z-score/Pullback/UTC range; không lọc winner từ Q1/2022 |
| Quy tắc | Cùng candidate IDs, code bytes và định nghĩa round1/round2 đã pin; không search tham số |
| Đối chứng | Giữ tiền mặt10.000USD, PnL0; Donchian là baseline so sánh trong cùng bài, không là benchmark đã chứng minh |
| Quy mô | Mỗi mô phỏng độc lập10.000USD, risk25USD/lệnh gồm chi phí, daily100/overall500USD nội bộ, tối đa1vị thế |
| Chi phí | Bid/Ask embedded, commission2,50USD/lot/side; reference slippage0+swap từ current spec đã pin; stress slippage0,00002/side+20USD/lot/rollover unit |
| Đồng hồ | H4UTC, chỉ nến đầy đủ đã đóng; fill quote sau quyết định; financing22:00UTC ngày thường, thứTư multiplier3 theo calendar giả định hiện có |
| Cuối mẫu | Giữ vị thế và pending state thật; không force close, không coi floating PnL là cash đã nhận |

Spec quan sát2026 áp lên giá2023 là **counterfactual scenario**, chưa xác minh
phí/broker lịch sử. Commission chưa account-specific verified. Các mức25/100/
500USD là internal simulation budget, **không phải** luật FTMO/The5ers. Bài này
chưa ước lượng khả năng pass hoặc đánh giá quyền dùng bot ở một chương trình.
Muốn chuyển shadow/demo phải xét firm/program/phase hiện hành riêng.

## Chấm theo tiêu chí nào?

Primary output mỗi candidate và mỗi scenario: **equity cuối −10.000USD**, cùng
cash change, floating PnL và open/pending state. So với cash0 trong cùng window.
Không gộp hai scenario thành hai mẫu độc lập, không lấy tick count làm cỡ mẫu
statistical. Giữ toàn bộ candidate/trials trước và sau, cả run âm/lỗi/bỏ dở.

Secondary outputs có sẵn: entry/closed trades, financing, minimum observed
equity, risk stops/rejections, ticks/gaps/excluded H4 và accounting/state checks.
`minimum_observed_equity` **không phải peak-to-trough max drawdown**. MaxDD,
tail days, losing streak, turnover và concentration chỉ được báo nếu tính có
định nghĩa, causal coverage và đối soát từ ledger/equity path; chưa làm thì ghi
`not_assessed`, không thay bằng proxy đẹp hơn hoặc tự bịa số.

| Điều kiện đã đăng ký | Quyết định cho đúng bài này |
|---|---|
| Hash/source/data/timing/accounting sai material hoặc warmup không đủ | Dừng; invalid affected result; sửa correctness bằng fixture/consumed data trước khi chạy lại. Giữ attempt lỗi |
| Equity change không dương ở reference hoặc stress | Không promote theo bài này; ghi không đạt cost-robustness screen của window. Không kết luận mọi thị trường đều vô dụng |
| Equity change dương ở cả hai, không có material error đã biết | `inconclusive`: chỉ có tín hiệu để nghiên cứu tiếp, chưa đủ OOS/uncertainty/prop evidence |
| Không có trade, coverage thiếu hoặc thiếu dữ liệu để kiểm điều kiện | `inconclusive`, ghi rõ nguyên nhân; không suy zero-risk/pass |
| Source/rules/size/cost/decision threshold đổi sau outcome | Tạo trial/version mới, window đã consumed; không sửa protocol cũ để đổi verdict |

Chưa báo confidence interval, Sharpe significance, DSR/PBO hoặc xác suất pass:
mẫu nhỏ, dependence/trial history và exposure chưa đủ để dùng đáng tin. Không
đăng ký một ngưỡng arbitrary để gọi đủ trade/đủ chuẩn. Cả kết quả dương và âm
đều giữ giới hạn sample/regime và selection bias. Không qualified tự động.

## Cửa thực thi và recovery

Registration khóa protocol/candidate definitions/source/spec/audit hashes trước
giá mới. CSV pins chỉ tạo **sau export**, phải bind vào attempt trước simulation;
đây không là sửa chiến lược/tiêu chí từ outcome. Hash/Git giúp truy vết nhưng
không là timestamp attestation từ một bên độc lập.

Source pins hiện tại là baseline trước bổ sung registration support. Thay code
đọc/kiểm contract cần reviewed implementation binding riêng trước export/run,
giữ snapshot baseline này để đối chiếu diff và tests; không sửa registration
đã freeze hoặc thay signal/core/cost/risk rules dưới tên thay đổi điều phối.

Runner hiện tại chỉ nhận window2022 và sẽ từ chối2023. Registration này **chưa
được CLI thực thi**: trước numerical run phải thêm opt-in contract binding,
targeted tests xác nhận sai candidate/date/hash hoặc nhãn clean-OOS bị từ chối,
giữ legacy guard; không xóa guard hay sửa dates trong artifact cũ để lách.
Đây là phần còn cần triển khai, không phải kết quả đã chạy hoặc gate đã pass.

Khi hỗ trợ contract đã kiểm: QDM CLI export từ cache vào directory mới; cùng
inputs cho5candidate×2cost scenarios; dùng finite supervisor hiện có,5giây/status,
một writer/attempt, tối đa4numeric workers sau first-job probe,30phút/job và
90phút/batch. Đây là hard ceilings, không hẹn phải chờ đủ thời gian. Không model
calls, broker calls, service mới, tải lại full history hoặc tự retry failed job.

Hủy/fail/timeout giữ log/failure locations; đối soát rồi reuse completed jobs/
sealed scenarios còn khớp bindings. Không resume giữa scenario khi CLI chưa hỗ
trợ; không chạy lại phần xong hoặc overwrite raw evidence. Dossier kiểm integrity
riêng; reviewer vẫn giữ G0–G6 unknowns theo
[khung kiểm chứng](STRATEGY-VALIDATION-FRAMEWORK-20261105.md).

Mục tiêu cuối bài là quyết định một bước research có căn cứ, không mua challenge,
tối ưu risk lên cao hoặc bật execution. Một bài independent prospective/final
evaluation cần đăng ký riêng; không tự dịch cửa sổ tới khi có kết quả đẹp.
