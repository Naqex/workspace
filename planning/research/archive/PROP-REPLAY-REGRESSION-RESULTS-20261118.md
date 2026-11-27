# Hồi quy BASE_GUARD và đối chiếu nguồn tick

18/11/2026. **Đã sửa lỗi ranh giới dữ liệu, đối chiếu 340 lệnh và chạy
lại ba lệnh EURUSD F5 trên một bộ tick khác.** BASE_GUARD vẫn là đối
chứng. Kết quả giải thích được vai trò của stop và làm rõ giới hạn của
kịch bản thiếu giá, nhưng chưa đưa ra một nhánh đủ để đi tiếp tới
Challenge. [Protocol và các lần điều chỉnh](PROP-REPLAY-REGRESSION-PROTOCOL-20261118.md)

## 1. Hồi quy bộ chọn giá

Bộ chọn giá cũ kiểm deadline trước ranh giới nhưng có thể chấp nhận
bar đúng tại ranh giới trong dung sai 60 giây. Đã tái hiện với cutoff
180.000 ms. Yêu cầu tại 120.000 và 179.999 ms đều được ghép vào giá
180.000 ms. Bản sửa cắt danh sách timestamp trước khi tìm. Ngay cả
index dùng khi kết quả ghi thiếu giá cũng trỏ về vùng đã cho phép.
[Bộ chọn giá](../../tooling/ai-engines/quant_core/vectorized_stage0_scanner.py)

Đã kiểm regressions giá trước, trong và sau ranh giới. Các loader được
đối chiếu cho V25–V26, Nhịp 1 và US500 VIX đều cấp tập Development đã
cắt năm hoặc dùng điểm dừng riêng. Không có căn cứ đổi kết quả lịch sử
đã lưu của các lượt đó từ lỗi này. Các kết luận âm vẫn giữ.

## 2. Tách chất lượng điểm vào khỏi tác dụng của stop

Giữ nguyên 340 entry đã nhận, chiều, số lot tham chiếu tại risk 150 USD
và phí của V19 trên 2018–2023. Đo giá khi tới deadline vốn có của từng
lệnh, rồi so với lệnh thực sự thoát theo stop/timeout trong sổ PRIMARY
và sổ thiếu giá bất lợi STRICT. Có endpoint cho cả 340 lệnh. `R` trong
bảng bằng PnL ròng chia 150 USD. Không cộng các bước giá khác tài sản.

| Nhánh | Lệnh | Thoát theo giờ | SL-active PRIMARY | SL-active STRICT | Số năm markout đạt ngưỡng kinh tế hiện hành |
|---|---:|---:|---:|---:|---:|
| EURUSD F5 | 194 | +13,34R | +25,19R | −0,57R | 3/6 |
| Gold F3 | 63 | −15,21R | −9,70R | −11,53R | 0/6 |
| Gold F4 | 83 | +7,45R | +8,36R | +4,15R | 4/6 |
| **Toàn danh mục** | **340** | **+5,58R** | **+23,85R** | **−7,95R** | — |

- **Stop có tác động đáng kể.** Chênh PRIMARY với thoát theo giờ là
  +18,27R, trong đó phần lớn đến từ F5 (+11,86R). Chênh lệch này áp dụng
  cho các lệnh được giữ nguyên entry và quy tắc thoát. Khi stress
  khoảng thiếu giá, F5 mất toàn bộ lợi nhuận tiêu biểu trong mẫu này.
- **F4 dùng được làm đối chứng dương hẹp.** F4 còn dương ở cả hai cụm
  2018–2020 và 2021–2023 dưới STRICT (+2,78R và +1,37R). F4 chỉ có
  6–21 lệnh/năm và vẫn có năm âm. F3 âm cả sáu năm theo markout giờ.
- **Phép kiểm chỉ ra giới hạn của Stage‑0.** Cả ba nhánh được giữ nguyên
  đều trượt ít nhất một cửa nếu dùng cổng cho ứng viên bổ sung mới. Mẫu
  đã qua tuyển chọn từ các đợt cũ. Kết quả chứng minh lựa chọn exit có
  thể đổi PnL được quan sát, chưa đo được Stage‑0 bỏ sót bao nhiêu chiến
  lược mới. Giữ nguyên tiêu chí và dùng F4 làm ca đối chiếu ở lượt sau.

Lần đầu bộ đối soát dừng vì yêu cầu timestamp thoát chính xác đến mili
giây phải bằng nhau giữa OHLC và OLHC. Hai cách xếp điểm giá trong nến
làm khác thời điểm 76 lệnh PRIMARY và 100 lệnh STRICT, tối đa 27,944
giây. Đã kiểm giá thoát, lý do thoát, ngày thoát, deadline, entry/stop
và PnL giống nhau trong từng kịch bản trước khi gộp thống kê kinh tế.
Lần thử đầu và các lần sửa báo cáo được giữ lại.

## 3. Kiểm nguồn cho các khoảng thiếu

