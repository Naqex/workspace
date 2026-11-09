# Hệ thống đã sẵn sàng kiếm tiền chưa? — 02/11/2026

**Chưa đủ bằng chứng để dùng tiền thật.** Đã có workflow nghiên cứu chạy được,
nhưng chưa có chiến lược được xác nhận đủ tin cậy cho bước đó. Kết quả tích hợp
và kết quả kiếm tiền là hai việc riêng. Receipt cùng thư mục giữ trạng thái và
bằng chứng thực thi; tài liệu này giải thích kết quả cho owner.

## Đã làm thêm trong lượt này

- Kiểm lại ứng viên cũ: Donchian 100/50, điều chỉnh tỷ trọng theo biến động
  30%, lookback 30 ngày; BTC/ETH spot D1. Giữ nguyên quy tắc, không tìm tham số.
- Dùng snapshot 2021–2024 cố định, bốn cửa sổ đánh giá 180 ngày từ
  01/01/2023 đến 20/12/2024. Mỗi cửa sổ chỉ tính tín hiệu từ lịch sử có sẵn.
  Phần cuối 11 ngày không dùng. So với cash và mua và giữ cùng dữ liệu/chi phí.
- Chi phí giao dịch giả định 15 bps và stress 40 bps trên phần tỷ trọng thay đổi
  (tương ứng 0,15% và 0,40%). Không phải phí tính mỗi ngày trên toàn tài khoản.
- Sửa lỗi kiểm tra ngày thiếu: kiểu thời gian s/ms/us từng bị hiểu là ns, khiến
  một ngày bị tính thành 86,4 giây trong worker. Nay dùng timedelta có đơn vị.
  Dữ liệu đang dùng đủ ngày theo kiểm tra UTC độc lập, không cần sửa giá/nến.
- Kiểm chứng: 21 tests chất lượng dữ liệu trên pandas 2.3.3 và 21 trên môi trường
  worker pandas 3.0.6; 7 tests workflow RD-Agent; Ruff ở hai file sửa đạt.
  pandas 3.0.6 của worker nằm ngoài dependency range Quant Lab (<3): đây chỉ là
  kiểm tương thích phần bị ảnh hưởng, chưa tuyên bố toàn Quant Lab hỗ trợ pandas 3.

## Kết quả kiểm lại chiến lược

Lợi nhuận dưới đây là **trung vị bốn cửa sổ 180 ngày**, không phải lợi nhuận cả
giai đoạn hoặc lợi nhuận dự kiến. Drawdown là mức sụt vốn lớn nhất trong từng
cửa sổ rồi lấy cửa sổ xấu nhất; chưa là drawdown danh mục xuyên suốt.

| Tài sản | Chi phí | Lợi nhuận chiến lược | Mua và giữ | Sụt vốn chiến lược | Sụt vốn mua và giữ | Cửa sổ có lãi |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 15 bps | 16,87% | 51,71% | −11,96% | −20,93% | 3/4 |
| BTC | 40 bps | 15,87% | 51,71% | −12,69% | −20,93% | 3/4 |
| ETH | 15 bps | 8,23% | 36,90% | −14,20% | −37,07% | 3/4 |
| ETH | 40 bps | 7,87% | 36,90% | −14,39% | −37,07% | 3/4 |

Có giai đoạn lỗ: cửa sổ đầu BTC −5,16%, ETH −10,78% ở 15 bps; khi stress
40 bps là −6,26% và −11,82%. Không bỏ các cửa sổ này khỏi tổng hợp.

Chiến lược có mức sụt vốn thấp hơn nhưng lợi nhuận thấp hơn mua và giữ trong
mẫu này. Đây là trade-off cần đánh giá theo mục tiêu rủi ro; chỉ thua passive
về lợi nhuận không đủ kết luận chiến lược vô ích. Ngược lại, 3/4 cửa sổ có lãi
không chứng minh lợi thế bền vững. Mức volatility target 30% không phải cam kết
giới hạn drawdown 30%.

## Nút thắt theo thứ tự ưu tiên

