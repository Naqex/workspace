# Discovery6/7 — kết quả, correctness và shortlist

**Chưa có ứng viên đủ để vào challenge.** Có thêm Asia→London breakout để
review sâu; không tăng risk hoặc gọi coarse survivors là có edge. C1/C2 vẫn
ACTIVE ở [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md).

Frozen recipes/decision trước outcomes ở [Discovery6](SESSION-DISCOVERY6-20261108.md)
và [Discovery7](ORB-DISCOVERY7-20261108.md). Giá trị sau là net equityUSD gồm
floating trên10k, **chuẩn/cao**, accounts mỗi năm bắt đầu flat riêng biệt.
Coarse không internal brakes/full tickDD/prop; không cộng rows thành portfolio.

| Rule |2023|2024|Decision |
|---|---:|---:|---|
| PreECB02NY→14Berlin |+145,32 / −15,21|+124,61 / −44,50|Phí cao làm âm; không promote |
| PostLondon16L→16NY |+384,81 / +262,16|+204,95 / +57,35|Dương nhưng không cải thiện weakestyear so parent16–20London |
| PreTokyo18NY→10Tokyo |−829,26 / −904,58|−138,68 / −269,60|Không promote version |
| Fixing composite3slots |−287,23 / −646,06|+190,88 / −256,75|Không promote; không cộng các leg accounts riêng |
| LondonORB |+170,49 / +67,42|−287,36 / −413,25|Không bền hai years |
| NYORB |−188,41 / −274,83|−162,49 / −268,16|Không promote version |
| Asia→LondonORB |+191,97 / +59,75|+278,01 / +138,57|Giữ nghiên cứu sâu, chưa challenge |
| BBflat80 |−153,75 / −197,66|+85,59 / +4,01|Không bền hai years |

Tất cả16annualrows/đợt đã flat ở cuối năm. Source snapshots riêng từng attempt
đã giữ **trước** metadata/ownership fixes tiếp theo. Dates đã consumed/selection,
không cleanOOS hoặc28independent alpha tests. ML real/control outcomes giữ ở
[Discovery5](DISCOVERY5-RESULTS-20261108.md).

## C2: đã kiểm và sửa gì

| Lát | Bằng chứng | Kết luận/remaining gap |
|---|---|---|
| Rule clock/state |30product tests/21subtests cho ORB/fixing/intraday/coarse; NY/EU DST lệch tuần,Tokyo crossdate, Friday/missingrange skip, oneemission và exits/restore | Hand fixtures trong scope; chưa xác thực mọi marketcase |
| Numerical parity |32legacy coarse Q1scenarios exact mọi field trừ wall/CPU;16newnative prefixcases trên326.373ticks/118H1, decisions/counts/open/pending khớp; maxdelta0,64USD |6,25USD chỉ diagnosticbudget trước test, không annualerrorbound. BBflat prefix0trades, còn bằng chứng behavior ở synthetic tests |
| Failed recipe |V1review gửi str thay Path cho validated tickreader, fail trước nativecase;V2sửa recipe, giữv1 và reuse32oldrows đã verified |Không lỗi economic simulator; không chạy lại32rows để giấu failed attempt |
| Protocol provenance |Native generic H1label vẫn trỏDiscovery4cho các rules mới; đã route đúng6/7, regression đạt5tests |Historical registered runs còn bind exactregistration/protocol hash; old snapshots giữ nguyên |
| Rejection atomicity |Unknown sessionposition bị reject sau indicator update; đã chuyển check trước mutation và kiểm state unchanged |5focusedtests/3subtests đạt; valid-signal math không đổi |
| Performance |Discovery6years7,37s/6,35s; Discovery7years7,28s/6,21s, gồm cache/raw validation; mỗi cặp năm chạy song song. Nativeprefix48,11s |Không cộng overlap walltime; compute không cần GPU/Rust mới |

## Bước đang thực thi

[Frozen native study](H1-SURVIVOR-TICK-REVIEW-20261108.md) giữ hai policies:
parentLondon16–20L và Asia→LondonORB; replay full2023/2024,3/6/12month horizons,
tick/risk/declaredFTMOprofile. Hai batches×2workers, nguồn Trader78a8397f; đang
chuẩn bị/reuse caches tại lúc viết. C1chưa có edge/target/forward evidence.
2025+vẫn closed; no broker/LLM calls. Finalnumbers đọc đúng PROGRESS/results,
không dispatch lại screen đã xong.

Private root chung:
`E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1`.
`session-discovery6/`, `orb-discovery7/`, `discovery6-7-correctness-v1/` và
`discovery6-7-correctness-v2/review.json` giữ nguồn/results/failures/parity.
`h1-survivor-tick/batch-2023-v1/PROGRESS.md` và `batch-2024-v1/PROGRESS.md`
giữ actual progress; chưa nhận annual native results khi viết review này.
