# Chiến dịch intraday mới — đề xuất trước khi chạy

**Trạng thái: PROPOSAL_PENDING_OWNER_APPROVAL. Chưa code chiến lược, đếm tín
hiệu, backtest, mở giá2025–2026 hoặc chạy benchmark mới.**
Task vẫn STRATEGY-E2E; đây là thiết kế thay hướng sau khi owner gác R043,
không reset lịch sử thử. [Envelope chuẩn](../../.agents/skills/strategy-qualification/references/validation-gates.md#prop-target-envelope--profile-owner-ngày-13112026)
giữ thresholds và định nghĩa; [R043 fixture](GOLD-R043-REGRESSION-FIXTURE-20261113.json)
giữ benchmark. PR69 đã merge `920b48a`, nhánh cũ đã xóa; VIWIP/Traderpin giữ nguyên.

## Quyết định đề xuất: B trước, A dự phòng

| Hướng | Cơ sở đã có | Chưa chứng minh / nút chặn | Đề xuất |
|---|---|---|---|
| B — EURUSD H1→M15 | Metadata517.750.341Bid/Ask ticks; có native tick path, sizing/cost/reconciliation trên selected2022–24 | Count tổng không là coverage toàn kỳ. Catalogue13 gross mỏng; sànSL không tự sinh alpha. Targetaccountcost/calendar vẫn cần bind | **Một hypothesis mới, kiểm feasibility trước economics**; giảm bất định execution trước |
| A — XAUUSD H1→M15 | Có M1Bid2010–24 và bộ đo/clock/ledger; R043 cho câu hỏi về trend dài ngày | Chưa bulk observedAsk/tick đã admit cho wholewindow; lợi nhuận R043 nằm ở longholds, chưa chứng minh intraday trend/BUYedge. Biên dao động lớn không bằng expectancy | Giữ một nhánh dự phòng; cần data/cost admission trước, không code/chạy song song để tìm winner |

Đây là lựa chọn về chi phí kiểm chứng và data readiness, **chưa biết asset nào
có xác suất tìm edge cao hơn**. Chọn B không tái chạy Catalogue13: hypothesis
là H1bias + M15break/retest có state và cost admission, không chỉ nớiSL cũ.
Nó vẫn cùng family breakout/session, phải nối trialhistory Catalogue13/BR-01;
thêm timeframe/filter không tự tạo một cơ hội độc lập.

## Những tiền đề cần sửa trước khi triển khai

- Bỏ swap8.950,80USD của R043 không giữ nguyên lợi nhuận/trades khi đóng sớm.
  Số80–150lệnh/năm của vàng intraday là giả thuyết, chưa đo. Không coi dữ liệu
  của BUY trong Original là cadence của executable BUY-Only mới.
- 25–40netR0/năm là mục tiêu kinh tế ban đầu; ở risk0,30% cần50R0 để qua hai
  vòng, ở0,40% cần37,5R0. Pace12tháng tương ứng50/37,5R0/năm;6tháng100/75.
  **Chọn12tháng làm mục tiêu chính,6tháng là stretch**, không ép risk để khớp.
- Mean gross sau spread25–35USD/lot chỉ là target screening, không đủ chứng
  minh R-velocity. Ví dụ minh họa EUR100k/lot,SL20pip, phíroundtrip9USD/lot:
  R0/lot=200+9=209USD; gross35→net26→0,1244R0/trade;120trades≈14,93R0/năm.
  Chưa tính lotround/gaps; không là backtest. Phải kiểm **netR0/trade×cadence**.
- CumulativeDD15R0 ở risk0,40% bằng6%, không phải<6%; cũng không suy daily<2,5%.
  Corealpha/risk/daypath cần bằng chứng riêng, không đóng dấu bằng tỷ số Calmar.
- B2stress/risk200:21,10–25,05R là **lỗ so vốn đầu**, còn peak-to-trough DD
  BUY-Only/Original là25,22/40,21R. Không dùng hai cặp số thay nhau. Friction/R
  thấp cũng chưa chữa được Catalogue13: đã có nhiều bản cost/R nhỏ nhưng gross yếu.

## Card B0 đề xuất để owner duyệt — một baseline

Mọi con số sau là lựa chọn thiết kế ban đầu, chưa được đo/tối ưu.

| Tầng | Luật dự thảo cụ thể |
|---|---|
| Thị trường / clock | EURUSD, signal từ Bid H1/M15 đóng hoàn chỉnh, UTCsource và Europe/London cho session; native execution BUYAsk/SELLBid. Canonical indicator seed01/11/2021, không reseed theo năm/account; chỉ dùng observations admitted. |
| H1bias | BUY khi H1Close>SMA20 và SMA20 cao hơn giá trị3H1 trước; SELL đối xứng; không đủ dữ liệu/không rõ hướng thì abstain. Xét lại tại breakout và retest, chỉ H1 đã đóng. |
| M15zone | High/Low của07:00–08:00London, chỉ chốt khi đủ4M15; thiếu bar/session không đoán hoặc padding. Zone không dùng extrema của phần ngày chưa biết. |
| Setup | Từ08:00 đến11:00London, M15 đóng vượt zone theo bias ít nhất0,10ATR14M15; ATR là Wilder từ các bar đã đóng trước breakout, khóa buffer cho setup đó. |
| Retest/trigger | Đợi lần chạm đầu trong4M15 kế tiếp vào zoneedge±buffer; BUY cần Close trên upperedge+buffer và Close>Open, SELL đối xứng. Firsttouch không xác nhận/bias đổi/hết4bar/hết11:00→cancel. |
| Entry | First admissible tick sau retestclose; quyết định xong mới fill, không chọn giá thuận trong nến vừa đóng. Một setup/vị thế tại một thời điểm; tối đa2entries/ngày, không quota phải có lệnh. Sau thoát chờ M15 đóng tiếp theo mới tạo setup khác. |
| SL / cost floor | BUY: Low retest−buffer, SELL: High retest+buffer, round ra ngoài targettick. Khoảng SL tự nhiên không đạt friction cap thì **skip**, không tự kéo xa SL hoặc tối ưu pipfloor để tạo lời. PlanF/R0≤12%, ưu tiên≤10%, dùng spread/fees/reserve biết tại intent. |
| Exit | TP khoảng cách2×initial price stop-distance; giữSL/TP, khôngpartial/BE/trailing. Flat lúc12:00London hoặc trước datedrollover/sessionclose−15phút nếu sớm hơn. Hủy pending tại11:00. Không có quote/không xác nhận flat →data/execution failure, không gán swap0. |
| News / Standard-funded | Không nhận setup có khả năng giữ qua restrictednews; policy dự thảo đóng trước sự kiện5phút, không entry từ5phút trước đến5phút sau. Phải có lịch historical/known-at phù hợp và buffer; thiếu thì chưa claim Standard-funded compliant. Đây là policy nội bộ chặt hơn news rule, không alpha filter được chọn sau lỗ. |
| Sizing | Economics baseline0,30%/initialphase, fixedUSD/R0, native lotfloor/minlot/margin + cost reserve;0,40% chỉ endpoint qualification sau khi corealpha đủ evidence. Không dùng rủi ro này chạy broker. |

Londonrange/bias/retest có thể giảm cadence dưới sàn: đó là giả thuyết bác bỏ
được, **không nới giờ/filter sau outcome để buộc có60lệnh**. Không áp velocity
gate cho từng lệnh; gồm cả losers/abstains/tháng0 trong toàn sample.

## Split dữ liệu và ngân sách

| Phần | Vai trò được đề xuất, chưa chạy |
|---|---|
| Warmup Nov–Dec2021 | Indicatoronly; không trades/pending trước evaluationstart |
| Development2022–2023 | Feasibility rồi economics; cửa sổ đã exposed bởi research trước, không clean OOS |
| Historical validation2024 | Khóa B0/B1 trước đánh giá; vẫn ghi **previously exposed historical validation**, vì đã có nghiên cứu2024, không gọi final unseen |
| Stress lịch sử2018–2021 | Chỉ xét sau freeze; thêm role/calendar/source admission riêng, không dùng sửa B0/B1 hoặc cộng làm dữ liệu độc lập |
|2025–2026 | **CLOSED — không truy cập**. Chưa đủ exposure map để gọi globalclean; campaign cũ đã dùng2025ở lane khác. Sau này chỉ mở bằng gate riêng; không sạch thì final evidence cần prospective locked evaluation |

Budget mới **tối đa4alpha versions cho toàn chiến dịch**: B0 + tối đa1diagnostic
B1 có cơ chế đăng ký trước; A0 + tối đa1diagnostic A1 là phần dự phòng, cần card
được duyệt trước. Không tự chạy A khi B thất bại. Giữ cả failures/abandoned;
priorCatalogue13/US500/Gold trials vẫn trong selectionhistory. Đổi exit/side/
filter/SL/timewindow đều ăn alpha budget, không rename để mở vòng mới.

Hai risk endpoints và reference/stress costs là policies/scenarios được ghi
riêng, không4edge độc lập và không grid tối ưu. Targetcost chưa bind thì chỉ
declared-model result. Mỗi baseline chỉ một fixedwindow; không tìm start đẹp.
Sau2vòng không thêm thông tin hữu ích: checkpoint/gác, không tự quét thêm family.

## Trình tự sau khi được duyệt

1. Chốt G0 card/source/spec/cost/news/rollover/consumedmap và budget trên; audit
   metadata/quality trước. Không biết targetrollover thì không dispatch net-PnL
   zero-swap claim. Không bắt làm full517triệu tick; admit đúng partitions.
2. Count-only development, gồm mọi skipreason. Nếu sau filter/minlot/margin
   cadence không đạt60/năm hoặc tập trung rất ít ngày, gác vì suitability;
   không gọi đó là proof alpha âm. Đây vẫn là phép thử cần approval ở lượt này.
3. Economics baseline; báo gross/matched spread/comm/slip/swap/net, R0/Rprice,
   filled/attempted/missed và precision/dependence. 25–35USD/lot là aggregate
   gross-afterspread target của toàn cohort (kể cả losers), không hindsightfilter.
4. Chỉ survivor mới selected tickpath parity/replay lịch sử2024 và sizing0,40%,
   daily/static/peakDD/firstbreach/timefit6/12tháng với coverage/censoring. Không
   dùng trade-dayledger chỉ có minfloating cho strategy cóSL+TP/ambiguousorder;
   cần chứng minh sufficientstats/position-state invariance như B2 hoặc directtick.
5. OOS/prospective→shadow/reconciliation→ownerhandover→challenge; fundedreward
   là bài toán riêng. Payout bền vững/thu nhập chính chưa được chứng minh chỉ
   bằng passchallenge, capF/R hoặc số lệnh.

## Nguồn và giới hạn

- [FTMO2-Step](https://ftmo.com/en/how-it-works/): targets10%/5%; planning không
  phải xác suất pass. [NewsFAQ](https://ftmo.com/en/faq/can-i-trade-news/):
  selectednews±2phút có exceptionsSwing/evaluation; không gọi intraday100%compatible.
- [UpdateSep2026](https://ftmo.com/en/blog/trading-updates/trading-update-24-sep-2026/)
  ghi MTclockGMT+3, [Nov2026](https://ftmo.com/en/blog/trading-updates/trading-update-5-nov-2026/)
  GMT+2 và swap cần symbolspec. Chúng **không chứng minh targetrollover luôn22UTC**.
- [Gold data inventory](GOLD-R043-FINANCING-PATH-AUDIT-20261112.md#4-dữ-liệu-vàng20252026-và-lựa-chọn-intraday),
  [nativeEUR evidence](H1-NATIVE-SURVIVORS-RESULTS-20261108.md),
  [Catalogue13 economics](GOLD-EURUSD-PORTFOLIO-STAGE-A-20261113.md) là nguồn local;
  metadata không là completequote/brokerdata certificate.

Lượt này chỉ cập nhật thiết kế/reference/fixturemanifest và kiểm số học/link/
skillstructure. Chưa tạo executableB0, chưa chạy card trên data hoặc mở OOS.
