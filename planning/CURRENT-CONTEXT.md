# Current context — Naqex Workspace

16/11/2026 · `RESEARCH: V16_NO_QUALIFIED_BREADTH_ADDITION · SYSTEM: G2_STILL_SOURCE_UNCERTAIN · PROP: NOT_QUALIFIED`.

## Việc hiện tại

**V16 chưa có nâng cấp đạt zero-gap/time-fit; PR #95 giữ mở.**
[Báo cáo bốn phần](research/GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116.md) /
[JSON](research/GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116.json) /
[freeze](research/GAP-IMMUNE-MULTIASSET-V16-FREEZE-20261116.json) /
[protocol](research/GAP-IMMUNE-MULTIASSET-V16-PROTOCOL-20261116.md).
PR #94 đã merge `1c6e516`; nhánh V15 đã xóa. V16 đăng ký `d68a5d4`,
khóa `985df06` trước đo G2 mới trên 2024–13/10/2026 đã exposed giá.
715 DAY cells: Gold 198, EUR 103, US500 202, GBP/AUD mỗi asset 106;
0 qualified additions. GBP/AUD thiếu M1 dài hạn; US500 0/202 dương cả hai
cụm Dev; 18 Gold + 11 EUR qua Stage-0 đều còn gap, đa số thiếu cadence.
G2 daily flat 20:30 UTC dùng lịch biết trước, không hindsight outage exits.
494 signals, 0 overnight nhưng 32 source-uncertain trades (Dev 25).
SYM hai order: primary 71/105, median 47,08 tháng; strict 1/105.
Strict median 18,95 tháng chỉ của một start 02/2023, không chứng minh nhanh.
Cả hai vẫn 0/33 recent starts; 0 breach mô hình không là bảo đảm broker.
G1 thêm 0 M1; 38 native-envelope cases có 0 quote trong phút thiếu;
zero recorded ticks không chứng minh continuity. Giữ V15 làm research baseline.
Sửa Gold P1 một ô giá bằng regression; audit scanner 85.387 endpoints/
7.624 paths; A cash/active levels parity giữ nguyên, không mở grid mới.
Nén 8 console logs, SHA/restore trước xóa bản dư: 53.155.811 bytes →
2.657.786 bytes; nguồn/freezes/ledgers/path và packages giữ nguyên.
Private job `execution-v1/gap-immune-and-multiasset-v16-20261116`.
1.138 tests/0 skip, giữ đủ 1.126 IDs cũ; full wall 34,01→28,23s.
Smoke 10/10 <0,80s, max 0,758s. CI exact-head receipts và giới hạn nằm
trong báo cáo, đối soát bằng artifact tải về sau push. Giữ VI WIP/Trader pin.
Không broker/deploy/provider downloads/Astra/memory update; không merge PR #95.

## V15 đã merge (lịch sử)

**V15 đã hiệu chỉnh sizing trên Dev; chưa đạt time-fit.**
[Báo cáo bốn phần](research/BRIDGE-AND-VELOCITY-V15-RESULTS-20261115.md) /
[JSON](research/BRIDGE-AND-VELOCITY-V15-RESULTS-20261115.json) /
[freeze](research/BRIDGE-AND-VELOCITY-V15-FREEZE-20261115.json) /
[protocol](research/BRIDGE-AND-VELOCITY-V15-PROTOCOL-20261115.md).
PR #93 đã merge `69bc7a6`, nhánh V14 đã xóa. Candidate B dừng tối ưu; giữ
năm sleeves cho attribution. V15 đăng ký `7ed51a5`, khóa code/sizing
`4b426ae` trước khi đo sizing mới trên 2024–13/10/2026 đã exposed giá.
Dev chọn factor 1,5: risk 300/262,50/187,50 USD, có throttle/cap/reserve.
SYM full: V14 48/105, median 54 tháng → V15 63/105, 41,03 tháng →
cushion 66/105, 34,85 tháng; chưa đạt mục tiêu <18 tháng.
Static max 8,13102%; cushion daily max 2,36724%; không breach mô hình.
Đó không phải chứng nhận an toàn broker hoặc tỷ lệ thành công độc lập.
296 clean/44 uncertain Dev giữ trung vị 5,13/18,77 giờ; uncertain vẫn 17 lệnh thua.
38 conditional native-envelope exclusions + 95 model-low-risk gap occurrences;
0 chứng nhận thị trường tuyệt đối. Primary stress 0 patches bằng baseline;
all-uncertified shared-path stress 133 bars chỉ 0/105 hoàn tất hai vòng.
47 duplicate targets đã có disposition: archive+restore+SHA rồi xóa 2 copies
(11.875.972 bytes logic, archives 3.247.516 bytes); 45 package subtrees giữ toàn vẹn.
Không lặp purge 4 cây V14. Giữ VI WIP/Trader pin, không broker/deploy/Astra.
PR #94 đã merge trong V16; receipts/test IDs/CI lịch sử giữ tại private V15 job.

## V14 đã merge (lịch sử)

**V14 đo đầy đủ A/B qua 2018–13/10/2026.**
[Báo cáo](research/EVIDENCE-AND-LIFECYCLE-V14-RESULTS-20261115.md) /
[JSON](research/EVIDENCE-AND-LIFECYCLE-V14-RESULTS-20261115.json) /
[freeze](research/EVIDENCE-AND-LIFECYCLE-V14-FREEZE-20261115.json) /
[protocol](research/EVIDENCE-AND-LIFECYCLE-V14-PROTOCOL-20261115.md).
PR #92 merged `65bf0c2`, V13 branch đã xóa. A/B khóa `ae575b7`; chỉ đổi cổng
tần suất thành trung bình >=50/năm theo quyền owner, không sửa verdict V13.
Core A 3 sleeves tốt hơn B thêm 2 sleeves về Validation: +13,89R vs +6,18R
SYM. A/SYM NEXT_QUOTE pass hai vòng 48/105 starts nhưng median ~54 tháng;
CLEAN_COHORT 0/105. Không phải tỷ lệ thành công độc lập hoặc filter chạy live.
Giá 2024–2026 đã exposed lịch sử; các M1 order/source scenarios không chứng
nhận native intraminute path. Chưa shadow/demo/broker, không actual payout.
4 E backup trees xóa với manifest/rehash, 47 giữ; VI WIP/Trader pin nguyên.
PR #93 đã merge trong V15; `codex/evidence-and-lifecycle-v14` đã xóa.
Errata kỹ thuật giữ original freeze và log; không đổi alpha/SL/exit/risk grid.

## V13 đã merge (lịch sử)

**V13 định giá được 19/19 cases trọng tâm; tổ hợp vẫn chưa qua Dev gate.**
[Báo cáo bốn phần](research/PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115.md) /
[JSON](research/PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115.json) /
[decision](research/PATH-RESOLUTION-AND-DEDUP-V13-DECISION-20261115.json) /
[protocol](research/PATH-RESOLUTION-AND-DEDUP-V13-PROTOCOL-20261115.md).
PR #91 merged `ad362ea`; PR #92/V13 đã merge trong V14.
Nhánh V13 đã xóa; kết luận dưới đây giữ nguyên theo gate tại thời điểm V13.
Private job `execution-v1/path-resolution-and-dedup-v13-20261115`.

Giữ đúng 28 cells/modes/entries/SL/costs V12, không grid mới. 19 cases chỉ
vướng path: 2.156/2.156 lượt được định giá theo next-quote scenario; toàn lô
3.165/3.179, hai EUR F5 H1/n10 còn 14 lượt clock-invalid (7 unique events).
Source uncertainty không bị xóa: gap giữa phiên có thể che một excursion.
Native timestamp probe: 48 gap có tick hours nhưng không quote; 328 gap
chưa có native hours được admission. Không source-verified component.

