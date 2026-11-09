# Gold: đã kiểm phí công khai, chưa đủ để định giá lại challenge

Ngày kiểm: 09/11/2026. Tiếp ưu tiên 1 của [Goal](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md#goal-cập-nhật--09112026),
cho R043 `xauusd-h4-sma20-80-atr14-r025-v1`.
**Giữ research survivor, chưa ưu tiên challenge; không chạy lại với phí thấp hơn.**
Đã xác minh một giới hạn quan trọng: swap-free của The5ers được công bố cho
giai đoạn funded, không đủ căn cứ áp vào các vòng đánh giá.

## Đã xác minh và điều còn thiếu

| Khoản / phạm vi | FTMO CFD | The5ers CFD |
|---|---|---|
| Commission vàng | Thông báo 25/09/2025: 0,0007% notional mỗi chiều, hiệu lực 29/09/2025. Đã đọc lại thông báo; không suy thành rate lịch sử 2010–24 | FAQ 22/07/2026: metals dùng tỷ lệ %, khác mức 4 USD/lot roundtrip dành cho Forex. Công thức FAQ dùng entry price × contract × lot × rate/100 ×2; chưa có rate vàng đúng account |
| Swap | Update 05/11/2026 nhắc kiểm specification từng symbol vì swap thay đổi | FAQ giờ giao dịch dẫn tới MT5 để xem swap; chưa có cash rate vàng đúng account |
| Swap-free | Không có evidence mới cho việc bỏ swap trong challenge | FAQ 14/06/2026 nêu cung cấp ở funded stage qua support. Chưa chứng minh áp dụng cho evaluation, chưa xác nhận eligibility/terms với owner |
| Point / mode / conversion | Snapshot public 08/11 ghi points, contract100; chưa đủ point size/mode/multiplier để suy USD một cách chắc chắn | Public specifications yêu cầu xem specification trên platform; HTML được tool đọc mặc định là Forex, không dùng giá trị đó làm XAUUSD |
| Account / lịch sử | Chưa xác minh đúng server/platform/account/program và historical fee series | Tương tự; không lấy specification FTMO/Exness hoặc bài tổng hợp làm The5ers |

Nguồn chính thức đã đọc trong lượt:

- [FTMO commission announcement](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/).
- [FTMO update 05/11/2026](https://ftmo.com/en/blog/trading-updates/trading-update-5-nov-2026/).
- [The5ers commissions](https://the5ers.com/faqs/what-are-the-spreads-and-commissions/).
- [The5ers swap-free](https://the5ers.com/faqs/does-the5ers-offer-swap-free-accounts-islamic-accounts/).
- [The5ers hours/swap](https://the5ers.com/faqs/market-trading-hours/) và
  [specifications](https://the5ers.com/asset-specifications/).

Không gộp rate của hai hãng hoặc công thức commission khác basis. Khi có đủ
rate và contract để làm study mới, phải khóa riêng entry/exit notional theo
nguồn đúng hãng; không mặc định hai chiều luôn cùng giá hoặc copy công thức
entry×2 của The5ers sang FTMO. Cả hai vẫn thiếu account acceptance.

## Quyết định cho Gold

[Sổ đã kiểm](GOLD-SMA50K-REVIEW-20261108.md) và
[phân rã nhiều tầng](HIERARCHICAL-PNL-ATTRIBUTION-20261109.md) vẫn là nguồn số.
Funding chiếm 77,75% cost-debit pool trong stress model, nhưng đó là declared
40 USD/lot với clock/multiplier đã khai báo, chưa phải phí vàng FTMO/The5ers.
Baseline fixed commission 2,50 USD/lot/chiều cũng chưa là exact metals fee.

| Trục | Kết luận / hành động |
|---|---|
| Đúng số học của mô hình cũ | Đã đối soát; giữ nguyên artifacts và verdict |
| Phí đúng tài khoản quỹ | Chưa được chứng minh; không reprice bằng rate/point suy đoán |
| Dùng swap-free để giải quyết challenge | Chưa được phép suy từ funded-only FAQ; không mở nhánh zero-swap evaluation |
| Ưu tiên nghiên cứu | Chưa có economic/spec evidence mới đủ để chạy Gold lại; chuyển compute sang cơ hội khác biệt |
| Khi nào xem lại | Có source package đúng symbol/account hoặc giả thuyết cơ chế mới đăng ký trước outcome, không chỉ vì muốn kết quả đẹp hơn |

Không bỏ SELL/SL, giảm holding, tăng risk hoặc cộng phí giả định tiết kiệm vào
net cũ. Giá trị mới của lượt này là admission/decision, không thêm trial hoặc
chứng minh rằng mọi trend strategy đều kém. Không đòi owner mua account để
tiếp tục các hướng offline khác; không hỏi support thay owner.

## Evidence và kiểm tra truy xuất

Private campaign base:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
`execution-v1/gold-public-cost-admission-v1/` giữ `sources.json`, HTML/text của
FTMO commission announcement và `web-evidence.json` chứa kết quả tool đọc
nguồn chính thức; không phải account specification dump.

6 direct requests, 3 workers, không retry: 1 thành công, 5 TLS/connection
failures; giữ nguyên failure evidence. Không tắt kiểm TLS hoặc ghi failure
thành website không công bố. Web tool đọc được 4 nguồn FAQ/update cần thiết;
kết quả được lưu riêng, không giả raw HTML của direct requests đã thành công.
FTMO raw announcement SHA256:
`9475ab08da30a5cfcc49097fb07eadddce83c877f2f7b204550ef809f5e8e45d`.

Saved fetch script `fetch-gold-cost-admission-v1.py`; fetch wall 39,705 giây.
Không benchmark/model/broker call, không simulation hoặc market-price rescan;
không có thay đổi code cần chạy lại test engine. Phạm vi review là đối chiếu
primary texts với declared model, không audit account hoặc historical swaps.

Việc kế: EIA clock/PIT và endpoint admission. Giờ phát hành chuẩn công bố
không phải timestamp thực tế của 103 sự kiện đã census; không lấp unknown
bằng 10:30 hoặc lấy giờ xuất bản PDF thay giờ ra dữ liệu ban đầu.
