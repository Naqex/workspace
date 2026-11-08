# NASDAQ100 H1 đã chuẩn bị; bước tiếp là recipe/cost contract

Thực hiện [history protocol](NASDAQ100-HISTORY-PROTOCOL-20261108.md), commit
`862b5c2` trước download, sau [pilot tick/M1/H1 khớp](NASDAQ100-SOURCE-RESULTS-20261108.md).
**Đã nhận nguồn cho registered coarse research; chưa strategy PnL hoặc ứng
viên challenge-qualified.** Không lấy data admission thành hoàn thành Goal.

## Dữ liệu có gì và đã kiểm gì?

8books Bid/Ask: Nov–Dec2018 warmup +2019development; Nov–Dec2021 warmup
+2022development. Đây là `USATECH.IDX/USD` CFD theo NASDAQ100, không chính
NDX/QQQ/NQ hoặc quỹ US100. Không2025+, historical-development exposure,
cleanOOS=false. Không account/provider/package mới, không sửa raw đã có.

| Role | Paired H1hours | Đủ4H1/groupUTC H4 | Incomplete groups | Adjacent gaps>1h |
|---|---:|---:|---:|---:|
| Warmup2019 | 947 | 205 | 54 | 41 |
| Development2019 | 5.903 | 1.280 | 320 | 258 |
| Warmup2022 | 1.003 | 218 | 53 | 43 |
| Development2022 | 5.903 | 1.282 | 317 | 257 |

Side hours mỗi role bằng paired count; không one-side gaps hoặc crossed
Open/Close trong scope. Source clock/grid0,001/OHLC/volume hợp lệ. Gap dài
nhất giữa giờ quan sát là74giờ trong ba roles,53giờ warmup2019; **không tự
chứng nhận nguyên nhân là market closed**. Quality giữ closures/unknownfeed
gaps và incompletegroups, không padding thành dữ liệu đủ.

| Verification | Kết quả |
|---|---:|
| Raw source months /8books | 56/56 đầy đủ |
| Pilot month-side raw hashes reuse | 4exact,52newmonth sources |
| Retained source-side bars | 27.512 |
| Price/volume transform checks | 137.560; canonical decoder và Fraction khớp |
| Decoder carried-padding loại ra | 13.138rows |
| Explicit volume0 giữ lại | 2rows |
| Paired crossed Open/Close | 0 |
| Negative cases | Giá, missingrow, futureclock, authority reject; bổ sung wrongrawhash reject bằng exact frozen verifier statement |

H1 volume native aggregate round4, không rawfullprecision hoặc exchange volume.
H1Open là interval proxy, Close/High/Low known tại barend. **Không tạo observed
mid extrema bằng trung bình extrema của Bid/Ask**. Khi triển khai H4 cần chốt
Bidchart basis/aggregation/gap semantics riêng, không giả actual joint ticks.
Hai cash-hour bridges đã exact chỉ chứng minh pilot, không fulltickhistory.

## Lưu và tái sử dụng

- Raw source:56JSONmonth-side files có hash trong common provider cache, giữ
  source path/instrument/side/dates/package và nguyên bytes.
- Normalized source-only:8JSONbooks cùng seal/proof, role warmup/development,
  UTC/ms/price basis/units/known-at/exposure/authority trong config; nguồn sự
  thật là raw/pinned provenance, không narrative tóm tắt.
- Quality/rawbindings/crossed flags/review/status nằm cùng attempt. Không ghi
  PnL vào memory/search rồi coi đó là numerical source; chưa cần RAG/vectorDB.
- Bước sau hash/load đúng artifact, không tải lại hoặc parse toàn tick history
  chỉ để tính features. Không đổi bindings để dùng cache với source khác.

## Hậu kiểm kỹ thuật

| Phase thực đo | Wallseconds /CPU | Quyết định |
|---|---|---|
| Pilot source collection | 3,063 /1,064 | Giữ exactfixture, không rerun |
| Pilot fidelity review | 3,674 /không đo riêng | Đủ scope2days/2cashhours |
| History collection | 26,884 /0,937 | Chủ yếu I/O; đủ ngắn, không cần song song/GPU |
| History full source review | 2,002 /không đo riêng | Không numeric backtest/rerun |

Research/code/active-agent time chưa có timer; không gọi bảng này là toàn bộ
thời gian từ ý tưởng đến kết luận. Không transport/review failure hoặc retry.
PID11072/session66816, pilotPID20068 và reviewers terminal0; không còn source
worker của lượt này để chờ. Existing package/helpers/oracles đủ; không sửa
product/runtime/skills/globalconfig, không cleanup evidence/raw.

Review source chỉ cùng provider/agent với code paths khác. Actual broker
point/tickvalue/lotstep/margin/swaps/calendar/dividends/latency chưa verified.
FTMO public zero-index-commission hỗ trợ một declared commission scenario,
không đủ gắn `broker_spec_verified=true` hoặc dùng NQfutures multiplier cho CFD.
Không lấy model inference hoặc test pass làm authority.

## Evidence và quyết định tiếp

Private campaign root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/nasdaq-history-v1` có8books/source proofs/sealed-books/config/
manifest/source-snapshot/result/review/quality/raw-source-bindings/crossed-pair-
quality/progress/events. `hash-mutation-review.json` giữ expected-hash mutation
bổ sung sau source collection/review, trước economicrun; không sửa data.
Driver `prepare-nasdaq-history-v1.cjs`, reviewer `check-nasdaq-history-v1.py`.
ResultSHA `858a86b14c739a91a1751fa9b5aff388453e5cbc347beae91cce7232f72ff9c0`;
reviewerSHA `c110b26d059694e9aa7d774e51c6aadadd553da867b19c45999a86ff67b54400`.

Catalogue thêm R061 hypothesis NASDAQ H4SMA20/80, **chưa policy implementation**:
61records vẫn43researchpolicyversions/25nativeofflinerules. Bước tiếp chốt
recipe/market/cost/funding/gap contract, reuse indicator và financial primitives
với đúng instrument/basis, fixtures trước PnL rồi paired development2019/2022.
Không cho NASDAQ đi qua guard dưới nhãn US500/XAUUSD hoặc giảm fees cứu kết quả
cũ. Goal C1/C2 active, chưa đề xuất mua challenge/gửi broker/đọc holdout.
