# Native survivors — kết quả đã có và coverage còn thiếu

**Chưa có ứng viên đủ C1.** Hai Londonjobs timeout, không nhận fullannual.
Đọc [frozen study](H1-SURVIVOR-TICK-REVIEW-20261108.md),
[recovery](H1-ASIA-RECOVERY-20261108.md) và [engineering review](ENGINEERING-REVIEW-CAMPAIGN-20261108.md).
Chỉ các dòng completed_verified/sealed được dùng làm final scenario evidence.

## Asia→London2024 — completed_verified

| Cost | Net3m/6m/12m USD trên10k | Closedtrades12m | Tick maxdrawdown12m | Headroom nhỏ nhất daily/overall | Phase/breach |
|---|---:|---:|---:|---:|---|
| Reference |−223,70 /+279,76 /+201,41|223|472,46USD|442,94 /691,57USD|Vẫn phase1, không observedbreach |
| Stress |−245,64 /+205,39 /+64,52|223|489,26USD|445,43 /661,16USD|Vẫn phase1, không observedbreach |

Source78a8397f,20.687.149observedticks mỗi cost; no open/pending ở cuối, không
forceclose hoặc internalriskstop. Task109,26phút worker. Dossier/protocol/hash/
source drift/cash/horizon inspections đạt. Chưa cleanOOS, brokerrealism hoặc
challenge-pass probability; no breach không tự là edge.

## Annual coarse→native attribution, không rerun

| Cost | Coarse/native net USD | Difference | Đối chiếu |
|---|---:|---:|---|
| Reference |278,01 /201,41|−76,60USD|324decisions exact,223trades cùng side/quantity/entryfill;122SLfills giải thích toàn delta;101strategyexits net exact |
| Stress |138,57 /64,52|−74,05USD|Cùng số liệu quyết định/count;122SLfills giải thích toàn delta;101strategyexits net exact |

Financing0cảhai vì intraday. Chênh lệch do H1modeledSLlevel thay cho native
first-crossingquote, không signalimplementation drift. Đây là measuredannual
approximation bias, không errorbound cho assets/years khác. Đúng lý do coarse
chỉ triage, không tự chứng nhận/loại cứng family; native review vẫn cần.

## Những dòng chưa hoàn tất

- London2024:reference seal đã có;+216,00USD. Stress timed_outở20.617.300/
  20.687.149ticks;worker7200,11s. Exitcode0ởtermination không là scenario seal.
- London2023:reference seal đã có;+388,35USD. Stress timed_outở26.436.285/
  27.549.175ticks;worker7200,08s. Không suy phần thiếu sẽ không đổi outcome.
- Asia2023parent:reference failed tại27.223.813ticks; recoveryv3 đã completed_verified.

## Asia→London2023 — recoveryv3 completed_verified

| Cost | Net3m/6m/12m USD trên10k | Closedtrades | Tick maxDD | Minimum daily/overall headroom | Phase/breach |
|---|---:|---:|---:|---:|---|
| Reference |+173,71 /+25,42 /+150,70|231|613,81USD|460,74 /691,65USD|Phase1;khôngobservedbreach |
| Stress |+137,09 /−53,27 /+18,79|231|643,96USD|460,22 /606,83USD|Phase1;khôngobservedbreach |

Nguồn e4481140/registrationbf63fed6…,27.549.175ticks mỗi cost,3150,45sworker/
3228,88sbatch gồmH1warmup. Cả2flat/no pending/nointernalriskstops;dossier mới
source/protocol/cash/horizons đạt. Chưa edge hoặc khuyên mua challenge.

## Recovery cho những lượt sau

[Complete resume](NATIVE-RESUME-REVIEW-20261108.md) đã được triển khai/kiểm rồi
fastforward vàoD:source9fd6cd00 sau khi mọi nativewriter đã kết thúc. Londonlegacy
checkpoints thiếu candidate/builder/observer state nên không tự resume bằng
featuremới. Giữ reference seals, không rerun chúng hoặc gọi partialstress đạt.
Source/data/protocol drift cần registration/compatibility review; không sửa pins.

Artifacts dưới privatecampaignexecution-v1/`h1-survivor-tick/`:
batch-2024-v1/asia-break/replay,`asia-2024-coarse-native-attribution.json`,
parentterminals và recoveryv3PROGRESS. Không broker/LLMcalls,2025+vẫn đóng;
C1/C2campaign còn ACTIVE.
