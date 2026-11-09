# Vàng–bạc: không mở lại R067 từ điểm gãy nhìn sau toàn mẫu

09/11/2026. Đối chiếu [R067 đã kiểm](GOLD-SILVER-FORMATION-RESULTS-20261109.md)
với [CESifo working paper 12559](https://www.ifo.de/DocDL/cesifo1_wp12559.pdf),
March 2026, Caporale/Fons Palomares/Gil-Alana. Đã đọc §§3–6, Table 2–6;
render và xem PDF page 17 để kiểm cách chia mẫu. Không chạy lại formation,
không mở own market data 2025+, không thêm trial hoặc cài thư viện.

## Bằng chứng mới và cách áp dụng

Paper dùng daily futures 2010–2025. Full-sample Engle–Granger/Johansen không
hỗ trợ quan hệ ổn định. PELT trên monthly residuals và supF tìm điểm gãy cuối
2017/đầu 2018; post-break Johansen chỉ vượt ngưỡng sát biên, FCVAR có bằng
chứng mạnh hơn. Local Whittle cho persistence gần unit root; tác giả lưu ý
hồi rất chậm và bất ổn quan hệ. Paper không cung cấp kiểm định lợi nhuận bot
CFD sau phí hay thời gian đạt mục tiêu quỹ.

| Câu hỏi | Quyết định của project |
|---|---|
| Có mâu thuẫn với R067 không? | Không: R067 dùng CFD sampling hai formation riêng 2018/2021, EG cố định; paper khác công cụ, độ dài mẫu và inference. Không đổi p-value cũ |
| Lấy mốc 2017 để bật bot từ 2018? | Không: mốc được chọn sau nhìn dữ liệu tới 2025. Gán ngược vào lịch sử sẽ dùng thông tin tương lai |
| Đổi sang FCVAR/Markov-switching ngay? | Chưa: phương pháp phức tạp hơn chưa giải quyết causal regime availability, thời gian hồi, hai chân phí, hedge/risk và target contract |
| R067 bác bỏ mọi cặp vàng–bạc? | Không. Nó chỉ không qua bộ lọc ưu tiên của exact formation đã khóa; chưa có PnL và chưa đo xác suất bỏ sót |

Đây là method-admission decision, không backtest mới hoặc tuyên bố paper sai.
Muốn mở hướng regime sau này cần một protocol mới: detector chỉ nhìn prefix,
thời điểm fit/availability, trading horizon, chi phí hai chân và kiểm future
mutation; không chọn điểm gãy/giai đoạn theo PnL. Hiện chưa đủ cơ sở ưu tiên
đầu tư đó thay vì lấp một khoảng trống correctness đã biết của survivor.

## Reuse và bước tiếp

R067 giữ nguyên `not_retained`, catalogue vẫn 90 records/58 account-policy
versions, chưa ứng viên challenge. Không tạo R091 chỉ vì đọc thêm paper.
Chuyển sang [kiểm tín hiệu SMA vàng](GOLD-SMA-SIGNAL-REVIEW-PROTOCOL-20261109.md):
review cũ chưa có SMA/ATR oracle riêng. Đây là C2 correctness work trên
outcomes đã exposed, không clean OOS hoặc bằng chứng edge mới.

Nguồn PDF lưu personal reference ở private campaign root:
`cesifo1_wp12559.pdf`, 31 pages, 669.155 bytes, SHA256
`1953334364269ec923ef35e544fa86a881ce2f58c5d0f51f8bc366f40d9d31c1`.
Web reader timeout hai lần; direct official HTTPS download thành công,
không bypass TLS/auth. Text/render là derivatives, không redistribute PDF.
Đọc full method này không phát sinh market/provider/broker/model calls.
