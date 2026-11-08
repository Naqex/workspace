# Fixture cổ phiếu: giá nguồn đã kiểm, chưa nhận strategy volume

**Đã hoàn tất fixture; chưa có chiến lược cổ phiếu hoặc ứng viên challenge.**
[Protocol/admission](STOCK-INFORMATION-SOURCE-ADMISSION-20261109.md) và validator
được commit `db9c30f` trước fetch, không có PnL hoặc training trong lượt này.

| Nội dung ngày03/01/2019 | AAPL | MSFT |
|---|---:|---:|
| Bid/Ask native rows, mỗi side | 1.260 | 1.260 |
| Explicit source bars, mỗi side | 390 | 390 |
| Decoder padding, mỗi side | 870 | 870 |
| Paired cash minutes / expected | 390/390 | 390/390 |
| Unpaired source bars | 0 | 0 |
| Source grid | 0,001 | 0,001 |

4requests/4rawURLs,1.560explicit rows;7800price/volume fields và timestamps khớp
raw decoder. Padding được nhận diện và giữ trong historical native exports,
không được coi là quotes trong source-only view. Giữ explicit volume0 nếu có;
fixture này không có explicit volume0. Không endpointcrossed trong paired
review; chưa simultaneous ticks hoặc intraminute spread/firstfill certificate.

## Cải tiến hệ thống đã áp dụng

Mở rộng đúng `research_input_admission.py`, không tạo DB hoặc validator cạnh
tranh. `stock_cfd_proxy` bắt buộc units/volume scale rõ, adjustment unknown,
volume chưa xác minh là exchange shares và PIT universe chưa certified. Không
âm thầm coi source bars là giá sàn hoặc metadata là bằng chứng economic edge.
LegacyFX/ETF vẫn được kiểm trong9focused tests đạt. Actual fixture chạy được
qua cùng CLI/module; không chỉ synthetic. Năm mutations trên disposable copies
đều bị chặn: exchange-volume claim, PIT claim, adjustment claim, actual price
và padding price dù đã reseal JSON/result. Frozen exports/raw giữ nguyên bytes.

## Quyết định nghiên cứu

- Chưa admit replication Stocks in Play ORB: relative traded-share volume và
  PIT universe trong paper chưa có mapping đáng tin từ stockCFD source. Không
  thay volume bằng quote activity rồi vẫn gọi là replication.
- Tạm gác **mở rộng full stock history/PnL**; một known-event day chỉ kiểm
  decoder/clock/price semantics, không signal hoặc winner evidence. History
  adjustment/dividend/shorting và target-broker economics vẫn chưa đủ.
- [The5ers stock FAQ](https://the5ers.com/faqs/available-stocks-for-trading/)
  đọc09/11 liệt kê AAPL/MSFT nhưng chỉ Bootcamp/ProGrowth, commission0,1%/side.
  Không tự đổi HighStakes sang các programs này. FTMOindividualstock rows/specs
  chưa xác minh trong textfetch; không nói đã ready cảhaihãng.
- Source này có thể reuse khi có hypothesis phù hợp, nhưng không download
  hàng loạt chỉ vì fetch nhanh. Catalogue vẫn69records/48policyversions/25native;
  source fixture không được cộng thành strategy mới. Goal C1/C2 tiếp tục active.

Hướng khảo sát kế: **NY-session-conditioned FX moving-average reversal**,
khác unconditional local-flow và Z20±2 cảngày đã thử. Primary author manuscript
[LeBaron/Zhao2008](https://people.brandeis.edu/~blebaron/wps/fxnyc.pdf) được tìm
trong search, nhưng fullfetch timeout; CiteSeer mirror403. Hiện chỉ có indexed
method excerpts, **chưa full-method audit hoặc exact recipe/protocol**; không
claim paperprofitability áp dụng cho hiện tại. Cần reconcile parameter/price
orientation/clock, costs và available sources trước khi đăng ký economic run;
không lấy snippets làm authority hoặc retune oldZscore. Nguồn có thể thu hẹp
hoặc gác nếu không tiếp cận/không phù hợp; không có numerical job đang chờ.

## Bằng chứng, thời gian và hậu kiểm

Private root: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Output: `execution-v1/stock-information-source-fixture-v1/`; producer
`prepare-stock-information-source-fixture-v1.cjs`, reviewer
`check-stock-information-source-fixture-v1.py`.

| Artifact | SHA256 |
|---|---|
| `result.json` | `ace43e74c8eb7b2c86fc7e6322b3eab52d01e29b5a57a1a010dede0eba5a3fa0` |
| `admission-review.json` | `7b8454eedac7ad64c6de6d5a721bd1bb638db0aa6342700b8f8ba422c9241c3a` |
| `cash-presence.json` | `5731f9df9f695c595cb4d3746548794abbc320e6403eb2d4e96389403eee9cd5` |
| `review.json` | `164ae2f9869981af9085597ed5c79fc34578c50a53a5c64d713031ce350d0778` |

| Phase | Wall / CPU | Kết luận |
|---|---|---|
| 4source requests + seals/log | 1,825s /0,219s | 0cachehits/4misses,0retries,PID9892terminal0 |
| Admission raw/canonical | 0,100s /0,094s | Source fixture only, không PnL |
| Full reviewer gồm admission+cash+5mutations | 0,336s /0,281s | Dòng admission nằm trong dòng này, không cộng hai lần |
| Focused9tests | 0,290s unittest-body | Không fullsystem/broker/edge certification |

Nút thắt của hướng stock hiện là **đúng semantics và khả năng áp dụng cho
program**, không tốc độ CPU. Chưa có lý do GPU/Rust rewrite hoặc data migration.
Thời gian research/authoring chưa instrument, giữ unknown. Không xóa logs/raw,
không đổi UI/runtime/MT5/skills/globalconfig, ownholdout2025+ vẫn đóng. Existing
research/qualification/continuity/retrospective skills đủ workflow này.
