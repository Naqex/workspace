# Lộ trình hệ thống giao dịch tự động dành cho một người vận hành

Cập nhật 18/11/2026. Đích đến là hệ thống chủ dự án tự vận hành, có bằng chứng
đủ để quyết định thi hai vòng Challenge và đánh giá payout ròng có thể đều
đến mức nào. Thu nhập chính là mục tiêu dài hạn. Mức thu nhập, ngân sách phí
và mức lỗ chấp nhận được sẽ được chốt trước quyết định dùng tiền thật.

**Nhịp 1 đã chốt.** Hai cơ chế liên thị trường trượt Stage‑0. Mười khoảng
giá ưu tiên vẫn thiếu. Nhịp 2 cần ứng viên đã qua Stage‑0 hoặc bằng chứng
mới cho một khoảng giá có tác động. [Task](PROP-STAGE0-NEXT-SLEEVE-TASK.md) ·
[Kết quả và quyết định](PROP-N1-RESULTS-20261118.md).
Đã đo thiếu hụt vòng 1 trên sổ Development. PRIMARY qua 6/61 cửa sổ
trong 12 tháng và thiếu trung vị 4.929,17 USD ở nhóm chưa qua. Dùng
yêu cầu về độ bổ sung để đặt card cho một Stage‑0 kế tiếp.
[Bài đo và yêu cầu ứng viên](PROP-PHASE1-SHORTFALL-20261118.md)
Kế hoạch này tiếp nối kết quả V26. Chiến dịch STRATEGY-E2E cũ đã đóng theo
quyết định của owner, với lịch sử thử nghiệm được lưu riêng.
[Chiến dịch cũ](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)

## Điểm xuất phát và cách đo thành công

`BASE_GUARD` là đối chứng. Phí chuẩn cho 71/105 mốc hoàn tất hai vòng,
trung vị 48,06 tháng trong nhóm hoàn tất. Kịch bản giá thiếu bất lợi cho
0/105. ISO ở V26 cho 69/105 ở phí chuẩn và cải thiện từ 15 lên 57/105
khi phí tăng 50%. Vì thế có hai việc đáng ưu tiên: tìm thêm nguồn lợi
nhuận sau phí và giảm bất định ở các khoảng thiếu giá có tác động lớn.
[Kết quả V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md)

| Nhịp | Câu hỏi và bằng chứng cần có | Quyết định cuối nhịp |
|---|---|---|
| **1. Sàng lọc lợi thế sau phí** | So cơ chế với lịch sử thử, kiểm tần suất và nguồn, khóa công thức rồi đo markout sau phí stress và quy mô SL tự nhiên. Song song rà các khoảng thiếu giá có giá trị quyết định. | Chọn ứng viên có lý do để replay, gác vì kinh tế/tần suất, hoặc ghi đúng đầu vào đang thiếu. |
| **2. Replay và ghép danh mục** | Replay SL/exit bằng Bid/Ask và kiểm khoảng trống. So đối chứng và danh mục ghép cùng vốn, chi phí và ngân sách rủi ro. Đo net R theo cụm, tháng không có lệnh, equity DD, lỗ ngày, rủi ro mở và mức phụ thuộc lệnh thắng lớn. | Xét vòng đời nếu danh mục có cải thiện đã đăng ký và còn khoảng đệm rủi ro. Giữ kết quả riêng của ứng viên để phân biệt edge với vai trò bổ sung. |
| **3. Vòng đời và độ bền** | Khóa cấu hình trước khi kiểm dữ liệu ngoài Development. So trên cùng mốc lịch sử và cùng chuỗi bootstrap, có stress phí, giá thiếu và kiểm thực thi. Báo tỷ lệ hai vòng theo 6/12/18/24/36 tháng, thời gian có tính cả cửa sổ chưa hoàn tất và kết quả Funded theo kỳ. | Xét theo dõi tiến về phía trước khi bằng chứng kinh tế, độ bền và rủi ro đủ cho đúng chương trình đích. |
| **4. Theo dõi tiến về phía trước và bàn giao vận hành** | Khóa luật rồi ghi tín hiệu, spread, chi phí, lệnh giả lập, trạng thái và chênh lệch giữa mô hình với tài khoản đích. Kiểm restart, mất feed và đối soát trạng thái. Bàn giao cách đọc báo cáo, dừng hệ thống và xử lý sự cố. | Chủ dự án quyết định tiếp tục quan sát hay thử Challenge sau khi có bằng chứng và ngân sách. Challenge, Funded và payout thực tế có tiêu chí riêng. |

Cửa sổ 12 tháng là mục tiêu thiết kế chính, 6 tháng là mốc tham vọng đã
dùng trước đây. Chốt ngưỡng tỷ lệ hoàn tất và ngân sách rủi ro trước Nhịp 3
để tránh chọn tiêu chí theo kết quả. Các mốc dài hơn cho thấy mất bao lâu
nếu mục tiêu sớm chưa đạt. Lịch sử 2024–2026 đã được dùng nhiều lần. Dùng
đúng nhãn kiểm định lịch sử và dành đánh giá thực sự ngoài mẫu cho dữ liệu
chưa dùng hoặc giai đoạn theo dõi từ sau khi khóa cấu hình.
[Tiêu chí kiểm định](../../.agents/skills/strategy-qualification/references/validation-gates.md)

Khi xét thu nhập, báo theo dòng tiền **đã nhận** sau phần chia, phí thi,
phí thử lại và chi phí vận hành. Báo cả số tháng không payout, mức lỗ và
thời gian hồi vốn. Hạ tầng phục vụ những phép kiểm này: nguồn và chi phí
truy vết được, job có thể resume và một nơi đối soát trạng thái. Ưu tiên
sửa hạ tầng khi nó ngăn một quyết định nghiên cứu hoặc vận hành cụ thể.

## Cập nhật sau mỗi nhịp

Lưu kết quả, kể cả kết quả âm, bên cạnh protocol và số liệu của nhịp. Kế
hoạch này chỉ cập nhật quyết định, lý do và nhịp đang ưu tiên. Nếu đổi tín
hiệu, giờ, phí, exit hoặc tiêu chí sau khi đã xem kết quả, đăng ký phép thử
mới và nối lại lịch sử. Agent xử lý lựa chọn nhỏ trong phạm vi đã giao.
Chủ dự án chốt các quyết định thay đổi mục tiêu, dùng dữ liệu đã khóa,
chi phí thật và quyền thực thi trên tài khoản.
[Workflow chiến lược](../../tooling/ai-engines/STRATEGY-WORKFLOW.md)
