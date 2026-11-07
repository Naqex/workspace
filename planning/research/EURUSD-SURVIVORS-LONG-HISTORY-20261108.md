# Discovery11 — fixed survivors, EURUSD2010–2022 indicative history

Đăng ký trước outcomes mới, kế thừa [preparation](EURUSD-LONG-HISTORY-PREPARATION-20261108.md)
và [campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md). Câu hỏi: hai
policies được chọn từ2023/2024 có giữ economics ở các năm trước không? Không
tune thresholds/hours/exits/risk hoặc tìm thêm variants trong batch này.

## Frozen recipe và dữ liệu

- Giữ nguyên `eurusd-h1-london-postfix16-20-atr14x1p5-r025-v1` và
  `eurusd-h1-asia09-15tokyo-london-break-atr14x1p5-r025-v1`: H1closed signals,
  SL1,5WilderATR14, noTP, same clock/DST/one-entry/day/time exit. Không đổi
  signal code hoặc imports numerical của annualnative đang chạy.
- Raw QDM `EURUSD_TW` M1 UTC,01/11/2009–31/12/2022; SHA
  `9ee570591522f879d9b3a8734e5b0071ba672cb20a562b28d16bb62402749c05`,
  4.917.083rows. Same-asset03/01/2022:65.215ticks/1.425M1bars, BidOHLC
  1.425/1.425exact, Ask/Mid0exact. Cùng provider, không independent feed hoặc
  chứng minh tất cả ngày đều đúng. Không mở2025+ hoặc mua/download thêm data.
- 13annualbooks riêng2010–2022; warmupNov–Decnăm trước,100observedH1 tối
  thiểu. Không cộng books thành CAGR/continuous equity hoặc coi13năm unseen.
  Đây là development/historical robustness của exposed-selected policies;
  history ngoài project không rõ, không cleanOOS.
- Fixed declared Ask=Bid+0,00010reference và+0,00020stress; slippage0/0,00002
  mỗi side, commission2,50USD/lot/side. Financing9,30BUY/−0,31SELLreference,
  20/20stress, Wed×3/22UTC. Cost scenarios declared counterfactual, không
  historical broker spreads/swap hoặc spread-tail bound. Không sửa sau outcomes.
- Initial10k/risk25USD (0,25%),minimumlotstep0,01; reuse exactFXsizing/margin/
  cash/coarse SL kernel. Một vị thế, noforceclose/sort/fillgaps. Không internal
  risk brakes, fulltickDD hoặc propengine ở bài này. Row count2×2×13=52.

M1→H1 được gắn nhãn indicative: nextmodeledhourOpen, stop level hoặc hourOpen
gap, không actualfirstcrossingtick/strictmillisecondfill. SourceM1rows không
được báo observedticks. Default nativeBidAsk coarse và metal behaviors phải
giữ tests;33tests/27subtests có explicit FXgrid/window/source-label cases đạt.

## Execution và quyết định

Config freeze exact protocol/raw/runtime/source pins, cùng script snapshot;
1writer,deadline900s,status/log/failure/manifest, không autoretry hoặc overwrite.
Không sửa source đang pin ở nativejobs; current coarse-only extension source
được ghi trong manifest. Preparation đã68,23s, reuse raw không export lại.

Primary report: từng year/cost netequity/trades/financing/open state, tổng của
annualbooks (không CAGR), số năm dương, ba bands2010–14/2015–19/2020–22 và
concentration. Giữ cả hai policies và negativeyears, không chọn đẹp một band.
Heuristic research-retention khóa trước outcome: totalnet dương hai costs,
stresspositive≥9/13years và cả ba bandstresssums dương. Đây là heuristic
triage, không ngưỡng chứng nhận edge; không tự loại cả cơ chế hoặc promote.

Không đạt heuristic: giữ version/window negative và tìm hypothesis khác có lý
do; không tăng risk/cost assumptions để cứu. Đạt: vẫn phải selection-aware
uncertainty, exacttick/risk/prop và freshfrozen/forward review; không tự mở
holdout hoặc gửi broker. C1/C2 chưa đạt chỉ vì batch này xanh.
