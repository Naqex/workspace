# Dòng tiền theo phiên địa phương: hai phép thử mới

Đăng ký trước outcome cho chiến dịch [C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Đây là price/cost components, chưa phải bot hoặc giấy phép giao dịch.

## Căn cứ và quyết định trước đo

Đã đọc lại toàn phần method §2.1–2.3, Table 1/2 của
[SNB 2011-04](https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2011/working_paper_2011_04/publications0_en/working_paper_2011_04.n.pdf)
ngày 08/11/2026; PDF lần này truy cập được. Paper nghiên cứu dòng tiền bán
nội tệ trong giờ địa phương. Table 1 dùng Mỹ 08–16, Australia 10–16 local;
Table 2 có GBPUSD và AUDUSD. Paper cũng cho thấy costs có thể xóa lợi nhuận
của hai cặp này; **không lấy statistical mid-return làm bằng chứng có lời**.
Sample EBS 1997–2007, thị phần hai cặp nhỏ, khác feed/era/costs của project.
Chỉ diễn giải phương pháp; không nhập/redistribute paper data hoặc code.

Hai hướng được cố định bởi cơ chế, không chọn opposite controls vừa xem ở
[R057/R058](TWO-FX-PRE-ECB-COMPONENT-RESULTS-20261108.md). R059 đổi cả clock
và hypothesis sang bán USD trong phiên Mỹ; R060 bán AUD trong phiên Australia.
Chúng vẫn cùng họ local-flow, không phải hai edge độc lập. R023 BUY EURUSD
08–16NY đã thất bại và không chạy lại. R058 SELL AUD trước ECB vẫn bị gác.

| ID | Recipe primary | Câu hỏi bác bỏ được |
|---|---|---|
| R059 | BUY GBPUSD 08:00 → 16:00 America/New_York | Dòng bán USD tại phiên Mỹ có tồn tại sau chi phí khai báo trên feed hiện có không? |
| R060 | SELL AUDUSD 10:00 → 16:00 Australia/Sydney | Dòng bán AUD tại phiên Australia có tồn tại sau chi phí, khác clock trước ECB không? |

Không scan giờ, news/calendar filter, SL grid hoặc đảo side nếu thất bại.
Opposite side ở đúng clock chỉ là falsification context, không thành winner.

## Input và semantics cố định

- Tất cả weekdays của **ngày địa phương** trong 2010–2024, giữ ngày lễ/thiếu
  quote trong denominator. Đây là historical development đã có exposure,
  **clean OOS=false**. Không mở 2025+.
- Reuse đúng 60 source books đã seal và review tại `fx-h1-history-v3` của
  campaign private root; không download hoặc sửa raw/source. Global source
  admission vẫn false: AUD Ask tháng 01/2013 thiếu, có crossed source fields.
- Chỉ dùng Open tại đúng UTC hour của target. IANA zones xử lý DST; không dùng
  offset cố định. Open thuộc interval `[hour,hour+1h)`, chưa actual quote time
  hay joint-tick executable price. High/Low/Close không dùng để quyết định/fill.
- Sydney 10:00 trong DST có thể nằm ở ngày/năm UTC trước đó. Tra source theo
  UTC timestamp trên các năm **đã có**; không giới hạn vào file cùng local year,
  không tải năm 2009 bù boundary. Endpoint ngoài coverage giữ missing.
- Entry cần cả Bid/Ask dương, đúng grid và Ask≥Bid. Thiếu/crossed entry không
  eligible. Thiếu/crossed exit vẫn entry-eligible nhưng unresolved: không
  lọc entry dựa vào tương lai, không PnL=0 hoặc tự dời thời gian thoát.
- BUY tại Ask, thoát Bid; SELL tại Bid, thoát Ask. Contract 100k, 1 standard lot,
  pip=0,0001. Commission 5 USD roundtrip; slip reference=0 và stress=0,00002
  mỗi side. BidAsk embedded. Đây là costs khai báo, chưa historical target
  broker costs. Không funding trong component cùng phiên này.
- Không SL/TP/sizing/margin/account equity/prop drawdown/phase resets. Tổng pip
  trên cơ hội per lot không là return trên 10k hoặc risk 25USD/trade.

## Metrics và retention khóa trước kết quả

Mỗi asset/year/primary hoặc control/reference hoặc stress giữ planned,
entry-eligible, resolved/unavailable, net pip sum/mean/min/max, win/loss/zero
và top5 positive share. Không gọi các năm/trades/legs độc lập.

Giữ heuristic của lượt trước: primary stress total>0, ít nhất **10/15 năm
dương**, mỗi năm≥200 resolved, và **cả bốn blocks 2010–12 / 2013–15 / 2016–18 /
2019–24 dương**. Đây là research-priority gate, không statistical chứng nhận.
Fail thì gác exact recipe; pass chỉ đủ xét một risk-wrapper đã đăng ký riêng.
Giữ missing/concentration và selection exposure trong kết luận, không chỉ sum.

## Execution, review và hậu kiểm

Runner riêng `run-local-flow-two-fx-v1.py`, reviewer
`check-local-flow-two-fx-v1.py` tại campaign root. Reuse `price_return` và
native cost core, không thêm engine/service. Snapshot/pin protocol, hai scripts,
60 books, source-review/quality/rawbindings, helpers/runtime và config trước PnL.

Preflight trước outcomes: flat BUY/SELL/chi phí, missing/crossed field-role,
NY DST, Sydney DST/UTC previous-year, thiếu previous-year input và eligible
entry có missing future exit. Runtime report ghi checks đã qua.

Output mới `execution-v1/local-flow-two-fx-v1`, 1 writer, deadline 120s,
progress/events/PID/CANCEL/failure. Không retry/overwrite old attempts.
Review deadline 120s: code khác cho calendar và Fraction arithmetic, kiểm mọi
row/metadata/summary/retention và mutations giá, side, clock, false tick claim,
net, future exit filtering, authority. Cùng agent/provider không là independent
human/model audit hoặc full-tick replication. Không reuse cost implementation
trong numeric oracle của reviewer.

Ghi timing/status, bugs và quyết định tại results owner. Không rerun component
không đổi, không thêm GPU/Rust/vectorDB nếu không có bottleneck. Nếu retained,
bước tiếp cần SL/risk chung toàn account, causal ticks/path, prop rules hiện
hành, time-fit, OOS, forward và owner handover trước challenge. Goal vẫn active.
