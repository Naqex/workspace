# S03 — kiểm định tiếp năm2024 của danh mục S02 giữ nguyên

Đăng ký18/11/2026 trước lần đọc giá2024 của chiến dịch độc lập này. Owner đã
cho tự chủ toàn bộ mục tiêu;2024 chỉ được mở theo protocol đóng băng,2025–2026
vẫn đóng. Đây là **Historical Validation có điều kiện**, không clean OOS,
không phiên bản alpha/sizing mới và không quyền broker/Challenge purchase.

## Câu hỏi và quyết định đã khóa

[S02](SOLO-THREE-ASSET-REPLAY-RESULTS-20261118.md) dương trong Development,
nhưng0P2/payout. Những cửa sổ vàoP2 đều cuối2023, còn68–88ngày; phần này cũng
yếu đi, không chỉ thiếu thời gian. S03 hỏi: **giữ nguyên hệ thống thêm một năm
thì kinh tế và vòng tài khoản diễn biến ra sao?** Không dùng kết quả để chọn
BUY/SELL, bỏ asset, đổi giờ/exit/risk hay tạo thêm monthly-start grid.

Composition/risk: Gold A Original/A0 BOTH150USD, EURUSD Asia/London sweep
DAY75USD, GBPUSD cùng recipe DAY75USD. Baseline bỏ GBP, các rule khác giống
candidate. Một sổ50.000USD; cap500USD, reserve46.500USD, daily-realized halt
1.000USD; fixed risk mọi phase, không equity throttle. Hai mô hình Gold
SYM−40/−40 và ASYM−45/−5USD/lot/rollover, các phí và reward proxy đúngS02.
SL/TP/entry/deadline/lịch lễ giữ nguyên. Không carry2024outcome vào thiết kế.

S03 **không vượt qua path gateS02**: giữ nguyên mọi unknown>15phút và
`scheduled_closures_exempted=false`. Lịch Dukascopy hiện tại khớp17–18NY
nhưng chưa có hiệu lực lịch sử; không chạy giả định mới để miễn trừ gap.
Đây là thay đổi có ghi nhận về thứ tự nghiên cứu: tiếp phép đo có điều kiện
để giải quyết censoring/time-fit, trong khi historical source calendar vẫn
unknown; không sửa verdictS02 hoặc hạ điều kiện Challenge.

## Hai lần khóa trước dữ liệu

1. Commit protocol, composition/code và meaningful synthetic tests; review
   độc lập các guard2024/2025, no-future-input, cutoff và prefix. Release JSON
   trong output riêng phải bind committed bytes, protocol, implementation,
   canonicalS02result/oracle, lịch và input metadata. Chỉ sau đó được đọc
   H1/events/source2024; không dùng script cũ có globalJOB trỏ nhánh gốc.
2. Chỉ tạo raw cohort2024 của recipeGBP đã khóa, kiểm nguồn/H1warmup và
   Devsignal parity; đăng ký census toàn bộ held hours gồm cả cost rejects
   **trước download ticks và trước economics**. Pin manifest/proofs rồi admit.
   Source mismatch dừng financial run; không tự sửa source theo PnL. Sửa lỗi
   nguồn mới cần addendum cụ thể, original giữ nguyên, proof signal/SL parity.

