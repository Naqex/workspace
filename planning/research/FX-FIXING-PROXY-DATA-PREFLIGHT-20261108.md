# R026: preflight dữ liệu proxy, chưa tính chiến lược

Đăng ký trước khi đọc fixture mới. [Method review](FX-MONTH-END-FIXING-METHOD-20261108.md)
giữ nguồn và các gap; [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) vẫn
chưa đạt C1/C2. Không tải hàng loạt hoặc đổi sang proxy khác theo kết quả PnL.

## Phạm vi hữu hạn

- Cùng public Dukascopy provider và installed `dukascopy-node@1.51.1` đã audit;
  không tài khoản/key/provider mới, cập nhật dependency, WAF/browser recovery.
- Chỉ `ezuususd`, `spyususd`, `eurusd`, ngày03/01/2023 UTC →04/01 exclusive;
  mỗi instrument có M1 Bid/Ask:6 requests. Không2025+, strategy simulation,
  PnL, OrderCheck/OrderSend hoặc thay runtime.
- Reuse raw SPY cache trong fixture Discovery14 nếu exact URL đã có. Explicit
  `ignoreFlats:false` cho cả sáu requests; không dùng output cũ đã lọc volume.
  Cache EZU/EURUSD ở attempt riêng, output mới, không sửa fixture gốc.
- Retry0: budget dừng ở lỗi transport đầu tiên; WAFoff/token-cachefalse.
  Deadline180s, CANCEL, PID/progress/log/manifest/source/package/protocol pins;
  một writer. Giữ lỗi/raw; không auto chạy lại hoặc đổi ngày nếu rỗng.
- Kiểm schema/OHLC/order/grid/volume, exact side alignment, open/close spread;
  thống kê coverage NYSE09:30–16:00 và phút cuối cho conversion đồng thời.
  Không sửa/sort/fill nến hoặc coi M1 extrema là actual tick execution.

## Bằng chứng trước fixture và cách hiểu

Installed metadata ghi EZU tick/H1 bắt đầu01/02/2018, SPY16/02/2017, nhưng M1
cả hai lại ghi01/01/2000. Không dùng mốc M1 này làm proof có21năm dữ liệu.
Ngày fixture là kiểm transport/schema trong một phiên bình thường đã chọn,
không xác nhận coverage dài hạn hoặc chốt evaluation window từ ngày đầu có giá.

[Issuer EZU](https://www.ishares.com/us/products/239644/EZU) xác nhận exposure
large/mid-cap Eurozone; [issuer SPY](https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-500-etf-trust-spy)
xác nhận S&P500. Cả hai chưa là Datastream Total Market Indices của paper.
Local provider báo giá hai ETF bằng USD. Nếu sau này dùng tín hiệu EUR-local,
phải khai báo conversion EZU_USD/EURUSD cùng endpoint và basis/fees/distributions;
không lấy return USD của EZU làm return cổ phiếu EUR nguyên chất.

Fixture đạt chỉ cho phép thiết kế thí nghiệm tiếp; chưa đủ corporate-action,
long-history/calendar/fill/cost/risk hoặc edge/prop acceptance. Giữ mốc giá
thô/adjusted và currency conversion rõ trong protocol trước numeric outcome.
WMR hiện hành công bố16:00 London theo [LSEG](https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks);
NYSE calendar vẫn không là lịch công bố fixing. Chưa mua benchmark history.
