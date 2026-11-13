# Gold B2 — reset bằng tiền, ledger M1 và rolling challenge

13/11/2026. Chỉ thị mới của owner mở rộng B1: sửa reset khi thiếu quote,
chạy hai pha2010–2024 và một structural diagnostic BUY-Only. EURUSD Catalogue13
được gác; không ghép các exact versions này vào portfolio. Giữ PR69 mở để
báo cáo trước merge; không gửi tin ASTRA, không2025–26/broker/runtime/productpin.

[Protocol đăng ký trước](GOLD-CONTINUOUS-B2-PROTOCOL-20261113.json) và private
registration giữ SHA/timestamp. Parent `f57ade8`, rawM1 hash `d209df9…471b9`.
Full seedNov2009, SMA20/80–ATR14–SL2ATR, risk125/200USD/fixed50k. Ba swap
counterfactual cũ20/20,40/40,45/5USD/lot/weekday22UTC/Wed×3; spread1USD/oz,
commission2,50/lot/side,slip0,20/oz/side. **Không là verifiedFTMO fees.**

## Hai điểm cần chỉnh trong thiết kế được đề xuất

**Không thể chỉ lọc lệnh của một global trade list.** Position state thay đổi
nghĩa của cùng một H4cross: đang giữ BUY thì cross xuống là EXIT; account mới
flat có thể dùng cross đó để vào SELL. BUY-Only còn có thể nhận một BUY mà
Original đang bận thoát SELL nên bỏ qua. Tests synthetic chứng minh cả hai.

PhaA vì thế lưu **potential entry episodes** cho mỗi causal flat-entry cross,
gồm entry/SL/exit opportunity và hai khối lượng mới tính đúnglotstep. PhaB
chọn episode theo trạng thái từng account, không nhập vị thế/pending trướcstart,
không tái dùng một intent đã tiêu thụ làm EXIT. Chỉ fixedcashbudget/fixedmargin
và rules hiện tại mới cho phép reuse; thay đổi risk theo balance, circuitbreaker,
trailing stop/partialclose hoặc dynamicentry sẽ cần contract/replay khác.

**Một daily minimum floating không đủ.** Trong ngày cash đổi vì swap/close;
minfloating và min equity có thể ở hai thời điểm khác nhau. Min/max cả ngày
cũng mất thứ tự peak-to-trough và firstbreach. Ledger chia tại mỗi reset,
funding, entry/exit và quarterlycut; mỗi đoạn cash không đổi giữ:

- floating min/max/first/last và DD nội bộ đúng thứ tự;
- prefix minima cùng timestamp/prefixpeak/prefixDD để dừng tại firstcrossing,
  không tính rủi ro sau khi account đã fail;
- point stream và fully-held-minute conditional envelope riêng;
- mọi cash event và cờ missingreset/gap/stopminute, không forwardfill giá.

Source dùng integerprice0,001 và moneycent với half-up đúng nativecost oracle;
không cài NumPy/provider mới. Một lượt parse admitted5.399.878M1rows tạo cache
có hash, H1/H4canonicalstream và episode ledger cho cả hai risk. Đây là một
lượt chuẩn bị dùng lại, không120lượt M1. Những lần build bị hủy/lỗi giữ lại;
không gọi tổng công sức phát triển là chỉ một lần chạy thành công.

## Reset và lifecycle

