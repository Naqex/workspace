# Recovery v2: eurusd-h4-utc-2024-historical-validation-v1

Parent protocol: [UTC-VALIDATION-20261107](UTC-VALIDATION-20261107.md); original registration remains immutable.
Owner task 07/11 authorizes consecutive offline research and bug fixes.

UTC v1 stopped at the first Jan 1 holiday calendar event before the first quote.
Compression v1 was canceled before changing shared numerical source. No completed
scenario exists in either attempt. Preserve their logs and partial artifacts.

Only calendar startup handling changes: a pristine flat account with no quote,
ledger, position, pending order or cash change records a zero-debit explicit
non-applicability event. It fabricates no quote/fill/cash ledger entry. After the
first observed quote, the original anchored financing guard applies. Reader must
validate every declared calendar event as charged or a matching valid exemption.
The exact opt-in contract is `explicit_not_applicable_v1`.

All parent rules, windows, prices, costs, risk, phase profiles, cutoffs and decision
criteria remain fixed. Inputs and verified caches are reused; no download/export,
no broker/model calls. 2025+ stays closed. Historical robustness, never clean OOS.
New source/protocol/registration binding; no weakening old source drift checks.
Synthetic holiday/open-position/tamper regressions pass before dispatch.
No automatic retry or claimed mid-scenario resume; finite native controller.
