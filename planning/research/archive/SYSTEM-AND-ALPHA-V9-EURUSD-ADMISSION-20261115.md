# S2 EURUSD — admission trước outcome

QDM `-symbol action=list` ngày15/11 xác nhận local EURUSD M1 từ2003 và
517.750.341 ticks. Chưa có admitted paired tick path2019–20 ở shared store.
Không gọi là thiếu dữ liệu thị trường. US500 không có QDM cache; nguồn
component lịch sử chưa có admitted M1/tick đủ hai cụm, source/carry/spec còn gap.

Thực thi đúng S2 của protocol V9, không thêm recipe/threshold. Development
2019–20 và2022–23; warmup hai tháng trước từng cụm. Chỉ export cached EURUSD
Bid M1, không update/download hoặc đọc ngoài scopes. Giữ nguyên H4 bias,
Asian ratio1,5, stop4H+0,1ATR cho sweep và whole-box breakout, DAY20:30.

**Screen conditional**, chưa execution qualification: Ask proxy cố định
1pip; commission+slippage stress9USD/lot (5+4), tức0,00009 mỗi đơn vịEUR.
Giá vào Ask cho BUY/Bid SELL, thoát Bid/Ask; báo USD/lot và pips. Đây là
giả định stress minh bạch, không FTMO live spread/spec. Lịch Gold conservative
guards dùng như flat sớm, không gọi là FX target calendar đã certify.
DAY đóng trước rollover; ghi assumption22UTC, không tự mở carry strategy.

Raw markout phải dương từng năm, positive hai Dev clusters, gross đủ phí,
medianF/medianSL≤15%, retain≥50%, admitted≥40/năm. Nếu fail, dừng; nếu pass
vẫn phải admit native BidAsk before SL/account/validation. Không hạ phí,
chọn side/giờ hoặc chạy thêm horizon sau xem kết quả. Validation không mở.
Không kết luận mọi EURUSD/S2 không edge từ một conditional model.