Mọi đầu ra dưới
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S03-three-asset-validation/`.
Một writer mỗi artifact, attempts mới, checkpoint/status/deadline rõ; không
đổi producer giữa run. Historical receipts giữ immutable. Không ghi original
checkout/runtime/DB/WIP, không gọi broker hoặc provider trả phí.

## Nguồn và cửa thời gian

- Account quotes/decisions chỉ `[2022-01-01,2025-01-01)`UTC. Metadata/loader
  kiểm path/date scope trước parse giá; tuyệt đối không2025–2026.2024 là
  exposed historical validation trong dự án, không gọi năm mới chưa dùng.
- Dev733sealed trades và manifestsS02 giữ nguyên:210Gold/236EUR/287GBP.
  Source/code provenanceS01v2 và lỗi15% được giữ; không regenerate rồi lặng
  lẽ thay Devbook hoặc nhập source/campaignV4 của thread gốc.
- Gold2024 reuse A/A0 sealed events từV1, manifest và source correction đã có;
  hai cost models phải giống event facts, không D1 scaling/protectedstop.
  EUR2024 reuse V3source và raw signals, kiểm inclusive integer15% trên toàn
  raw cohort trước dùng acceptedbook. Lệch membership phải dừng và ghi witness,
  không mặc định kế thừa false rejection hoặc âm thầm đổi kết quả.
- GBP2024 reuse H1 BID/ASK explicit source, bỏ padding đúng semantics cũ.
  WilderATR giữ chuỗi từ01/11/2021 qua hai H1 corrections2022 và toàn2023;
  không reset indicator ở đầu2024. Whitelist duy nhất
  `GBPUSD.SWEEP.ASIA.LONDON.DAY`; không gọi catalogue112cells.
- Paired ticks của mọi rawGBP opportunity từ decision đến deadline: grid,
  same-msordinal, H1OHLC, timestamp/gaps/emptyhours phải đối soát trước tiền.
  Exact costgate15%, commission5+slip4USD/lot/roundtrip, min/step0,01lot;
  naturalSL giữ nguyên, không nới để đạt phí. M1 nếu cần derive từ admitted
  pairedticks, không dựng nguồn song song. Samevendor không FTMOparity.
- Missingticks: reuse local/cache trước, nếu cần downloader pinned
  dukascopy-node1.51.1,2requests đồng thời,300ms pause,≤3calls/URL,
  ≤20transient failures, deadline120phút. Auth/rate-limit dừng; không bypass
  hoặc retry vô hạn. Output riêng; không overwrite cache/nguồn cũ.
- Lịch freeze đã có31/12/2024flat17:00UTC, là inherited guard scenario,
  không giờ đóng broker/nguồn đã xác minh; mọi intent phải có
  `deadline+60000 < 2025-01-01`. Require actual exitquote và terminalflat.
  Nếu invariant sai hoặc thiếu endpoint: source/contractfailure, không bỏ
  lệnh, giả close, kéo deadline hoặc đọc sang2025 để hoàn tất lệnh.

## Replay và đối soát Development prefix

Reuse `PortfolioAccount` và shared tickmergeS02, không thêm account engine.
Chưa có durable checkpoint; replay xác định toàn2022–2024 với Devbook là
prefix bất biến. Không lấy endingbalance rồi tái tạo phase bằng tay.

104sổ báo cáo =2costmodels×2systems×(24monthly starts cũ2022–2023 +1continuous
2022–2024 +1diagnostic2024). Không thêm starts2024, quét sizing hay variants.
108sổ sentinel giữ đúng từngstart/endS02 (annual2022 kết thúc01/01/2023),
chỉ để kiểm hồi quy, không thêm evidence thành công hoặc tính vào104sổ.
Nếu thiết kế checkpoint equivalent đơn giản
hơn thì phải review trước release; không đánh đổi đầy đủ state để ít code.

Trước công nhận kết quả2024, so toàn108sentinels vớiS02: accepted/rejected
và reason/state, trades/cost/cash bridges, phases/payouts, resets, daily/DD,
quote-age intervals và coverage. Ignore duy nhất global `joint_tick_marks`
không phải accountstate; counterprefix phải đối chiếu riêng nếu công bố.
Synthetic futuremutation phải giữ anchor/peak/gate/phase-days/dayhalt,
positions/accrual và quoteprovenance không đổi trước cutoff. So đồng thời
prefixtrade ordering/hashes. Sai khác material dừng, không chỉ so cuốiPnL.

`dump()`S02 thiếu internalstate nên sentinelprojection chưa đủ chứng minh
continuation. Trước run mở rộng, chạy Dev-only reference bằng coreS03 và so
đúng108rowsS02. Tại01/01/2024, fullrun chụp state trước bất kỳ2024action nào
của100sổcontinuation, so với reference: balance/anchor/peak/gate/phase-days,
dayhalt/positions/accrual/fundedclock/rewardclock, metrics/counters/ledgers,
lastquote/provenance và coverage đếnboundary. Chỉ configuredend/counter toàn
run được tách khỏistatecomparison; không whitelist arbitrarydifferences.
Đây là transient verification snapshot, không dựng durablecheckpointstore.

Entry tại observedquote, SL-first proof theo ordinal; clock/swap trước quote
cùng timestamp; exit trước entry; crossasset rankGold/EUR/GBP giữS02.
Unknown không làm đóng lệnh giả, bỏ sample hoặc nângno-breachclaim. Latest
quote ghi đúng age; không interpolate dailyanchor trong khoảng đóng nguồn.

## Đầu ra và tiêu chí quyết định trước outcome

- Năm2024 và full2022–2024: netUSD/commonR, từngasset/side, sốlệnh, annual
  contribution, top3USDdependency, equityDD vsstaticloss và worst daily;
  coverage/unknown theoasset và affectedaccount. RiskUSD là denominator rõ.
-24oldstarts/model/system: P1/P2/fundedpaths/rewardsproxy, observedfirstbreach,
  thời gian theo ngày lịch từstart; riêng phầnP2 còn tiếp2024. Dedupefunded
  paths, rightcensoring và overlappingwindows; không gọi làprobability.
- So candidate/baseline cùngpolicy; không dùng tổngR khácsizing nhưUSD.
  Tách tiền đã đóng, balance/equity, phase reset và khoảnreward model.
- G1: source/correctness/prefix/oracle đều đạt trong scope. Mismatch→dừng
  evidenceaffected; không kết luận alphaâm. Sourcepathunknown vẫn giữ.
- G2: dùng diagnostic2024 (không lifecyclebalance đãreset): candidate net>0
  dưới cảmodels và continuous2022–2024Net/equityDD không thấp hơnbaseline
  cùngmodel mới đủ review giữcomposition; không hạgate sauđo.
  DD=0 làm ratio undefined, không vôcực/PASS; báo không đủ để áp cổng ratio.
  Không đạt→gác exactcomposition khỏi đườngChallenge, giữ nguyên diagnostics.
- Timefit: báo số cửa sổ hoàn tất2phase trong365ngày,365–730ngày và>730ngày,
  cùng số chưa đủfollowup ở từngmốc; thước đo12tháng kế thừa owner envelope.
  Model nào không có completion≤365ngày→chưa chứng minhtimefit12tháng ở model
  đó, dù về sau cópass. Có≥1completion không tự xác nhậntimefit: cần báo
  phân bố/censoring/uniquepaths và không gọi tỷ lệ chồng lấn là xác suất.
- Observed daily/overall breach là thất bại cówitness, chặn propsuitability
  dùnetdương. Tách khỏi rightcensored/chưa đủfollowup; thiếuquote ởđoạnkhác
  không xóa witness hoặc biến breach thành censoring.
- Payout/survival chỉproxy. ĐạtG2/timefit vẫn **không Challenge-qualified**
  khi unknownpath/spec/news/margin/feed/OOS/forward còn thiếu. Primaryverdict
  về economics/timefit và path/prop tách nhau; không gom conditionalpositive
  thànhPASS.2025–2026không tựđộngmở saukếtquả.

Không sửa criteria hoặc thử thêm cấu hình nếu kết quả kém. Bước sau dựa vào
đúng bottleneckđo được, đăng ký mới nếu thay mechanism/sizing. Oracle độc lập
reuse phương phápS02 nhưng bind mới code/cutoff/books; PASSkhông independentfeed.
Giữ lịch sử112trials và ngoại lệ inheritedSLrecipeGBP córawmarkoutâm; S03
không làm GBP trở thànhStage0PASS hay2024thànhcleanOOS.

## Kiểm thử tối thiểu trước release

S02/defaults không mở2024, explicitS03only≤FINAL; forgedrelease/hash/path từ
chối; same-msordinal/firstSL/15%boundary; unchangedrawfunnel; correctedwarmup;
yearendflat/missingendpointfail; futurequotes/exitmutation khôngđổiintent;
futureyearappend khôngđổiDevstate/admissions; PragueDST/midnight; phase/reset,
funding/reward và cashbridges; quote-ageincludingall-streamsilence; source
decoder/H1reconciliation; nooverwrite/readoriginalJOB/no2025priceopen.

Implementation map:
`research/three-asset-preparation/s03-design-20261118/IMPLEMENTATION-PLAN.md`
dưới outputroot riêng, SHA256
`6f23d12d869789e35dfe78a259b732b510e015c8de108136c0b27271078579fa`.
Plan là tài liệu thiết kế; không receipt rằng các checks đã chạy.
