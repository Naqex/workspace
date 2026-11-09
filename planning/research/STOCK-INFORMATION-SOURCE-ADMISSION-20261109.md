# Cổ phiếu và thông tin mới: admission nguồn trước chiến lược

Đăng ký trước fetch/quote inspection. Đây là source-only fixture, chưa một
accountpolicy mới hoặc quyền thay FTMO/The5ers program. Goal C1/C2 vẫn active.

## Vì sao khảo sát hướng này?

[R068/R069](GOLD-ML-SL-LABELS-RESULTS-20261109.md) không có qualified signals.
Nhiều exact price-only recipes đã không qua screening; hướng khác cần kiểm
information conditioning, thay vì đổi threshold/SL để ép bản cũ có lợi nhuận.

Primary paper [Stocks in Play ORB](https://concretumgroup.com/wp-content/uploads/2026/02/A-Profitable-Day-Trading-Strategy-For-The-U.S.-Equity-Market.pdf),
đọc09/11 §§2.1/3/4, dùng traded-share volume, past14daily/liquidity/ATR,
opening5relativevolume và PIT universe gồm delisted stocks. Không giống QQQ
opening5/10R parentR065: paper này dùng stop-entry tại rangeedge/SL0,1ATR/EOD.
Không copy best-performer list, commission hoặc reported returns vào project.
Chưa full paper/data/code replication hoặc kiểm selection ngoài paper.

[Package output schema](https://www.dukascopy-node.app/output-formats) phân biệt
tick available quote volume với candle volume; chưa chứng minh stock-CFD candle
volume là exchange shares. [Dukascopy Bank market description](https://www.dukascopy.com/swiss/english/cfd/range-of-markets/)
còn ghi CFD prices không là exchange-price information. Vì vậy hiện **không
admit replication relative-share-volume paper** trên nguồn này. Quote activity
proxy, event-calendar hoặc price-only adaptation nếu làm là hypothesis khác.

[Corporate actions](https://www.dukascopy.com/swiss/english/cfd/cfd-corporate-actions/)
giải thích điều chỉnh positions/splits, không chứng minh historical downloaded
bars là adjusted hay unadjusted. Giữ unknown, không gắn historical USD/share
hoặc ATR dollar filters sau back-adjustment chưa kiểm.

## Đúng quỹ/program trước khi mở rộng

[The5ers stock FAQ](https://the5ers.com/faqs/available-stocks-for-trading/),
updated15/10/2026, đọc09/11: stocks chỉ Bootcamp/ProGrowth; liệt kê AAPL/MSFT,
contract1/minstep1/leverage1:5/commission0,1% mỗi side. Không áp cho HighStakes,
không thay profile/quyền đã giao. Đây là public hiện hành, không historical
broker cost hoặc account-specific proof. [FTMO symbols](https://ftmo.com/en/symbols/)
textfetch chưa trả individualstock rows/specs; giữ currenttarget mapping unknown.
Không chọn hãng/program khác chỉ để hợp thức hóa stock backtest đẹp.

## Fixture khóa trước nguồn

- Đúng hai symbols metadata đã có trong pinned dukascopy-node1.51.1:
  `aaplususd`→`AAPL.US-USD`, `msftususd`→`MSFT.US-USD`.
- Ngày03/01/2019UTC,4requests (hai symbols×Bid/Ask), M1 fullUTCday. Apple
  [guidance revision02/01/2019](https://www.apple.com/newsroom/2019/01/letter-from-tim-cook-to-apple-investors/)
  là known-event source fixture, **không PnL/winner hoặc PIT event calendar**.
  Page chưa chứng minh exact publication time. MSFT là comparison source,
  không control trade hoặc independent marketfeed. Không thêm TSLA/beststocks.
- Native expanded output giữ để kiểm raw/full decoder, `ignoreFlats:false`,
  explicit UTC/m1/JSON/volumeUnits:millions. Reviewer tách explicit observations
  khỏi padding, giữ source bars volume0; không sửa/fill/sort output cũ.
- Reuse `getCachedM1`, source-only raw decoder và `research_input_admission`.
  Extension nhỏ nhận `stock_cfd_proxy`, giá quote-per-share-proxy, adjustment
  unknown, volume semantics `provider_candle_volume_unverified_exchange_shares`;
  không cho metadata tự nhận exchange shares/adjusted/PIT universe đã kiểm.
  Raw multiplier là grid cần kiểm, không suy broker tick từ tên symbol.
- Report cash-session presence09:30–16:00America/New_York từ calendar hiện có,
  tức14:30–21:00UTC cho fixture; record missing/unpaired/crossed endpoint fields.
  Presence không chứng minh simultaneous quotes/fills, feed completeness ngoài
  ngày này, corporate-action history hoặc trading permissions.
- Private output `execution-v1/stock-information-source-fixture-v1`, reuse
  campaign cache; nooverwrite raw/seals/snapshots. Pin producer/helper/reviewer/
  protocol/package/lockfile. Budget4URLs/retry0/cumulativefailurecap1,
  WAF/token-cacheoff/deadline180s/CANCEL/onewriter/events/progress. Không auth,
  provider mới, paiddata, holdout2025+, model/broker calls hoặc strategyPnL.

## Cửa quyết định và kiểm chứng

Trước fetch: focused regression cho legacyFX/ETF và stock metadata mutations
(unit/adjustment/volume/PIT claim). Sau fetch: hashes/seals/census/clock/grid,
raw→canonical fullfields; mutation price/padding/count/semantic claims bị chặn.
Không sửa frozen inputs để reviewer pass. Status chỉ `source_fixture_verified_only`.
Nếu đủ source thì đăng ký adaptation/missing dependencies riêng trước history
và economics; nếu thiếu volume/universe/targetfit thì gác replication, không
tải hàng loạt để mong ra winner. Lưu failures/phase timing/remaining gaps và
update current context/index; không cần skill/framework/database mới.
