# V10 — storage tầng sâu và atlas F1–F4, khóa ngân sách trước kết quả

Task `dccd7cd7-31ec-4cec-8061-016d50e375c7`. PR88 merged `97a44f2`;
branch `codex/enterprise-alpha-v10`. Một PR mới, không tự merge.
Không broker/paid/Astra/production; giữ Trader pin, VI Dubber WIP và raw/seals.

## Diễn giải bằng chứng

9,8× V9 là warm M1 seek microbenchmark, không toàn engine. Gold S1 là prevday
sweep, không Asian box. Những phép thử đã fail không chứng minh mọi breakout
hoặc đa số ngày không trend. R043 còn cadence/time-fit, concentration, OOS,
floating-path/target-cost gaps; không chỉ weekend/swap. Dương markout không
tự là chiến lược có SL, khả năng Challenge hoặc payout.

Dev mở mới: 2018–2023, hai cụm2018–20/2021–23. Validation2024–13/10/2026
chỉ sau composition freeze. Tất cả đã có prior exposure, **reused historical
validation**, không independent clean OOS. Không giá sau13/10/2026.

## Storage và engineering

Inventory D/E logical bytes/files/folders cấp1/2, không follow reparse;
VI permissions unknown không thành zero. Top15 dùng partitions không chồng
lấn; ghi phần còn lại/root files, kiểm tổng. E chỉ copy của D không đúng:
private research/source ở E có owner/seals riêng. Không mirror purge.
Cho E xuất dry-run +manifest/hash plan bảo vệ `.git`, VI, ai-engine-jobs,
canonical/source data. Chỉ compaction thực khi ownership/refs rõ và archive
roundtrip/hash/restore đạt; giữ failed attempts.

Git repack root/Trader giữ refs/reflogs/unreachable, không prune-now trên
shared worktrees/WIP. fsck/connectivity trước/sau, không xóa worktrees chat khác.
Cold bundle chỉ derivatives/dependencies không CI/plan pins; source/bytes
manifest +restore locator. Không archive whole raw trees chỉ vì tên cũ.

Test baseline1013 IDs; thêm smoke nhỏ <5–10s nếu thực đo đạt; Full CI giữ đủ
base tests và frozen fixtures, optional runtime groups explicit. Song song
theo processes/subsuites, finite2workers, test IDs hợp phải exact bằng serial;
không chia lớp có fixture chung hoặc chạy mutation cùng source.

## Admission / mô hình screen

XAUUSD và EURUSD có QDM cached M1; first admission/export chỉ2017-11–2023.
US500/USDJPY/GBPUSD chỉ chạy nếu local M1/H1 sạch đủ toàn Dev và cost/spec
admitted. Không tải paid/new provider hoặc dựng M1 từ H1 để lấp.
Gold Bid M1 +Ask0,338USD/oz, EUR Bid M1 +Ask1pip là **conditional screen**,
không observed execution quotes. Trước promotion phải native BidAsk admission.

Gold spread+commission0,0007%/side+slip0,20USD/oz/side, swaps SYM−40/−40
và ASYM−45/−5USD/lot/rollover. EUR commission5+slip4USD/lot roundtrip,
swap−40USD/lot/rollover hai chiều declared stress.22UTC weekday, Wed×3.
DAY/24H/48H/FRIDAY đều min next holiday/Friday20:30; không blanket zero carry.
M1 endpoint đầu tiên >=deadline ≤60s, không stale/backfill. Gap/path unknown
không được raw endpoint scanner chứng nhận floatingDD.

## Ma trận cố định: 136 recipes ×4 horizons =544 tests/cost scenario

H1/H4/D1 từ closed Bid M1, giữ exact minute counts; chỉ full H1, full4×H1 H4,
D1≥20H1. Warmup2tháng; không năm reset indicator. Mỗi recipe tối đa1signal/day,
BOTH không side-selection; không grid khác sau outcome. Natural stop dùng
prior ATR(H4,14) hoặc structural levels đã biết, không nới để vượt cost gate.

