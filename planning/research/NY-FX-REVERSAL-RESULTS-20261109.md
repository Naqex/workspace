# R070/R071: NY-session MA4 đã kiểm xong, không qua sàng lọc

**Gác hai exact versions; chưa có ứng viên challenge.**
[Protocol](NY-FX-REVERSAL-PROTOCOL-20261109.md) commit`31d8084`, implementation
`391efba` trước economic outcomes. R070contrarian là primary, R071momentum là
diagnostic control đã đăng ký. Không flipcontrol thành winner hoặc đổiMA/SL/
giờ/phí/risk sau khi xem kết quả.

## Kết quả trên10.000USD mô phỏng, mỗi năm bắt đầu lại

| Policy / năm | Phí chuẩn,USD | Phí cao,USD | Lệnh đóng/cost |
|---|---:|---:|---:|
| R070 reversal2019 | −1.217,66 | −1.536,55 | 540 |
| R070 reversal2022 | −297,01 | −463,01 | 522 |
| R071 momentumcontrol2019 | +225,13 | −67,79 | 498 |
| R071 momentumcontrol2022 | −582,25 | −723,03 | 501 |

Cả16books terminal/knownflat, không unknownexposure;8nullbooks0trades/0PnL.
Primary cần cả2stressyears net>0/≥100closed theo protocol, không đạt. Năm
2019control dương ở phí chuẩn không là survivor hoặc licensepromotecontrol.
Các costs cùngtínhiệu và hai năm đãexposed không independenttrials/cleanOOS.
Không cộng annualbooks thành một account liên tục hoặc tỷlệpassquỹ.

EURUSD10/11/12/13NY quyết định từ past4midpointcloses và15Bidbars/TR14; action
mộtgiờsau,SL1,5TR14,25USDplannedrisk,lotsrounddown,flat15NY. Giữ same-side,
flip khi target đổi, noTP/trailing.2019có1.044decisions/policybook,1.036ready và
8feature-unavailable;2022có1.040/1.040ready. Giữ mọi expectedweekday/census,
không bỏ ngày thiếu.540/522reversaltrades được giải thích bằngSL/timeexit/flip,
không worker dừng hoặc không gửi lệnh. Đây chỉ offline modeledtrades.

## Đã kiểm để kết luận đúng phạm vi

| Cửa | Bằng chứng / giới hạn |
|---|---|
| G0 thiết kế | Freeze protocol trước fetch/quotes và outcomes; code commit trước numerical; giữ primary/control/null/costs |
| G1 nguồn/timing | 48rawmonths/4exports/24.932explicitH1bars/124.660price-volume fields và timestamps khớp canonical/Fraction; no unpaired/crossedOpenClose trong nguồn này.9.880paddinghours loại theo sourcemembership, không volumeheuristic |
| G1 logic | 7focused tests: manualFractionMA/TR/sizing/BUYSELLcosts,futuremutation,missing/equality/DST,hold/flip,SLintrabar/gap,scheduledexit,margin/null và entryOpen không bị futureClose lọc |
| G2 tài chính | Separate Fraction reviewer không import producer hoặc financialhelpers: toàn16books/signals/census/4.122closedpaths gồm lặpqua costs,entry/stop/quantity/cost/cash/endstate khớp; actual entry/quantity/net/count/authority mutations đều reject |
| G3 edge/OOS | Không đạt registeredtriage;2019/2022exposed,không cleanOOS hoặc selection-adjusted edgeproof |
| G4–G6 | Chưa targetbrokerhistoricalspec/cost/propintrabarDD/forward/handover;khôngexecutionauthority |

Review cùngagent/provider bằng codepath/arithmetickhác, chưa independenthuman/
model signoff. Không gọi16books hoặc4.122paths là samplesđộc lập. Fraction so
recurringTR/distance có tolerance1e−24 cho Decimal28 representation, không
nới lot/grid/cents hoặc selectiongates. Datafile/schema/hashpass không thay edge.

Paper authorPDF đã lấy đủ445.817bytes và đọc §§2–4/Table3/7; metadata/sourcehash
trongprotocol. Paper EBS2003–06, bản này Dukascopy2019/2022; H1midpointcloses,
onehourlag,SL/size/DST/lifecycle khác. **Negative của adaptation không bác bỏ
paper hoặc mọi NYreversal.** Không actual firstquote/15minlag/targetfills proof.

## Hậu kiểm: tốc độ đã đủ, fidelity là câu hỏi tiếp

| Phase thực đo | Wall / CPU | Quyết định |
|---|---|---|
| H1source48months | 18,010s /0,828s | 2cachehits/46misses/0unknownstate; cached raw bất biến, không retries |
| FullsourceFractionreview | 1,759s /chưaghi | 124.660fields,5mutations; không download lại |
| Producer16books | 4,132s /4,094s | Không cầnGPU/Rustrewrite; chưa gồm authoring/research |
| FullfinancialFractionreview | 9,409s /9,375s | Reuse outputs; không rerunsimulator |

Các phase có workload khác nhau, không benchmarkspeedup/end-to-endstudytime.
178events/progress ghi ngày/tháng/book,không per-ticklogs; không đổiUI hoặc
tracker Paperclip. Nếu lặp workload lớn mới đo reuseload/decisioncensus, không
optimize4srun bằng framework. Không xóa raw/failedattempts để làm sạch kết quả.

**Decisiondelta:** từ admittedhypothesis sang reviewednegative ở cảstressyears;
gác exactH1versions. Câu hỏi nghiên cứu tiếp là **timing fidelity**: onehourlag
có đổi kết luận so với near15minute execution trên cùng frozen MA4 không?
Paper có15minlagcheck nhưng không chứng minh adaptation đã giữ edge. Đây sẽ
là trial/protocol riêng, không sửa current pins/outcomes hoặc tuyên bố lỗi
simulator khi chưa có paired evidence. Reuse sources/code trước sourceM1/ticks
mới; khóa sample/scope/cost/entry/exit trước bất kỳ diagnosticPNL nào. Không
giảmSL/fees hoặc tăngrisk để cứu outcome. Không ownholdout2025+/broker/newaccount.

## Artifacts

Private base`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.

| Output | SHA256 |
|---|---|
| `execution-v1/ny-fx-reversal-source-v1/result.json` | `eb3043af676fae118e48bfdfd67e6eb806f9cf148ffb782f87b5bdc4438a272c` |
| Source `review.json` | `237c47ed328d3a91d74737e7382d966cdec159e93344849d8b9935032f828184` |
| `execution-v1/ny-fx-reversal-v1/result.json` | `721164170a936ec06a9cd285d833a33033490e544447e6ae7bbd1c347c37efe8` |
| Economic `review.json` | `f3419ec481f1fab18a6777d614d80da434090b9dd7662d6784ce5f27946a55a8` |
| Economic reviewer script | `review-ny-fx-reversal-v1.py`; `942336982d20c5bd383b2e33009d7363997ad3faa51a3c6fc346668a61957762` |

SourcePID27340/producer20592/reviewer terminal0; không job phải đợi. Scripts,
source snapshots,pins/config,progress/events,fullbooks/nulls/reviews giữprivate.
Catalogue71records/50policyversions/25native/5controls; chưa challenge-qualified.
Existing research/qualification/continuity/retrospective skills đủ; không skill
mới cho một negative hoặc dữ liệu nguồn mới. Trader vẫn83731fc8, runtime/MT5
giữ nguyên. GoalC1/C2 active, khôngcomplete hoặcblocked vì hai versions nàyfail.
