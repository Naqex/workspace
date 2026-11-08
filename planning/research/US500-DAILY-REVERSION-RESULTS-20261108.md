# Daily cash reversion — tiếp campaign, chưa có ứng viên challenge

**Nguồn hiện hành:** [IBS02source-only/results](IBS02-EXPLICIT-SOURCE-RESULTS-20261108.md)
đã kiểm3books/9scenarios, giữ originalrule/cost/risk; không đạt oldpriority.
RSI3 thuộc [longsource-onlyreview](INDEX-LONG-EXPLICIT-RESULTS-20261108.md).
Bảng filtered bên dưới giữ lịch sử; số IBS02 trùng source-only trong14fields
đã so, không có nghĩa filteredinput được chứng nhận tương đương.

**Input correction08/11:** kết quả bảng này làfilteredsource lần đầu. Loader
default bỏvolume0 được phát hiện và [đăng ký sửa](INDEX-UNFILTERED-SOURCE-CORRECTION-20261108.md);
canonicalrerun giữrules/cost/risk đã xong. Không dùngoldtable đểreject/promote
hiện hành; giữ sourceattempt nhằmtruyvết,không sửaoldnumericartifact.

[Protocol trước outcome](US500-DAILY-REVERSION-20261108.md). Hai versions cùng
họ, không independentedges. 6annualstudies/12numericrows +6nullcontrols,
completed74,39s tổng gồmverifiedinputloads/exports; không broker/model calls.

| Version | Năm | Net chuẩn / stress USD, vốn10k |
|---|---|---:|
| IBS02 hold | 2022 | +52,37 / +34,41 |
| IBS02 hold | 2023 | −49,08 / −63,68 |
| IBS02 hold | 2024 | +37,06 / +20,37 |
| RSI3 +IBS05 | 2022 | −7,25 / −20,74 |
| RSI3 +IBS05 | 2023 | +11,23 / +4,75 |
| RSI3 +IBS05 | 2024 | +48,53 / +39,93 |

RSI2024 còn1position mỗicostscenariocófloating; khôngforceclose đểlàmđẹp.
Cả2không đạt ưu tiên mọiannualyearpositive; không đề xuất challenge. MẫuRSI
19/8/10entries rất nhỏ; không chọn lại threshold/funding/risk sau outcome.
Không hardreject toànfamily từ3years hoặc gọi đây là cleanOOS.

Shared `index_m1_book.py` owns modeledqueue/oneposition/SL/calendarfunding,
reusefinancialprimitives. `index_daily_reversion.py` chỉ tạo causaldailyplans;
extendedM1data giữnguyên. Everyovernightgap bịflagged vìchưa brokercontract
đểphân biệtexpectedclosure/feedloss; không biến thành certifiedpropDD.

Hậu kiểm thêm exclusive-end funding choopenbook quaweekend, giữ stalequote
mark vàkhôngforceliquidate. 7newfocusedtests +7existingnoise/orchestrationtests
và4existingreviewertests đạt theoaffectedchanges. Actualopenbook2024 được chạy
lạiriêng ở`rsi-ibs-2024-end-horizon-v2`: cash/floating/trades/decisions/funding/
positions/queue/gaps byte/valueexact nhưv1, chỉthêmhorizonmetadata. Closedbooks
cũ giữsourcepin,không rerun khôngcầnthiết. `review_index_noise.py` được mởrộng
checkerDecimal riêng gồm đủcalendarfundingevents vàactualopenmark, không chỉ
tựđốisoáttổng đã khai. Cả6books đã kiểm đủ; sameagentcheck,khôngindependent
model/human signoff. Missing-funded-day tamper cũng bịchặn ởsyntheticfixture.

Private: `execution-v1/us500-daily-reversion-v1`, completedrows/results,
source/protocol/calendarsnapshots,stdout/stderr/events/progress,arithmetic-fill
reviews. Các sourceversion old/new được giữ, không tự nâng chứngnhận toànapp.

## Việc đã tiếp tục, không dừng ở checkpoint

ProviderD1history fetched23,66s,3671bars/side2011-09-18→2024-12-31; nhưng
[rangeoracle](INDEX-DAILY-RANGE-ORACLE-20261108.md) xác nhậnH1/D1low loại mất
134ticks trong minute18/10/2022. M1OHLC khớp; chưa chấpnhậnD1/H1rangeschoPnL.
Đã cóquote-to-barnegativecontrol đểngăn lẫnchecksum/schema vớimarketcorrectness.

[Lịch sử M1 tiếp theo](US500-VERIFIED-LONG-HISTORY-PREPARATION-20261108.md)
dùngcacheverified/adoption,khôngfetch lại2022–24. V1failed sauBidQ4/2012;
manualAskdiagnostic cùngscope trả22968rows/92HTTP200,fullschema/grid/orderđạt,
chưa tái hiện được lỗi cũ nên khôngclaim đãfixprovider. V2adoptcảhai phần và
tiếpremaining72parts, nativeCacheManager flushrawresponses incrementally và
safeHTTPfailurecontext; không auth/WAF/sourcebypass hoặc retryloop.

C1/C2 chưa hoàn tất. Checkpoint chỉlưu trạngthái; tiếp theo làdataquality +
freeze các cơ chế dài hơn/clockbasis mới trước outcomes,không ép winner.
