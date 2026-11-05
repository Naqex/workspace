# Công cụ FTMO, The5ers, TradingView và cộng đồng cho agent

Đối chiếu trực tiếp ngày **05/11/2026, Asia/Saigon**. Research/doc review,
chưa là kiểm chứng một integration đăng nhập hoặc permission của tài khoản.
Owner xác nhận **chưa có TradingView trả phí và chưa có tài khoản The5ers**.
Không đăng ký/mua gói, OAuth, mở service hoặc cấp broker authority trong lát này.

## Kết luận áp dụng

| Capability | Bằng chứng chính thức / nguồn gốc | Áp dụng với project |
|---|---|---|
| TradingView MCP chính thức, public beta | [Docs](https://www.tradingview.com/mcp/docs), [announcement](https://www.tradingview.com/blog/en/tradingview-mcp-server-public-beta-60864/); endpoint `https://mcp.tradingview.com/mcp`, OAuth2.1, Essential trở lên, trial không gồm MCP | Để sau vì owner chưa có gói. Dùng phân tích/sàng lọc khi có nhu cầu, không mua chỉ để đủ tool |
| TV market/screener/news/fundamentals/calendar | Docs MCP công bố các nhóm công cụ tương ứng; OHLCV tối đa5.000bars/request | Có ích cho research rộng; không thay QDM tick Bid/Ask hoặc broker spec/point-in-time historical data |
| TV watchlist/alert writes | Docs có cả read và write; `get_active_watchlist` ghi read-only nhưng mô tả có thể tạo/activate mặc định | Khi triển khai phải allowlist tool theo side effect thực; chưa bật create/delete/edit hoặc active-watchlist helper |
| The5ers MCP chính thức | [Landing/docs](https://the5ers.com/the5ers-mcp/), [release24/09/2026](https://the5ers.com/new-features/); `https://mcp.the5ers.com/mcp` | Ưu tiên kết nối chỉ đọc khi owner có account; không cần dựng scraper dashboard |
| The5ers account/rule/payout health | Trang hãng mô tả account balance/equity/status, objective progress, headroom, freshness, payout readiness; cam kết chỉ đọc | Là dữ liệu hãng để đối soát trạng thái account, không gửi lệnh/đổi thiết lập; chưa thấy authenticated schema hoặc kiểm tool thực trong phiên |
| The5ers skill tải về | Landing có Download Skill | Chưa tải/cài: chưa có consumer/account. Không xem hướng dẫn Always Allow trên website là quyền user cấp |
| FTMO portal tools | [Tools overview](https://ftmo.com/en/trading-tools-and-services/) có MetriX, Account Analysis, Trading Journal, calendar/timezone/news tools | Tận dụng UI chính thức và report/export nếu thực tế cung cấp; không tạo UI quản lý cạnh tranh |
| FTMO App Suite / FXBlue | [App Suite](https://ftmo.com/en/app-suite/) công bố35tools cho MT4/MT5; các phần hỗ trợ thao tác/tính lot/chart/account | Hữu ích cho trade tay/semi-auto. Chưa là MCP hoặc public agent API; không gắn thêm EA có quyền giao dịch lên terminal đang dùng |
| FTMO MCP / portal public API | Không tìm thấy công bố chính thức qua site search `MCP`, `API` và tools/FAQ đã đọc | Nhãn **chưa tìm thấy**, không khẳng định không tồn tại. Giữ MT5 adapter hiện có, không đăng nhập private DXtrade endpoints từ sample cộng đồng |
| TradingView webhooks/Pine | [Webhook docs](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/): ports80/443, timeout3s; [Pine](https://www.tradingview.com/pine-script-docs/) | Có thể mang alert sang hệ thống khác theo quyền/terms; chưa cần khi strategy chạy trong core, không mở public endpoint chỉ để làm bridge |

## Cộng đồng/open source: shortlist có vai trò riêng

Chỉ đọc docs/license/capability; không cài hoặc thực thi code từ các repo này.
Không coi stars, README hoặc Context7 reputation là kiểm toán bảo mật/maintenance.

| Nguồn | Capability / license được công bố | Quyết định và gap |
|---|---|---|
| [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) | Desktop CDP, chart/Pine/editor/replay; MIT cho source; yêu cầu debug port | Dự phòng nếu cần thao tác Pine/editor mà MCP chính thức chưa có. Không chính thức; CDP tiếp cận phiên đăng nhập, cần audit exact pin/manifest/scripts trước cài |
| [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp) | Screener/technical analysis/backtest, self-host hoặc hosted TradingMCP; MIT | Chưa nhập: trùng nhiều capability và cần xác minh data entitlement, endpoint/data semantics/backtest assumptions. Không nhầm hosted service với official TradingView |
| [Qoyyuum/mcp-metatrader5-server](https://github.com/Qoyyuum/mcp-metatrader5-server) | MT5 market/account/history và trade operations; MIT | Không nhập: project có adapter/risk boundary; một MCP khác có thể tạo đường OrderSend và lifecycle terminal thứ hai |
| [vincentwongso/mt5-trading-mcp](https://github.com/vincentwongso/mt5-trading-mcp) | Read/trade tools, consent/audit layer, screenshot EA; docs có nativeWindows/Linux deployment | Tham khảo kiến trúc, chưa chọn/cài hoặc audit đầy đủ license/source. Consent layer của package không tự tương đương grant project |
| [EarnForex PositionSizer](https://github.com/EarnForex/PositionSizer) | Tính lot/risk/commission và thực thi qua EA; Apache2.0 | Tham chiếu UX/semi-auto và công thức; không cài một position manager khác khi core đã size/risk |
| [EarnForex Account Protector](https://github.com/EarnForex/Account-Protector) | Emergency closing và dừng autotrading; Apache2.0 | Tham chiếu failure modes. Không cài guard đóng lệnh cạnh tranh runner; quyền source license không chứng minh được The5ers duyệt dùng |

Context7 được dùng để tra docs `/tradesdontlie/tradingview-mcp`, xác nhận CDP
debug port/Pine lifecycle; đây là thư viện cộng đồng, **không** phải docs của
MCP chính thức. Không copy lệnh launch/MSIX workaround vào cấu hình đang chạy.

## Quyền dữ liệu và độ tin cậy

[TradingView policies §3](https://www.tradingview.com/policies/) có hạn chế
non-display/automated trading trên content/market data. MCP chính thức công
bố hỗ trợ phân tích bằng AI, nhưng sự tồn tại MCP/webhook không tự cấp mọi
quyền downstream. Trước dùng feed cho order/risk automation cần xác minh
đúng điều khoản/entitlement; chưa dùng TV làm feed thực thi trong project.
MIT/Apache của wrapper không cấp quyền dữ liệu TradingView hoặc approval quỹ.

Không có authenticated smoke test vì thiếu account/plan. Các claim data fresh,
rate limits và permission phải kiểm tool list/response ở lần kết nối thật;
docs không chứng minh latency, tick completeness hoặc source point-in-time.
MCP beta có rate limit; không dùng truy vấn AI theo tick để thay event stream.

## Thực thi được giao và điều kiện mở tiếp

- Owner giao thực thi các đề xuất research trước: triển khai nghiên cứu quy
  tắc tái hiện được, hướng auto có giám sát, giữ rủi ro và compliance độc lập.
- Thực hiện offline theo [round2](PROP-STRATEGY-ROUND2-20261105.md): hai giả
  thuyết mới dùng execution/cost core hiện có; không thêm engine/MCP thiếu
  consumer, không thay hoặc optimize ba comparator round1 sau outcome.
- Đối chứng semi-auto cần quyết định nhận/bỏ từ owner trước kết quả và một
  replay riêng; chưa có quyết định người thật thì không công bố lợi ích của
  manual filter. Auto-supervised được chọn làm hướng nghiên cứu/vận hành;
  không đồng nghĩa strategy đã qualified hoặc grant broker mới.
- Khi có TVpaid: đối chiếu OAuth/allowlist read-only, kiểm một symbol/calendar
  và freshness bằng consumer thật. Khi có The5ers: ưu tiên MCP chính thức
  chỉ đọc, xác nhận account/program và dữ liệu nguồn. Không đăng ký account
  hoặc trả phí thay owner từ nghiên cứu này.
- Nguồn runtime/kết quả thuộc [receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md),
  scope thuộc [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md).
  Refresh khi có account, nhu cầu Pine/tool gap, thay plan/terms/tools hoặc
  trước cài package; không lặp toàn bộ survey khi chỉ một capability đổi.