16 scenario components → 3 medoids bằng risk, pair corr đều <0,25.
SYM +50,232R, ASYM +52,386R / 6 năm, 4/6 năm dương, ex-best SYM +13,034R.
Nhưng 2018/19 chỉ 43/47 tín hiệu dưới sàn 50 mỗi năm đã khóa trước outcome.
Không hạ gate, đổi subset/weights hoặc nâng risk. 2024–2026 **CLOSED** trong
V13; lifecycle/payout/account daily/static **NOT RUN/N/A**. Daily UTC profile
không phải Prague/intraminute equity. Không clean OOS/Challenge candidate.

403 cây/887 cặp directory bao phủ 1.998 file pairs: 106 whole-tree equal;
0 tree errors. Không xóa vì equality không chứng minh dependency/source/
backup được retire. D V10→V12 chỉ +1.925.237 bytes, không +15GB; phân biệt
decimal GB/GiB. Hai VI permission gaps giữ nguyên. Giữ raw/old seals/pins/WIP.
Auditor 3.165 paths/31.650 cash legs, zero discrepancies; same implementer/feed.
1.091 tests/0skip giữ đủ 1.072 IDs cũ; smoke timing và limits ở report.
Native gap probe/read-only report không thay source hoặc rerun financial batch.
Source repair cần admission riêng; không tự mở chiến dịch/holdout/broker.

## V12 đã merge (lịch sử)

**V12 đã quét đủ 2.888 path cells; chưa có ensemble đủ điều kiện Challenge.**
[Báo cáo bốn phần](research/SL-ACTIVE-ENSEMBLE-V12-RESULTS-20261115.md) /
[JSON](research/SL-ACTIVE-ENSEMBLE-V12-RESULTS-20261115.json) /
[decision](research/SL-ACTIVE-ENSEMBLE-V12-DECISION-20261115.json) /
[protocol](research/SL-ACTIVE-ENSEMBLE-V12-PROTOCOL-20261115.md) /
[cent correction](research/SL-ACTIVE-ENSEMBLE-V12-CENT-CORRECTION-20261115.md).
PR #91 merged `ad362ea`, nhánh `codex/sl-active-ensemble-v12` đã xóa theo V13.
Private job `sl-active-ensemble-v12-20261115`; V13 ở trên thay đường resume,
không sửa kết luận/attempts của V12.

1.264 F1–F4 × P0/P1 + 120 F5 × P0/P1/P2 = 2.888 cells. P2 chỉ TP 3R,
không side/weight/subset search. 28 cells dương hai cụm trên phần có path,
gồm 20 F1–F4 và 8 F5 EURUSD. 19 trường hợp (13 Gold, 6 EUR) chỉ còn vướng
path gate; positive available-only không chứng minh toàn bộ expectancy.
K=0 qualified components; không diễn giải empty ensemble thành return 0.
Report so V11/P0/P1 trên common cohort, giữ censoring/source limitations.

Kernel full lần đầu 36,91s, toàn pipeline có IO/profiles/write lâu hơn.
Auditor bắt US500 gross/cent rounding và P1 plateau; giữ failed attempt,
commit `c88cafb` trước correction outcome. Chỉ rerun US500, reuse bốn asset.
Auditor không import core accounting; cùng implementer/feed, không independent
person review. Actual continuous account daily/static vẫn chưa đo.
1.072 tests giữ đủ 1.048 IDs cũ, 0 skip; smoke 66 tests / 0,670s.

Không mở giá 2024–2026 trong V12, không Challenge/payout/GoldA variant mới.
Historical validation đã có exposure, không clean OOS. Reference 1 lot chưa
actual sizing; không nhân R thành payout. Trader pin/VI WIP/frozen attempts giữ.
Storage chỉ census/archive metadata/bounded duplicate hashes, không xóa thêm.
Chặng sau cần source-path repair có budget; chưa thêm grid, tăng risk hoặc
tune để cứu phần dữ liệu còn thiếu.

## V11 đã merge (lịch sử)

**V11: 6 nhánh đạt tần suất tổng nhưng chưa đủ ổn định để đi tiếp.**
[Báo cáo bốn phần](research/ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115.md) /
[JSON](research/ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115.json) /
[decision](research/ENSEMBLE-AND-STORAGE-V11-DECISION-20261115.json) /
[protocol](research/ENSEMBLE-AND-STORAGE-V11-PROTOCOL-20261115.md) /
[source admission](research/ENSEMBLE-AND-STORAGE-V11-SOURCE-ADDENDUM-20261115.md) /
[clock correction](research/ENSEMBLE-AND-STORAGE-V11-CLOCK-CORRECTION-20261115.md).
PR #90 merged `2175685`, nhánh `codex/ensemble-and-storage-v11` đã xóa theo V12.
Private job `ensemble-and-storage-v11-20261115`.

Đã xóa đúng 17 target E theo manifest được duyệt: 119.790.227.244 bytes /
100.287 files / 12.101 folders. Không raw/research/VI WIP bị xóa. Net snapshot
khác exact purge do journal/job phát sinh; 2 VI permission gaps vẫn unknown.
Health audit tìm cả build cache mới, cảnh báo budget 120 GB; không daemon,
không tự mở rộng quyền xóa và không bảo đảm dung lượng tương lai.

Tìm lại GBP/AUD paired H1 và US500 paired M1; index read-only, không copy raw.
Reuse 544 ô V10 + 720 ô nguồn mới = 1.264 ô. Sau sửa lịch nguồn US500 bằng
helper đã có: 42 dual-positive → 33 component-admitted → 6 medoids bằng risk.
Giữ attempt đầu và correction protocol trước outcome; không sửa frozen V10.
516 tín hiệu / 6 năm = 86/năm, chỉ dương 4/6 năm. SYM endpoint NetR +59,421,
DD 47,585R; tỷ lệ 1,2487 thấp hơn nhánh tốt nhất 1,2868. Năm 2023 đóng góp
vượt tổng cả 6 năm. No-Go theo gate Development đã đăng ký.

Không mở giá 2024–2026, không SL-active/GoldA variant/Challenge/payout mới.
Daily/static loss là N/A, không lấy endpoint DD thành prop loss. Các năm
validation có exposure lịch sử, không clean OOS. Phí/Ask nguồn vẫn conditional.
Không broker/paid/Astra/runtime promotion; giữ Trader pin và VI WIP.
1.048 tests giữ đủ 1.030 IDs cũ, 0 skip; smoke 44 tests / 0,673s.
Fraction/scalar/source-quote oracle khớp; cùng implementer, không reviewer độc lập.
Chặng tiếp cần hypothesis/budget hoặc source work mới, không thử thêm subset/
weights hay tăng risk để cứu chính lô này.

## V10 đã merge (lịch sử)

**V10 đã kiểm xong: 0/544 cấu hình vượt Discovery; chưa có ứng viên Challenge.**
[Báo cáo bốn phần](research/ENTERPRISE-ALPHA-V10-RESULTS-20261115.md) /
[JSON](research/ENTERPRISE-ALPHA-V10-RESULTS-20261115.json) /
[decision](research/ENTERPRISE-ALPHA-V10-DECISION-20261115.json) /
[protocol](research/ENTERPRISE-ALPHA-V10-PROTOCOL-20261115.md).
PR #89 đã merge `3dd35a7`, nhánh `codex/enterprise-alpha-v10` đã xóa theo V11.
Private job `enterprise-alpha-v10-20261115`.

