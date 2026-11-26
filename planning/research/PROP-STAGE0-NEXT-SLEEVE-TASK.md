# Nhịp 1 — Tìm ứng viên bổ sung cho BASE_GUARD

**Trạng thái: đã chốt ngày 18/11/2026.** Gác cả hai cơ chế vì trượt cổng
kinh tế. Mười khoảng ưu tiên chưa có nguồn giá mới đủ điều kiện.
[Protocol đã khóa](archive/PROP-N1-PROTOCOL-20261118.md) ·
[Kết quả](archive/PROP-N1-RESULTS-20261118.md) · [Lộ trình tổng](PROP-SYSTEM-ROADMAP.md)

## A. Sàng lọc cơ chế kiếm lời

**Ngân sách: tối đa ba cơ chế độc lập, mỗi cơ chế một cấu hình và một tài
sản chính.** Ưu tiên tối đa hai cơ chế trước, dùng suất thứ ba khi hồ sơ
cho thấy câu hỏi khác về nguồn tạo lợi nhuận. Một phép đổi oscillator,
timeframe, tham số hay tài sản tính vào ngân sách thử và vẫn thuộc nhóm
cơ chế gốc. Chốt danh sách trước khi xem kết quả markout của nhịp.
Mỗi thử nghiệm có một chân trời chính và tối đa một chân trời chẩn đoán.
Kết quả ở chân trời phụ dùng giải thích quy mô/thời gian giữ.

1. **Lập danh sách ngắn từ bằng chứng sẵn có.** Đối chiếu F5 range rejection,
   F3 compression breakout, F4 impulse theo giờ và các nhóm đã thử trong
   V18–V26. Với mỗi đề xuất, ghi nguồn tạo cơ hội, điểm khác với nhóm đã thử,
   khi nào dự kiến xuất hiện và điều kiện nào bác giả thuyết. Ưu tiên cơ
   chế có cơ hội ở những giai đoạn danh mục thưa, theo quy tắc biết được
   trước lệnh. Lịch sử tháng yếu dùng để mô tả nhu cầu và phải được ghi
   nhận là đã xem nếu ảnh hưởng lựa chọn. [Chỉ mục research](README.md)
2. **Lọc trước khi viết phần giao dịch.** Ghi dữ liệu và cost đã có theo
   tài sản, thời điểm có thể biết tín hiệu, logic dễ tái hiện, stop tự nhiên
   và độ dày mẫu cần thiết. Ưu tiên dữ liệu Bid/Ask đủ cho thời điểm vào và
   chân trời đo. Dùng kết quả cũ hoặc count-only theo luật cố định để đo
   số cơ hội, số ngày riêng và tháng trống. Sàn dự kiến cho nhánh bổ sung
   là 40 tín hiệu thô/năm trên từng năm Development đầy đủ, kế thừa V26.
   Nếu cần sàn khác theo vai trò hoặc phân bố cơ hội, ghi lý do và khóa
   trước khi đếm. Đây là tiêu chí phù hợp vai trò. Số lệnh thực vào và
   độ chắc thống kê được kiểm sau.
3. **Khóa card trước khi đo.** Ghi cơ chế, lần thử liên quan, tài sản, input
   và mã, UTC/giờ phiên, dữ liệu warmup, cut-off, giá vào/ra, cost model và
   điều kiện dừng, kể cả mức thiếu giá cho phép và cách tính mẫu số.
   Dùng Development 2018–2023 khi nguồn đủ kỳ. Dữ liệu
   tài chính 2024–2026 nằm ngoài nhịp sàng lọc này. Tận dụng runner markout
   và bộ ghi nhận missing quotes đã có, sau khi xác nhận phù hợp với card.
   Một recipe phải mô tả được bias → vùng/setup → trigger → entry, hoặc
   ghi rõ tầng nào không thuộc cơ chế. SL ở nhịp này dùng để đo quy mô.
