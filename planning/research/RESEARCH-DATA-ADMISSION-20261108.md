# Chuẩn hóa đầu vào và mở tiếp R026 — protocol 08/11/2026

Đăng ký trước khi chạy validator mới hoặc thu dữ liệu mới. Thuộc
[Goal mới](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md). Không sửa raw/seals,
DatasetManifest public API, PostgreSQL hay metadata của các study đã freeze.

## Quyết định trước outcome

`DatasetManifest` của Trader đã có source, raw/normalized hash, quality và
holdout policy. Quarterly M1 reviewer đã có seal/clock/grid/source proof,
nhưng giới hạn US500/four quarters; fixture EZU/SPY/EURUSD đang có phải dùng
script private riêng. Gap cụ thể là **admission metadata có thể kiểm bằng
code cho fixture nhiều instruments**, không phải thiếu database/vector RAG.

Reuse `candle_source_provenance.explicit_candles/inspect_expansion` và
`sealed_m1_review.validate_rows/paired_spreads/digest`; thêm reviewer nhỏ cho
manifest request/seals hiện có. Nó đọc raw được pin, không tải mạng, không
sửa/sort/fill dữ liệu, không export thành nguồn mới. Output chỉ có giá trị
source fixture; không tự chứng nhận execution prices, OOS hoặc edge.

Metadata có version: parent manifest/result hashes, protocol, producer pins;
UTC Unix milliseconds, M1 open timestamp/close known after one minute;
instrument/provider symbol, base/quote/price unit/grid, adjustment basis;
data role/exposure đã consumed hoặc unknown, quality tự tính từ raw. Không
cho sidecar tự nhận clean OOS hoặc bỏ quality để pass. Chưa có lịch sử
exposure được kiểm thì giữ unknown.

## Fixture áp dụng và acceptance

- Sáu exports native ngày03/01/2023 ở `execution-v1/fixing-proxy-fixture-v1`,
  original manifest/seals và raw cache nguyên vẹn. Mỗi side so exact giá/
  volume/timestamp với raw bằng decoder Python riêng; nhận diện padding,
  giữ cả nến nguồn volume0. Ghi missing/unpaired, không giấu bằng intersection.
- Metadata mới và output ở `execution-v1/research-input-admission-v1`,
  package/source/protocol/input bindings, phase wall/CPU. Không sửa output cũ.
- Mutation checks: wrong hash, units/clock/grid, source price, padding,
  adjustment semantics/role, unknown exposure/clean claim, missing side và
  holdout scope. Output không được hiểu là authority dù fixture đạt.
- Không benchmark full engine; chỉ báo thời gian thật của validator và chất
  lượng fixture. Giữ result/progress/failed attempt, không rerun unchanged.

## R026: hypothesis và dữ liệu cần thêm

Kế thừa [method review](FX-MONTH-END-FIXING-METHOD-20261108.md), không bắt đầu
lại từ abstract. Refresh primary sources08/11: Melvin/Prins §§2–3/5.1 mô tả
hedge và returns của **Total Market Indices**, không nói tên đó nghĩa là
**total return indices**. Không tự ép dividend-adjusted total returns làm
định nghĩa của paper. Với proxy ETF/CFD vẫn cần pin price/adjustment convention;
không gọi chúng là exact replication hoặc không có dividend distortions.

Hướng test tiếp: bilateral price-proxy adaptation, so chênh lệch return
EZU_USD/EURUSD với SPY_USD, chỉ dùng giá đồng thời đã có trước phiên cuối
tháng. Equity EUR tương đối mạnh hơn dự đoán áp lực bán EUR khi tăng hedge;
đây là adaptation được suy ra, không coefficient/fitted portfolio của paper.
Không giữ vị thế ETF; chúng chỉ là signal inputs, FX mới là component outcome.

Trước PnL cần khóa riêng: thời điểm đầu/cuối signal, NYSE sessions/early
close, fixing-day proxy và London DST, missing-data policy, mapping direction,
costs/entry/exit/delay, primary/control và tiêu chí. Lịch last NYSE session
không là lịch WMR. LSEG v31 §3.3 cho phép holiday/early-time exceptions; phải
giữ gap lịch sử, không dùng bản2026 làm proof mọi event2019/2022.

Lát kế tiếp sau fixture: source-only **hai tháng pilot Jan/Feb2022** để kiểm
availability/alignment/currency của first/penultimate NYSE close và FX trên
last-session day; tối đa28 instrument-side/day requests, không outcome/PnL
hoặc2025+. Cùng public Dukascopy/pinned1.51.1 đã audit; retry0, WAF/token-cache
off, deadline300s, CANCEL/status/log/source pins; reuse exact cached URLs.
Không đổi tháng/proxy để né dữ liệu thiếu. Pilot đạt mới đăng ký component
riêng/longer coverage, không tự coi pilot là đủ sample strategy.

## Nguồn vừa refresh và giới hạn

- [ECB author paper](https://www.ecb.europa.eu/events/pdf/conferences/131216/Third_FX_Workshop_MELVIN_PRINS_Equity%20hedging%20and%20exchange%20rates%20Nov%202013.pdf): §§2–3/5.1, cơ chế/relative returns; không retail bot proof.
- [LSEG WMR v31](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/wmr-fx-methodology.pdf): §3.3/4; calendar exception gap, current method không là historical contract.
- [Dukascopy dividends](https://www.dukascopy.com/europe/english/cfd/cfd-dividend-adjustment/?mob=1): cashflow adjustment có thể riêng khỏi giá; không xác minh adjustment basis của historical ETF export.
- [AQR trading costs](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies): chi phí/turnover quan trọng; institutional equities không chứng minh prop-CFD fit hoặc cho phép giảm phí của project.

## Kết quả

Chưa thực thi tại thời điểm đăng ký; cập nhật kết quả/bindings sau thực thi,
giữ nguyên phần quyết định trước outcome ở trên.
