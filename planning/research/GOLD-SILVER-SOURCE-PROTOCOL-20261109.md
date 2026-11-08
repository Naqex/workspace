# Vàng/bạc: kiểm nguồn trước kiểm quan hệ và bot

Đăng ký trước fetch giá. Lát tiếp sau [R066](NASDAQ-NOISE14-RESULTS-20261109.md),
khác fixed-hour/directional momentum: xem relative-value của hai kim loại.
Chung tài sản cơ sở không chứng minh cointegration hoặc lợi nhuận sau phí.

Primary đọc09/11: [CESifo12559](https://www.ifo.de/en/cesifo/publications/2026/working-paper/long-run-linkages-and-parameter-instability-gold-silver)
abstract mô tả bất ổn tham số và khác biệt trước/sau2017 trên futures. Chỉ
abstract đã đọc, chưa full-method replication. Đây là lý do kiểm quan hệ trước
bot, không là chứng minh spot/CFD pair có edge. Abstract có aggregate đến2025:
ghi literature exposure; không mở own holdout2025+ hoặc tự gọi literature blind.
[Maintainer XAG metadata](https://www.dukascopy-node.app/instrument/xagusd) và
installed1.51.1 xác nhận mapping `xagusd`→`XAG-USD`, `xauusd`→`XAU-USD`.
Ngày bắt đầu metadata không chứng minh actual source coverage.

## Một source pilot hữu hạn

- Existing Dukascopy public provider, pinned installed `dukascopy-node1.51.1`
  MIT/runtime/lock đã audit. Không install/update hoặc thực thi code từ paper.
- Bốn H1 side requests: `xauusd`,`xagusd` × Bid/Ask, đúng01/11/2018UTC đến
  02/11 exclusive. H1 API trả raw cả tháng11/2018; ghi whole-month exposure,
  export chỉ ngày đã chốt. Không lấy dates trong example2025 của website.
- Reuse `dukascopy_cached_h1.cjs` explicit-source only; raw grid kỳ vọng0,001,
  volume millions/round4 theo native. Raw và proof/hash phải được giữ; không
  padding, lọc volume0 hoặc biến quote volume thành exchange volume.
- WAFoff, token-cachefalse, retries0, cumulative transient failure budget1,
  không retry sau failure/auth/403/429. One writer, deadline180s/CANCEL,
  tối đa4month sources, reuse cache nếu đã có. Không thêm ngày/instrument.
- Full source byte/hash/schema/census, UTC H1 order/grid/OHLC, Bid/Ask Open/
  Close noncrossed và same-side fields đối chiếu raw bằng Fraction + canonical
  decoder. Không gọi paired sidebars là actual joint ticks. Mutation sai
  price/clock/side/count/hash/authority phải phát hiện trước source admission.
- Output private `challenge-discovery4-20261108/execution-v1/gold-silver-source-v1`:
  config/pins/raw proofs/exports/result/review/progress/timing/failure. Không
  ratio/trading/statistical outcomes trong source probe.

## Formation chỉ được làm sau admission và protocol riêng

Đề xuất khóa trước orientation y=ln(XAU BidClose),x=ln(XAG BidClose), formations
2018 và2021 để nghiên cứu subsequent2019/2022 đã exposed. Sample16UTC H1Close,
known17UTC; dùng frozen US cash business-date calendar như sample design,
không chứng nhận metals market hours. Retain census, min240observations/window,
thiếu source/crossed ngày đã định → inconclusive, không drop ngày để fit.

Reuse fixed Engle–Granger constant/maxlag1/autolagNone và reviewer của R035;
leg-label mapping phải ghi XAU/XAG, không báo GBP/AUD. Không pair/orientation/
lag/window grid; statistical filter chỉ ưu tiên economic design, không edge.
Chưa tải full formation history, chưa risk/hedge/2leg execution hoặc PnL từ
protocol source này. Không broker/account/paid provider/holdout/production.
