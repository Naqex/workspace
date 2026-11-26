# V23 — sleeve attribution, bounded ablation, calendar diagnosis and MT5 watcher

Owner request17Nov2026. PR101/head `26de14c` merged into main; use
`codex/sleeve-ablation-and-mt5-v23`, remove V22 branch after merge.
Preserve Trader pin, VI WIP, every source/freeze/negative attempt. No Astra,
subagents, memory updates, account/login/order submission or product deployment.
Watcher is a bounded foreground CLI the owner may start, not an installed service.

## Corrections and scope before new outcomes

V22 G_L3_A **already excluded EURUSD F5**. Its17.289R avoided loss is all
rejected losers, not all L3 losses: Dev L3 itself is10.858R. Lost17.813R wins
are Gold F3/F4. Do not credit the proposed F5 exemption as a new improvement.
No evidence yet that all F3 exhaustions are bad, all F5 high-range days good,
or that any observed regime relation generalizes.

The12 H1 rows called missing in V22 actually have exact entry and20:00 quotes;
their `ok=false` comes from applying the inherited Gold holiday CLOSED guard
to FX. Reconcile price availability separately from session eligibility. Do not
invent holiday fills or change deadlines just to reach100%. Raw endpoints can
be100% available while target-account permission remains unknown. Keep the V22
source/results, correct active interpretation and report exact dates/reasons.

Fit/select only Dev2018–2023,2017 warmup allowed. Later history2024–13Oct2026
is already exposed; no clean OOS claim. Do not compute new later sleeve
statistics until the Dev selection is committed. Existing V21/V22 later evidence
is prior exposure and must be declared, including global top10 identities.

## Track1: descriptive decomposition and exactly three Dev trials

Canonical V19 PRIMARY/OLHC fixed150USD with actual lot floor; repeat OHLC.
For each sleeve and Dev/later period, count, net winrate, netR, meanR, marked
equity peak-to-valley DD, closed cash DD and ExGlobalTop10 contribution. Global
top10 means the same10 whole-book identities, not each sleeve's own10.
Also report Dev-only top10 removal to avoid using later winners for selection.
Scope later-period DD to a flat fresh start2024, not the full2018 peak.
Fixed-unit attribution differs from adaptive-account ablation/admission replay.

Before child outcomes, freeze A1 target from Dev only: weakest sleeve by mean
netR/trade (lexical tie break). Record ExDevTop10 contribution as diagnostic.
`A1_DROP_WEAKEST`: drop that sleeve entirely, do not redistribute its risk.
No search over0.25/0.5/etc weights. This is the owner's allowed two-sleeve case.

`A2_F3_EXHAUSTION90`: only Gold F3 refuses decision-known day-range/closed-D1
Wilder ATR14>0.90; Gold F4 and EUR F5 unchanged.
`A2_F4_EXHAUSTION90`: only Gold F4 same0.90 rule; F3/F5 unchanged.
These split V22's failed compound gate; no new threshold/signal/exit/side/risk.
Missing covariates abstain on affected sleeve and counted separately.

All3 trials count against history. Gate both M1 orderings: Dev netR>23.8524,
marked equityR-DD<12.2065333 using same baseline calculation, no increase worst
daily marked loss, both three-year cluster net positive. Report own ExTop5/
ExTop10, preserved baseline Dev top10, W1/L3, rejected winner/loser contribution
but do not tune them. Rank passers by worst-order Calmar, then net, then ID.
Freeze one winner before later statistics/replay. No second selection on later data.

## Track2: source/session repair and exact F5 transfer (three recipes)

For the6 GBP and6 AUD invalid recipe observations, enumerate date, recipe,
entry/endpoint exactness, prior off_kind/calendar provenance, whether holiday
is instrument-specific. Verify primary FTMO historical notices where available;
otherwise label unknown, not closed/open by inference from price alone.
Good Friday FX schedules are distinct from metals; Christmas/Boxing Day need
their own evidence. No source price edits, artificial early-close or backfill.

