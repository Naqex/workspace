# R080: EU-open đã kiểm; chưa giữ để phát triển thành bot

[Protocol](US500-EU-OPEN-COMPONENT-PROTOCOL-20261109.md) `2f04156` và core/tests
`44cbdac` trước economic outcomes. Fixed BUY23:30→03:30 New York, M1Open proxies
23:31/03:31, không VIX/clock grid. **Không đạt frozen retention**; Goal C1/C2
vẫn active, chưa ứng viên challenge. Không gọi đây là bác bỏ paper futures hoặc
cả họ uncertainty-resolution; đây là exact CFD adaptation trên consumed2019/2022.

## Kết quả và phần chưa biết

Một hypothetical unit=1USD/index point, chưa lot/risk/tài khoản10k. Các số dưới
là tổng **phần có hai endpoint hợp lệ**, không full annual PnL/account equity.

| Năm | Planned | Resolved | Chưa xác định | Phí chuẩn USD/unit | Phí cao USD/unit |
|---|---:|---:|---:|---:|---:|
| 2019 | 249 | 191 (76,71%) | 58 | −218,64 | −409,64 |
| 2022 | 250 | 248 (99,20%) | 2 | −393,38 | −641,38 |

2019 không đạt coverage98%;2022 đạt coverage nhưng known stress net âm. Không
suy 60 missing cases thành0, bỏ planned rows, forwardfill hoặc lấy phút kế.
2019 có52missing entries/10missing exits (4ngày thiếu cảhai);2022 mỗi phía1.
Reviewer tìm đủ998raw day-side responses, nên không phải quên load file/quý:
đây là absence đúng phút trong original source. 186/191 và112/248resolved
windows còn thiếu ít nhất1interior M1; không dùng endpoint sum làm equity/SL proof.

Không chọn riêng Q1/2022 chuẩn+57,67 để cứu rule: cùng cohort stress−3,33;
ba quý còn lại stress−396,72/−75,03/−166,30. Quartiles/concentration giữ là
diagnostics như đăng ký, không thêm gate sau outcome hoặc loại tail ngày xấu.

## Kiểm chứng và dữ liệu tái sử dụng

| Lát | Bằng chứng / giới hạn |
|---|---|
| Core | 6focused tests đã đạt trước run: DST/Monday/halfday, source grid, missing/crossed/interior gaps, future exit không đổi entry, fees/rounding/funding/null và authority |
| Separate preflight | 36synthetic role-cost cases,10rawdelta fixture fields;3mutations net/clock/funding reject trước outcomes |
| Full source | Full4quarters/8seals mỗi năm qua `us500_year_source`, không Jan/Jul pilot subset; source/census/coverage emit trước costs |
| Actual review | 503cashday rows,439resolved windows,2.634role-cost cases; calendar/rawM1 decoder riêng +frozen Fraction cost oracle;5actual mutations reject |
| Provenance | Raw hashes, canonical proofs, calendars, current code/costs, protocol/preflight và per-attempt snapshot; before-use/final pin checks |
| Scope | Same agent/method khác, không independent feed/model/human; M1 proxies không simultaneous executable ticks; funding0 chỉ declaredNY17scenario |

499planned/439resolved/60unknown là window cases;2.634checks gồm cả hai cost
scenarios/controls, không 2.634independent trades. Chưa protective exit, sizing,
margin/equity, target-broker funding/spec, prop/time-fit, cleanOOS/prospective
hoặc owner handover. Không network/model/broker calls, own2025+ vẫn đóng.

## Hậu kiểm kỹ thuật và quyết định

| Phần | Số đo / hành động |
|---|---|
| Producer | 4,578s wall;2019load/filter1,649s,2022load/filter1,812s; một năm tại một thời điểm, giải phóng fullsource trước năm tiếp |
| Compute | Source preparation và costs mỗi năm dưới0,1s; không có lý do thêm GPU/Rust/DB cho workload này |
| Reviewer | 4,331s wall/4,328sCPU; kiểm đủ actual endpoints/costs/presence, không sampled-only |
| Reuse | Existing frozenM1, không fetch/rawrewrite hoặc rerun16million closingticks; annual window khác có raw admission riêng |
| Reliability | Saved producer/reviewer, PID/progress/events/CANCEL/deadline180s/nooverwrite, result+review seals; không còn job nền |
| Rework | Reviewer draft có `else251` SyntaxError, đã sửa/compile/preflight trước economic run; không market attempt bị ghi đè hoặc trial bị giấu |
| Skills | Existing research/qualification/continuity/retrospective đã bao phủ workflow; chưa có bài học mới cần skill riêng hoặc sửa instruction |

Tổng producer+review8,909s, không gồm thời gian research/code/test và không là
speedup ratio so workload khác. Bottleneck quyết định hiện là chất lượng/khả
năng chuyển cơ chế sang instrument sau phí, không throughput máy.

Gác exactR080; không thêm clock/VIX/fee/SL variants để cứu outcome. Bước tiếp
là giải quyết method/source admission cho cơ chế khác trong
[oil/EIA queue](EU-OPEN-AND-OIL-METHOD-20261109.md), bắt đầu historical event
calendar và instrument mapping, chưa bulk history/PnL. Retained false không
cho phép tuyên bố full annual loss2019 hoặc mọi uncertainty strategy thất bại.

## Artifact và tiếp tục

Private base `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Output `execution-v1/us500-euopen-price-component-v1/` giữ rows503,summary12groups,
sourcefacts/scopes,config/manifest/snapshots,result/review,timings/events/progress.
Saved `run-us500-euopen-v1.py`, `review-us500-euopen-v1.py`, `euopen-preflight-v1.json`.

- Result SHA `2ce7ed34073d46718bd9c23518a584c25fc4b93c163626594c6fe0dda1a91229`.
- Review SHA `756d63a3d275e84ddd6432241e3464239521e8a6d37808555c992e1a6774a4f1`.
- Reviewer SHA `9b29531ab1c5a9c88508ee117067322f21332b47f07ff5f3cd817f46375b22e7`.
- Manifest SHA `12e4aafc54ac20cffeacb8428bdfd280e3843ffac6ab8162c4d2eb06428e4c05`.

Các receipts đã freeze không repin; catalogue vẫn80records/58policy-model
versions/25native/9controls vì component không là account policy mới.