F1–F4 trên XAUUSD/EURUSD, Dev2018–2023,136 recipes ×4horizons.
Không có cấu hình qua toàn bộ cổng kinh tế/cadence; tất cả fail Holm/DSRproxy.
Không mở giá2024–2026, không Stage1/portfolio/lifecycle cho nhánh fail.
Ask/swap/calendar vẫn conditional; raw endpointR không SL-active/accountPnL.
Không cleanOOS, broker/paid/Astra/runtime promotion.

Fraction oracle bắt backward DAY exit; đã chặn cùng post-Friday-flat entry.
24cells/176occurrences invalidated, không đổi grid/entry/SL/quotes;
cluster scale dùng pooled medians đúng protocol. Original attempts/pins giữ nguyên,
Top15 không đổi,0economic/eligible.243.884priced occurrences ×2costviews đối soát;
V8 exact seals/V7 snapshot giữ nguyên. Same implementer, không independent person review.

1.030tests giữ đủ1.013IDs cũ,0skip; smoke30tests/0,64s.
Base serial40,96s→2process21,91s; full grouped Windows29,02s.
Signal cache16alternatingpairs giữ toàn bộ136recipes,6,29→1,39s (~4,52×).
Không gắn speedup signal/seek cho full account simulation.

D đọc được591.222→575.154files; giảm ròng362.263.076bytes.
E chỉ dry-run119.790.227.244bytes/100.287files build caches, chưa purge.
Hai VI permission gaps giữ nguyên; E có private research duy nhất, không mirror D.
[Maintenance](../tooling/WORKSPACE-MAINTENANCE.md) /
[quant core](../tooling/ai-engines/quant_core/README.md).
Chặng mới cần hypothesis/budget hoặc source/cost admission được giao;
không hạ gate, thêm grid hoặc tăng risk để cứu Top15.

## V9 đã merge (nền hạ tầng)

[Báo cáo4trụ cột](research/SYSTEM-AND-ALPHA-V9-RESULTS-20261115.md) /
[JSON](research/SYSTEM-AND-ALPHA-V9-RESULTS-20261115.json) /
[closure](research/SYSTEM-AND-ALPHA-V9-DECISION-20261115.json) /
[protocol](research/SYSTEM-AND-ALPHA-V9-PROTOCOL-20261115.md) /
[EUR admission](research/SYSTEM-AND-ALPHA-V9-EURUSD-ADMISSION-20261115.md).
PR88 merged `97a44f2`, nhánh V9 đã xóa. Private job `system-and-alpha-v9-20261115`.

D scanned633.571→591.665files, giảm11,84GB/4.627folders;2VIpermission gaps
không đụng ACL. Cache/Rust incremental đã purge;2coldvenvs nén và roundtrip.
E chỉ inventory +backup dry-run, không purge hoặc mirror các raw/evidence pins.
[Maintenance](../tooling/WORKSPACE-MAINTENANCE.md) và
[quant core/testtiers](../tooling/ai-engines/quant_core/README.md) là entrypoints.
1.013unique tests giữ995IDs cũ,18regressions mới;2anti-bloat fixtures riêng.
Warm seek same-slice9,79×; không full-campaign speed claim. Timings/receipts ở report.

Gold S1.DAY/S1.24H/S2.DAY và conditional EURUSD S2 đều fail Stage0 Dev
2019–20 +2022–23. Không mở validation để cứu hoặc chạy lifecycle cho nhánh fail.
9năm trong report chỉ reuse baseline control V8; không portfolio V9.
USD/oz raw endpoint khác SL-active NetR/account PnL.2018–2026 đều exposed,
cutoff13/10/2026; không giá mới saucutoff, broker/paid/Astra hoặc independent reviewer.

V8 exact-byte Dev/release seals đạt; V7 cần exact-byte view riêng do LF/CRLF
trên sharedsource khác V8. Không đổi oldpins hoặc numericalsource. Giữ failed
attempts và4same-byte JSON rewrites của lỗi snapshot path; hashes vẫn nguyên,
helper containment +regression đã sửa. Không claim V7 raw seal cùng một checkout.
VI WIP/Trader pin nguyên scope. Chặng tiếp cần hypothesis/budget hoặc source work
được giao rõ; không tự mở S3/risk tuning hoặc muaChallenge.

## V8 đã merge (bằng chứng nền)

[Report](research/PROP-GOLD-V8-RESULTS-20261115.md) /
[N2 conditional correction](research/PROP-V8-N2-CORRECTION-20261115.json) /
[calendar correction](research/PROP-V8-CALENDAR-CORRECTION-20261115.json).
N1/N2 và ba sweep horizons No-Go. Baseline2018–21 ASYM−52,16R là **net**;
gross2020 dương. N1 đổi cả compression/cost/stop gates, chưa chứng minh80%
ngày làfalsebreak. Giữnative gap~66phút09–10Oct2024 làDATA_PATH_INCOMPLETE.
995tests/492accountoracles/3.936costbridges cũ giữ nguyên; V9 không thay lịch sử.

## V7 đã merge (lịch sử; V8 thay verdict ứng viên)

**V7 đã sửa lịch và kiểm đủ 804 sổ; chưa đủ Challenge/thu nhập chính:**
[báo cáo](research/PROP-GOLD-V7-RESULTS-20261115.md) /
[JSON](research/PROP-GOLD-V7-RESULTS-20261115.json) /
[freeze](research/PROP-GOLD-V7-DECISION-20261115.json) /
[protocol](research/PROP-GOLD-V7-PROTOCOL-20261115.md) /
[calendar](research/PROP-V7-SESSION-CALENDAR-20261115.json).
Task `66e95afe-4594-4ddf-a63c-0278e67b3b78`, branch `codex/prop-gold-v7-audit`,
private job `execution-v1/prop-gold-v7-20261115`.
PR #85 đã merge `70b9ba1`, nhánh V6 xóa. PR #86 sau đó merge `c99fa7e` theo V8.

Freeze `b5e5f08`: Gold A BOTH entry/SL không đổi; EURUSD Sweep đã decommission,
chỉ còn trong đối chứng co-core. FTMO xác nhận Metals đóng 03/07/2026 17:00 UTC;
rule buffer 2 phút cho holiday từ 2025 cho exit 16:58, 931/931 đường lệnh có giá,
476/476 tín hiệu Gold có exit. 12 hồ sơ đổi deadline, 6 đổi thời điểm exit.
Mọi policy/phí đủ 57 mốc tới 13/10/2026, không data censor hoặc vị thế mở.
11 ngày có giờ đóng đích FTMO xác minh; lịch còn lại vẫn declared guards.

36 mốc cũ: co-core sửa lịch qua hai vòng 7/36 mỗi phí; Gold V4 0/36;
Gold tăng risk 0/36 SYM, 1/36 ASYM (37,38 tháng). 21 mốc mới đều chưa qua P1.
Gold giảm DD nhưng không tăng challenge completion. Jan2022 standalone Funded
nối gần 5 năm: Gold V4 trader 3.656,35/4.145,22 USD SYM/ASYM; Gold tăng risk
4.048,26/4.732,30 USD. Payout mô phỏng, không tiền nhận thực; năm 2024 không payout.

Annual cùng risk150: Gold Net R ASYM 5,9006 /16,4619 /2,6449 /−0,1347 /3,5321.
2026 có 72 tín hiệu có giá nhưng 71 thực thi vì minimum lot. Kết luận V6
“2025 dương” dùng risk125 (+2,9490R sau sửa lịch); risk150 âm do lot grid đổi
trọng số. Không coi Gold dương bền 4 năm ở cùng sizing, không chọn risk125 hồi tố.
Asia range/SL median tăng mạnh; ngày2 cứu 2022–24 nhưng làm giảm R ở 2025–26,
không đổi policy thành24h. Ba Gold Top10 cells chỉ reuse Dev, chưa đủ source/scale.

