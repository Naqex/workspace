# Phân rã lời/lỗ nhiều tầng — 09/11/2026

Đã triển khai và đối soát trên Gold SMA50k R043, dùng lại sổ đã kiểm của
[chẩn đoán trước](SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md).
Đây là nâng cấp cách tổ chức và đọc số liệu; không đổi chiến lược, chi phí,
risk hoặc kết luận chưa đủ bằng chứng để đề xuất challenge.

## Từ tổng thể xuống từng lệnh

| Tầng | Nội dung | Quy tắc cộng |
|---|---|---|
| Chiến lược / phiên bản | ID quy tắc, các kịch bản và đường dẫn nguồn | Không cộng các kịch bản phí thành lợi nhuận chung |
| Kịch bản phí | Chuẩn và cao, mỗi bên có tổng riêng | Tổng các sổ năm của chính kịch bản đó |
| Sổ năm | Năm, vốn đầu sổ, net đóng, khoản còn mở | Vốn reset mỗi năm; không giả tài khoản liên tục |
| Hướng giao dịch | BUY / SELL trong sổ | Hai nhóm không trùng lệnh |
| Lý do thoát | SL, gap qua SL, quy tắc chiến lược | Chia tiếp bên trong từng hướng |
| Thời gian giữ | ≤1 ngày, 1–5 ngày, >5 ngày | Dựa khoảng thoát sớm nhất trong mô hình đã có |
| Từng lệnh | ID ghép kịch bản + năm + position ID | Truy ngược đúng sổ nguồn và SHA256 |

Đây là một cây phân nhóm duy nhất: chỉ cộng các con cùng cha. Các bảng BUY/SELL,
lý do thoát và holding tổng hợp trên nhiều năm từ báo cáo trước là các góc nhìn
khác nhau; không cộng chúng thành một tổng mới. 439 trường hợp lệnh–chi phí
không phải 439 giao dịch độc lập: gồm 219 trường hợp phí chuẩn và 220 phí cao.

## Mỗi phần trăm trả lời một câu hỏi

Mỗi record % có `percent`, `numerator`, `denominator`, `unit` và
`denominator_scope`; đường dẫn scope chỉ rõ nhóm cha/kịch bản/sổ vốn.

| Số liệu | Mẫu số | Hiểu đơn giản |
|---|---|---|
| % từng khoản bất lợi | Tổng price losses + các cost debit + rounding debit của nhóm | Trong tiền bất lợi, phần này chiếm bao nhiêu? |
| % từng khoản có lợi | Tổng price gains + funding credit + rounding credit của nhóm | Trong tiền có lợi, phần này chiếm bao nhiêu? |
| % từng loại phí | Tổng spread + commission + slippage + funding debit của nhóm | Trong phí phải trả, loại này chiếm bao nhiêu? |
| % đóng góp lên cha / cả kịch bản | Chính khoản tương ứng ở cha / kịch bản | Nhóm này tạo bao nhiêu % khoản đó? |
| % nhóm lệnh lời / lỗ đóng góp | Tổng net dương / tổng trị tuyệt đối net âm của cha | Bao nhiêu tiền lời hoặc tiền lỗ đến từ nhóm này? |
| Win / loss / hòa rate | Số lệnh đã đóng của nhóm | Bao nhiêu % lệnh có net sau phí dương / âm / bằng 0? |
| Net đóng / vốn sổ | Vốn đầu của chính sổ chứa lệnh | Nhóm đóng góp bao nhiêu điểm % lợi suất sổ? Không là ROI riêng của nhóm |
| Equity return của sổ | Vốn đầu chính sổ đó | Tính cả phần còn mở, sổ thay đổi bao nhiêu %? |

Không lấy trung bình tỷ trọng nhóm con để tính tỷ trọng cha; cộng tiền/count
gốc rồi chia lại. Mẫu số 0 → `null`/N/A, không thành 0%. Vốn thiếu, sai hoặc
không dương → tỷ lệ vốn N/A; nếu bất kỳ sổ nào thiếu vốn thì mean annual return
của kịch bản N/A, không bỏ sổ đó hoặc mượn vốn sổ khác. Làm tròn % cuối cùng
đến 0,01 điểm %; tổng số hiển thị có thể lệch 0,01 do làm tròn.

Nhóm lệnh lỗ **sau phí** khác pool price losses/costs. Hai cách nhìn có thể
trùng nguyên liệu, không cộng vào cùng biểu đồ. Spread đã nằm trong Bid/Ask
gross; cây chỉ tách riêng sau khi chuyển về mid benchmark đã đối soát.
% accounting không là % nguyên nhân chắc chắn có thể sửa hoặc tiết kiệm.

## Ví dụ thật: cùng khoản funding, ba tỷ lệ khác nhau

Gold, phí cao, sổ năm 2010:

