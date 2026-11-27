# Phá kênh20 trên2013–2021: đã đếm, phải đọc cùng dữ liệu thiếu

12/11/2026. **Hoàn tất thêm9năm với cùng FP07. Chưa thể nói cadence ổn định
suốt quá khứ vì dữ liệu cũ làm nhiều cửa giao dịch bị chặn.** Không có PnL,
financial simulation, broker/model/network calls hoặc data2025+ mới.
[Protocol](US500-CHANNEL-HISTORY-PROTOCOL-20261112.md) commit`dc92d0a`,
preflight amendment`58f74fa` trước mọi số đếm; các năm xấu/thiếu vẫn giữ đủ.

## Kết quả từng năm

Đơn vị: signal đầu ngày có đủ quote tại clock entry dự kiến, chưa là fill/
trade đã qua positions/risk/fees. Per5 dùng toàn scheduled cash sessions,
không chỉ ngày trade hoặc ngày dữ liệu đủ. Rawsignals là breakout episodes.

| Năm | Rawsignals | Cơ hội đầu ngày đủ quote | Mỗi5phiên lịch | Tuần không cơ hội | Cửa10–15NY đủ dữ liệu /phiên thường | PairedcashM1 đủ |
|---|---:|---:|---:|---:|---:|---:|
|2013|86|47|0,93|34/53|60/249|89,48%|
|2014|33|24|0,48|40/53|35/249|92,86%|
|2015|224|133|2,64|3/53|183/250|99,11%|
|2016|257|160|3,17|0/52|219/251|98,42%|
|2017|69|46|0,92|32/52|59/249|94,93%|
|2018|199|107|2,13|14/53|140/248|98,88%|
|2019|142|87|1,73|16/53|115/249|98,77%|
|2020|240|152|3,00|4/53|206/251|98,61%|
|2021|265|156|3,10|2/52|195/251|99,85%|

So với [kết quả gần đã có](US500-OPPORTUNITY-SCREEN-RESULTS-20261112.md), reuse
savedrows và hash, không replay prices/numerical study2022–24:

| Năm | Cơ hội đầu ngày đủ quote | Mỗi5phiên lịch |
|---|---:|---:|
|2022|195|3,88|
|2023|174|3,48|
|2024|171|3,39|

9năm cũ có1.515rawsignals,915firstdays,912firstdays đủ quote. Không chọn signal
sau để bù signal đầu thiếu quote:2013thiếu2firstclocks,2018thiếu1;rawquote
missing còn gồm một số signal sau. Không gộp raw/first/costs thành mẫu độc lập.
Monthly/quarterly distributions, zero periods và reason counts giữ trong JSON.

## Vì sao không kết luận năm ít tín hiệu là rule kém?

Luật đã khóa: khi thiếu M1 cash, reset history nếu M15 thiếu và ngừng phát
signal ở phần còn lại của ngày. Chỉ cần mất một phút sớm cũng có thể ảnh
hưởng nhiều giờ sau. Không được chèn giá hoặc nhìn cả ngày rồi xóa entry trước gap.

Ví dụ2014có92,86%phút cash, nhưng chỉ35/249phiên thường đủ prefix/window
10–15NY. Các phiên khác có thể có một phần dữ liệu dùng được, **không phải
tất cả đều bị bỏ cả ngày từ đầu**. Không gọi số24 là toàn bộ cơ hội thật mà
thị trường2014có, cũng không suy35phiên là toàn bộ eligible sessions.

2013/2014/2017đặc biệt bị data blocks;2018/2019cũng nhiều cửa bị ảnh hưởng dù
tỷ lệ phút gần99%. 2016/2020/2021quan sát khoảng3–3,2cơ hội/5phiên, nhưng vẫn
không là proof về full-data cadence hoặc lợi nhuận. Dữ liệu mất có thể làm
thay history/ATR/state nên số đếm không tự là lowerbound được chứng minh.

