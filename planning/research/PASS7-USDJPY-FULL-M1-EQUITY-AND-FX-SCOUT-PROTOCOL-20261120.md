# Pass 7 · Protocol USDJPY M1 và Stage-0 FX

Parent Pass 5 `52a824c`, Pass 6 `268f3a4`. Development [2018-01-01,
2025-01-01) UTC. A 2018–2020, B 2021–2024. Dữ liệu có exposure.
Giữ nguyên native holdout lock và pins. Offline, không MT5, OrderSend 0.
80% trọng tâm Swing 10k/25k và 20% đối chứng Standard 50k.

## Nguồn và replay

Nguồn chính Dukascopy M1 Bid/Ask theo ngày UTC. Tái dùng raw packet
R084/R085 có SHA. Tải hai side còn thiếu trong đúng 2.557 ngày lịch, kể
cả dữ liệu mở lại Chủ Nhật nếu có. Chuỗi lưu Parquet/Zstd theo năm, outer
join timestamp hai side, thiếu bên nào giữ null, SHA256 raw và Parquet.
Cấm forward-fill. Giới hạn tốc độ toàn job, retry hữu hạn 5xx/timeout,
dừng khi 403/429 và giữ checkpoint. Phân biệt ngày lịch trống, ngày FTMO
có hộp/cửa H1, và ngày đủ từng phút từ 00:00 đến hard-flat inclusive.
Ngày có thiếu phút bị loại cả khỏi phép đo execution/equity. Báo độ phủ
theo năm/cụm, nguồn gap và thiên lệch khi ghép ngày. Nếu nguồn không đủ,
chạy phần đầy đủ đã xác minh và đánh dấu kết luận toàn kỳ chưa đủ dữ liệu.

Giữ đúng Pass 5: hộp mid từ 00:00 đến 03:00 UTC, OCO 03:00–10:00 UTC
exclusive, lần phá đầu/ngày, stop đối diện hộp, flat 18:00 Europe/Helsinki.
Cửa UTC cố định theo code Pass 5, gồm lệch London khi DST đổi. M1 mid
extrema là xấp xỉ từ extrema hai side. M1 gap qua entry/SL dùng opening
quote trên side thực thi. Nếu phút entry cũng chạm SL, ưu tiên SL sau fill.
Nếu cùng chạm hai entry, dùng phía có kết quả mô hình xấu hơn cho mọi
profile, khóa theo base để không đổi tín hiệu theo stress. Đếm riêng dual
entry, entry+SL và hợp hai loại. M1 vẫn chưa có trình tự tick. Dùng lại
kinh tế Pass 6, commission 5 USD/lot, slip 0,20 pip mỗi phía và thêm
0 / 0,50 / 1,00 pip vào entry tại ba profile. Swap 0. Báo USD, R, lệch H1
cùng ngày, R/năm hiệu dụng trên cohort rộng và coverage đi kèm, 7 năm,
hai cụm, BUY/SELL, top 10 trên tổng thắng dương và net bỏ top 10.

## Equity

Dùng sổ liên tục từ vốn đầu, risk cố định theo vốn đầu 0,20/0,25/0,30/
0,40%, không compounding, không reset năm. Sizing dùng stop cash dự tính
sau phí, gồm trượt giá profile và commission, làm tròn xuống 0,01 lot.
Kiểm min/max/step và margin theo spec USDJPY Swing và Standard đã pin
trong 8fd77ef và 36f1535. Margin theo USD notional và hệ số hiệu dụng
của từng profile. Không dùng 10k Standard làm bằng chứng native 50k,
ghi rõ phép ngoại suy. Bỏ lệnh nếu min lot hoặc margin vượt vốn khả dụng,
đếm nguyên nhân, không dừng sổ sau breach để giữ cùng diagnostic path.

Dùng giá đóng vị thế Bid/Ask theo từng M1, thu nửa commission khi mở,
nửa khi đóng, trượt giá entry/exit thực hiện mỗi bên. Intraminute báo
envelope bất lợi: phút entry chưa chạm SL giới hạn MAE ở cạnh SL và
bỏ favorable pre-entry do unknown ordering. Phút stop gồm open nếu
còn sống rồi fill theo stop hoặc gap, không mark sau stop. Phút giữa lệnh
dùng open, high/low và close của side liquidation. Báo DD trên đường
open/close và biên bảo thủ high-then-low theo minute. Đối chiếu Peak DD
7,5% và 8% riêng, daily buffer 2,5%, cùng strict FTMO 2-Step equity
5% theo balance tại 00:00 Europe/Prague và static 10% so vốn ban đầu.
Số âm ở đỉnh margin/free margin là sức chịu thực tế của mô hình, không
impute nến thiếu. Không lifecycle, Monte Carlo hoặc sizing tối ưu.

## Scout

Đúng EURJPY/EURUSD/GBPUSD native H1/D1 Development đã seal. Giữ cùng
hộp, window, dual-touch exclusion và điểm +4h/+8h/18:00 như Pass 5.
Spread median snapshot 36f1535 từng mã, slip stress 0,20 pip mỗi phía,
commission 5 USD/lot, swap 0. Đúng pip 0,01 JPY hoặc 0,0001 USD.
Quy PnL EURJPY theo open USDJPY H1 đồng thời, ngày thiếu quote quy đổi
giữ riêng. Không dùng ATR làm filter. Screen cùng chuẩn Pass 5: gross
và net dương hai cụm, thắng Fade trong cả hai, còn dương bỏ hai năm
tốt nhất, báo độ bền top 10. Kiểm thêm quy mô Stage-0 với median phí/
stop <=12% và tối thiểu 50% cơ hội nằm dưới trần 12%; không lọc tín hiệu.
Chỉ khi có horizon vượt đủ cổng mới chạy SL-active đối diện hộp và
hard-flat một lần, đối chiếu tương quan ngày lỗ với USDJPY trên giao hai
sổ. Toàn bộ kết quả promotion chỉ mở quyền xét M1 ở Pass 8.