| Câu hỏi | Phép tính USD | Kết quả |
|---|---:|---:|
| Funding chiếm bao nhiêu bất lợi trong năm? | 712 / 1.793,97 | 39,69% |
| Funding chiếm bao nhiêu tổng phí trong năm? | 712 / 881,65 | 80,76% |
| Năm 2010 đóng góp bao nhiêu funding của cả kịch bản? | 712 / 8.709,20 | 8,18% |

Tất cả đều đúng vì trả lời câu hỏi khác nhau. Sổ này có 14 lệnh, net đóng
−170,31 USD = −0,34% vốn 50.000 USD; sau −22 USD financing của vị thế còn mở
và +140,83 USD floating, equity PnL là −51,48 USD ≈ −0,10% vốn.
Các khoản còn mở chỉ nằm trong cầu nối equity; không gán tùy ý vào lệnh đã đóng.

Một đường đọc sâu: `phí cao → 2010 → BUY → stop_loss → ≤1 ngày → coarse-1`.
Lệnh này net −122,73 USD, chiếm 33,50% net lỗ của nhóm cha gồm 3 lệnh,
và đóng góp khoảng −0,25 điểm % lợi suất sổ. Đây là cùng một lệnh được nhìn
ở nhiều tầng, không phải nhiều lần thua mới.

## Phạm vi và kiểm chứng

- 30 sổ năm 2010–2024, 2 kịch bản, 861 node gồm nhóm và lệnh.
- 40.418 record % được tính lại bằng Fraction, không import producer/helper.
  Đối soát membership, components, tổng tiền/count, cây cha–con, vốn từng sổ,
  win/loss/hòa, open/closed bridge và danh tính ghép.
- 9 mutation bị chặn: cha sai, child trùng, mẫu số sai, % sai, cộng hai kịch bản,
  gán khoản mở vào nhóm đóng, trade ID sai, tự cấp authority, vốn sai.
- 8 test mới cho hierarchy; 4 adverse-budget và 7 EURUSD diagnostic regressions
  đạt. Có mixed-capital, unknown/zero, zero-trade book, funding credit,
  rounding, duplicate/missing book và lỗi phân loại/accounting.
- Skill reference đã audit/validate/link-check: 0 lỗi, 0 cảnh báo; global
  12.279 B, project 10.133/65.536 B, reserve 55.403 B, combined 22.412 B.
- Tạo/bind/ghi output 1,265 giây; review gồm 9 mutation 11,085 giây;
  tổng khoảng 12,350 giây. Đây là thời gian phân rã, không phải tốc độ backtest.
- 0 simulation mới, raw rescan, network, model hoặc broker call; không đọc
  2025+, không sửa dữ liệu/manifest đã đóng. Đây vẫn là cùng agent viết hai
  cách tính, chưa là independent human/feed review.

## Dùng lại và nơi xem

Code: `tooling/ai-engines/hierarchical_attribution.py:build_hierarchy`.
Input trade schema từ diagnosis cũ; mỗi sổ phải kèm vốn riêng, source locator
và SHA256. Currency USD, annual resets, cùng valuation basis. Consumer khác
phải normalize/bind theo hợp đồng này; chưa tích hợp tự động vào mọi runner.
Không giả đã cài skill lên Paperclip hoặc thêm UI quản lý mới.

Private campaign base:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Output `execution-v1/gold-hierarchical-attribution-v1/` giữ:

| File | Công dụng |
|---|---|
| `HIERARCHY.md` | Bảng đầy đủ từ tổng xuống lệnh cho người đọc |
| `hierarchy.json` | Toàn bộ số tiền, components, các tỷ lệ và mẫu số cho code/agent |
| `normalized-books.json` | Vốn và locator/hash của từng sổ; không thay nguồn gốc |
| `manifest.json`, `result.json`, `review.json` | Pins, thời gian, output seals và kiểm chứng |
| `progress.json`, `events.jsonl`, `source-snapshot/` | Trạng thái, lịch sử các bước và mã đã chạy |

Saved producer/reviewer: `run-gold-hierarchy-v1.py`, `review-gold-hierarchy-v1.py`
tại campaign base. Output đã tồn tại bị từ chối; sửa thuật toán cần attempt
mới, không đổi pin của kết quả cũ. Result SHA256:
`b8793ea8006668f5f65ecf650718c2999a35b95143aa40e5386957d56e9a85b3`;
hierarchy SHA256:
`16964b15dffc11c85f148f1f5aa4eeb89abefe5c90fe6f119700f0bfc6588103`.

Quy tắc tái sử dụng đã bổ sung vào reference của skill kiểm định hiện có.
Bước nghiên cứu tiếp vẫn là kiểm swap/spec thật trước khi cân nhắc version
mới; bảng phân rã không tự chứng minh edge, cho phép bỏ SELL/SL hoặc giảm holding.
