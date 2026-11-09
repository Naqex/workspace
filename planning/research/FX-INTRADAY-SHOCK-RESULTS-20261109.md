# R090: tiếp diễn trong ngày không qua sàng lọc hai năm

Thực hiện [protocol](FX-INTRADAY-SHOCK-PROTOCOL-20261109.md), commit
`c6fd32f` trước nguồn thật và outcomes. Đã kiểm đủ 521 ngày trong tuần,
12 sổ và 3.126 trường hợp tài chính. **Gác phiên bản hiện tại:** năm 2022
âm trước phí, không đạt điều kiện cả hai năm dương sau phí cao. Chưa có
ứng viên challenge; không bác bỏ mọi chiến lược momentum trong ngày.

## Cách thử và kết quả

Tại các mốc từng giờ 01–18 UTC, so biến động từ 00 UTC với phân phối của
20 ngày trước. Chỉ nhận lần vượt ngưỡng đầu tiên đã quan sát được, quyết
định lúc h:01, vào ở giờ kế tiếp theo hướng biến động, thoát 20 UTC. Dữ liệu
sau tín hiệu không được dùng để chọn lại giờ hoặc hướng. Đây là own hourly
adaptation, không first-tick crossing hoặc sao chép nguyên phương pháp paper.

Tiền trong bảng là **USD trên 100.000 EUR notional nghiên cứu**, không lợi
nhuận tài khoản 10.000 USD, risk 25 USD/lệnh hoặc khối lượng an toàn để trade.

| Năm | Cơ hội được chọn | Phí chuẩn | Phí cao | Selected chưa rõ giá vào/ra |
|---|---:|---:|---:|---:|
| 2019 | 18 | +664 USD | +592 USD | 0 |
| 2022 | 26 | −1.479 USD | −1.583 USD | 0 |

Control ngược hướng cùng tín hiệu: 2019 −943/−1.015 USD, 2022 +1.038/+934 USD
ở phí chuẩn/cao. Không chuyển control 2022 thành winner: năm 2019 của nó âm,
và primary đã được chọn trước outcomes. Null có 0 exposure và 0 PnL.

| Khoản trên primary, USD/notional nghiên cứu | 2019 | 2022 |
|---|---:|---:|
| Midpoint price benchmark | +803,50 | −1.258,50 |
| Spread đã nằm trong Bid/Ask | −49,50 | −90,50 |
| Commission | −90 | −130 |
| Extra slippage trong kịch bản cao | −72 | −104 |
| Funding trong window đã đăng ký | 0 | 0 |
| **Net phí cao** | **+592** | **−1.583** |

Không trừ spread hai lần. Commission 5 USD khứ hồi/unit và stress extra slip
4 USD/unit là giả định đã khóa; chưa là phí thật của tài khoản FTMO/The5ers.
Funding 0 chỉ vì entry 02–19 → exit 20 UTC không qua declared 17 NY rollover.
2022 không thể được giải thích chỉ bằng phí cao: price benchmark đã âm.

## Nguồn và causality

- Pilot chọn theo lịch trước giá: Tuesday đầu tháng 2 của mỗi năm, 61 mốc
  mỗi ngày, **122/122** hợp lệ; 88 mốc dùng lại từ R089, 34 mốc mới. Không
  tính tín hiệu thật hoặc PnL trong pilot; 4 mutation về giá/giờ/sequence/
  thiếu target bị phát hiện.
- Full source census đúng 4 partitions: 2018 40 warmup slots, 2019 5.481,
  2021 40 warmup slots, 2022 5.460. **11.021 mốc, 10.985 trong lag 60 giây**;
  36 late/missing giữ explicit. Source admission xác nhận phép biến đổi và
  census đúng, không có nghĩa mọi mốc đều available hoặc fill được ở broker.
- Full phase reuse 1.990 mốc từ sealed packet R089/pilot; decode 9.031 mốc
  mới. Native quote decoder và Fraction/raw selector riêng đối chiếu actual
  time, Bid/Ask, sequence, predecessor và registered H1 reference. Giữ
  original producer runtime, ghi consumer runtime riêng, không sửa cachekey
  hoặc rebuild raw. Không tải lại lịch sử, không thêm provider.
- 2019: 25 ngày unavailable history, 1 ngày unavailable prefix, 217 normal,
  18 shock. 2022: 1 ngày unavailable prefix, 233 normal, 26 shock. Cả 521
  ngày giữ trong mẫu; feature coverage 235/261 và 259/260 đều trên 80%.
- Missing trước crossing làm không nhận tín hiệu ngày đó. Missing sau
  crossing không đổi selection/side; entry/exit thiếu sẽ là selected unknown,
  không retry ở giờ sau hoặc biến thành PnL 0. Actual cả 44 selected có đủ
  endpoints, không vì thế bỏ kiểm nhánh unknown ở synthetic.
- Khoảng chờ tới giờ kế tiếp là một phần recipe đã đăng ký. Kết quả âm không
  chứng minh entry tức thời tốt hơn, cũng không cho thay lag sau outcomes rồi
  giữ cùng version. Dữ liệu hourly không chứng minh SL/path/risk trong giờ.

