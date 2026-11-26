# Chẩn đoán đà sau phá kênh, trước khi đổi tham số

12/11/2026. Owner giao thực thi lượt chẩn đoán đã đề xuất. Tiếp
[so entry cùng giờ](US500-ENTRY-METHOD-COMPARISON-RESULTS-20261112.md).
**Khóa thiết kế trước diagnostic outcomes mới**, trên2022–2025 đã exposed;
không OOS, không newstrategy/parametergrid, không mở2026 hoặc broker.

## Một câu hỏi và cohort cố định

Giá sau BR01-common14-v1 hoặc RS02-v1 có đi tiếp đủ bù modeledcost không?
Giữ kênh20M15/ATR14Wilder/đệm.10/SL2ATR của savedbooks. Entry lấy đúng các
trade decisions/entry timestamps của reference books; kiểm reference/stress
entrycensus giống nhau trước dùng chung cohort. Không chọn signal theo PnL.
Không coi624+331 là samples độc lập vì cùng parent/phiên và horizon overlap.

## Markout15/30/60phút và decomposition

- Bắt đầu tại modeled entryopen decision+1phút; kết thúc tại M1open entry+h.
  Không stop/timeexit trong **markout**, nên đây không phải backtest exitrule
  mới hoặc lợi nhuận đã có thể thực hiện. Không điều chỉnh giờ/hold/SL/TP.
- Phải có pairedBidAsk mọi phút từ decision tới endpoint, trong cùng cash
  session. Missing giữ unknown; vượt session giữ outofscope, không inventprice,
  tự đóng cuối phiên hay lấy endpoint-only để che gap. Full cohortcounts giữ.
- Benchmark là synthetic midpoint của hai sideM1opens, không observed
  synchronousmidtick. Cho mỗi1unit: signedmidmove − halfspread(entry+exit)
  −2slip = modelednet; slip.25/.75point/fill, commission0 declared scenario.
  Kiểm direct BUY(Bidexit−Askentry)/SELL(Bidentry−Askexit) và bridge riêng.
- Báo points/unit và Rdiagnostic=2×decisionATR, không1Rcash25USD đã thực hiện.
  Tất cả costscenarios cùng path/cohort: revaluation, không native simulation
  đổi costs/size/stop. Không doublecount spread hoặc gắn actualFTMOfee.

## Đối chứng khóa trước outcome

Từ native prepared closedM15, lấy các bars đủ prior20history/positiveATR,
normalcashsession và không có gap đã biết, clock10–15NY; **close nằm trong
priorchannel±.10currentATR**, không dùng futureday để xác nhận nonbreak.
Các control bars không bị chọn theo tương lai sẽ lãi/lỗ hay cả ngày có breakout.

Tại mỗi event, đối chứng là mean markout ở **cùng năm, cùng slotNY, cùng hướng
BUY/SELL trên các ngày khác**, với normalization theo decisionATR của mỗi bar.
Loại eventday khỏi pool; thiếu pool/coverage giữN/A. Control có thể nhiều slot
một ngày: không strategy1trade/day và không cộng chúng thành independenttrades.
Giữ controlcounts/missing, actualevent mean và paired-event-vs-control contrast
riêng; không đổi event sample khi một control thiếu.

Đây là retrospective clock-matched comparison, **không randomized causalproof**;
chưa matching volatility/regime/news. Pool được tổng hợp sau năm, không bot có
thể biết poolmean ở thời điểm entry. Không dùng meancontrol như tradable rule.

## Đường đi của lệnh và nguyên nhân lỗ

Recheck sealed native books/BidAsk/accounting/actualexit. Trước exit chỉ dùng
M1bars **kết thúc trước phút chứa exit**, thêm actualexitfill; không dùng high/
low của phút stop nếu có thể xảy ra sau stop. Unknownheldpath không thành known.
Diagnostic favorable/adverse envelopes dùng executable side và modeledslip,
chuẩn hóa riskunit=plannedrisk/quantity. Khóa ngưỡng mô tả **0,5R**: tỷ lệ known
losers từng thuận≥0,5R trước khi đóng lỗ. Đây không TP đề xuất/tickexact MFE,
không lấy max mỗi trade thành lợi nhuận hoặc hứa exit khác sẽ cứu được lệnh.

## Chạy, kiểm và dừng

Reuse acceptedsource/proofs/indicators và reviewer; pure math helper có fixture
BUY/SELL/costbridge/gap/session/exit-minute regressions trước numerical pass.
Pin protocol/code/tests/inputbooks/sourceproof/lock trong manifest và snapshot;
source loaders vẫn giữ named2025grant, không mởBI5/2026 guards khác.
Output mới `execution-v1/us500-continuation-diagnostics-v1`, một writer,
progress/events/CANCEL/deadline600s, timers theo phase. Không provider calls.

Report đủ3horizons, cả4năm,2recipes,reference/stress; không chọn hindsight horizon
tốt nhất rồi gọi validated. Không pvalue/Sharpe/pass probability mới từ overlapping
samples. Per-year heterogeneity/controlgap/knownsubset phải rõ; chỉ nêu giả thuyết
tiếp nếu có evidence, không thay verdict challenge từ descriptive numbers.

Nếu không thấy ưu thế rõ/consistent sau phí, park exactrecipes thay vì autoATRgrid.
Nếu có dấu hiệu đáng xem, đề xuất **một** thay đổi có lý do và protocol mới trên
đúng data exposure, không auto-rerun samewindow như OOS. Thiếu data giữ inconclusive.
