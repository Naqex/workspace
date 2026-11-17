# V22 — ex-ante exhaustion, H1 clocks and bounded MT5 preflight

Owner attachment `099856be-7fc9-4543-aa69-f76a59bb0ca7`.
PR100/head `1118904` merged `ec0cbe7`; V21 local/remote branch removed.
Use `codex/exhaustion-gate-and-h1-align-v22`. Preserve Trader pin, VI WIP,
all sources/freezes/negative attempts. No Astra/subagents, memory updates,
provider downloads, account creation/login, broker orders or product deployment.

## What this experiment can and cannot conclude

L3 uses losing outcome + MFE<0.25R + range/ATR>0.90, so it is retrospective.
An executable gate can use range/ATR only and must also count rejected winners.
The45 losses/−20.73R are full-period descriptions; Dev has27 exclusive L3 losses.
Do not promise to save all losses or retain the known future top10. One failed
BE policy does not prove all trailing exits fail; ATR is not a daily range cap.

Fit only Dev2018–2023, with existing2017 warmup. Earlier V21 full-period/top10
results are already exposed; no clean OOS claim. Before opening new Full entry
snapshots, commit Dev selection/freeze. Full anatomy is descriptive after freeze,
never an excuse to choose another threshold. Keep V19 canonical494/fixed150USD
and V16 separately (different timeout exits).

## Track1: two gates, no new stop/exit/sizing parameters

Snapshot every Dev entry, then full baseline entries after freeze: sleeve/side,
decision-known UTC day high/low/range, latest closed D1 Wilder ATR14,
range/ATR, same-direction day-edge minus executable entry, signal candle
body/range divided by latest closed H4 ATR14. Last known M1 is strictly before
decision. Include separate global top10 (already exposed) and Dev-only top10;
all45 full L3 rows, split by period, with unknown/provisional flags.

Register exactly two executable variants before their outcomes:

1. `G_L3_A`: refuse F3/F4 (Gold) entries with day-range/closed-D1-ATR>0.90.
   EURUSD F5 unchanged. Missing covariate abstains and is separately counted.
2. `G_L3_B`: same F3/F4 scope, threshold = 90th percentile of **all finite Dev
   decision-known ratios per sleeve**, without labels/returns/Top10 as fit inputs.
   Normalize each sleeve ratio by this frozen threshold; refuse normalized>1.
   No search over percentile, multiplier, candle shape or side. EURUSD unchanged.

Dev gate, both M1 orderings: retain>=90% of Dev-only top10 winner identities,
net strictly higher; peak-to-valley marked equity R-DD strictly lower;
Ex-Top10 NetR higher than baseline (report sign, do not claim it was negative
without measuring). Remove each candidate's own largest10 for this metric;
also show removal of original baseline top10 identities. Top5 reported too.
Worst daily marked loss may not increase. Signals/exits/SL/cost/size unchanged
on retained trades; source gaps remain. Compare W1/L3 and rejected winners as
diagnostics, never tune to labels. Count all two trials even if both fail.

If both pass, rank by Dev worst-order Ex-Top10 improvement, then Calmar, then
lexical ID. Freeze one winner only. No reselect using later results. Do not
raise risk or adjust stops to create smoother carry.

## Track2: resolution-aware replay, finite inherited recipes

Original24 B2 +4 B3 parameters stay unchanged. Reuse exact hash-bound22
unaffected M1 cases; recompute6 GBP H1 B2 cases with corrected clock. Add6 AUD
H1 B2 cases explicitly as an owner-mentioned extension, not hidden in the28.
No new B3 asset/time grid. Use V21 corrected two-sided-sweep abstention.

H1 deadline = floor to UTC hour of min(20:30UTC, declared holiday early guard),
normally20:00UTC; M1 unchanged. Never use last available price chosen after seeing
a gap. Model entry/exit on observed H1 opens at registered boundaries, show
19–20 close separately when needed; an H1 OHLC timestamp does not certify an
exact broker tick. Missing20:00 quote or earlier holiday quote stays missing.
No guarantee of100% endpoints or FTMO compliance; daily session/news/spec still
must be verified. Same-day holding under inherited costs has zero modeled swap.

Stage-0 unchanged from V21: net mean positive in every Dev year and both
three-year clusters; net mean exceeds same-unit mean stress friction; pooled
median friction/natural SL<=12%; cost-only retention>=50%; priced/admitted cadence
>=40/year; no unresolved primary endpoints. Report cost acceptance separately
from data availability. H1-only survivors get natural-SL H1 scenario replay in
both OHLC orderings, with endpoint-open truncation and no synthetic M1; they
remain ineligible for exact intrahour equity/daily-DD/account qualification until
an admitted M1/tick path exists. Do not call source limitation economic failure.

## Track3: conditional lifecycle, exactly one frozen candidate

If a gate passes, apply it to unchanged V19 quote/event tapes: remove only entry/
exit actions for rejected trades, remap block-local IDs, preserve every retained
quote/clock/order/cost/risk/admission/house-money rule. No daily-PnL surrogate.
Dev first before freeze; Full both orderings PRIMARY100/PRIMARY150/STRICT100,
105 monthly starts + standalone Funded, separate full ledger/path oracle each.
Source/cost stress retained; unknown remains unknown, not native qualification.

Run same5,000 quarter draws/36 months with12/18/24 prefixes, PRIMARY100 both
orderings; Challenge + standalone Funded per path and full separate audits.
Reuse baseline V16/V19 receipts with original hashes rather than rerun baseline.
Report Total/ExTop5/ExTop10 R, W1/L3, both-phase starts/conditional median and
bootstrap completion24 months. Frequencies are not calibrated future odds.
If no Dev candidate passes, no new Full/MC child; full baseline anatomy still
delivered, and baseline account results shown as reused.

## Track4: MT5 checker, storage, tests and PR101

`--check-mt5-ready`: bounded read-only connectivity/symbol-access diagnostic.
Inspect already running terminals before SDK initialization, never autostart/login.
Only FTMO DEMO/TRIAL USD allowed; unrelated/real accounts fail closed.
Show wall duration, connected state, last terminal-reported `ping_last` converted
µs→ms, quote age and readable-symbol status. This is not a freshly measured
network RTT or proof of full strategy readiness. No symbol_select/order_check/
order_send. Missing sessions/news/seeds/spec parity keep shadow blocked.
Measure actual1s target; no cold-start promise or fabricated ping.

Private job `execution-v1/exhaustion-h1-align-v22-20261117`: exclusive outputs,
events/checkpoints, Zstd9 + original/compressed SHA256 + roundtrip for new large
tables. Reuse price tapes, no cache duplication/deletion. All attempts retained.
Keep all1,261 V21 IDs, add meaningful tests to>=1,275, zero skips. One final full
suite attempt: hard<=13.5s, stretch<13.2s; ten fresh serial smoke processes same
78IDs: hard<0.75s each, stretch<0.72s. No retry to choose a faster streak.
Push PR101, leave open, wait three exact-head CI checks, download/reconcile all
IDs and save completion receipts. Four-part report: anatomy/gates, clock/B2/B3,
conditional lifecycle decision, checker/engineering/storage. No invented winner.

Sources checked17Nov2026:
[MQL5 initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py),
[Python API](https://www.mql5.com/en/docs/python_metatrader5),
[FTMO holding rules](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/).
Current account-specific sessions/news/specs remain unverified.
