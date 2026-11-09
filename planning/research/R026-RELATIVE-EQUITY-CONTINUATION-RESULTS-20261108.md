# R026 không giữ được lợi thế khi mở rộng lịch sử

**Gác exact price-proxy v1; không viết bot/SL để cứu kết quả này.** Thực hiện
[continuation đã đăng ký](R026-RELATIVE-EQUITY-CONTINUATION-20261108.md), giữ
signals/hours/costs/missingpolicy. Bốn năm mới chỉ1/4stresspositive và tổng âm,
không đạt tiêu chí≥3/4positive+aggregatepositive. Goal mới vẫn active.

## Kết quả và quyết định

| Năm | Phí chuẩn,pip | Phí cao,pip | Đủ/planned | Vai trò |
|---|---:|---:|---:|---|
|2019|+21,6|+16,8|12/12|Baseline đã giữ, không rerun|
|2020|+55,9|+51,1|12/12|Mở rộng|
|2021|−306,1|−310,9|12/12|Mở rộng|
|2022|+144,1|+140,1|10/12|Baseline đã giữ, không rerun|
|2023|−54,5|−58,5|10/12|Mở rộng|
|2024|−62,2|−66,2|10/12|Mở rộng|

Đơn vị vẫn là costed price component, chưa%tài khoản/SL/sizing. Tổng6năm
stress−227,6pip trên66/72cơ hội đủ dữ liệu;6missingmonths giữ nguyên. Không
coi hai năm đầu đẹp là edge, đảo hướng hoặc gác riêng năm2021. Năm2021 có
11/12tháng lỗ, không chỉ một outlier. R026 vẫn là adaptation hai proxy, không
kết luận bác bỏ paper/mọi equityhedging strategy hoặc strategy không tồn tại.

Source thiếu mới:07/2023,09/2023 thiếu ETFfirstclose;11/2024 thiếu ETFpenultimate;
12/2024 thiếu EURUSDfirstclose. Reviewer kiểm nguồn thực của **mọi** missing
event, không tin riêng nhãn producer. Không carry/fill hoặc di chuyển endpoint.

## C2 và hậu kiểm kỹ thuật

-144dayfixtures/672instrument-side exports được bind raw/native/schema/grid/
  clocks/seals/producer/protocol;6rawcache hits, giữ nguồn/hash/exposure.
- Reviewer riêng Fraction/raw-delta kiểm **768source-presence checks** trên
  tất cả48months,704retained endpointprices,352financialcases,32summarycensus.
  Cùng agent/separate implementation, không independent feed/human/model.
-8mutations reject:phí,hướng,futureknown-at,missingmonth,sourceprice,
  falsequalification,**falsemissingness**,missingsummary. Không nâng authority.
- Bổ sung reducer `registered_priority` nhận explicit yearset/coverage/positive
  yearcount; chặn dùng nhầm kết luận2years cho4years.7focused tests đạt, gồm
  cases3/4positive nhưng cumulative âm,2/4positive,lowcoverage,missing/duplicate
  year/NaN và2025. Scope checks mới trước outcomes, không thay thresholds.
- AST4policyfunctions `positive/month_schedule/relative_signal/costed_views`
  exact với baseline snapshot; code mới chỉ thêm triage reducer. Historical
  source hashes cũ khác current file không xóa evidence của frozen snapshot.
- Presence-only preflight trên2020Jan kiểm16raw endpoints và2negativecases
  trước numeric; economicoutcomes không được đọc bởi preflight này.

| Phase thực đo | Wallseconds | Giới hạn |
|---|---:|---|
| Source672parts |844,432|666newURLs,6cachehits,1helpertransientevent; serialized source fetch |
| Admission144fixtures |22,258|Bao gồm full raw/native binding |
| Numeric+finalbindings |7,365|48months×4views×2costs,không broker/account simulation |
| Producer tổng |29,638;CPU27,531|Đã gồm admission và numeric; không cộng trùng |
| Separate review+8mutations |3,416|Không rerun economics |

Pipeline thu→review≈877,487s,14phút37giây; không tính research/code/agenttime.
Networkwait vẫn lớn nhất. Không có lý do GPU/Rust cho vài giây arithmetic;
lát mới ưu tiên phương pháp/dữ liệu đã có để tránh network lặp, không bỏ checks.
Mọi workers của lượt này đã terminal, giữ raw/negative/attempts, không cleanup
evidence hoặc chạy lại annualbooks để benchmark.

## Research cập nhật và bước tiếp

Rà hai hướng khác: R010multiasset/volscaledtrend và R033cross-sectional FX
momentum. [AQR2017](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf),
Data/strategypp1–2, dùng nhiều markets, excessreturns,1/3/12month signals và
volatility scaling. Đây khác việc thử một tín hiệu trên EURUSD đơn lẻ; chưa
bằng chứng cùng hiệu quả khi chuyển sang3CFDs/prop. [BIS366abstract](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies)
nêu currency momentum khác carry nhưng chi phí/limits-to-arbitrage quan trọng;
R033 chưa có common multi-FX/funding/universe đủ nên defer numeric.

[R010 source admission](MULTI-ASSET-TREND-DATA-ADMISSION-20261108.md) là bước
kế tiếp: kiểm dữ liệu/causal as-of observation và rủi ro chung, không lặp
R026/624FXcases hoặc giảm financing để tạo winner. Chưa strategy recipe/PnL
mới hoặc holdout/broker. Không kết thúc Goal mới bằng quyết định B cũ.

Source research phụ: [Dukascopy corporateactions](https://www.dukascopy.com/swiss/english/cfd/cfd-corporate-actions/)
xác nhận positions có thể được điều chỉnh, không chứng thực historical ETF
candle adjustmentbasis. Hai JForex IHistory URLs search trả404 khi open;
giữ unknown, không lấy snippet làm certificate. Không đổi loader/fees vì vậy.

Private campaign root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/relative-equity-continuation-data-v1` giữ plan,registration,
preflight,source snapshots/raw/seals/status/events/result; sibling
`relative-equity-continuation-component-v1` giữ source/input-admission/
events/result/review. Source/scripts và hashes nằm trong manifests và
analysis-registration; không sửa baseline dirs.

ResultSHA `78525abdc16af5028f3ba66d9b0f159b948fc72e0dbccb6013d95ec65cbe2bfe`;
reviewSHA `5abb328abce3b4a45c65deeaecf0fd98d9a4f4c567d99cd9181ca4418b3bf9fc`.
C1false,C2partial: source/component financials đã kiểm, chưa economic edge,
nativeprop/SL/sizing,time-fit,genuinelyunseen/prospective hoặc ownerhandover.