4. **Chạy Stage‑0.** Đo markout theo chiều tín hiệu tại chân trời đã khóa,
   gồm spread, commission, slippage và financing nếu phát sinh. Dùng
   Bid/Ask đúng chiều và giữ số mẫu thiếu giá. Cổng hiện hành yêu cầu
   mean net stress dương từng năm, ít nhất bằng mean ma sát thực thi trên
   cùng tập mẫu. Dùng trần 12% cho tỷ lệ median phí stress/median SL tự
   nhiên và giữ ít nhất 50% mẫu thô tại trần phí đã khóa. Ghi quy mô phép
   đo và dùng nguồn phí mô phỏng có nguồn gốc rõ nếu thông số đích còn thiếu.
   Thiếu giá có thể đảo kết luận hoặc không đủ phủ kỳ đã đăng ký thì giữ
   trạng thái thiếu bằng chứng.
   [Stage‑0](../../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen)

**Đầu ra.** Một bảng cho mọi cấu hình đã đăng ký, gồm theo từng năm: cơ
hội thô, ngày có cơ hội, tháng trống, coverage, SL tự nhiên, tỷ lệ qua phí,
mean net stress tại chân trời chính, phân bố/độ bất định và nguyên nhân
dừng. Gắn nhãn `ECONOMIC_FAIL`, `CADENCE_OR_SAMPLE_SHORTFALL` hoặc
`DATA_PATH_INCOMPLETE` theo bằng chứng. Hết ngân sách hoặc không có cơ
chế đủ điều kiện: ghi kết quả và gác. Có ứng viên qua: ghi lý do và đề
xuất thứ tự replay dựa trên độ đủ nguồn, kinh tế sau phí và cơ hội bổ
sung. Nhịp này dừng ở quyết định chuyển sang replay. Tương quan PnL,
drawdown và khả năng qua Challenge cần sổ lệnh/đường vốn ở nhịp sau.

## B. Rà khoảng thiếu giá có thể đổi kết luận

Dùng danh sách **32 lệnh và 55 lần gặp khoảng thiếu** đã biết. Đối chiếu
sổ chuẩn với stress đã lưu để tìm những khoảng có thể đổi thứ tự chạm SL,
giá thoát hoặc trạng thái tài khoản. Nếu dữ liệu đã lưu chỉ cho chênh lệch
ở cấp lệnh, xếp ưu tiên theo cấp lệnh và gắn từng khoảng thay vì quy kết
riêng cho một phút. So theo cả hai thứ tự giá mô phỏng và khử trùng các
khoảng trùng giữa các lệnh. [Đối soát V19](archive/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md#2-các-lệnh-vướng-giá-thiếu-và-guard-có-tác-dụng-gì)

**Giới hạn một lượt**: ưu tiên tối đa 10 khoảng có tác động lớn trong
Development, tối đa hai nguồn cục bộ có chứng cứ mới hoặc chưa kiểm và
90 phút rà nguồn. Ngoài Development, chỉ dùng metadata và chẩn đoán đã
lưu để xếp ưu tiên. Khi có quote mới, lưu nguồn, symbol, thời gian, Bid/Ask
và đối chiếu hai đầu khoảng. Ghi trạng thái xác minh hoặc vẫn thiếu cho
từng khoảng đã rà. Nếu chưa có nguồn mới đủ chứng cứ thì đóng lượt rà với
danh sách còn thiếu và ảnh hưởng có thể có. Ghi rõ khi tác động chưa lượng
hóa được. Replay phần bị ảnh hưởng là bước kế tiếp khi đủ bằng chứng.

## Chốt nhịp

Lưu card trước outcome cùng bảng kết quả và nguồn số liệu. Đưa ra đúng một
quyết định tiếp theo: **replay ứng viên**, **giải quyết thiếu nguồn cụ thể**
hoặc **gác nhóm cơ chế**. Hai phần của nhịp có thể làm độc lập vì quyết định
Stage‑0 dựa trên dữ liệu của ứng viên, còn rà gap dựa vào bằng chứng đã lưu
của danh mục gốc. Đợt này dùng nghiên cứu offline. Các bước tiếp theo theo
phạm vi và cổng trong lộ trình tổng.