Cột “cửa đủ dữ liệu” là chẩn đoán hồi tố sau run, **không dùng lọc entry**,
không đổi mẫu số sang ngày đẹp; đủ cửa dữ liệu cũng chưa chứng minh đủ indicator
warmup/targetbroker execution. Lịch cashNYSE không là hợp đồng giờ CFD của quỹ.

## Giữ nguyên gì, đã kiểm gì?

Same FP07 prior20high/low, closedATR14Wilder,0,10ATR,10–15NY, BUY/SELL,
episode dedup/firstday và gap/shortsession rules. Mỗi năm reset giống parent,
không warmup năm trước. Không MA/threshold/hourgrid. Signal→quote availability
không có exit/SL/order state hoặc risk/prop promotion.

Nguồn: [accepted explicit-source long correction](INDEX-LONG-EXPLICIT-RESULTS-20261108.md),
source receipt và proof/reader/native-oracle hashes từng năm được pin. Nến
giá/pairing/calendar/4quarters vẫn exact; không normalize/reseal market data.
2012không có full-year proof phù hợp nên không đọc.2013–2021đã consumed trong
research khác, **không gọi đây là clean OOS**;2025+ không mở.

-11focused tests trong lượt này đạt:7source admission (gồm2scope regressions),
  4history/coverage/source-newline tests.9signaltests trước được reuse vì luật
  không đổi; không tuyên bố chạy lại chúng hoặc old financial batches.
-Rule/preparation/native-lock identity so parent:4files byteexact; chỉ source
  `us500_opportunities.py` đổiLF→CRLF sau Git. Snapshot gốc đúng oldhash và
  normalized bytes equal; không semantic edit. New manifest giữ old/new hash.
-Final savedreview9annualcases: source/input/manifest/result hashes, raw
  ordering, BUY/SELL/NYdecision clocks, firstday/daily/monthly/quarterly/weekly
  arithmetic. Same-agent/separate arithmetic, chưa independent feed/reviewer.

## Failure, hiệu năng và quyết định

Preflightv1 bị exact-source-identity guard chặn trước price-quarter reads,
0years; giữ `failure.json` với sourcecheckpoint`dc92d0a`. Amendment chỉ cho
Python source CRLF/LF khi verified frozen snapshot khớp; data/.lock và semantic
source changes vẫn reject. V2newoutput hoàn tất, không sửa oldpins hoặc kết quả.

| Phase | Wall |
|---|---:|
|Source admission+native indicator preparation9năm|42,148s|
|Count/write9năm|1,040s|
|Toàn v2, gồm final checks/persistence|45,407s|
|Code/research/preflight repair/docs/Git|Chưa đo riêng; không gọi toàn task45s|

Đã lưu từng năm, source snapshots, progress/events/PID/CANCEL/deadline; không
còn numerical job/controllerlock. Không cần thêm engine/GPU/skill hoặc chạy
lại kết quả không đổi để có bảng này. CLI này chưa có state-resume contract.

**Quyết định:** giữ FP07 đáng cân nhắc economic-screen riêng trên data gần
đã admitted, nhưng chưa nâng bằng chứng thành “đều mọi năm”, edge hoặc pass
challenge. Không loại hoặc chỉnh rule từ các năm bị gaps; nếu cần kiểm chắc
cadence toàn2013–2021 thì cần giải quyết nguồn/coverage trước kết luận đó.
Chưa tự download/backfill/nới gap-policy trong task này.

Evidence private tại campaign `execution-v1/us500-channel-history-v1/` giữ
preflightfailure; **`us500-channel-history-v2/`** giữ manifest/source-snapshot,
9annualresults/inputadmissions, completed-years/result/progress/events/timers
và`final-census-review.json`. Catalogue123/88/53 và3frequencydesignsFP06–08
giữ; đây là windowextension củaFP07, không strategy/ruleversion mới.