978 tests PASS qua 4 môi trường; oracle hữu tỷ PASS 402 sổ mỗi thứ tự M1.
Hai lỗi verifier đầu giữ nguyên attempts; sửa observe harvest trước admission,
không sửa producer/rerun kinh tế. Cùng implementer, không independent reviewer.
Gold 2025–26 vẫn Bid M1 + Ask proxy0,338, không native tick/prop certification.
Giữ label post-holdout cho mọi diễn giải mới; không giá sau13/10, broker/paid/
Astra/subagent; giữ VI WIP/Traderpin. Bước tiếp chỉ đề xuất: chốt target
quote/cost/news gaps và protocol dữ liệu thực sự mới; chưa promote/tune thêm.
Delivery/CI receipt ở private job.

## V6 đã merge (lịch sử; lỗi endpoint đã được V7 xử lý)

**V6 đã chạy, có payout mô phỏng nhưng chưa đủ điều kiện Challenge:**
[báo cáo](research/PROP-V4-HARVEST-V6-RESULTS-20261115.md) /
[JSON](research/PROP-V4-HARVEST-V6-RESULTS-20261115.json) /
[freeze](research/PROP-V4-HARVEST-V6-DECISION-20261115.json) /
[protocol](research/PROP-V4-HARVEST-V6-PROTOCOL-20261115.md).
Task `ed4d3a18-01c0-4907-8e16-5ffbd13e4440`, branch
`codex/prop-v4-harvest-v6`, private job `execution-v1/prop-v4-harvest-v6-20261115`.
PR83 merged `5a8dd69`, nhánh V5 đã xóa.
V6 ở [PR #85](https://github.com/Naqex/workspace/pull/85), đã merge `70b9ba1` theo V7;
GitHub cấp số85 thay cho84 dự kiến. Delivery/CI receipt nằm ở private job.

Freeze `665ed5b` trước mở giá; giữ V4 $200/$175/$125, cap800/reserve46k,
bỏ D1/D2/ratchet, harvester chỉ Funded.72checkpoint cuối2024 khớp V4.
24 standalone Funded cases (12 quý ×2 phí): Jan2022 có12 payout, trader
3.667,64 ASYM/3.856,49 SYM USD trong3năm; riêng2024 không payout.
Max daily12mốc0,795/0,832%, max static7,909/7,995%, không modeled breach.

Owner đã cho phép đọc giá/signals/PnL 2025–13/10/2026. Đoạn này nay consumed,
không còn timestamp-only hoặc pristine OOS mới; không tune lại trên đó.
EUR38.292.958 paired ticks tới13/10:2025 -14,5963R,2026 -3,5090R.
Gold632.140 BidM1, Ask proxy0,338 USD/oz khóa trước release; không native tick.
Gold2025 +2,82/+2,96R;2026 chỉ known-cohort+1,70/+2,04R, thiếu1exit,
2tín hiệu không đạt minlot ở risk125. Không gọi Gold2026 đã dương trọn kỳ.

Gold02/07/2026 thiếu quote ở hạn nghỉ lễ03/07 17:00UTC: censor tài khoản
còn giữ lệnh tại hạn này, không carry unknown exposure tới tháng10. Giữ attempt
lỗi riêng; candidate không đổi.36mốc cũ SYM/ASYM P1 23/26, hai vòng7/7,
payout23/21events; tổng trader chồng lấn6.678,20/6.369,78USD, không thu nhập
một tài khoản.20/21sổ cũ và17/21sổ mới censored; mốc mới chưa pass trước cutoff.
Không modeled breach trên đoạn đã đo, không bảo đảm phần thiếu.967tests qua
runtime matrix;252alternate-accounting cases đạt, không independent reviewer.

Đính chính: V4 Funded từ10/2023;49.751,56 là V3, không phải V4. FTMO FAQ
fetch TLS lỗi;14ngày/80:20/zero admin delay vẫn proxy. Không broker/paid/Astra/
subagents; giữ VI WIP/Traderpin. Báo cáo giữ full ledger/failed attempts locators.
Các trạng thái V5 trở xuống là lịch sử; phạm vi holdout cũ đã được V6 thay thế.

## V5 đã merge (lịch sử)

**V5 đã có kết quả, không promote; source/exact-MC gates còn thiếu:**
[báo cáo](research/PROP-OVERNIGHT-V5-RESULTS-20261115.md) /
[JSON](research/PROP-OVERNIGHT-V5-RESULTS-20261115.json) /
[quyết định](research/PROP-OVERNIGHT-V5-DECISION-20261115.json) /
[protocol](research/PROP-OVERNIGHT-V5-PROTOCOL-20261115.md).
Task `36b050c6-aa94-4b8c-bb1d-8c5520b23a61`, branch
`codex/prop-overnight-v5`, private job `execution-v1/prop-overnight-v5-20261115`.
PR82 merged `5beeb75`, branch V4 xóa. Không tự merge PR V5.

Rà local/QDM không có GBP M1/tick2022–24; upstream fixtures GBP2012,
AUD2020/USDJPY2013 không đúng kỳ. 28 thiếu ban đầu là24US500+4AUD;
tái dùng V3 sửa715/732US500 endpoints,17unknown còn giữ nguyên.
Không third sleeve, không tự tải dữ liệu từ provider mới.

EUR DD35,757R: đỉnh30/09/2022, đáy10/03/2023, hồi đỉnh trên tick18/10/2023.
BUY góp17,665R/SELL18,093R. D1(rangeAsia>2ATR) netDev4,829R/DD35,899R;
D2(coldDD8R/factor.5/recover4R) net9,967R/DD23,351R, mất tốc độ2023.
Cả hai rớt cổngDev, giữPARENT. Recheck year-carry bằng continuous closed cash
thay annual standalone cold starts xác nhận cùng verdict, không thêm trial.

V5 giữ V4 risk/cap/reserve, thêm ratchet7%/5% và3,5%; harvester1%/2%,
requestproxy14ngày. Commit`c63a255` trước2024 replay. 72accounts:
ASYM P1 6/36,hai vòng1/36; SYM4/36,hai vòng0. Payout0, không modeledbreach.
Worstpeak12,957/12,773%, chưa<9,5%; static7,994/7,995%, daily1,280/1,341%.
15SYM/14ASYM phase1 đứng ở protectedfloor;32dynamic closes dùng quote thật.
FundedASYM một đường, balance cuối49.683,57USD; không harvesttrigger.

231tests/22V5fixtures và oracle72accounts/9.532admissions/11.952rejects/
32nativeforcedfills/104.985.511quotes đạt. Cùng implementer, không independent
human/model reviewer. Holiday-null failure và reference-admission bug giữ
failed artifacts; không dùng outputs lỗi để chọn.

10.000paths/model/block20day và5day sensitivity, challenge/funded start riêng.
512scalar/vector bridges đạt, nhưng daily-flat surrogate khác exact lifecycle,
không qualification/xác suất tương lai. Exact V5 event-bootstrap còn chưa đạt.
Không coi CI xanh là toàn bộ mega-task acceptance đạt.

Owner đã cho phép timestamp-only holdout audit: Gold632.140M1 tới13/10/2026,
EUR657.549M1 tới07/10;445/458 ngày thường07–21UTC đủ timestamp,33/20ngày
gap/nghỉ chưa phân loại;GBPabsent. Không đọc cột giá/indicator/signals/PnL
holdout, không update/download. Chưa certified Stage1/fullwindow/pristineOOS.
Giữ VI DubberWIP/Traderpin, không broker/model/paid/Astra, không mở nghiên cứu
mới hoặc holdout strategy. SourceGBP/exactMC blockers ở báo cáo; giữV3/V4benchmark.
Delivery/CI receipt ở privatejob; không numericalwriter còn chạy khi bàn giao.

## V4 đã merge

**V4 đã hoàn tất, chưa payout hoặc sẵn sàng mở full holdout:**
[báo cáo](research/PROP-COCORE-V4-RESULTS-20261114.md) /
[JSON](research/PROP-COCORE-V4-RESULTS-20261114.json) /
[quyết định](research/PROP-COCORE-V4-DECISION-20261114.json) /
[protocol](research/PROP-COCORE-V4-PROTOCOL-20261114.md).
Task `d6d78dc3-c7e9-40ee-a684-61490c368f27`, branch `codex/prop-cocore-v4`,
private job `execution-v1/prop-cocore-v4-20261114`.
Tên campaign dùng ngày UTC 14/11, bàn giao ngày địa phương 15/11.

PR81 đã merge `5864d8b`, branch V3 xóa. Top10 chỉ xét Dev 2022–2023:
không third sleeve đủ source/scale/carry gates. GBP Asia/London có screen
dương nhưng chỉ H1, QDM không list GBP cached dataset. EUR thực tế có
Dev drawdown 35,757R so với net14,334R, không gọi đường vốn mượt.
Trong 13 cửa sổ V3 chưa xong vòng2, 7 dương/6 âm. V3 funded equity từng
50.379,30USD nhưng flat balance đủ14/30ngày cao nhất49.849,38USD.

Một trial co-core: hai nhánh $200/$175/$125 theo phase, cap mở1,6%,
reserve floor46k (8%), throttle4%/6% và daily halt2% giữ nguyên.
48 Dev accounts đạt: worststatic7,9359%, daily1,34082%.
Commit composition `8b1bfba` trước replay2024; không chọn theo2024.
144 V4 accounts (36starts ×2models ×14/30day proxies): ASYM quaP1 14/36,
qua2vòng3/36; SYM13/36 và2/36; payout0 ở cả14/30ngày.
Mỗi model chỉ một đường funded riêng, không độc lập. Worststatic7,994/7,995%;
daily1,280/1,341%; peak-to-valley14,365/14,468% vốnđầu. Không modeledbreach.
Caprejects0 nhưng reserve chặn nhiều hơn V3; không tăng risk tiếp để ép payout.

209 tests (12 fixtures V4), oracle144accounts/32.866 admissions/
10.102 rejects/104.985.511 jointquotes đạt. 72V3defaults tái hiện đúng cash,
DD,accepted/closed/rejects/lifecycle. Cùng implementer, không independent
human/model review. Không numericalwriter còn chạy; delivery/CI receipt tại job.

Chỉ QDM symbol metadata: EURtick quảng bá tới01/11/2026, EURM1 07/10,
GoldM1 13/10; Goldpairedticks2025–26 chưa được chứng nhận. Chưa fullwindow
01/2025–10/2026 hoặc pristineOOS certified. FAQ FTMO fetch lỗiTLS;14ngày là
request proxy, không currentofficial acceptance hay tiền nhận thật.
Giữ giá2025–26 đóng, VI DubberWIP/Traderpin; không broker/model/paid/Astra,
PR82 sau đó đã merge `5beeb75` theo chỉ thị V5; branch V4 đã xóa.
Các trạng thái bên dưới là lịch sử, không phải hàng đợi thực thi.

## V3 đã merge

**V3 đã hoàn tất Phase 0–4, chưa đủ điều kiện Challenge:**
[báo cáo](research/PROP-PORTFOLIO-V3-RESULTS-20261114.md) /
[JSON](research/PROP-PORTFOLIO-V3-RESULTS-20261114.json) /
[composition](research/PROP-PORTFOLIO-V3-DECISION-20261114.json) /
[protocol](research/PROP-PORTFOLIO-V3-PROTOCOL-20261114.md),
task `ded836a8-3f42-4204-9742-9fc0ad3c369e`.
PR #80 đã merge `91dd2d5`, nhánh cũ xóa; nhánh giao V3
`codex/prop-portfolio-v3`, job `execution-v1/prop-portfolio-v3-20261114`.

Funding reserve chỉ dùng deadline biết trước, không nhìn exit tương lai.
Một trial D1 SMA50/slope5/0.5x làm giảm tỷ số Net/DD, giữ A_Original.
112 Natural-SL screens; 42 đủ đường cho M1 scenario. US500 khôi phục
715/732 endpoint cũ, 17 còn unknown; GBP/AUD thiếu M1/tick, USDJPY thiếu nguồn.
Lượt lỗi Ask=0 ở Gold giữ nguyên trong quarantine, không dùng để chọn.
Chỉ chọn `EURUSD.SWEEP.ASIA.LONDON.DAY`: tick Dev +3,7714R / +10,5621R,
112/124 lệnh, correlation ngày khoảng 0,10; cải thiện Net/DD ghép nửa ngân sách.
Composition commit `ec602f7` trước release/mở 2024; LF/CRLF preflight đã chặn
trước release, semantic/byte binding sửa rồi commit lại, không đổi tham số.
Historical Validation 2024 của EUR: 67 lệnh, +6,3371R; đã exposed, không clean OOS.

144 accounts (2 models × 2 systems × 36 monthly starts), cùng shared-account
lifecycle và joint paired ticks. Portfolio qua vòng 1 15/36 ở cả SYM/ASYM;
hoàn tất hai vòng 0/36 SYM, 2/36 ASYM, payout 0. Hai cửa sổ ASYM chỉ có
một đường funded riêng biệt: funded lỗ $1.096,26 cuối 2023, lãi $847,82
năm 2024, cuối mẫu $49.751,56. Không suy thành xác suất pass tương lai.
Worst static portfolio 6,998% / 6,997%, sát reserve nội bộ 7%;
worst daily 1,132% / 1,071%; không observed modeled breach.

197 tests (21 fixtures V3) và bốn đối soát đạt: 112 screens, 420 D1 decisions,
25.447.523 tick EUR khớp CSV gốc, 144 account ledgers cùng admissions/rejections.
Cùng implementer dùng phép tính khác; không reviewer người/model độc lập.
Giữ A + EUR để review hữu hạn tiếp theo, chưa Challenge/thu nhập chính:
không payout, top-trade concentration, completion phụ thuộc swap proxy,
actual target spec/news/margin/feed/forward còn thiếu. `prop_qualified=false`.
Không numerical writer còn chạy; CI/delivery receipt ở private job.
Giữ đóng giá 2025–2026, WIP VI Dubber; không broker/model/paid/Astra,
PR81 sau đó đã merge `5864d8b` theo chỉ thị V4; nhánh V3 đã xóa.

## V2 đã hoàn tất

**V2 đã hoàn tất phép đo, chưa đủ điều kiện Challenge:**
[báo cáo](research/PROP-ATLAS-V2-RESULTS-20261114.md) /
[JSON](research/PROP-ATLAS-V2-RESULTS-20261114.json) /
[quyết định đã khóa](research/PROP-ATLAS-V2-DECISION-20261114.json) /
[protocol](research/PROP-ATLAS-V2-PROTOCOL-20261114.md).
PR #79 đã merge `a42fb9f`, nhánh cũ đã xóa. Nhánh giao V2:
`codex/prop-stage0-atlas-v2`; private job `execution-v1/prop-atlas-v2-20261114`.

2024 BUY +14,689R / SELL −12,044R; 13 tài khoản cũ vòng 2 đều hết dữ liệu,
không vi phạm DD. CA1/CA2 không đạt đủ cổng Development, giữ A0.
Atlas 112 cấu hình / 5 tài sản: 84 đủ endpoint nhưng không qua cổng, 28 còn
thiếu endpoint; 0 sleeve. Stage-1/correlation N/A, không dựng portfolio giả.
Risk v2 trên 36 mốc tháng/mô hình: SYM qua vòng 1 2/36, ASYM 5/36;
không hoàn tất hai vòng, không payout. Worst static 6,157% / 6,083%,
worst daily 1,071% / 0,979%. Cổng dự trữ 7% chặn 0 lệnh.

176 tests và bốn đối soát số học đạt, gồm 72 tài khoản; cùng implementer,
không gọi là review độc lập bởi agent khác. Cổng dự trữ kế thừa dùng exit
đã biết cho funding; kiểm lại bằng deadline khóa trước không đổi admissions,
nhưng helper chưa đạt nhân quả cho vận hành. Decision JSON khóa private trước
replay, chỉ commit lúc báo cáo: sai lệch yêu cầu commit trước Phase 3 được ghi rõ.
Giữ A0 làm benchmark, chưa đủ Challenge/thu nhập chính. Năm 2024 đã exposed,
chỉ Historical Validation; không mở giá 2025–2026, broker/model/paid.
Giữ WIP VI Dubber; không tự merge PR V2, gửi Astra hoặc mở chiến dịch mới.

## Chiến dịch V1 đã hoàn tất

**Chiến dịch exit → sleeves → phase-aware36monthlystarts đã hoàn tất:**
[báo cáo duy nhất](research/PROP-QUALIFICATION-CAMPAIGN-RESULTS-20261114.md) /
[JSON](research/PROP-QUALIFICATION-CAMPAIGN-RESULTS-20261114.json) /
[protocol](research/PROP-QUALIFICATION-CAMPAIGN-PROTOCOL-20261114.md).
PR78merged`3307fae`; freeze`95e3709`, Devdecision/code`2e713c1`.
Không E1/E2/E3 hoặc S1/S2/S3 nào đủ cổng Dev; giữ A0, không sleeve.
Risk.50→.35→.25%: P1 8/36SYM,13/36ASYM; P2/payout0; observedbreach0.
Worststatic9,321/8,899%, không đủ buffer để khuyến nghị Challenge.
147tests +72accountoracles +2.464Fractioncostbridges đạt; cùng implementer,
không Astra/agentreview. Chỉ2022–23select;2024HistoricalValidation;
khônggiá2025–26/broker/model/paid. WIP VI Dubber nguyên vẹn.
Privatejob`execution-v1/prop-qualification-campaign-20261114`; không numericalwriter
còn chạy. Branch`codex/prop-qualification-campaign` chờ owner duyệt PR, không tự merge.

## Baseline trước chiến dịch

**Đã hoàn tất calendar + Historical Validation 2024 + rolling accounts cho A BOTH/noTP.**
PR77 merged `3406ed1`, nhánh cũ đã xóa. [Protocol](research/XAUUSD-A-HOLIDAY-VALIDATION-PROTOCOL-20261114.md) /
[báo cáo](research/XAUUSD-A-HOLIDAY-VALIDATION-RESULTS-20261114.md) /
[JSON](research/XAUUSD-A-HOLIDAY-VALIDATION-RESULTS-20261114.json).
Lịch freeze trước mở2024: Friday20:30, holidayguard17UTC, GoodFridayevecut;
không đổi tín hiệu/SL. Coverage103/103,107/107,98/98; không loại ngày theo outcome.
11M1revisions2024 sửa workingcopy trướcPnL, all308signals/SL identical;
giữ nguyên original và attempt1fail. Hai phút cótick thiếuM1 được ghi riêng.

Risk.30%, SYM+4,050/+13,795/+1,845R và ASYM+5,901/+16,462/+2,645R (2022/23/24).
Năm2022 giảm vì holidayflat: SELL04July từ+3,921R thành−0,333R ASYM;
BlackFriday24Nov2023 khôi phục+0,673R. Top3/year chiếm hơn toàn bộ net profit;
phần còn lại âm3năm. Không chọn SELL-only hay vá exit sau nhìnValidation.
36monthlystarts×2risks×2costs=144cases;12quarterstarts làsubset.
Risk.30%0/36quaP1; risk.40%2/36SYM,5/36ASYMquaP1;0casequaP2.
Không observedbreach 5%daily/10%static; risk.40%worstrollingstatic7,234/7,083%.
**Đề xuất gác khỏi đường Challenge hiện tại; giữ researchbenchmark.** Positive point
estimates không chứng minh edge bền/thu nhập chính. Chưa timefit hoặc fullpropqualified;
actualswap/minstep/news/margin/feed/calendar còn gap. Không mở2025–26/variant/risk/broker.
209/222midnightmarks cũ>60s; DD/daily là observed/carriedmarkconditional, không boundunknownquotes.

14newfixtures+18execution+12Stage0regressions và2negativeCLIguards đạt;
308firstpassage/1.232rationalcostbridges/12annualcostbooks directtick selfaudit đạt.
Không independent/ASTRA review. Privatejob `execution-v1/xauusd-a-validation-20261114`:
`execution-config-v2.json`, `source-snapshot-v1` code, `source-snapshot-v2` inputs,
`attempt-2/result.json` và `arithmetic-review.json`; không còn numericalwriter.
Branch `codex/xauusd-holiday-validation`, chưa được giao merge báo cáo mới.
Giữ WIPVI Dubber; Trader không đổi. Bước mới cần scope riêng; không tự tiêu holdout.

**Parent đã hoàn thành — không thay kết luận cũ:**
**Lượt mới được owner mở:** [XAUUSD H1 Stage-0](research/XAUUSD-H1-STAGE0-PROTOCOL-20261113.md),
3 recipe cố định (Asian breakout/H4-trend H1 reclaim/momentum), BUY/BOTH views.
[Kết quả](research/XAUUSD-H1-STAGE0-RESULTS-20261113.md) /
[JSON](research/XAUUSD-H1-STAGE0-RESULTS-20261113.json): Development2022–23,
seedNov2021; không giá2024–26 hoặc bot SL/TP/account replay. RawBOTH103/107,
116/136,61/85. Primary8h/24h/8h chưa pass; chỉ48h có observedmeans dương2năm.
Lead ưu tiên A/BOTH48h:+1,767/+1,326USD/oz stress saufunding, observed63/65;
raw103/107, SL11,512/8,667, giữ90,3%/76,6% ở12%. C/BOTH48h leadphụ,
nhưng2022chỉ32observed. Không candidatechallenge; endpoint48h missing không
ngẫu nhiên (229weekend/231missing), CIqua0 và48h là horizonphụ đã xem.
Funding proxy20/40USD/lot,weekdays22UTC,Wed×3 chưa targetverified.
Job `execution-v1/xauusd-h1-stage0-20261113/attempt-2` completed;19.722.614ticks,
114.803M1OHLC khớp sau1M1openrevision, H1/H4 và608signals identical.
Giữfailedattempt1/snapshotv1; registration-v2/snapshotv2 vàFractionselfaudit
1.976markouts/608entries/48summarygroups đạt;12fixtures+11regressions+2guards.
PR76 đã merge/xóa branch; verdict primary cũ giữ nguyên, follow-up ở bằng chứng mới bên trên.
Đây là campaign mới được giao, không phục hồi các B1 đã hủy hoặc tự bật Goal.

**Chiến dịch cũ đã đóng theo owner:** [STRATEGY-E2E](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Owner chốt No-Go XAUUSD B1, hủy lượt chưa dùng; EURUSD B1 cũng đã hủy.
PR74 đã merge `f0aadae`, nhánh cũ đã xóa. Không mở biến thể, batch, holdout
hoặc goal mới. C1/C2 chưa đạt, chưa có ứng viên challenge; đóng chiến dịch
khác đạt mục tiêu lợi nhuận. AppGoal kiểm khi chốt sổ=null.
[Stage-0](../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen)
là chính sách mới cho nghiên cứu sau này; không chạy hồi tố hoặc tự mở lại.
Các checkpoint và backlog bên dưới giữ làm bằng chứng lịch sử.

**PR69 đã merge, chuyển sang thiết kế từ ràng buộc:** mergeSHA`920b48a`,
nhánh`codex/gold-eurusd-portfolio` đã xóa local/remote. [R043fixture](research/GOLD-R043-REGRESSION-FIXTURE-20261113.json)
đóng băng source/evidence: `CADENCE_OR_SAMPLE_SHORTFALL` + `PROP_TIMEFIT_REJECTED`;
dừng tối ưu challenge, giữ làm regression khi có correctness/sourcecompatibility need.
[B2report](research/GOLD-CONTINUOUS-B2-20261113.md) giữ720conditionalpaths,
36tests/7parity,120stresscached30,81s;0nhóm hoàn tất2vòng trong24tháng.

**Checkpoint mới — Scale & Horizon Audit, chỉ Development 2022–2023:**
PR73 đã merge `f1fa995`, nhánh cũ đã xóa local/remote.
[Báo cáo](research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.md) /
[JSON](research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.json):
ma sát median0,3486USD/oz chuẩn,0,7486stress; slip chiếm53,43% median.
772/813tínhiệu loại phí; SLrawmedian1,958USD/oz, sàn liên tục≈5,935,
fillsmedian7,02. Giữ cùng37fills tới18UTC vẫn stress−211,86USD;
14fills SL6,5–8 tới18UTC:1TP/6SL/7right-censored. Median toàncohort chưa xác định.
Rawmarkout18UTC meanstress+0,365USD/oz, dayclusterCI[−0,845;+1,731], chưa edge;
không bác mọi tínhiệu M15. **Owner đã chốt No-Go/hủy B1**, không dispatch.
B0 vẫn ECONOMIC_FAIL + CADENCE_OR_SAMPLE_SHORTFALL,
PROP_UNMEASURED. 10fixtures/2sourceguards/153passage/2.401markoutchecks đạt;
23.829.464ticks chỉ2022–23, không2024design/2025–26giá/ASTRA/broker.
Privatejob `execution-v1/xauusd-scale-horizon-audit-20261113/attempt-1` completed;
branch audit đã merge/xóa ở PR74; Traderpin/VIWIP giữ nguyên.

**Bằng chứng kế thừa — XAUUSD Intraday B0/A0:**
PR72 đã merge `7ee9ace`; nhánh `codex/intraday-funnel-audit` đã xóa.
Owner hủy EURUSD B1, không chuyển quota. [Kết quả XAU B0](research/XAUUSD-INTRADAY-B0-RESULTS-20261113.md)
/ [JSON](research/XAUUSD-INTRADAY-B0-RESULTS-20261113.json): chỉ A0, Development2022–23
và historicalvalidation2024. Raw399/414/390 → fills24/13/30; stress
+156,13/−425,93/−451,15USD. ECONOMIC_FAIL + CADENCE_OR_SAMPLE_SHORTFALL;
PROP_UNMEASURED, strictfunded còn calendar/targetspecblocked. Không A1/B1.
30.403.243ticks đã kiểm;135.281phútOHLC khớp sau3sourcecorrections trướcoutcomes,
giữ originalcache/failedviews/snapshot.11fixtures +134scenario-trade bridges,
2.035.213floatingmarks self-audit đạt; không independentagentreview.
Privateattempt `execution-v1/xauusd-intraday-b0-20261113/attempt-1` completedconditional;
registration và source-snapshot-v2 đóng băng. Branch cũ đã merge/xóa ở PR73;
Traderpin/runtime và VIWIP giữ nguyên;2025–26giáclosed, không ASTRA/broker.

**Bằng chứng kế thừa — audit Development EURUSD:** PR71 đã merge
`7d29ce4`; nhánh `codex/eurusd-b0-study` đã xóa local/remote. Owner gác EURUSD B0
với `CADENCE_OR_SAMPLE_SHORTFALL` + `DATA_PATH_INCOMPLETE`; prop vẫn unmeasured.
[Audit phễu](research/EURUSD-FUNNEL-AUDIT-RESULTS-20261113.md) / [JSON](research/EURUSD-FUNNEL-AUDIT-RESULTS-20261113.json):
chỉ EURUSD2022–23,517zones→62ngày/67signals→24fills;455zones không confirmation.
43costrejects có medianSL6pip, cần median9pip theo spread/lotfloor.
NO-GO dispatchB1; owner đã hủy lượt chưa dùng, không chuyển quota sang Gold.
[Card XAUUSD Intraday B0/A0](research/XAUUSD-INTRADAY-B0-PROPOSAL-20261113.md)
đã được owner duyệt và thực thi theo protocol mới dẫn ở trên. M1timestampquality2022–24 cho10/11/12ngày
thiếu đoạn>15phút, không gapnộiphiên>15phút; chưa certify calendar/Ask/tick.
Không EURUSD2024diagnostic hoặc giá2025–26; GoldA0 là scope được duyệt riêng.

**Bằng chứng B0 đã được kế thừa:** PR70 đã merge `0a8542ba`, nhánh
`codex/prop-target-envelope` đã xóa. [Protocol B0](research/EURUSD-B0-PROTOCOL-20261113.md)
và [registration](research/EURUSD-B0-REGISTRATION-20261113.json) khóa duy nhất
EURUSD H1→M15 breakout/retest: Development2022–23 + historicalvalidation2024.
Nativecost/sizing + observedtickpath. [Kết quả B0](research/EURUSD-B0-RESULTS-20261113.md)
và [JSON](research/EURUSD-B0-RESULTS-20261113.json): 13/11/6 lệnh ở2022/23/24,
stressmodel +22,01/+864,84/+12,59USD;95pre-costsignals,65costrejects.
CADENCE_OR_SAMPLE_SHORTFALL;2023 có sourcegap54,54phút lúc giữlệnh,
DATA_PATH_INCOMPLETE. Strictfunded còn BLOCKED_BY_CALENDAR/PROP_UNMEASURED;
không gọi conditionalnet là edge, fullpathDD hoặc khả năngchallenge.
Không EURUSDB1/GoldA1 hoặc risk0,40%. Privateattempt:
`execution-v1/eurusd-b0-20261113/attempt-1`: completedconditional,17fixtures,
60scenario-trade checks/19.482bar parity; giữ frozenattempt/reviews, không rerun
unchangedbatch. Numericalcheckpoint `d33d917`; postrun chỉ sửa writer/reviewguards.
[Prop Target Envelope](../.agents/skills/strategy-qualification/references/validation-gates.md#prop-target-envelope--profile-owner-ngày-13112026)
là ownerdesignprofile, khônguniversalstandard/officialFTMOrule hoặc runner đãenforce.
F/Rplan ưu tiên≤10%,trần12%;cadence≥60/năm ưu tiên120;25–40netR0/năm là dảikhởiđầu.
Planning12tháng cần50R0 ở0,30% hoặc37,5R0 ở0,40%;6tháng cần gấpđôi. DD15R0
không bảo đảm Daily; giữ daily<2,5%/staticloss<6,5%,strict6% làdesignaspiration.

Trần4alpha versions mới toànchiếndịch;B0+tốiđa1diag,A0+tốiđa1diag chỉdựphòng,
khôngreset priortrialhistory hoặcdispatchA tựđộng. Dev2022–23 vàhistoricalvalidation2024
đều previouslyexposed.2025–26 **CLOSED**, chưa chứng nhậnglobalcleanOOS; khôngđọcgiá.
ExactEURCatalogue13 gác,khôngportfolio. US500overlaypaused; chưapayout/candidatechallenge.
Không còn branch audit cần giữ sau khi merge; không gửiASTRA,
broker/ordercalls hoặcđổiTraderpin/runtime. Publichistory2022–24 đã cache theo grantA0.
VIWIP vàotherownedworktrees giữ nguyên. Không Goal/skill mới hoặcglobalconfig.
[Hồ sơ Bước1–2](research/STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md)
giữ taxonomy/gap/testdesign; đề xuất US500overlay cũ đã được owner gác.

Research mở rộng US500/EURUSD và cách dùng cả năm engine đã được khảo sát.
[Báo cáo chiều sâu/engine/milestones](research/STRATEGY-DEPTH-ENGINES-AND-MILESTONES-20261112.md)
đề xuất US500 chính/EURUSD phụ (80/20 công sức), một hypothesis mỗi lane;
FX trước hết rà oldevidence/readiness, chưa numericalprotocol mới. Đây là
đề xuất phân bổ, không tự đổi exactmethod hoặc bật nhiều broker runtimes.

Owner bổ sung: [lọc feasibility sớm](../tooling/ai-engines/STRATEGY-WORKFLOW.md#lọc-độ-phù-hợp-trước-khi-triển-khai-sâu)
trước code sâu/financialbatch; reuse/count-only khi thiếu cadence. Bản có edge
được xét sizing khác nếu stressDD/prop cho phép;0,25% chỉ baseline, chưa đổi risk thật.

**T1 US500 lịch sử vẫn chưa freeze card mới**, không tự chạy study sau hậu kiểm: hypothesis →
H1bias/clock/carry → M15zone/available_at → setup → trigger → risk/entry/exit.
US500/intraday/Standard là scope trước đợtA; lượt hiện tại ưu tiên GoldSwing
continuous/EUR economics/portfolio theo chỉ thị mới, không tự mở US500overlay.
Đề xuất chính là confirmedM15level→break→retest, giữ MA-arm comparator;
đây chưa là exactrecipe đã được owner chốt. [Research/spec gaps](research/H1-M15-ZONES-AND-AI-VALIDATION-20261112.md)
và [oldB/C spec](research/US500-MULTITIMEFRAME-DRAFT-20261111.md) dẫn luật cũ.

Owner đã chỉnh rõ H1→M15; không tự chuyển sang thống kê20ngày/market khác
ngoài phạm vi research mở rộng vừa giao; numeric mới vẫn cần protocol riêng.
R120 làM15laneA, R121 mới là counterpart cóH1. Bias cũ là closedcashH1close
soSMA20; trước10:30 cócarryphiên trước. Không giả đó là nativeMT5H1 hoặc
manualstructure đã được xác nhận. Zone cũ là nến hồi quanhMA, không OB/FVG.

## Bằng chứng nghiên cứu cần kế thừa

- [Catalogue](research/STRATEGY-CATALOGUE-20261107.md):123historicalrecords/
  88versions/53native, cộng scopedstudies; không đếm chúng là independentedges.
- [R120 savedreview](research/US500-R120-SAVED-REVIEW-20261112.md):15lệnh/3năm,
  stress+48,87USD trên3sổreset10k; cadence142/157tuần vắng, giữ researchphụ.
- [TC01 same-clock](research/US500-SAME-CLOCK-RESULTS-20261112.md):673signals,
  endpointstressâm3năm;park exactcomponent, giữnegativehistory, không lanechính.
- [BR01/RS02 diagnostics](research/US500-CONTINUATION-DIAGNOSTIC-RESULTS-20261112.md)
  giữnegative/unknowns; không quét tiếp ATR/channel/exitgrid để cứu.
- [Recent8setups](research/US500-RECENT-SCREEN-RESULTS-20261112.md):2025selection,
  RS01/RS07 đã2026diagnostics; fullnetN/A doheldgaps. [Gap probe](research/US500-RECENT-GAP-RESULTS-20261112.md)
  chưa khôi phục phút thiếu; khôngdrop/ffill. Exposure/permission tùy protocol.
- GoldR043/FX/portfolio và các nhánh khác ở [researchindex](research/README.md)
  và [backlogQ1–Q12 của task](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md#những-việc-xét-sau-đã-đưa-vào-task),
  không tự resume từ “bước tiếp” lịch sử.

Privateevidencebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Giữ failedattempt/raw/seals/snapshots. Reuse khi đúngbinding; sửa luật là trial
mới, sửa bug chỉ rerun affectedscope. Không nối annualreset thành CAGR hoặc
pricecomponent thành accountPnL. Dataset đã xem không tự thành cleanOOS.

## Đọc theo phạm vi và quyền

| Việc | Authority / đường đọc |
|---|---|
|Task nghiên cứu hiện tại|TaskSTRATEGY-E2E → đúngstage → protocol/results/artifacts; [workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md) giữ phương pháp|
|Trader source/UI|[ProductPlan](trader/PRODUCT-COMPLETION-PLAN.md) → [entrypoint](trader/EXECUTION-ENTRYPOINT.md) → ledger; không thay bằng researchplan|
|Runtime/MT5/Paperclip|[Operations](../tooling/ai-engines/OPERATIONS.md), đúngruntime skill/owner; reconcile jobs/unknown submissions trước restart|
|Context/skills|[Lifecycle](CONTEXT-LIFECYCLE.md), [maintenance](../docs/development/SKILL-MAINTENANCE.md); không globalconfig/manager mới|
|Project khác|AGENTS/README của đúngrepo; không sửa/commit WIP VI Dubber hoặc restart integration từ audit này|

Auditdoctor đọc được4integration sources đúngpin/license; configuredPaperclip
health endpoint unavailable. Không kết luận mọi runtime hỏng, không tự start/
restart trong audit. Broker/target account/production chưa được acceptance.
Lượt mới đã có fixed-trade M1diagnostic được owner giao; không strategyjob mới,
holdout2025–26, install hoặc lệnh broker. Không promote/runtime từ kết quả này.

Ngoài nativePaperclip task/runstate và existingreceipts không tạo tracker/UI
cạnh tranh. Research/plan không cấp OrderCheck/OrderSend/account/provider/
paid/deploy/delete quyền mới. Giữ đúng authorization/accountscope khi tớiT7–T9.

## Lịch sử và khôi phục

[Snapshot trước audit](archive/2026-11-12-strategy-e2e/CURRENT-CONTEXT.before.md),
[campaign trước audit](archive/2026-11-12-strategy-e2e/CAMPAIGN-V2.before.md) và
[manifest](archive/2026-11-12-strategy-e2e/MANIFEST.json) giữ trạng thái/nextactions
cũ; chỉ đọc khi truy why/regression. OriginalGit`2b52c79763b1653ea9cf96dba40ce5eaafa3e341`.
Các archive cũ hơn vẫn được giữ; ưu tiên task/stage hiện hành để resume.
