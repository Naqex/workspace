# FOMC surprise: kiểm nguồn lịch sử trước giả thuyết giao dịch

09/11/2026, tiếp[R027/R028 catalogue](STRATEGY-CATALOGUE-20261107.md) và
[residual admission](RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md).
Source-only, chưa candidate/recipe/returns hoặc grant/provider/account mới.

## Nguồn cố định trước tải giá trị

Author [historical repository](https://github.com/marekjarocinski/jkshocks_update_fed_202401),
commit`f04846678ad4ec981dc24de615c0af16dd3573e8`,20/04/2024. Authorhomepage
đã đối chiếu; README tại commit mô tả phạm vi1988–2023. Không dùng branchmain
của bản cập nhật2026 hoặc datasets hiện hành chứa ownholdout2025+.

Chỉ ba GitHubcontents GET tại đúng commit, không clone/install/run Matlab:

| File | Git blob SHA trước fetch | Vai trò |
|---|---|---|
|README.md|635449da6a2159e0e7204eef64fde82944aa91f8|Semantics/public citation, đã đọc trước registration|
|readme.txt|449851685b0b7eec045cbf82775d0ea9b1186765|Metadata bổ sung, không code execution|
|fomc_surprises_jk.csv|bb9f095dbbe7ac4033ece0ac0bb9b3b46fa80c23|Source historical event changes, chưa strategy PnL|

Metadata API đã kiểm không thấy license permissive; chỉ private research với
citation của tác giả, không copy/run code hoặc redistribute data; chưa quyền
realtime/trading-feed/redistribution của underlying vendors. Không dùng raw
data làm proof target-broker execution hoặc commercial licence.

## Scope và cửa kiểm

- Tải nguyên raw ở private `execution-v1/fomc-surprise-source-v1/`,nooverwrite;
  kiểm blob object SHA và SHA256, size, header, dates/order/duplicates/missing/
  finite numeric fields. Nếu có năm2025+ dừng và quarantine, không dùng làm
  holdout hoặc sửa lịch sử. Max3GETs/deadline90s,no retries/authchanges/WAF.
- Phạm vi toànfile theo metadata1988–2023 được consumed cho sourcecensus;
  không gọi những năm đó cleanOOS. Focus16scheduleddates2019/2022 từ accepted
  R062calendar, không chọn theo dấu hoặc độ lớn surprise. Các event khác vẫn
  giữcensus, không ép unscheduled thành scheduled.
- Giữ zero khác missing; Fraction/Decimal đối soát các ô numeric đã chọn.
  Không PCA/fullsample rotation/orthogonalization, regressions hoặc threshold
  tối ưu; các derivedshocks không tự thành causal input. Schema/timezone chưa
  rõ thì report unknown, không guess để tạo winner.
- Reconcile date/time với16officialrelease14ET của R062. Chỉ thử UTC và NY
  clock conventions đã khai báo, report matches; không chọn theo lợi nhuận.
  Đây là reconciliation, chưa là independent raw timestamp certificate.
- README mô tả median postwindow có thể kéo dài tối đa24h nếu ít quan sát.
  Vì vậy announcement timestamp/nhãn“30min” **không chứng minh** field đã có
  tại t+20/t+25min. Cần perrow availability bounds/observation counts hoặc
  conservative rule được đăng ký riêng; unknown phải chặn intraday signal.
- Kiểm sourceavailability validator bằng fixtures before/at/after known-at,
  unknown bound, future-fitted factor, delayed published dataset, nonfinite/
  missing vs0 và authority mutation. Không tự bỏ guard để admit source.

## Đầu ra và quyết định

Receipt/pins/snapshots/progress/events/PID/deadline và result/review giữ ngoài
chat, sourcefetch/parse/review timers riêng. Chỉ kết luận source fixture
reviewed hoặc inconclusive; không account policy, edge, prop-fit, G5/G6.
Intraday admission chỉ khi exactfield/availability/causality đủ; không lấy
public download hiện tại làm realtime feature historical. Nếu thiếu, giữ
gap và tìm observable primitive có thể tái hiện bằng nguồn được phép.

Giữ allnegative R062/R084/R085, không retune clock/fees để cứu. Không mua feed,
account/EA/challenge, không broker/holdout/runtime/globalconfig/skill mutation.
