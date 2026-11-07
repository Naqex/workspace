# GoldH4 — indicative screening và hậu kiểm

**Chưa có candidate đủchallenge.** [Frozen protocol](METAL-DISCOVERY8-SCREEN-20261108.md)
trước outcome, isolatedTrader112e2a26, reusablecoarse kernel. D:source78a8397f
không đổi khi EURUSDannualbatches chạy.

NetUSD trên10k, gồmfloating; **chuẩn/cao**, accounts riêng mỗi year:

| Rule |2021|2022|2023|2024|
|---|---:|---:|---:|---:|
|Donchian20/10|−111,89 / −139,83|−64,42 / −222,03|+91,72 / +24,85|+39,89 / −99,85|
|SMA20/80|+102,38 / +64,48|+13,03 / −23,77|+127,61 / +82,11|+293,23 / +265,73|
|Z20±2/time6|−150,79 / −201,36|+63,96 / +2,03|−119,13 / −205,78|−2,42 / −19,82|

SMA giữ research theo frozen3/4positiveyears+totalspositive; chưa edge, chỉ46
closedpositions. SMA2022/23cònposition;Donchian2021/23vàZ2021cũng cònopen.
Không épclose hoặc cộng annualbooks thành continuousportfolio.2024Donchian
skipminlot87/104times vàZ164/166; đây là infeasible subset ở10k/risk25, không
proof family vô dụng. [Longhistory/capitalfeasibility](METAL-LONG-HISTORY-20261108.md)
đã freeze giữ0,25%, không nhânPnL10k×5 hoặc mua50kchallenge.

## Phạm vi kiểm/giới hạn

| Lát |Evidence / hành động|
|---|---|
| Data/source |1.773.334observedM1Bid;1.380/1.380sameassetminuteOHLC khớp206.215Dukascopyticks03/01/2023UTC; quotegrid0,001 verifiedday, Askmodeldeclared. Không nativeobservedticks vào simulation |
| Unit/sizing |100ozlot/0,001tick/0,01minstep, manualgoldPnL/risk/commission fixture;9tests/9subtests trước run;35legacytests/25subtests trước goldscope |
| Reuse/code |Cùngcoarseexecution/cost/financing; newtypedmetalspec+candidateidentities, không monkeypatch EURUSD hoặc nới ForexPilotSnapshot nativeguard.32actuallegacyQ1rows exact mọi fieldtrừtiming |
| Workspace issue |Managedworktree kếthừacore.worktree từsubmodule, Gittrỏsaimetadatafolder; explicitper-worktreecore.worktree sửa đúngcheckout, D:giữclean/branch. UnchangedreaderfilesLF/CRLF làmcachemiss; đồngbộbytes đúngbaseline sauverify normalizedsame, không bỏhashguard. Failedparityattemptv1 giữ, v2verified |
| Accounting |24/24rows balance/equity/floating/tradecounts independentlyreconciled; snapshots giữ21sources |
| Speed |26,27s total;M1aggregateonce~18s,24scenarios~7s; noGPU/newnumericalengine. Preparation/export49,93s làjobriêng; không cộngactivewall của parallelwork |
| Economic realism |ConstantmodeledAskspread/slippage/financing; H1stopmodellevel/open, notfirstcrosstick. Nointernalbrakes/prop/intrabarDD/nativebrokeradapter; notqualified |

Privatecampaignexecutionroot: `metal-discovery8-screen/attempt-v1` giữmanifest,
source snapshot/quality/24results/accounting-review. `metal-legacy-parity-v1/`
failed binding và`metal-legacy-parity-v2/result.json` giữ32goldens. Khôngoverwrite
parentprotocol/sourcepins sau outcome. MetadataCLIversion/SRI/license/sample
checks trong [preparation](METAL-DISCOVERY8-PREPARATION-20261108.md).
