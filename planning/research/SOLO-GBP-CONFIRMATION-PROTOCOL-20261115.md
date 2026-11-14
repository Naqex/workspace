# S01 — xác nhận nguồn/đường giá GBPUSD Asia–London sweep

Owner cho phép nghiên cứu độc lập toàn bộ mục tiêu ngày 15/11/2026.
Baseline workspace `5864d8b`; task/goal trong `SOLO-PROP-SYSTEM-PLAN-20261115.md`.
Đây là một thí nghiệm hữu hạn thuộc goal dài hạn, không tự kết thúc goal khi fail.

## Câu hỏi và lịch sử lựa chọn

Recipe kế thừa duy nhất: `GBPUSD.SWEEP.ASIA.LONDON.DAY` của V2/V3.
Screen H1 đã xem: 147/153 raw, 142/144 fills, +5,6166/+26,0753R trên Dev.
H1 không xác định paired entry quote hoặc thứ tự SL, nên chưa chứng minh edge.
Chọn ứng viên để giải quyết gap nguồn, không gọi nó đã qua Stage-0 gốc.
Giữ lịch sử 112 configs, V3 ngoại lệ marginal selection, các fail và exposure
2024 đã công bố. Không mở V4 của thread gốc để thiết kế study này.

Giả thuyết có thể bác bỏ: lợi nhuận screen còn tồn tại sau paired ticks/phí
và GBP góp thêm giá trị vào **A+EUR**, không chỉ ít tương quan với Gold.

Đối chiếu source trước numeric mới: saved raw DAY markout sau phí thực tế đã
âm cả2022 (−0,0004035374, khoảng−4,0354pip) và2023 (−0,0000097386,
khoảng−0,0974pip). Vì vậy S01 xác nhận **recipe có Natural SL đã được thử
trong ngoại lệ V3**, không tuyên bố tín hiệu raw có edge hoặc pass Stage-0.
Sự khác biệt raw và stopped outcomes phải được báo rõ cùng selection history.

## Budget khóa trước outcome mới

- Một recipe, hai chiều cùng lúc; không BUY-only/SELL-only, đổi giờ, filters,
  SL, TP, horizon, ATR, tối ưu risk hoặc chọn lại vùng.
- Vùng Á 00:00–06:00 UTC; H1 sweep qua biên rồi đóng quay lại với màu nến
  xác nhận trong 08:00–11:00 UTC; semantics đúng saved generator, không đổi
  UTC sang London local theo DST.
- Natural SL ngoài nến tín hiệu ±0,1 ATR14 đã biết; no hard TP; DAY20:30UTC
  và holiday clamp kế thừa. Fill là quote hợp lệ đầu tiên sau decision.
- Spread paired Bid/Ask; commission $5/lot/vòng, slip $4/lot/vòng; natural
  cost gate15%, min/step0,01lot, contract100.000 base units. Giá/lot đúng units.
  Giữ ngày phải flat trước rollover; không đơn giản đặt swap0 nếu path chưa rõ.
- Economics reference $150 risk; GBP marginal $75 thêm vào A$150+EUR$75.
  Một trọng số đã chốt, không grid. Gold giữ hai models SYM−40/−40, ASYM−45/−5.
- Development2022–2023; chưa đọc source/outcome mới2024. 2025–2026 đóng.

## Nguồn và đường ghi riêng

Read-only parent evidence dưới
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`:
`prop-atlas-v2-20261114/stage0-GBPUSD.SWEEP.ASIA.LONDON.DAY.json`,
`GBPUSD-endpoint-manifest.json` trong cùng folder,
`fx-h1-history-v3/*gbpusd*-source-proof.json` chỉ2021warmup/2022/2023,
và V3 sealed curves/decisions. Hash input và source code trước sử dụng.

Mọi output mới nằm trong
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S01-gbp-confirmation/`.
Không gọi CLI cũ với global JOB. Dùng pure readers/math, output explicit.

Timestamp census ban đầu: toàn300raw có3.576heldhours; parent endpoint
manifest tái dùng292hours phù hợp; còn3.284hours trước tìm cache bổ sung.
Đăng ký toàn bộ cohort, gồm cả14cost rejects trước đây, không chọn source
theo winner hoặc bỏ trade chưa có giá. Chỉ request giờ trong2022–2023.

Downloader reuse pinned dukascopy-node1.51.1, cache riêng, no browser/auth/WAF
bypass. Tối đa2 requests đồng thời, pause300ms giữa batches, tối đa20 transient
failures toàn attempt, tối đa2retry mỗi URL; deadline120phút. Nếu gặp auth/rate
limit không retry lách; giữ missing và receipt, dừng source stage theo policy.
Resume giữ cùng census/hash và sealed hours, không fetch trùng nếu cache hợp lệ.
Không tự bỏ unknown để lấy subset có lãi.

## Thứ tự và gate

1. Commit protocol trước source/numerical outcome mới. Seal raw cohort, input
   hashes, desired hours, producer và cache package version ở registration.
2. Đối chiếu clock/price grid/same-ms ordering, raw→binary. H1 proof có
   `observedTickTimestamps=false`: không biến separate BID/ASK candles thành
   paired ticks. So H1 từ ticks với source trên hours trùng trước PnL.
   Mismatch có receipt và quyết định source-only; không sửa candle theo profit.
3. Gap>15phút trong held path giữ unknown. Exception NY16:15–18:00 thuộc
   US500, không áp ngầm cho GBP/EUR. Kiểm fixture positive/negative và callsites.
4. Chỉ khi source hợp lệ, đo raw DAY markout, natural geometry/cost retention,
   exact SL/time exit, gross/fees/netR theo năm và chiều, concentration và DD.
   Raw markout là diagnostic của inherited trial, không đổi horizon để cứu số.
5. Promotion gate Dev: median friction/median naturalSL≤15%; retention≥60%
   mỗi năm; cả2022và2023 netR≥0, tổng≥8R. Không dùng ngoại lệ weakyear−1R của
   V3 sau khi thấy outcome. Nguồn thiếu thì inconclusive, không economic fail.
6. Fixed budget phải cải thiện Net/equity-DD của A+EUR ở cả Gold cost models;
   pooled daily correlation GBP↔A+EUR<0,25; báo thêm GBP↔EUR, từng năm,
   exposures/overlap, tail/top-trade dependency. Screen curves chỉ conditional
   M1-envelope nếu chưa exact joint tick. Không suy xác suất pass từ rho thấp.
7. Chỉ sau gate này mới mở slice shared-account3assets: reuse lifecycle,
   thực thi budget chung, không cộng riêng netR thành lợi nhuận tài khoản.
   Freeze composition/risk và commit trước historical validation2024 mới.
   Chưa cho phép mở2025–2026 hoặc kết luận Challenge-ready từ Dev.

## Dừng và review

Source/cost/correctness failure được giữ riêng. Một candidate fail thì đóng
S01 với nguyên nhân và bước mới dựa evidence; không sửa exit/risk hay hạ gate
trong study để pass. Thay đổi cơ chế tiếp theo là registration riêng có lý do.
Kiểm bằng implementation/arithmetic khác và regression có case lỗi thật;
phân biệt independent source/feed với independent code review.
