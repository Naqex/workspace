# V8 — hai cải tiến Gold A và ba sleeve đã có

Task `690031eb-d490-465f-84f1-7b372e0902b8`. PR86 đã merge `c99fa7e`;
branch `codex/prop-gold-v8`. Không broker, provider trả phí, Astra/subagent,
giá sau13/10/2026 hoặc sửa V7. Giữ VI Dubber WIP và Trader pin.

## Phạm vi và exposure

Chỉ thiết kế/chọn trên2022–2023. Khóa composition bằng commit trước mọi phép
đánh giá mới2024–2026 và trước mở2018–2021. Một release backward duy nhất,
có thể có producer/oracle và hai thứ tự M1 trong cùng release; không chọn lại
sau outcome. Warmup backward01/11/2017–31/12/2017 chỉ mở sau release.

**Không gọi2018–2021 là pristine ở cấp dự án:** Gold R043 đã dùng2010–2024;
`GOLD-ML-SL-LABELS-PROTOCOL-20261109.md` dùng2018/2021; nhánh H1 có seed
Nov2021 và V3 có warmup từJan2021. Chỉ có thể gọi là backward historical
validation của cấu hình V8 đã khóa, có ghi prior exposure; không là forward OOS.
Trong Phase1–2 không đọc cả warmup2021 mới: reuse tín hiệu/ATR đã xuất2022–23
và chỉ seek price partitions2022–23 trong cache. Timestamp inventory/hash
manifest không là đọc giá hay chạy tín hiệu holdout.

SL28,21/58,85 khác Asian range23,33/46,06USD/oz. Phình stop là observation;
“sóng đã chạy xong” chưa được chứng minh. N1/N2 là strategy trials mới,
không phải sửa bug được bảo đảm làm PnL tốt hơn.

## Ngân sách cố định trước outcome

Baseline A giữ entry H1/H4, BOTH, Natural SL toàn hộp+0,1ATR_H1, no hard TP,
48giờ lịch/Friday/holiday flat. Hai candidates, không grid/kết hợp thứ ba:

- **N1:** Asian range / median20 Asian ranges của các ngày hoàn chỉnh trước
  ngày quyết định. k=P85 (linear percentile) của ratios trên tất cả ngày
  đủ context trong2022–23, không fit theo PnL. Giữ stop baseline.
- **N2:** stop theo Low/High của nến H1 breakout+0,1ATR_H1 trước nến; chỉ dùng
  khi gần hơn stop toàn hộp, nếu không giữ stop baseline. Không cắt stop bằng
  số USD tùy ý, không mid-box/ATR variant khác, không thêm compression filter.
- Cả N1/N2 chỉ nhận **natural SL ≤25USD/oz** để budget125 đạt ít nhất5oz
  (0,05lot), và stress spread+commission+slip / SL ≤12%. Ngoài dải thì skip,
  không sửa level để lách gate. Bộ lọc này không bảo đảm giữ đủ cadence.
- Context median20 bắt đầu01/01/2022, không reset qua năm; backward bắt
  đầu01/01/2018. Chưa đủ20ngày thì abstain, không dùng giá2021 trong thiết kế.
- Đánh giá125/150/200USD trên cùng trade set: mỗi năm/model phải cùng dấu
  dương; chênh mean R/trade giữa budgets ≤0,10. Ghi utilization/error distribution,
  không tuyên bố R bất biến tuyệt đối vì lot và cents vẫn rời rạc.

Core promotion Dev: net>0 ở cả2022/23 dưới cả hai swaps và ba budgets,
≥40lệnh/năm, retention≥50% baseline raw, cost rejects≤50% raw và
median friction/median stop≤12%. Nếu cả hai đạt chọn max(min annual SYM
NetR tại150USD), tie N1. Nếu không ai đạt thì normalized **NO_GO**; giữ
baseline làm control, không cưỡng ép một winner.

Ba sleeve duy nhất: `XAUUSD.SWEEP.PREVDAY.LONDON.{DAY,24H,48H}`. Giữ
entry sweep Low/High ngày trước, nến H1 London08–11UTC, stop extreme H1
+0,1ATR; không thêm biến thể stop khác. Chỉ nhận stressF/SL≤15%; báo cả
12% như diagnostic, không chọn threshold theo kết quả. Gates: endpoint
coverage100%, retain≥50% raw từng năm, medianF/medianSL≤15%, net>0 cả
hai năm/hai swaps; ≥20lệnh/năm. Cùng entry, chỉ chọn tối đa một horizon,
max(min annual SYM NetR), tie DAY→24H→48H. Không coi ba horizon là ba alpha.

Composition chỉ thêm sleeve nếu core mới đạt và sleeve đạt. Ghép equal
per-trade V4 budget200/175/125USD P1/P2/Funded; shared cap800/reserve46k,
throttle150/90 tại48k/47k, daily realized halt1k, V6 harvester14ngày/80:20,
zero admin delay proxy. Core ưu tiên khi trùng asset/decision. Nếu không có
sleeve đủ cổng thì portfolio alias core, không cộng lại cùng tín hiệu.
Nếu core NO_GO, full/backward chỉ chạy baseline control; các cột mới N/A,
không đốt holdout để cứu trial đã fail Dev.

## Đường giá, lịch, cuối mẫu

Reuse native Gold paired tick hours hiện có; giờ thiếu dùng Bid M1 cache
với Ask proxy0,338USD/oz, hai orders O-L-H-C/O-H-L-C (0/20s/40s/59,999s).
Tất cả paths ghi source-kind; không gọi fallback M1 là observed ticks.
V7 baseline hiện có giữ riêng; baseline trên source bổ sung có parity check,
không giấu delta nếu dữ liệu realization khác. Không tải nguồn mới.
Historical M1 đọc bằng seek partition; không parse whole cache price arrays.

Lịch2022–26 giữ V7. Backward calendar dùng US metals holiday-date conservative
guards, Good Friday closed/eve20:28, early holidays16:58, Christmas/NewYear
closed và eve16:58, ordinary Friday20:30. Dates và status phải khóa trước
giá backward; không suy giờ thoát từ PnL hoặc tùy tiện dùng last stale quote.
Chưa có giờ FTMO lịch sử thì unverified guard, không “certified calendar”.
Endpoint thiếu vẫn unknown và không promote. Missing minute/path không tự
thành zero exposure. Mẫu kết thúc31/12/2021 hoặc13/10/2026 là observation
boundary; không giả market exit cuối mẫu.

## Bàn giao

Freeze code/protocol/k/composition và nguồn trước Phase3; full2022–26 là
post-holdout diagnostic. 57mốc tháng cũ+mới, backward48mốc tháng; standalone
Funded Jan1 mỗi năm nối cuối kỳ. Hai fee models và hai OHLC orders, annual
reference150USD plus sizing invariance125/150/200. Nếu Dev NO_GO thì chỉ
baseline controls, ghi canceled columns thay vì dựng danh mục không đủ gate.

Đối soát hữu tỷ/cash-posted độc lập implementation cho mọi sổ, cùng
implementer không independent person/model review. Full unit matrix qua
môi trường có sẵn; tests clock/fence/causality/stop/rounding/collision/source
và hand calculation. ReportMD+JSON, context/index, private ledgers/attempts,
commit/push và một PR dự kiến87,3CI xanh đúngHEAD; không tự merge PR mới.