- **F1:24 recipes/asset.** H4 Donchian N10/20/40 hoặc D1 N5/10/20, close
  vượt previousN high/low, previous close chưa vượt previousN tương ứng;
  impulse abs(close−open)/ATR_H4 trước nến ≥0 hoặc0,5; SL close∓1/2ATR_H4.
- **F2:8/asset.** H4 close/SMA20 hoặc40 cùng slope3bar; H1 có2/4bar
  pullback ngược chiều (ít nhất1bar) và latest H1 đóng vượt high/low H1 trước
  theo bias. NaturalSL extreme4/8H1 +0,1priorATR_H4.
- **F3:12/asset.** NR7/14 previous completed D1 (range bằng min rollingN),
  H4 close phá previous D1 high/low (4recipes với ATRstop1/2); hoặc H4
  BB width20 (4std/mean) percentile trên60/120prior widths ≤10%/15% tại
  previous H4, latest close phá prior20bar high/low (8recipes), ATRstop1/2.
- **F4:48 Gold only.** H1 quyết định13/14/15/16UTC, directional body
  ≥0,5/1priorH1ATR; ALL hoặc first2tradingdays/week hoặc first/last2tradingdays
  của month theo weekdaycalendar (không tìm lastdata retrospectively).
  ATR_H4stop1/2. US500 cùng họ chỉ nếu source admission đủ. Không F4 FX.

Horizons: DAY20:30,24H,48H,FRIDAY(đóng trước next long-break). TP/trailing/
conditional loser-close **chưa search**; chỉ Stage0 fixed horizons. Không
tự đổi exit để biến exact model mới thành R043 tái hiện.

## Gates và statistical selection

Đo all raw markouts trước lọc và cohort admission15%; báo cả cost12%.
Core gate: raw/admitted clusterNetR>0 ở cả hai cụm, ≥4/6năm net>0, retain≥60%
mỗi cụm, medianF/medianSL≤15%, admitted≥20/year trung bình mỗi cụm (satellite)
và endpoint100%; signal counts/dependence giữ rõ. Không chọn snapshot filter
hậu nghiệm. Stage0 là multiple-trial discovery, không edge certificate.

Daily-summed raw netR có zeros ngày không signal, HAC lag5 t-stat, one-sided
normal-approx p; Holm across toàn544fixedtests (familywise5%, conservative under
dependence). Deflated-Sharpe diagnostic uses expected max Sharpe (all trials),
skew/kurtosis/effectiveN from HAC; ghi approximation, không exact iid validity.
Statistical gate adjustedp≤0,05 và DSRproxy≥0,95; không chỉ rank meanPnL.
Hai fees là stressviews cùng thử nghiệm, không alpha độc lập. Global trials
trước V10 không đầy đủ, không claim correction xóa toàn bộ selectionbias.

Top15 kể cả fail, rank minclusterNetR/year rồi totalNetR; không gọi “winner”
nếu gate fail. Chỉ đủ Stage0 mới SL-active fixedrisk150, noTP, sameexit,
hai M1 orders, quantitygrid/cost/nativepath/annualaccount checks. Stage1 phải
giữclusterpositive/4positiveyears/retention và buffer daily<2,5%,static<6,5%.
Chọn tối đa1/họ, không nhiều horizons cùng entry; equalrisk sharedbudget,
correlation diagnostic trước compositioncommit. Không đủ thì validation/
portfolio9year lifecycle N/A/canceled, không ghép nhánh âm.

## Kiểm chứng / bàn giao

Scalar/Fraction endpoint/cost/rounding oracle không gọi producer helper,
causal prefix +same signals, Friday/holiday/carry, pricefence, rank/holm/
HAC fixtures, both assets. Sameimplementer khác arithmetic, không independent
person review. Benchmarks cùng output/scope,16alternatingpairs where bounded;
scan wall time riêng I/O/statistics, report configs×years/sec, no promise.
MD/compactJSON/top15/decision, private matrices/receipts, context/index,
fulltestmatrix, PR dự kiến89 3CI đúngHEAD, không tự merge.