**Đính chính đồng hồ.** Các tick ở bốn phút thiếu trong ngày 26/05 và
14/07/2021 thực ra thuộc một giờ trước. Số ở mục này là kết quả theo cách
đọc UTC−5 ban đầu. Ngày 03/01/2022 khớp UTC.
[Đối chiếu tick và định giá lại](PROP-EUR-CLOCK-AND-TREASURY-AUCTION-RESULTS-20261118.md#1-lỗi-đồng-hồ-của-dữ-liệu-eurusd-dùng-cho-đối-chiếu-f5)

Ba link FXCM công khai theo tài liệu thực tế chuyển sang cổng đăng nhập.
Dukascopy trực tiếp trả 429. Chuyển sang ba archive EURUSD Generic ASCII
Tick của HistData và dùng giờ EST cố định UTC−5 đúng đặc tả. Chỉ đọc
các ngày cần đối chiếu trong tháng 05/2021, 07/2021 và 01/2022.
[FXCM TickData](https://github.com/fxcm/MarketData/blob/master/TickData/README.md) ·
[HistData Tick Specification](https://www.histdata.com/f-a-q/data-files-detailed-specification/)

**Có tick trong 4/10 khoảng ưu tiên**, tổng 89 tick bên trong. Sáu phút
ngày 03/01/2022 vẫn trống dù cả hai phút kề có tick. Dùng nguyên ba ZIP
đã tải, rà tiếp mọi khoảng EURUSD Development thuộc đúng ba tháng đó.
Tổng là **8/14 khoảng có tick**, với 170 tick bên trong. So 28 phút kề
giữa hai bộ dữ liệu cho thấy 24/56 trường Bid Open/Close khớp tuyệt đối.
Chênh tuyệt đối trung vị **0,8 pip**, lớn nhất **7,2 pip**. Feed nguồn
của HistData chưa xác minh được, và các chênh lệch này cần giữ tách biệt
khi đối chiếu stop gần mức giá.

| Lệnh F5, UTC | PRIMARY | STRICT | Toàn lệnh trên HistData | Tick trong các phút thiếu |
|---|---:|---:|---:|---:|
| 26/05/2021 08:00 | +326,28 USD | −154,78 USD | +368,49 USD | 45 tick ở 2/2 khoảng |
| 14/07/2021 04:00 | +503,49 USD | −157,71 USD | +485,44 USD | 44 tick ở 2/2 khoảng |
| 03/01/2022 04:00 | +239,52 USD | −152,16 USD | +242,40 USD | 0 tick ở 0/6 khoảng |
| **Tổng** | **+1.069,29 USD** | **−464,65 USD** | **+1.096,33 USD** | **89 tick ở 4/10 khoảng** |

Ba lệnh trên HistData đều tới deadline với stop gốc và cùng lot. Mức
gián đoạn tick lớn nhất trong lệnh là 119,387 giây, dưới ngưỡng ba phút
đã khóa cho phép kiểm độ nhạy này. HistData cho bằng chứng rằng kịch bản
ép chạm stop ở cả ba lệnh là bảo thủ trên feed được kiểm. Mức giá chạm
stop ở broker gốc vẫn chưa xác định. Không cập nhật giá vào sổ V19 từ
phép thử chéo nguồn.

## 4. Quyết định và bằng chứng tái lập

Giữ cả PRIMARY và STRICT, cùng trạng thái `NOT_QUALIFIED`. Hồi quy giá
giúp bảo vệ ranh giới cho lượt sau. Đối chiếu HistData giúp ưu tiên các
gap còn mơ hồ, và khả năng qua Challenge vẫn cần một nhánh có lợi nhuận
đủ nhanh trong cùng ngân sách rủi ro. Quy trình đợt lớn tiếp tục theo
điều kiện trong lộ trình. [Lộ trình](PROP-SYSTEM-ROADMAP.md)

Đã kiểm 340 phép so PnL, 14 khoảng, ba phép chạy trên nguồn thứ hai,
76 kiểm thử tập trung và bốn kiểm tra fixture bổ sung. Bộ quant đầy đủ
có **1.400 pass, 0 skip**, trong 47,27 giây cho lần chạy này. Dữ liệu giá
2024–2026 vẫn đóng. Artifact tư nhân trong `execution-v1/prop-replay-regression-20261118/`.

| Manifest | Vị trí trong job | SHA256 |
|---|---|---|
| `exit-rows-manifest.json` | `exit-audit-v3/749687b9be70` | `5a204ccd2dca65a4ca639a9e306771e171f79d671eb03e713d3cd412f1e905a5` |
| `tick-sensitivity-manifest.json` | `histdata-gaps/749687b9be70` | `d45b4e284a944fa9f815bbbecb036b4b139ddc9227e85b421e4ee3038afb05e9` |
| `cached-month-overlap-manifest.json` | `histdata-overlap/749687b9be70` | `b68f2d45ba7ea5c60cd7140b75b42d2ff283f2f5a358c3b0b5568b3a8e25b1bb` |
| `quant-suite.json` | `quant-regression/749687b9be70` | `4ed5cd316f3d0b78c8ec350c2a58e983b3358d4caa3f87d66a33d223fc7bef8e` |
