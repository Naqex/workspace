# Complete checkpoint và CLI resume — phạm vi đã kiểm

Đã triển khai tại Trader `3ae4f844`/`b741bee1`, branch `codex/research-resume`,
checkout `C:/Users/MIIKEY/.codex/worktrees/replay-history-validation/trader`.
Workspace `3fe3b34` forward config `resume_scenarios_from`. D:source78a8397f và
research-metals native job e4481140 không bị thay trong lúc chạy.

## Hành vi mới

| Phần | Trước | Bây giờ |
|---|---|---|
| Trong một scenario | Account checkpoint chưa đủ state; thiếu phần còn lại thì phải attempt mới | Atomic packet mỗi24observedH1windows: execution/risk, strategy/builder, quyết định, horizons, phase accounts, observer/reset/financing và input cursor |
| Completed scenario | Có seal để reuse | Giữ nguyên; resume mode ưu tiên reuse seal, chỉ restore scenario chưa xong |
| Gián đoạn | Không được tự gọi restore từ account JSON | CLI `--resume-scenarios-from <stopped-attempt>`, output mới; worker/root/code/data/cost/protocol/runtime phải khớp |
| Prefix đã tính | Phải replay numerical toàn bộ | Hash/validate lại input và kiểm count+lasttick của prefix; bỏ numerical decisions đã lưu, tiếp từ đúng H1boundary |
| Legacy/corruption/source drift | Có thể dễ bị hiểu nhầm snapshot là resume | Missing packet/checksum/binding/risk/profile/cursor mismatch fail rõ; không silent rerun/migration hoặc nới kiểm tra |

Restore kiểm cả nested session profile và phase initial capital. Phase2 dùng
effective-from của account phase, không ép thời điểm bắt đầu cả study; case
kiểm phase2 đã bắt lỗi này và sửa trước commit. Observer chứa cả firstbreach,
drawdown/headroom, reset, counters và state machine; không dựng lại từ finalPnL.

## Bằng chứng

- Suite liên quan:104tests/112subtests đạt trước final profile hardening;
  sau đó14resume/reuse tests/13subtests và3observer guard subtests đạt. Không
  chạy lại toàn bộ suite không đổi chỉ để tăng con số.
- Có interruption/EOF/openposition/financing/Prague reset, actual phase-account
  reset, H1Asia quote gap/pendingexit, changedbinding/risk/inputprefix và CLI
  seal reuse+partialresume. Final execution/candidate/decisions/prop/horizon
  artifacts khớp bytes với uninterrupted run. Missing legacy packet bị reject
  trước simulation, không lén replay.
- Actual consumedDec22–31/2023:442.341ticks,100causalH1warmup, ASIA policy,
  current declaredprofile/risk/cost. Cắt sau packet đầu (114.227ticks), restore
  và đối chiếu full result cùng4finalfiles exact;6closedtrades,−9,42USD giữ nguyên.
  v1source3ae4f844 đạt; v2sourceb741bee1 sauprofile guard cũng đạt.
  v2uninterrupted9,62s, resumed8,23s **chưa gồm công prefix đã thực hiện trước
  interruption** và vẫn đọc/validate prefix. Không annual speedup/capacity claim.
- Driver/source/input hashes, exact artifacts và result ở privatecampaign
  execution-v1/`native-resume-parity-v1/` và`native-resume-parity-v2/`.
  Inputcrop từ pinned consumed2023, warmup từ source-bound H1cache đã kiểm;
  không sort/fillgaps/2025+/broker/LLMcalls.

## Giới hạn và vận hành

Hai Londonparents cũ đã timeout không có complete packet của schema mới,
**không tự phục hồi chúng bằng tính năng này**. Giữ reference seals và partial
evidence; chưa nhận fullannual stress. Không chạy lại cả batch chỉ để diễn
feature mới. Source drift khi sửa economic bug vẫn cần registration/compatibility
review riêng; source unchanged là điều kiện resume, không tên strategy giống nhau.

Snapshot lớn hơn và thêm serialization khoảng mỗi24observedhours; chưa đo
annual overhead của feature mới. Checkpoint chỉ giảm rework khi ngắt, không
chứng minh edge, broker realism hoặc C1. Future expensive run phải pin source
này/đăng ký scope trước outcome. Sau khi nativewriters kết thúc đã fastforward
D:source lên9fd6cd00, giữ18parent-source files78a8397f với verifiedhashsnapshot.
Discovery12 đang pin source mới; không sửa numerical files trong lúc job chạy.

Git metadata của checkout replay-history-validation từng resolve nhầm vào
submodule gitdir. Đã đối soát clean explicit-worktree status, sửa **per-worktree**
`core.worktree`, tạo branch mới từe9ac3683; cả D: và research-metals vẫn resolve
đúng và active source files không đổi. Không sửa global Codex/Gitpolicy.

## Follow-up08/11: nested candidate identity

Ca phápacket thực tế cho thấy innercandidateNYORB có thể được restore dưới
outercontextASIAORB nếu recomputechecksum; type/statevalidators riêng chưa
chặn được đổi policy cùngclass. Trader`7ab57907` thêm identitycomparison trước
restore; regression failedtrướcsửa rồi15resume/reuse tests+13subtests đạt.
Không đổi signalmath hoặc healthyresumeoutcome. Bản sửa ởcheckout riêng trong
lúcDiscovery12/13pinD:9fd6cd00; chỉfastforwardD:7ab57907 sau cả2jobs completed,
artifact/sourceaudit đạt. Oldpins/snapshots giữ,không tự nhận source mới đã
rerun624outcomes. Đây là scopedfix,không chứng nhận đầy đủ chống mọi tamper.
