# Chiến dịch tìm ứng viên challenge — Goal mới, 08/11/2026

**Đang thực hiện.** Owner giao mở rộng phương pháp, tìm ứng viên đủ bằng chứng
cho challenge, đồng thời sửa correctness, cải tiến performance và dữ liệu khi
có nhu cầu thực. Goal mới đã active. Quyết định dừng B ở
[campaign trước](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) là lịch sử, không là
điều kiện tự hoàn tất Goal này. Giữ nguyên tài liệu/pins của các đợt đã freeze.

## Đích và cách biết đã đạt

Kế thừa **C1/C2** của campaign trước: ứng viên có lợi thế sau phí và đủ bằng
chứng cho đúng bước challenge; quá trình có protocol, causal inputs, kiểm
chéo số học/nguồn, trial history, prop equity/time-fit, prospective
reconciliation và bàn giao owner. Không hạ ngưỡng để tạo winner hoặc coi một
batch/admission hoàn tất là đạt mục tiêu. Không bảo đảm thị trường có edge.

FTMO/The5ers phải đánh giá riêng theo program và điều kiện hiện hành. Profile
10k/25USD mỗi lệnh và mốc so sánh 3/6/12 tháng kế thừa để nghiên cứu; chưa là
đề nghị mua challenge hay deadline cá nhân. Holdout 2025+, broker sends,
tài khoản/provider mới, trả phí và production vẫn có gate riêng.

## Baseline và các lát kế tiếp

Baseline: 53 hồ sơ/41 policy versions, chưa challenge-qualified. Giữ negatives
và [owner report](OWNER-EVIDENCE-REPORT-20261108.md), không chạy lại 624 cases
FX không đổi. Gold SMA50k là research survivor, chưa đủ time-fit/realism/OOS.

| Lát | Câu hỏi sẽ giải quyết | Đầu ra cần |
|---|---|---|
| Chuẩn hóa đầu vào đang dùng | Một file có hash có thật là đúng loại giá, giờ, side và nguồn không? | Reuse validators, metadata có version, hash/lineage, exposure, units và quality; áp fixture thật, kiểm mutation; không migration/raw rewrite |
| R026 hedge cổ phiếu cuối tháng | Có thể tạo tín hiệu tương đối EUR/US causal bằng proxy đang có không? | Source/clock/mapping admission trước outcome; ghi rõ proxy khác paper, dividend/adjustment unknown; không gọi Total Market là total return |
| Component trước bot | Với recipe được khóa, tín hiệu có giữ economics sau phí qua hai giai đoạn không? | Protocol trước outcome, các ngày thiếu vẫn có mặt, baseline/control và uncertainty; không claim account PnL từ price component |
| Qualification | Survivors có giữ được sau causal fill, prop equity path và dữ liệu chưa dùng không? | Exact C1/C2 review, chỉ affected reruns, đúng permissions; owner handover dễ hiểu |

Mỗi lát có phạm vi hữu hạn; kết quả âm dẫn tới hypothesis mới có lý do, không
đóng Goal mới bằng kết luận B của đợt cũ. Lưu timing/status/log/attempt và
quyết định trước/sau tại artifact/protocol owner. Sau batch có kết quả mới,
hậu kiểm gọn; chỉ profile hoặc dọn khi có bottleneck/phần thừa đã xác minh.
Không xóa evidence, không thêm dashboard/ledger cạnh tranh Paperclip.

## Lát đang triển khai

[Data admission và R026](RESEARCH-DATA-ADMISSION-20261108.md) khóa phạm vi
fixture/currency/quality trước thực thi. Tình trạng kết quả ở chính tài liệu
đó và các artifacts nó dẫn tới. Dùng repo skills hiện có; mở rộng reference
khi workflow đã kiểm, không tạo một skill quản lý toàn bộ khác.
