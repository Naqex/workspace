# Japan200+ cuối phiên Tokyo · đối chiếu Nikkei và đo sau spread

**Gác cơ chế động lượng 30 phút cuối phiên.** CFD Dukascopy JPN.IDX/JPY
bám sát Nikkei 225 quanh giờ đóng cửa tiền mặt trong hai năm kiểm. Cùng
luật đã khóa, phần đường giá đủ dùng **âm cả 2019 và 2022 ngay khi chỉ
tính spread** và kém hơn đối chứng luôn BUY. Năm 2019 thiếu giá M1 ở
nhiều mốc. Kết quả đủ để gác lượt nghiên cứu, còn PnL trọn năm và kết
quả trên đúng hợp đồng FTMO chưa xác định.
[Pilot DAX/Nikkei](PROP-DAX-NIKKEI-CLOSE-PILOT-20261119.md).

## Nhận dạng nguồn và phiên

Dùng 485 phiên tiền mặt theo lịch Cabinet/JPX đã khóa của R087. Cả 485
ngày khớp lịch phiên có giá đóng cửa Nikkei công bố. Dùng FRED NIKKEI225
để đối chiếu giá cuối **14:59 JST** trên CFD, so với giá đóng cửa tiền
mặt. Các thử tải CSV từ FRED/ALFRED bị timeout. Bảng công khai của FRED
đã cung cấp đủ hai khoảng ngày cần đối chiếu. Bản sao giá đóng cửa và
bảng sai lệch từng ngày lưu riêng trong job local theo điều khoản của
nguồn. Bảng dưới chỉ công bố thống kê đối chiếu.
[Lịch JPX](https://www.jpx.co.jp/english/equities/trading/domestic/tvdivq0000006blj-att/tradinghours_eg.pdf) ·
[NIKKEI225 và điều khoản](https://fred.stlouisfed.org/series/NIKKEI225).

| Kiểm nhận dạng | 2019 | 2022 |
|---|---:|---:|
| Phiên có cả đóng cửa benchmark và CFD đúng phút | 238/241 | 241/244 |
| Tương quan lợi suất trên các cặp phiên liền nhau đủ giá | 0,9947 (235 cặp) | 0,9975 (237 cặp) |
| Hai giá cùng hướng từ phiên trước | 94,0% | 98,3% |
| Tỷ số CFD / benchmark trung vị | 0,99995 | 1,00003 |
| Sai lệch có dấu trung vị (bp) | −0,54 | +0,27 |
| Sai lệch tuyệt đối trung vị / P95 (bp) | 4,62 / 13,14 | 4,17 / 10,86 |
| Ngày lệch tuyệt đối lớn nhất | 22/03, −35,30 bp | 08/07, +28,70 bp |

Trên các ngày có đủ cặp để so, mốc CFD 14:59 gần giá đóng benchmark
hơn cả 14:29 và 15:29. Hai mốc kia chỉ dùng để phát hiện lệch giờ,
không tham gia chọn thời điểm vào/thoát. Số liệu hỗ trợ cách hiểu
**CFD proxy gần Nikkei tại giờ cash**, vẫn còn sai lệch từng ngày.
Dukascopy ghi Japan200+ trong bảng tài sản và Japan225+ trong lịch phiên.
FXCM mô tả sản phẩm của họ bám Nikkei 225 USD futures. Đặc tả FXCM
không dùng để tính tiền, lot hay slippage của Dukascopy hoặc FTMO.
[Danh mục Dukascopy](https://www.dukascopy.com/europe/english/cfd/range-of-markets/cfd-indices/) ·
[Lịch Dukascopy](https://www.dukascopy.com/wiki/en/manuals/jforex4-desktop/trading-sessions/) ·
[Đặc tả FXCM](https://www.fxcm.com/markets/help/indices-jpn225/).

## Phễu và kinh tế của CFD đã lưu

So Bid Close 14:29 với Bid Close 14:59 của đúng phiên liền trước.
Vào **14:31 JST**, định giá theo Bid/Ask. Thoát khi stop tự nhiên
của 30 phút trước tín hiệu bị chạm, hoặc tại Open **14:59 JST**.
Phiên đầu năm thiếu phiên trước cùng năm trong phạm vi. Phút thiếu
sau khi có tín hiệu được giữ là unknown nếu chưa thấy stop chạm
trước đó. Giá mở đã ở phía ngoài stop thì bỏ entry. Nếu gap qua stop
sau entry và có giá mở, dùng giá mở xấu hơn. M1 thể hiện biên độ
quan sát, chưa xác minh khớp intraminute thực tế.

| Phễu / độ phủ | 2019 | 2022 |
|---|---:|---:|
| Phiên trong lịch / thiếu dữ liệu ở bước tín hiệu | 241 / 220 | 244 / 83 |
| Tín hiệu có đủ điều kiện tính hướng, trước xét stop và phí | 21 | 161 |
| Trong đó bị chặn vì giá vượt stop ngay lúc vào | 2 | 9 |
| Chỉ spread, cap 12% · qua / định giá / còn thiếu | 5 / 4 / 1 | 29 / 27 / 2 |
| Spread + stress 3 điểm mỗi chiều · qua / định giá / còn thiếu | 0 / 0 / 0 | 4 / 4 / 0 |
| Ngày định giá sau cap spread-only, không có entry BASE cùng ngày UTC | 4 | 22 |
| Ngày định giá sau cap spread-only, không chồng khoảng giữ của BASE | 4 | 24 |

Spread median ở phút vào/thoát là **6,062 / 6,062** điểm năm 2019 và
**7,112 / 7,162** năm 2022 trên tập endpoint đầy đủ. Stress **6 điểm
mỗi vòng** kế thừa từ R087 của cùng nguồn Nhật, chưa phải trượt giá
đo được tại FTMO. Commission đích tham chiếu bằng 0 theo công bố FTMO,
không có funding qua đêm trong cửa sổ này. Không dùng 1,50 điểm của DAX.
[R087](JAPAN-US-CASH-REACTION-RESULTS-20261109.md) ·
[FTMO phí chỉ số](https://ftmo.com/en/blog/zero-commissions-on-indices/).

| Chỉ trên lệnh đã định giá | 2019 | 2022 |
|---|---:|---:|
| Chỉ spread · Mean Net R / tổng Net R | −0,342 / −1,368R | −0,319 / −8,612R |
| Chỉ spread · USD quy chiếu, không tính phần thiếu | −256,49 | −1.614,77 |
| Chỉ spread · điểm cơ bản ròng trung bình mỗi lệnh | −9,26 bp | −10,07 bp |
| Stress · số lệnh / Mean Net R / USD quy chiếu | 0 / — / — | 4 / −0,569R / −427,00 |
| Chỉ spread · đối chứng cùng ngày và size, momentum / luôn BUY | −71,27 / +109,99 USD (3 ngày) | −1.326,17 / −785,74 USD (26 ngày) |
| Chỉ spread · DD từ lệnh đóng / USD khi bỏ năm lệnh lời lớn nhất | 1,45R / −401,01 | 8,61R / −2.082,12 |

So BUY trên cùng ngày đủ giá hai chiều, giữ số đơn vị như nhau
và dùng stop của từng chiều. Lấy stop rộng hơn trong cặp để cả
hai vẫn nằm cùng ngân sách. Cổng phí của BUY chỉ ghi đối chứng,
không lọc lại tập ngày. Ở phép đo không SL để soi riêng chiều tín
hiệu, midpoint trung bình đã âm **−11,19 / −2,67 bp** trên 10 / 139
phiên đủ cửa sổ. Sau spread, momentum chỉ **−15,23 / −5,29 bp**,
so với luôn BUY **+0,94 / −1,69 bp** trên cùng mẫu.

Kiểm trần stop chung 1.000 USD với sổ BASE mở tháng 1 của mỗi năm,
PRIMARY và STRICT cho cùng kết quả trên mẫu. Dùng tối đa 187,50 USD
tham chiếu Funded cho 1R, position size liên tục và điểm lợi nhuận
giả định bằng 1 JPY trên mỗi đơn vị. USD/JPY là fixing DEXJPUS
gần nhất có ngày trước ngày Tokyo, dùng cùng tỷ giá cho hai đầu.
Quy đổi này triệt tiêu trong PnL theo tỷ lệ risk/SL, đã kiểm bằng
hai lượt có và thiếu fixing. Chưa dùng lot thực hoặc min/step của
FTMO, margin hay replay để ghi nhận lệnh đủ chuẩn quỹ. 3/4 lệnh
định giá ở 2019 thuộc tháng 5. Trong 2022 có 18/27 lệnh trong quý 1,
7/27 ngày có BASE cùng ngày và 3/27 chồng thời gian giữ.
[DEXJPUS](https://fred.stlouisfed.org/series/DEXJPUS).

Ở **tập lệnh đã biết, cố định membership và size khi chỉ tính
spread**, dư địa phí bổ sung để hòa vốn là **−23,97 / −24,36 điểm
mỗi vòng**. Dấu âm nghĩa là lệnh cần kiếm thêm số điểm đó bình
quân theo khối lượng ngay cả khi phí bổ sung bằng 0. Muốn đạt
+1.000 USD trên đúng phần mẫu này cần cải thiện **117,41 / 39,44
điểm mỗi vòng**. Cả hai hụt mốc xem xét replay. Số tiền từ các
lệnh đã biết không được xem là PnL trọn năm. Bốn năm còn thiếu
không gán 0 hay ngoại suy sang toàn kỳ.

## DAX · độ nhạy từ 12 dòng đã lưu

Bỏ trượt giá trong phép đọc lại, mỗi cụm có **5/6** cơ hội qua
cap, so với **3/6 và 1/6** ở stress đã khóa. Dư địa trung vị là
**0,852 / 0,478 điểm mỗi vòng**. Giá trị âm nghĩa là spread đã
vượt cổng. Không mở thêm giá hay tính PnL DAX. Giữ quyết định dừng.

| Ngày cụm 2018–2020 | Trượt tối đa (điểm/vòng) | Ngày cụm 2021–2023 | Trượt tối đa (điểm/vòng) |
|---|---:|---|---:|
| 2018-01-17 | 0,06692 | 2021-01-20 | −1,00456 |
| 2018-07-18 | 0,19892 | 2021-07-21 | 1,88000 |
| 2019-01-16 | 1,74560 | 2022-01-19 | 0,07024 |
| 2019-07-17 | 1,50560 | 2022-07-20 | 0,54224 |
| 2020-01-15 | −0,79160 | 2023-01-18 | 0,49304 |
| 2020-07-15 | 2,34080 | 2023-07-19 | 0,46240 |

## Quyết định và kiểm chứng

Dừng hướng cuối phiên này. Độ tương đồng benchmark đủ để hiểu
chuỗi proxy, song phần lệnh đã đo vừa hụt cơ hội, vừa không còn
dư địa phí. Không mở thêm bốn năm, đặt lệnh, mua dữ liệu hoặc
chạy replay quỹ. Dữ liệu giao dịch chỉ gồm 2019/2022, đều đã
dùng trong R087 cho cơ chế đầu phiên. BASE_GUARD vẫn NOT_QUALIFIED.

Đã so SHA của 970 file cache với catalogue R087 và giải mã
1.086.598 bản ghi hai phía, có 4 file rỗng. Sáu fixture kiểm
Bid/Ask, mốc thoát và thứ tự stop/gap. Đối soát độc lập các
phương trình PnL, funnel, risk overlap, phí hòa vốn và tính nhất
quán giữa hai lượt có/không có FX. Bằng chứng local tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-jpn-close-proxy-20261119/`.

| Artifact | SHA256 |
|---|---|
| `registration.md` | `8992faa50d3d3e585fe4b12940c2eae6ffc72569320f56050581a21dcb8c142f` |
| `proxy.py` | `97eb73ed4d6d5ded0d807439c24397b310b59fee036ff28738582fb54650ece4` |
| `proxy-results-v2.json.zst` | `c4f2fc7ead224d4afb4a8f41b86e634f9afb9a0d13278cd053dbe489cb28b4c2` |
| `benchmark-private-v2.json.zst` | `fef57c8be0c54718ccd2ace1f80fb2064da8a136bf6eddf3df841a181403388d` |
