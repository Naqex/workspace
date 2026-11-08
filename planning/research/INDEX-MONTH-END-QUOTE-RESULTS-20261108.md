# Bốn mốc cuối tháng: ba khoảng không có ticks, một khoảng thiếu Ask M1

[Protocol trước response](INDEX-MONTH-END-QUOTE-ORACLE-20261108.md) giữ scope
bốn requests, không thêm ngày hoặc retry. Hoàn tất 11,92 giây, existing public
provider/package, không auth/provider mới, simulation hoặc broker/model calls.

| Mốc | Ticks trong hai phút | So raw M1 / kết luận có giới hạn |
|---|---:|---|
| 30/09/2013, 19:58–20:00 UTC | 0 | Raw M1 cả hai side cũng thiếu; chưa có bằng chứng phục hồi |
| 31/12/2014, 20:58–21:00 UTC | 0 | Tương tự; không tự kết luận thị trường đóng |
| 31/12/2015, 20:58–21:00 UTC | 0 | Tương tự; không lấy giá cũ làm close mới |
| 31/10/2016, 19:58–20:00 UTC | 304 | 110/194 ticks từng phút; Bid OHLC exact raw M1 ở cả hai phút, Ask M1 thiếu |

Raw ticks có order/grid/spread/scope checks; quote-bar oracle Decimal đã có
được reuse cho aggregate và overlap. Kết quả 2016 phù hợp với Ask candle request
không khả dụng trong V6, không phải bằng chứng toàn ngày đóng. Hai phút có thể
được xem xét trong dataset reconstruction có provenance riêng; hiện **0 hàng
được thêm**, không sửa input/backtest hoặc tự nâng qualification.

Đối chiếu V1 của private script dùng `datetime.fromtimestamp` theo giờ máy:
31/12 UTC qua 01/01 Việt Nam nên đọc nhầm root năm sau. Raw tick downloads không
bị ảnh hưởng; phần raw M1 lookup 2014/2015 của V1 không được dùng kết luận.
V2 chọn năm UTC, assert khớp năm request và lưu exact `data_root`/raw hashes;
đã chạy lại comparison trên cùng quotes, **0 network calls**. V1 result/source
và V2 result đều giữ, không ghi đè bằng chứng lỗi.

Artifact owner: private campaign `execution-v1/us500-month-end-tick-oracle-v1`.
Nguồn hiện hành là `M1-comparison-v2.json`, cùng manifest/protocol/raw seals;
V1 chỉ để truy vết. Chưa giải quyết ba endpoint thiếu, CFD session history,
target financing hoặc native prop path. Không đủ chứng nhận whole feed/edge.