[FTMO Daily Loss](https://academy.ftmo.com/lesson/maximum-daily-loss/) kiểm13/11
xác nhận reference là balance tại midnightCE(S)T, loss đo bằng equity gồm
floating/fees/swap. [Hai vòng](https://ftmo.com/en/how-it-works/) dùng10%/5% và
daily5%/overall10%. Đây là current-rule counterfactual, không historicalterms.

`advance_cash_reset` là **adapter bridge có phạm vi hẹp**, dùng nativeprofile/
calendar/eventvalidation rồi cập nhật typedphase clock/sequence/cashanchor.
Thiếu quote không đóng băng mốc ngày; audit ghi `NO_FRESH_QUOTE_AT_RESET`.
FreshM1point kế tiếp được kiểm với anchor mới. Knowncash không cần marketquote,
nhưng stale floating không thành observed equity. Coverage uncertainty vẫn
giữ; **không chặn đồng hồ khác với chứng minh an toàn toàn path**.

Không sửa generic native `approximate` snapshot contract hoặc Trader source.
Native phase/money/transition reducers vẫn được dùng cho entry/exit/breach/
phasepass và phase2reset+explicitstart. Thresholds lấy từ nativeoracle, equality
không breach dưới profile `<`. Internal caps daily2,5%/staticloss6,5% báo riêng;
peakDD không đổi nghĩa thành staticloss. Mô hình đóng toàn bộ lệnh/khôngpending
và ít nhất4Pragueentrydays mới pass; phase2 account mới50k, indicator khôngreseed.
Administrative delay0 chỉ là giả định thuận lợi, không có actualapproval.

Giờ bảo trì không được suy ra chỉ từ mọi khoảng thiếu giá. Quan hệ timezone
NewYork/Prague và lịch symbol/broker khác nhau, gồm các tuần đổiDST lệch nhau;
không gán lịch CME thành observed spotCFDsession hoặc tựfill toàn bộ gaps.

## Exposure, parity và sửa lỗi trong triển khai

BUY-Only là **một biến thể diagnostic đã xem dữ liệu**, được owner cho phép vì
BUY/SELL breakdown cũ; không phải OOS hay discovery độc lập. Không đổi MA/ATR/
SL/exit, không quét filter hoặc đổi ngân sách sau outcome. Cùng60quarterstarts,
hai risk và ba swap cho hai variants =720conditional paths. Windows overlap,
followup3tháng–15năm và censor tại2025-01-01; không IID pass probability.

Parity khóa Q1/2010 cảrisk với sealedB1; RNGseed6902 chọn thêmQ4/2013 vàQ4/2011
trước outcome. Hai quý này so directM1canonicalseed cảrisk; BUY-Only thêm
directQ1risk125. Kiểm cash, floating, equity, funding, counts, filledintents,
trade entry/exit/cents và point/envelope DD. Pendingintent tại cutoff không
được nhầm thành filledtrade. Không đọc quote sau cutoff để forceclose.

Các failure/correction giữ riêng trong attempt directories:

1. Rà source phát hiện `next_phase` mới tạo next_phase_ready; thêm `start`
   để phase2 running. Lượt đầu hủy có kiểm soát sauparse, cache giữ nguyên.
2. Additionalquarter bắt lỗi gaprecord được đặt trước reset/fees xảy ra sớm
   hơn trong gap. Sửa chronologicalordering và thêm regression.
3. BUY-Only witness: B1reference envelope có thể bỏ phần DD ở point sau một
   intraminutepeak. Diff2,31USD trongQ1BUYOnly; money/point/trades không đổi.
   B2 `PointAwareQualityPath` sửa phép đo; frozenB1 files giữ nguyên. Original
   Q1 và hai quý random vẫn khớp. Test1000USDconditionalpeak→point49000 đảm
   bảo DD envelope2000USD, pointDD1000USD.
4. Paritychecker ban đầu tính queuedBUY tại cutoff thành filledentry; sửa
   census theo observed cutoff, giữ pending. Một command trỏ nhầm reusepath
   fail trước cohort; không là economic result.
5. Entrycost có thể đẩy account qua floor trước segment tiếp theo; latch
   ngay nativebreach, không gọi evaluator trên attempt đãfailed. Có regression.
6. Hai fixture mở rộng ban đầu dùng cutoff giữa minute không được ledger
   admit; sửa fixture sang completed-minute endpoint, không nới validation.

Profile mộtfull15yearcohort cho thấy phần lớn overhead còn ở native lifecycle
serialization/calendar lặp cho marks không đổi accountstate. Bản nhanh giữ
mọi min/floor checks và cashreset; chỉ gọi full native lifecycle tại entry,
exit và firstbreach, dùng cùng thresholds. Bản chậm dừng sau440cohorts vì
entrycost đã kích hoạtbreach nhưng caller chưa latch; không claim full720
cũ/mới parity. Bản nhanh kiểm lại7directcases và repeat120Original/stress
cohorts tới từngfield; full720 có numeric invariants riêng. Native full-quality trong B2 là **đủ cho sampled-M1 declared
model**, không xóa missingpath hoặc biến modelpass thành certifiedFTMOpass.

## Kết quả và bàn giao

[Số liệu tổng hợp/hashes](GOLD-CONTINUOUS-B2-RESULTS-20261113.json). **Đã xong720paths; chưa có candidatechallenge được chứng nhận.**

| Swap Long/Short | Risk/lệnh | Bản | Qua vòng1 /60 | Qua cả2 /60 | Median hoàn tất, năm | Modelbreach /60 | Qua2 và giữinternalbuffer |
|---|---:|---|---:|---:|---:|---:|---:|
| 20/20 | 125USD | Original | 14 | 5 | 13.82 | 0 | 5 |
| 40/40 stress | 125USD | Original | 0 | 0 | — | 0 | 0 |
| 45/5 giả định | 125USD | Original | 7 | 0 | — | 0 | 0 |
| 20/20 | 125USD | BUY-Only | 20 | 7 | 13.82 | 0 | 7 |
| 40/40 stress | 125USD | BUY-Only | 4 | 0 | — | 0 | 0 |
| 45/5 giả định | 125USD | BUY-Only | 0 | 0 | — | 0 | 0 |
| 20/20 | 200USD | Original | 29 | 14 | 6.14 | 5 | 11 |
| 40/40 stress | 200USD | Original | 9 | 1 | 7.22 | 18 | 1 |
| 45/5 giả định | 200USD | Original | 16 | 6 | 6.48 | 7 | 6 |
| 20/20 | 200USD | BUY-Only | 51 | 10 | 8.01 | 0 | 7 |
| 40/40 stress | 200USD | BUY-Only | 15 | 3 | 14.53 | 0 | 1 |
| 45/5 giả định | 200USD | BUY-Only | 12 | 0 | — | 0 | 0 |

Counts là mô tả các cửa sổ trùng nhau đến cuối2024, không xác suất pass đã hiệu chỉnh.
Median chỉ tính những cửa sổ đã hoàn tất, không coi phần còn lại là fail hoặc đưa vào median.
Internalbuffer: mọi phase có daily<1.250USD và staticloss<3.250USD; không là fulltick chứng nhận.

**Không có đường nào trong cả12nhóm hoàn tất hai vòng trong3/6/12/24tháng.**
Số start có đủ followup tại các mốc đó là60/59/57/53. Late starts được rightcensor,
không đánh trượt vì chưa đủ thời gian. Phần lớn hoàn tất được mất6–15năm.
BUY-Only có thể giảm DD hoặc tăng số cửa sổ đạtphase1, nhưng không tự rút ngắn
hai vòng: trong swap20/20,risk200,Original có14hoàn tất/median6,14năm,
BUY-Only có10/median8,01năm. Trong45/5,risk200,Original có6,BUY-Only0.

### Rủi ro trong lane stress40/40

| Risk | Bản | Worst Daily/50k | Worst static loss/50k | Worst peakDD/50k | Modelbreach |
|---|---|---:|---:|---:|---:|
| 125USD | Original | 0.486% | 8.500% | 9.828% | 0/60 |
| 125USD | BUY-Only | 0.276% | 5.047% | 6.103% | 0/60 |
| 200USD | Original | 0.762% | 10.019% | 16.084% | 18/60 |
| 200USD | BUY-Only | 0.432% | 8.439% | 10.089% | 0/60 |

Các worst có thể thuộc các cửa sổ/phase khác nhau, không gom thành một ngày.
Dưới125USD,BUY-Only giảm worststatic còn5,047% nhưng chưa hoàn tất2vòng ởstress.
Tăng200USD giúp một vài cửa sổ đạt target, nhưng Original có18modelbreaches
do overallstaticfloor; daily vẫn dưới1%. BUY-Only không chạm luật10% trong
sampledmodel, nhưng worststatic8,439% vượt internal6,5%. Trong3BUY-Only/stress
cửa sổ hoàn tất ở200USD, chỉ1giữ được cảhaiinternalbuffers. Chưa có quyền nângrisk thật.

### Thời gian và mức kiểm chứng

| Công việc | Thực đo / scope |
|---|---|
| Đọc/hash/validate5.399.878M1 + cache lần đầu | Khoảng54s theo artifacttimestamps; không có exact phase timer của attempt bịhủy |
| Build canonicalframes/308potentialepisodes mỗi risk | Khoảng56s gồmwriteledger theo timestamps; không gọi là stablebenchmark |
| Đánh giá720paths từ ledger đã có | **178.58s** wall |
| Successful cached invocation, gồmload/parity checks/serialization | 184.38s wall /181.45s CPU |
| Đo riêng120Original/stress starts | **30.81s**, mọifield khớp output đã lưu |
| DirectM1 tại hai quý thêm | 14,25–15,10s/case, gồm warmupsource đãcache |
| Cùngquarter qua ledger | 0,00845–0,00978s/case sauprepare; không áp tốc độ này cho toànpipeline |
| PeakprocessRAM | 778.1MiB |
| Fixtures | 36focusedunittests đạt; gồm fullB1 suite |
| Parity | 7cases đạt từngcent; Q1Original125/200 khớp sealedB1, haiquý2011/2013risk125/200 vàBUYOnlyQ1risk125 so corrected directM1 |
| Numeric review | 720unique cohorts/12groups; target/min-days/cashidentity/countconservation;4negative mutations bịchặn |
| Reset audit | 5.479reset records trên Original2010/risk125/stress;830lần held khôngfreshresetquote, mọi cashanchor/clock vẫn đúng |

Ngân sách coldprepare+build+120evaluation hiện khoảng2–3phút theo hai phase
chuẩn bị ước từtimestamps và evaluation đo30,81s. Với720paths khoảng5phút
nếu tính prepare; **không phải tổng thời gian lập trình/triage hoặc cam kết ETA**.
Estimate16–22giờ cũ chưa từng là fullM1benchmark; không dùng nó để quảng cáo
speedup đo thực. Hai process old/fast từng chạy overlap khi kiểmperformance,
nên wall không là benchmark tải máy ổn định. Measurement120sauđó chạy riêng.

Bản chậm dừng ởcohort≈440 vì entrycostbreach handler đãfailed, do đó **không có
full720old-vs-new parity**. Bản nhanh hoàn tất720; kiểm7directcases và repeat120.
Đã sửa thêm terminalfloating của30failedpaths lấy đúng nativefirstbreachmark
thay vì mark cũ; replay30ca này cho thấy chỉfloating/markednet đổi, mọi count/
target/time/DD/verdict khác giữ nguyên. Case đó là derived accountingfix, khôngalpha tuning.

Ledger/cache re-use có source/hash/selectedAST checks, giữ mọifail/cancel.
Bổ sungoutputlock để hai lần chạy sau này không giành cùngstatus/receipt;
log hủy trong lượt này đã xác minh cancellation thực. Không tuyên bố automatic
CLIresume sauhardkill; staleRUNNING.lock cần reconcile, không tựxóa/submit lại.

**Quyết định:** sửa kỹ thuật đã tạo ra phép thử nhanh và rõ hơn, nhưng exactGold
recipe vẫn quá chậm cho mục tiêu challenge/thu nhập chính. BUY-Only không được
promote chỉ vì một vài cửa sổ pass hoặc DD thấp hơn. Chưa fundedpayoutseries/
stableincome/OOS/targetcost/broker acceptance. Giữ PR69 mở, báo owner trước merge;
không tự quét thêm filters hoặc chạy nghiên cứu mới.
Private owner:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/gold-continuous-B2-20261113-v1/`.