## Kiểm chứng và giới hạn

5 focused tests đạt trước nguồn: first crossing/cost BUY–SELL, strict boundary,
known-at, missing prefix/history, future exit invariance, selected unknown,
calendar/holdout guard và no false pass. Native cost core được reuse.

Trước actual PnL có 84 synthetic financial cases, thêm full empty calendar
3.126 cases và 9 guard mutations; normal/missing/late/future-sign-change/null
đều có đối chiếu. Actual 3.126 cases/12 books được reviewer riêng tự tính
mean/variance bằng rational determinant, first-hour prefix, dấu/clock, nguồn,
costs/rounding, summary và frozen gate. 10 mutations bị chặn: net, commission,
side, entry clock, first hour, feature mean, missing weekday, authority,
promotion gate, source authority. Cùng agent, codepaths/số học khác; không
gọi thành independent human/feed review.

Correctness/source pass tách khỏi profitability fail. Chưa SL, TP, sizing,
account equity, margin, daily reset, luật quỹ, time-fit 3/6/12 tháng, target
contract, clean OOS, prospective reconciliation hoặc owner handover. Không
OrderCheck/OrderSend, không broker/runtime mutation hoặc own data 2025+.

## Hậu kiểm và thời gian

| Lát | Wall thực đo | Phạm vi |
|---|---:|---|
| Pilot source + review | 14,732 s | 122 mốc; 88 reuse + 34 mới |
| Full source + review | 112,748 s | 11.021 mốc; 1.990 reuse + 9.031 mới |
| Synthetic preflight | 0,275 s | 84 cases và guard mutations |
| Numeric | 0,667 s | Nằm trong economic phase bên dưới |
| Economic phase + full review/mutations | 3,357 s | 3.126 cases/12 books |
| 5 focused tests | 0,059 s unittest body | Không command/end-to-end wall |

Full source/preflight/economic successful phase tổng khoảng **116,381 s**,
không gồm pilot/research/authoring/tests, không nhận đây là thời gian người
dùng phải chờ end-to-end. CPU full source 106,828 s, economic 3,250 s;
peak RAM và tổng authoring time chưa đo. Không claim speedup so với workload
R089 hoặc lấy thời gian PnL dưới 1 s làm thời gian toàn quy trình.

**Cải tiến có ích đã dùng:** reuse target packets đúng seal trước đọc raw;
không rerun R089 hoặc archive chase. Bộ 11.021 mốc hourly mới tiếp tục được
giữ để consumer sau reuse nếu đúng scope/semantics. Chưa có nút thắt cần GPU/
Rust, framework, skill hoặc dashboard mới; source validation vẫn phần lớn
chi phí. Không nới gate để nhanh. Không failure/retry trong pilot/full/
preflight/numeric lần này; mọi process đã terminal, không job đang chạy.

## Artifact và quyết định tiếp

Privatebase:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.

- `execution-v1/fx-intraday-shock-source-pilot-v1/` và
  `fx-intraday-shock-source-full-v1/` giữ raw/native/reference receipts,
  target calendar trong manifest, seals, snapshots, progress và events.
- `execution-v1/fx-intraday-shock-component-v1/` giữ synthetic rows/preflight,
  normalized observations/quotes, rows/summary/decomposition/result/review,
  input/source pins và status. Result `pending_review` bất biến đi cùng
  `review.json` bind exact SHA và progress `completed_reviewed`.
- Saved controllers tại privatebase:
  `run-fx-intraday-shock-source-v1.py`, `run-review-fx-intraday-shock-v1.py`.

| Artifact | SHA256 |
|---|---|
| Full source result | `61f25e5573f27e8a7f75a6c01cbe844b62309737db0ea40c5aaba83afa2774bb` |
| Economic result | `5ceb6bb597e139d6b753816960f043cf055b6af2200c9bd48c1f7ba4195f4222` |
| Economic review | `526ebf68e062785b86392db913cdfb545658045f7b30c942ce62b6708724e8cf` |
| Summary | `2c186a63c7d27ce7cac4119fa69b1631a602957f0c4719a5ec35540df98b364e` |
| Decomposition | `f2d3dd8f8abeb00967b7c6d655e9a7826294e95eca805d1354d8c53a41f9e283` |

Gác exact R090; không mở temporal/history/risk wrapper cho bản đã không qua
hai năm. R089 next-day và R090 same-day là hai related hypotheses, không
hai bằng chứng độc lập cho cùng edge. Không đổi lag/hour/k/side/fees hoặc
chọn riêng giai đoạn dương để cứu. Catalogue90 research records/58 account
policy versions; chưa challenge, Goal active/C1/C2 chưa đạt.

Bước kế tiếp là admission cơ chế khác có nguồn lợi nhuận và đầu vào rõ, hoặc
một blocker material của survivor đã có được giải quyết bằng nguồn mới.
Tra lại catalogue/source/cost gaps trước khi đăng ký; không thêm biến thể
chỉ vì code/quote packet đã sẵn. Phí/spec còn unknown không được mặc định 0,
và không tự gọi broker để lấp gap trong task nghiên cứu offline.