| Ưu tiên | Đang thiếu gì? | Việc tiếp theo |
|---|---|---|
| 1 | Chưa xác nhận lợi thế chiến lược sau chi phí và mức rủi ro chấp nhận được | Chốt tiêu chí trước lượt đánh giá mới; giữ lịch sử mọi lần thử và dữ liệu đã xem |
| 2 | Giá khớp còn là xấp xỉ close-to-close, dù tín hiệu đã dịch một nến | Kiểm accounting/giá có thể giao dịch sau khi nến đóng, spread, trễ, phí, sai lệch và lệnh không khớp |
| 3 | Chưa có dữ liệu theo dõi tiến về phía trước | Sau kiểm chứng phù hợp, lập forward paper contract rồi quan sát theo thời gian thực |
| 4 | Chưa chốt vốn, ngân sách rủi ro và lợi nhuận ròng cần đạt | Biểu diễn lỗ theo % và VND; tính cả chi phí AI/vận hành trước cân nhắc tiền thật |

2021–2024 đã được dùng; báo cáo cũ còn xem dữ liệu tới 08/2026. Lượt này không
mở holdout mới và không gọi các giai đoạn đã xem là dữ liệu chưa biết. Không tune
tham số để làm đẹp kết quả vừa có. Đối chiếu nguồn dữ liệu độc lập vẫn còn thiếu.

Paper hiện **NOT_RUN, 0 ngày**. Bộ contract paper-soak có sẵn kiểm bằng chứng
vận hành 30–60 ngày; chưa có runner/observations được chấp nhận cho chiến lược này.
Với chiến lược khung ngày ít lệnh, đủ số ngày vận hành cũng không tự chứng minh
hiệu quả đầu tư. Chưa mô phỏng danh mục BTC/ETH xuyên suốt hoặc tính chi phí AI,
vận hành, thuế. Chưa chốt sàn hoặc xác minh khả năng khớp ở tài khoản cụ thể.

Các agents hiện thực hiện thí nghiệm có contract định sẵn và phản biện kết quả;
chưa là hệ thống tự chủ toàn bộ quá trình tìm, kiểm định và chọn chiến lược.
Lát số liệu này do operator chạy offline, không giả thành một lượt AI/native run.
Không thêm engine, gọi model, kết nối sàn hoặc đặt lệnh trong lượt này.

**Khuyến nghị:** tiếp tục với ứng viên cố định để kiểm giá khớp và accounting
sát thực tế trước. Sau khi có tiêu chí và kết quả phù hợp mới chuyển sang paper.
Hoàn thành các bước này giúp đánh giá đáng tin hơn, không bảo đảm có lợi nhuận.

Tài liệu chính thức Freqtrade cũng khuyến nghị kiểm lookahead/recursive bias và
dùng dry-run trước live: [Strategy Customization](https://www.freqtrade.io/en/stable/strategy-customization/).
Đây là tham khảo quy trình, không phải đề xuất cài thêm engine.

## Nguồn và giới hạn tái lập

Artifact root local:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f/`.

- `donchian-frozen-review-20261102/`: `run.py`, `registered-contract.json`,
  `data-preflight.json`, `validation.json`, `report.md`, `receipt.json`.
  Contract ghi trước đánh giá; hoàn tất trong 104,26 giây, provider calls = 0.
  Quant source `943b779dc96ac16aae6718cec16f4f3f00e07a92`.
  Script SHA `0be6331e0feacd4eda4b7e598b7eec57c34ef79b161436b9c31e74a70d24f27e`;
  validation SHA `f1efed9425fa5f13be67239d0f32a2439f98eecc092792c6b4c3cfb4e3d65dc2`.
- `quality-revalidation-20261102/`: script, preflight và receipt riêng xác nhận
  CSV/canonical data hash không đổi sau sửa. Snapshot cũ và lịch sử run giữ nguyên.
  Snapshot mới `crypto-daily-2021-2024-quality-r2` có khoảng ngày 86.400 giây;
  manifest SHA `9b95da82fc591dccee5f9b8f32025476e226a8da02806959305a92e5048f0c38`.
  Settings dataset pin chuyển sang manifest mới khi bốn agents idle/timer off,
  có bản sao settings cũ trong runtime riêng. Quant source sửa
  `52f6501c4058d46e298678d963908b5ef76d84e8`.

Kết quả số được chạy trước sửa quality metadata, có kiểm ngày đủ độc lập.
Lượt revalidation chứng minh nến/hash không đổi; không chạy lặp toàn backtest
chỉ vì metadata thay đổi, cũng không ghi đè provenance của kết quả cũ.
