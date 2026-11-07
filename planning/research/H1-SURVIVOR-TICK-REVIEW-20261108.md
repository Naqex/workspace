# Hai ứng viên nghiên cứu — native tick/risk/time-fit

Khóa sau Discovery4/6/7screens, trước annual native outcomes. Đây là exposed
historical validation, không độc lập với selection hoặc cleanOOS.

| Candidate | Vì sao được giữ | Giới hạn đã biết |
|---|---|---|
| eurusd-h1-london-postfix16-20-atr14x1p5-r025-v1 |ParentDiscovery4 dương2023/2024 chuẩn và cao; weakeststress68,22USD/10k|Chưa đủ lợi nhuận/uncertainty/prop/forward để vào challenge; không chọn new16NYvì không cải thiện weakestyear |
| eurusd-h1-asia09-15tokyo-london-break-atr14x1p5-r025-v1 |Discovery7 dương cả hai years/costs; weakeststress59,75USD|Same-data selection; H1close adaptation, không intrabar stop-entry |

Không cộng PnL hai strategies hoặc annual accounts thành portfolio. Không
chọn theo một năm đẹp, không coi hai families là độc lập thống kê, không ép
challenge bằng tăng risk. Tất cả failures/MLcontrols giữ history.

## Exact study

- WarmupNov–Dec2022→eval2023; warmupNov–Dec2023→eval2024. Raw inputs/hashes
  như Discovery4registrations, không download/export khác hoặc mở2025+.
- Giữ nguyên rules/exit/SL1,5WilderATR14/initial10k/planned25USD, dailyinternal100,
  overallinternal500, oneposition. Hai cost scenarios và signed financing từ
  account spec930e5670… giữ nguyên, historical execution/spec vẫn unverified.
- Reuse native run_scenario/execution/risk/ForexPropObserver, checkpoint/seals/
  cash reconciliation/dossier; shared source-bound quality/tick/H1warmup caches.
  Đọc toàn observed ticks mỗi scenario. No forceclose/gap fill/reorder.
- Reuse canonical declared FTMO2StepSwing10k profile từ UTC/Compression recovery
  protocols: targets1000/500USD, daily500/overall1000, resetPrague00:00, min4days,
  unlimited. Current [objectives](https://ftmo.com/en/2-step-challenge/) và
  [Swing](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/)
  được đối chiếu08/11. Profile terms_version/hash giữ nguyên để không sửa lịch
  sử; là current-rules counterfactual cho cả hai years, không historicalfirm
  certification. The5ers software approval chưa có, không gắn nhãn đủ điều kiện.
- H1signals, nextobservedquote fills, horizons3/6/12calendar months. Tick equity
  metrics/firstbreach/phase transitions của observer, không suy DD từ ledger.
  Sau passphase reset account theo existingcontract; flat trướcadvance, không
  cộng profit giữa phases như cùng một equitycurve.
- Hai batches mỗi năm2candidatejobs, max2workers/batch (tổng4), parallel-start
  cho phép sau boundedprefixverified. Worker deadline7200s, batch10800s là trần,
  không ETA. Job ownership/cancel/completed-job reuse dùng supervisor đã có.
  PROGRESS.md/progress.json/terminal/stdout/stderr ghi actualphases/counters.

## Review và quyết định

Trước dispatch:32legacy coarse Q1rows exact và16newnative prefixcases trên
326.373ticks/118hours khớp decisions/counts/open/pending; maxPnLdelta0,64USD.
Diagnosticbudget6,25USD không annualerrorbound.32oldrows được reuse sau fixture
v1truyền str thay Path, v2chỉ sửa recipe và giữv1; không lỗi simulator.
Metadata protocol routing và pre-mutation ownership rejection đã sửa, regression
tests đạt; không đổi numerical rules sau outcomes.

Chỉ công nhận completed sau hashes/seals/accounting/dossier. Bất kỳ correctness
failure: giữ attempt, sửa/root-cause/regression rồi rerun affected; không sửa
prices/costs/risk/criteria để pass. Source drift cần snapshot/review đúngversion.

Sau run: bảng3/6/12m gồm netbalance/equity/floating, trades/exposure/concentration,
tickDD/headroom/days-to-target/phase/breaches, nguồn costs và uncertainty. Hai
years độc lập về accountstate nhưng overlapping exposure/data-dependent trials.
Bootstrap hoặc CI chỉ conditional theo observations/assumptions, không biến
resamples thành market samples hoặc calibratedpassprobability.

Net không dương ở một cost/window hoặc risk/target/time-fit yếu → no challenge
promotion, không cứu bằng sizing. Dương/khôngbreach vẫn cần selection-aware edge,
frozenfreshholdout và prospective shadow/demo/reconciliation. Không tự mởholdout
hoặc cấpbrokerpermission. C1/C2campaign còn ACTIVE đến evidence đủ cả hai.