New FX research calendar: ordinary weekdays open under declared scenario,
Christmas25Dec/NewYear1Jan closed; unresolved special-day permission stays
unknown for target qualification. Deadline20:00UTC for native H1, asset-known
early guard only if independently supported. Counterfactual full-priced holiday
economics may be shown with provenance, never called broker-compliant acceptance.
Reuse V22 saved arrays/net prices for affected B2 cases; no need regenerate signals.

Transfer exact F5 H4/n5/ADX<=25/buffer0.10ATR/prior5-day range rejection/first
signal per UTC day to GBPUSD/AUDUSD native H1-derivedH4 and XAUUSD admittedM1.
No alternate timeframes/lookbacks/thresholds. P0 natural SL, daily flat20:00H1 /
20:30M1 and inherited asset guards; same stress fees and costs. Report raw
endpoint economics and dual-cluster(2018–20,2021–23) before stop replay.
Stage0 gates remain net mean positive each year and above friction, median
friction/SL<=12%, cost retention>=50%, cadence>=40/year, exact endpoints. Only
survivors receive SL-active replay in both ordering scenarios. H1 paths are
H1 assumptions, not syntheticM1 or measured intrahour DD. Missing M1 means not
eligible for exact account replay/promotion, even if dual-cluster positive.

## Track3–4: conditional account replay and read-only watcher

If a Track1 candidate passes, reuse frozen V19 native quote/event quarter tapes,
drop only rejected trade entry/exit actions and remap IDs; preserve quotes,
session/reset clocks, costs/SL/exits/lot rules/shared budget/house-money behavior.
No daily-PnL proxy. Dev selected policy unchanged in Full evaluation.
Full historical both orderings ×PRIMARY100/PRIMARY150/STRICT100,105 monthly
starts plus standaloneFunded; separate full ledger/path oracle for each.
Same5,000 common quarter draws/36months and12/18/24 prefixes, PRIMARY100 both
orderings, Challenge+standaloneFunded, full audits. Reuse baseline receipts with
hashes; don't sum overlapping account returns. Bootstrap is not future probability.
No winner→no new Full/MC child; later descriptive sleeve breakdown still delivered.

`--watch-mt5 --watch-timeout <seconds>`: default300s, bounded1–3600s,
poll default5s, capture default60s bounded1–3600s. Wait for already-running
terminal and FTMO DEMO/TRIAL USD account; no autostart/login/symbol_select or
orders. On ready, call existing native read-only capture, spec/parity and
ZstdParquet Bid/Ask. **Never silently switch to fixture replay** if terminal
vanishes between probe and capture. On multiple/unrelated/real terminal stay
blocked, log sanitized reasons, preserve timeout/failure receipts and account
binding. Symbols outside portfolio observed only. Sessions/commission/news may
stay unknown; read access is not shadow authority. No live broker execution.
Use fake-clock/native-reader fixtures and actual bounded no-terminal CLI to
verify waiting/timeout, detection/capture, disappearing terminal, account drift,
interrupt/failure output and no submission. Do not leave a daemon running here.

Private job `execution-v1/sleeve-ablation-and-mt5-v23-20261117` owns logs/events,
exclusive stage outputs, pins/corrections/checkpoints. New large tables direct
Zstd9 with original/compressedSHA256 and roundtrip; no price-cache duplication,
source deletion or unrelated cleanup. Existing budget/testing infrastructure.
Keep all1,280 IDs, meaningful new regressions,0skip. One final full suite<13.2s;
ten fresh serial smoke/same78IDs each<0.72s. Profile justified bottlenecks first,
preserve outliers/failed attempts, never retry to select a faster streak.
Open PR102, leave open, wait3 exact-head CI, download/reconcile all test IDs.
Four-part report: sleeve/ablation, gap/F5, conditional lifecycle, watcher/perf/storage.
