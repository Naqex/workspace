# Sau R088: kiểm phương pháp và chọn giả thuyết FX tiếp theo

09/11/2026, thuộc [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Đây là admission phương pháp, chưa kết quả chiến lược hoặc ứng viên challenge.
Không mở lại các negative chỉ vì dữ liệu đã sẵn; không tăng số trial bằng số
paper đã đọc. Catalogue giữ88 hồ sơ/58 account-policy versions.

## Hai hướng chưa đáng chạy batch

| Hướng | Primary source và phạm vi đã đọc | Quyết định |
|---|---|---|
| Mua chỉ số trước ngày lễ | [Ko/Yang, bản tại journal host](https://cfr.ivo-welch.info/published/papers/ko2021pre.pdf), §§1–2/Figure1/Tables1–2; [publication2024](https://doi.org/10.1561/104.00000111) | Kiểm lại mẫu tới2019 cho thấy premium tập trung ở small firms, yếu ở large-cap indices sau1990. Chưa ưu tiên chuyển thẳng sang US500 CFD; không kết luận mọi preholiday rule đều vô dụng |
| Mua tuần chẵn theo chu kỳ FOMC | [Knox/Vissing-Jorgensen, FEDS2026-023](https://www.federalreserve.gov/econres/feds/files/2026023pap.pdf), §6/Figure5/Table5, không fullpaper replication | Nguồn cập nhật chỉ ra cycle đổi chiều2017–2021. Không lấy kết quả1994–2016 làm luật BUY cố định, hoặc chuyển sang SELL sau khi biết mẫu mới. Cùng event family R062/R086/R088, không edge độc lập mới |

Không source nào chứng minh current retail-CFD net hoặc prop fit. Đọc literature
2025/2026 không là mở ownmarketdata2025+. Không tải lịch sử giá, chạy backtest,
thay fee hoặc tự cấp quyền từ kết quả của paper.

## Hướng chọn: hồi lại ngày sau biến động bất thường

Primary: Caporale & Plastun, *Daily abnormal price changes and trading strategies
in the FOREX*, DOI [10.1108/JES-11-2019-0503](https://doi.org/10.1108/JES-11-2019-0503),
[Brunel repository](https://bura.brunel.ac.uk/handle/2438/20567),
[full author PDF](https://bura.brunel.ac.uk/bitstream/2438/20567/5/FullText.pdf).
Đã đọc §§3–4, equations1–8 và Tables1–4; không đọc supplementary appendices
của mọi currency. PDF trang đầu ghi CC BY4.0; tự viết implementation, attribution
giữ ở đây, không nhập code/data của tác giả.

Paper dùng ngày Open→Close, ngưỡng mean±2std và nghiên cứu continuation trong
ngày/reversal ngày sau. Bản mô phỏng bỏ transaction costs; nhận xét rằng nhiều
trades làm phí ít quan trọng và winrate≥50% đủ sinh lời không được dùng làm
tiêu chí của project. Nhiều lệnh còn có thể trả thêm phí; mean payoff/loss và
chi phí phải được tính. Giờ server/timezone, cửa sổ hiệu chỉnh `n` và một số
chi tiết triển khai causal chưa đủ rõ để gọi exact replication.

Chọn nhánh **ngày sau** để tránh nhận diện ngày abnormal bằng Close tương lai
rồi giả đã vào sớm trong chính ngày đó. Liên quan price reversion R003/R013,
nhưng không cùng recipe: trạng thái của ngày trước khác H4 z-score hoặc H1
shock fade. Đây là transfer hypothesis có lineage, chưa là cơ chế độc lập đã
được chứng minh. Tin tức/herding/liquidity là giải thích khả dĩ, không inputs
đã quan sát hay causal proof.

## Điều phải làm trước economics

- [Protocol riêng](FX-ABNORMAL-DAY-PROTOCOL-20261109.md) khóa own UTC dayproxy,
  cửa sổ calibration, timing, phí và controls. Không chép giờ9h của paper thành
  UTC hoặc chọn giờ theo PnL đã xem.
- Fixture tính tay cho classification/variance/boundary/known-at, thiếu nguồn
  và thay future quotes. Statistical feature khác financial net.
- Admission nguồn hiện có cho đầy đủ calibration/feature/entry/exit; source
  Bid/Ask, minute/tick interval, first-after lag và gaps phải có proof. Không
  mặc định H1 Close là giao dịch cuối ngày hoặc QDM Bid có Ask thật.
- Chỉ numeric khi protocol/source/preflight đã bind; thiếu thì giữ unknown.
  Cả reference và stress phải trả đầy đủ phí. SL/account/prop/OOS/forward vẫn
  là những cửa riêng; positive component không tự thành bot challenge.

R065 không được mở lại archive: [bounds đã đủ lý do gác exact recipe](NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md).
Đây là kiểm lại next-action trước chọn công việc, không thực hiện resume cũ
ở data-revision report. R088 giữ eventgatefail và netdương đúng scope.
