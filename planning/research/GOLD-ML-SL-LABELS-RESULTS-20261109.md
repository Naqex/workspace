# R068/R069: forest vàng đã kiểm xong, không có tín hiệu đủ ngưỡng

**Không giữ exact recipe để qualification; chưa có ứng viên challenge.**
Toàn bộ 16 books không có lệnh và PnL bằng 0. Đây không là lợi nhuận hay bằng
chứng ML nói chung không có tác dụng. Không hạ ngưỡng hoặc refit sau outcome.

[Protocol](GOLD-ML-SL-LABELS-PROTOCOL-20261109.md) được freeze ở `06c6972`,
implementation `3232d0c`, trước thu nguồn mới, labels và training. R068 là
real policy; R069 ghi riêng paired-label shuffled control đã đăng ký từ đầu.
Hai folds/costs/null books không được đếm thành các chiến lược độc lập.

## Kết quả dễ kiểm

Model học BUY/SELL net R sau cùng SL, holding và costs với replay. Train2018
→ dev2019; train2021 → dev2022, không refit trong năm kiểm. Các năm đã exposed,
không gọi clean OOS. Chọn side có điểm lớn hơn side kia và **>0,10R**.

| Model / năm kiểm | Cơ hội được chấm | Điểm cao nhất, R | Điểm tốt nhất >0 | Vượt 0,10R | Lệnh |
|---|---:|---:|---:|---:|---:|
| Real2019 | 747 | 0,0394084 | 33 | 0 | 0 |
| Shuffled2019 | 747 | 0,0989124 | 26 | 0 | 0 |
| Real2022 | 750 | 0,0834018 | 234 | 0 | 0 |
| Shuffled2022 | 750 | 0,0970541 | 128 | 0 | 0 |

Cả reference/stress và null đều `modeled_flat`, net0USD trên10k/year. Gate
khóa trước cần net>0, knownflat và≥100closed/year ở cả2stressyears nên không
đạt. Mọi decision được score; không có broker execution lỗi để sửa hoặc retry.
Các score trên là dự báo của model, không phải lợi nhuận đã thực hiện.

Training2018 có744opportunities:732usable/12feature-unavailable;2021 có753:
740usable/12feature-unavailable/1both-sides quantity-or-margin rejected.
Census giữ đủ rows, không biến unavailable thành flat-return label.

## Phạm vi đúng và kiểm chéo

- Observed Bid/Ask XAU H1: train2018/2021 reuse R067; dev2019/2022 mới thu và
  review4exports/48months/23.650bars/118.250fields bằng canonical/Fraction.
  Không crossed/unpaired. Legacy source-review formation flag không dùng
  làm ML authority; exact ML schema và source-canonical bindings mới là gate.
- Decisions08/12/16UTC,100past BidH1/21features; entry09/13/17UTC, exit12/16/20,
  SL1,5TR14, fixed25USD plannedrisk. UScash full-session dates là sample design,
  không lịch metals. H1Open/OHLC là interval proxy, không actual tick fills.
- Declared contract100oz/lot, min/step0,01, leverage10; commission2,5USD/lot/side,
  observed spread, slip0,1/0,2USD/oz/side, intraday funding0. Chưa target-broker
  historical specifications. Không intrabar prop-equity/DD hoặc challenge pass.
- 8focused tests đạt trước run. Hai synthetic fits real/shuffled kiểm endpoint
  purge và safeJSON trước actual labels;4manual Fraction BUY/SELL×cost path
  fixtures cùng paired-label oracle đạt. Không unpickle model từ nguồn ngoài.
- Full reviewer Fraction riêng kiểm2.994opportunities/features,
  1.497training-label census và hypothetical financial paths; float32 tree
  traversal riêng,16books/zero cash. Actual net/count/authority mutations bị
  phát hiện. Không có selected actual trades để claim entry/quantity mutation
  coverage từ marketbooks; các nhánh đó được kiểm bằng manual fixtures.
-4actual exports khớp library với maxerror1,94e−16→3,05e−16. Training algorithm
  vẫn dùng cùng library; reviewer cùng agent/provider với phương pháp khác,
  chưa independent human/model signoff. Không suy một permutation thành pvalue.

## Artifacts và thời gian

Private base: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.

| Artifact | Locator / SHA256 |
|---|---|
| Source mới | `execution-v1/gold-ml-source-v1/result.json`; `7a92af801cff7d8acba9b9b373350a858c5bbda73154d8305bc6b0a908e62101` |
| 16books/census/packs/pins/logs | `execution-v1/gold-ml-sl-labels-v1/result.json`; `a986deb11477637e188d4707b01b2ed2506f8fc2ff77caa1f5ae85c902c9ea23` |
| Full review | cùng thư mục `review.json`; `22afd3be4b958a9a1f0a25fbae69a7174e45321814f2cf1d83d7673e5b6930a3` |
| Reviewer code | `review-gold-ml-sl-labels-v1.py`; `12e9b5bf460f7b493974cced37a22d1f644f1807a184559956457bb4d30425dc` |
| Post-run score/census diagnostic | cùng thư mục `no-signal-diagnostic.json`; binds result/review/books, threshold unchanged/model not retrained |

| Phase đo được | Wall | CPU | Hậu kiểm |
|---|---:|---:|---|
| Source mới48months | 22,841s | 0,859s | 0cachehits/48misses, không retries |
| Producer với pre-fit checks | 7,894s | 7,563s | 4fits/16books, không compute bottleneck cầnGPU/Rust |
| Full Fraction review | 3,988s | chưa ghi | Reuse sealed outputs, không simulation rerun |
| Diagnostic no-signal | 0,073s | chưa ghi | Đọc scores/census, không training hoặc threshold search |

Không cộng thành end-to-end authoring/research time; phần đó chưa đo. Ban đầu
đã sửa tên native class và đường import Pydantic trước actual fit; không cài
dependency mới hoặc đổi product/runtime. Scripts/source snapshots và negatives
được giữ. Mọi job terminal0, không job chờ hoặc broker/model calls.

## Quyết định và bước tiếp

Method alignment đã được thực hiện, nhưng chưa tạo usable edge cho exact
recipe này. Gác R068/R069; giữ R038/R039 negatives và không nói surrogate
alignment đã được chứng minh là nguyên nhân thất bại của parent. Catalogue
69records/48policyversions/25native, trong đó4controlversions. Goal C1/C2 active.

Hướng tiếp đang được method admission: stock-specific information/abnormal
activity khác unconditional price-only signals. Paper Stocks in Play dùng
relative traded-share volume; quote-CFD volume chưa được chứng minh thay thế
được. Chưa đăng ký/training/PnL một stock strategy, không lấy best-performers
hoặc một event nổi tiếng làm bằng chứng. Chỉ tiếp numerical khi source/clock/
adjustment/universe và cơ chế có protocol riêng.

Data flow giữ: immutable raw → side/time/unit/quality/source-bound view →
frozen protocol/code/config → output → review → catalogue/context. Theo
[data/retrieval review](AGENT-DATA-RETRIEVAL-20261108.md), chưa cần vectorDB/RAG
service hoặc migration. Skills hiện có đủ workflow; không tạo skill mới chỉ
cho một model không phát lệnh. Không xóa dữ liệu, mởholdout2025+ hoặc đổi broker.
