# Hướng tiếp sau Tokyo: tách biến động chung và áp lực giá riêng

**Đã rà: tạm gác triển khai stock-residual; chưa tải fullhistory/PnL.** Đã
đọc method bổ sung, reuse fixture và kiểm program; kết quả ở dưới. Bước hiện
tại chuyển sang [FOMC price-conditioned protocol](US500-FOMC-PRICE-MOMENTUM-PROTOCOL-20261109.md),
sau [surprise-source review](FOMC-SURPRISE-SOURCE-RESULTS-20261109.md).

09/11/2026, sau[R085 không đạt](USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md).
Chỉ method/source admission, **chưa recipe/PnL/candidate mới**. Liên quan
R034factor-residual, không tự chứng minh cơ hội độc lập hay đổi verdict
R035pair-formation. Không quay lại R065 để tìm archive cứu bản đã gác:
[bounds](NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md) đã không ưu tiên exactrecipe.

| Primary source | Đã đọc hôm nay | Ý nghĩa / giới hạn |
|---|---|---|
| [Avellaneda/Lee, author NYU PDF](https://math.nyu.edu/~avellane/AvellanedaLeeStatArb20090616.pdf), [author index](https://math.nyu.edu/inmemoriam/avellaneda/Papers.html) | Primary search-served abstract và author page; directPDFtimeout, chưa fullmethod | Tách residual bằng PCA/sectorETF rồi contrarian trên universe USstocks; performance thay đổi theo giai đoạn. Không paper FX/CFDindex hoặc license để copy code |
| [NYFed StaffReport513](https://www.newyorkfed.org/research/staff_reports/sr513.html) | Official abstract mở được | Tách reversal thành các thành phần; residual gắn thay đổi giá ngoài fundamentals, liquidity/sentiment. Cần dữ liệu phân loại/news phù hợp; không suy mọi rawprice dump đều nên mua ngược |
| [Brogaard/Han/Kim, Intraday Price Pressures](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4731947) | Primary search-served abstract ghi revision02/10/2026; direct403 | Residual-reversal của S&P500stock30min; chưa full specification/costs, không nhận advertisedreturn làm bằng chứng cho project |

Đây là lý do khảo sát cơ chế khác: giao dịch phần lệch riêng sau khi tách
chuyển động thị trường, thay vì tiếp tục chọn giờ cho unconditionalfixing.
Chưa có bằng chứng USstocks chuyển được sang EURUSD hoặc cặpNAS/US500.
Một chỉ số không là stockuniverse; factor-neutral không tự là risk-free.

## Checklist admission đã rà

1. Đọc fullmethod primary nếu truy cập thông thường được; giữ403/timeout,
   không vượt WAF/auth hoặc dùng abstract để bịa window/threshold/regression.
2. Kiểm dữ liệu hợp pháp hiện có: universe/PITmembership, delisted/splits/
   dividends khi liên quan, session/holiday/BidAsk/known-at, commonfactor và
   residual không dùng tương lai. Chưa bulkfetch/returns.
3. Đối chiếu assetavailability/costs/short/contract của program đích từ
   officialterms; không mặc định FTMO/The5ers cùng hỗ trợ individualstocks.
   Không mua feed hoặc mở account.
4. Chỉ khi method+data+cost+horizon có đường hợp lý mới freeze một own
   adaptation và fixtures trước outcomes. Thiếu thì deferred/chuyển mechanism,
   không lách bằng proxy/index hoặc factorindexPnL.

Reuse skills và sourcecatalogue hiện có; không cài package/MCP/framework/
manager hoặc mở broker/holdout2025+. Catalogue vẫn85/58; Goalactive/chưa đạt.

## Delta sau đọc method và kiểm nguồn

- NYU authorindex dẫn tới [bản11/07/2008](https://math.nyu.edu/inmemoriam/avellaneda/AvellanedaLeeStatArb071108.pdf),
  khác bảnJune2009 ban đầu timeout. Đã đọc §§2–5 và appendix: adjustedprices,
  stock/ETFhedge,OUwindow60days; detail close-short0,75 khác summary0,5 và
  close-long0,5. Sameclose signal/fill trong paper chưa là causal executable
  fill của project. Không copy headlineperformance hoặc đổi intraday/index
  thành replication. Chi tiết/version phải pin trước implementation.
- NYFed513 đã đọc decomposition/inputs: monthly sector/factor và analyst
  forecast revisions; rawM1price đơn lẻ không thay các inputs đó. Chưa full
  replication hoặc analyst/PIT-universe data contract.
- [Stockfixture cũ](STOCK-INFORMATION-SOURCE-RESULTS-20261109.md) exact3accepted
  artifact hashes còn khớp; không refetch. Hai stocks/một ngày không chứng
  minh corporateactions/universe lịch sử hoặc exchange-share volume.
- [The5ers FAQ](https://the5ers.com/faqs/available-stocks-for-trading/) đọc lại:
  stocks Bootcamp/ProGrowth,commission0,1%/side; không tự đổi HighStakes.
  [FTMO Marchlisting](https://ftmo.com/en/blog/trading-updates/trading-update-12-mar-2026/)
  xác nhận stockCFDgroup, không chứng minh currentexacttickers/specs/fees.
  Symbols text không trả stockrows; localbrowser ERR_CONNECTION_CLOSED rồi
  toolpolicy chặn đọc data:errorpage. Không đổi network/proxy/security hoặc
  lấy thirdpartyfee làm primarytruth; giữ gap này.

Private `execution-v1/residual-method-sources-v1/` giữ personal-reference
PDFs và receipts; không redistribute. NYU47pagesSHA
`c40eb1ad5af07234ad2cbcde491e2e781470b44c44b37c7f79b7cefc7106a97d`;
NYFed45pagesSHA `4c8636a52b940acb4ec09649cefad88032b838e08935981761b75e3e3d85f85f`.
HaiHTMLcaptures bằng localHTTP failSSL/timeout; webreader chính thức đọc được
như nguồn ở trên, không bịa localcapture thành công. Giữ failure receipt.

**Vì sao gác:** method phụ thuộc stockuniverse/hedges và inputs chưa có;
targetprogram/costs chưa đủ, không phải numericalnegative hoặc bác bỏ edge.
R034 vẫn chưa implement, không thêm catalogue record. Không thay stock bằng
FX/index để chạy cho có kết quả. Đã rà thêm literature monetarymomentum;
nguồn surprise lịch sử được kiểm riêng, rồi chọn causalprice-only thử trước.
