# Hướng tiếp: thông tin cả ngày → cuối phiên, chưa outcomes mới

## Primary evidence và giới hạn

Đọc 09/11/2026 [Baltussen/Da/Lammers/Martens, JFE 2021](https://academicweb.nd.edu/~zda/intramom.pdf),
các định nghĩa/data ở §1/2, §4.3, Table 6/12 và Appendix A1. `rROD` đo previous close → trước nửa
giờ cuối; khác `rONFH` dừng ở đầu phiên. Phương pháp dùng dấu rROD cho chiều
giao dịch cuối phiên. S&P/NASDAQ theo cash hours 09:30–16:00. Paper cảnh báo
chi phí có thể xóa lợi thế; không lấy headline Sharpe làm net CFD proof.

Đây là method admission, chưa protocol economic mới hoặc preregistered outcome.
Không import code/data của paper; không mua futures/options/OptionMetrics data.
Chưa audit full appendix hoặc tái hiện pooled regressions; không nói đã đo
gamma exposure chỉ từ price. Nguồn tác giả truy cập được, không bypass paywall.

## Vì sao khác các exact recipes đã gác?

- R074/R075: gap overnight → **đầu phiên**, chiều contra, entry 09:32.
- R051/R064: return tới **10:00** → cuối phiên; bản cũ còn readiness/ATR constraints.
- Câu hỏi mới: thông tin tới **15:30** → cuối phiên, cùng chiều. Đây là đổi
  tập thông tin theo cơ chế hedging, không chỉ chỉnh giờ entry hoặc đảo control.
  Vẫn related momentum family và đã biết nhiều negatives, không independent edge.

Own adaptation có thể dùng previous cash BidClose → 15:29 BidClose, known
15:30; decision 15:30, fill 15:31, exit 15:59. Những mốc này là đề xuất trước
registration, chưa outcome. Tận dụng sealed US500/NASDAQ M1/calendar hiện có,
costs/BidAsk/interval semantics và source snapshots đã review; không cần nguồn
thị trường mới hoặc download lại để kiểm một component hữu hạn.

Trước numeric cần khóa candidate/assets, primary và counterfactual/control,
fee/latency/coverage gate và denominator. Control first-half chỉ có nghĩa khi
so trên mask/clock/cost phù hợp; không lấy parent account PnL khác SL/ATR làm
benchmark trực tiếp. Missing late signal vẫn unavailable, không carried price.
Không nhìn full current day/close/quality để quyết định; 2025+ vẫn đóng.

Nếu price component sống qua costs và hai development regimes mới đáng chốt
wrapper/risk/prop/OOS/prospective checks. Không bỏ bước này bằng statistical
metric hoặc coi published mechanism là bảo đảm challenge/payout.

## Nhánh khảo sát khác, chưa chọn làm numeric

[Wen/Indriawan/Lien/Xu 2023, university record](https://digital.library.adelaide.edu.au/items/13d367dd-06b2-4eca-8d21-4dfeb46c4f55)
có abstract về intraday oil/EIA; landing không extract full text trong lần mở.
[Wen/Gong/Ma/Xu 2021](https://www.sciencedirect.com/science/article/pii/S0264999319310417)
primary search-served abstract dùng USO ETF. Chưa full method, CFD/futures/ETF
mapping và announcement/calendar/target-cost admission; không giả một oil CFD
replicate USO hoặc lấy volume quote làm exchange volume. Gác mở bulk oil data
ở lượt này, ưu tiên câu hỏi có reviewed source sẵn. Không numerical oil outcome.
