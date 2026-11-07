# US500 noise14 — development2022 và exposed robustness

**Bản noise14 không qua tiêu chí giữ lại: 2023 và 2024 âm ở cả hai mức phí.**
[Bản đăng ký](US500-NOISE-STUDY-20261108.md) đã viết trước PnL; không đổi
rules/risk/costs để tiếp [2023/24](US500-ROBUSTNESS-20261108.md).

| Năm/scenario | Net USD /10k | Lệnh đã đóng | Giao dịch có gap | Trạng thái |
|---|---:|---:|---:|---|
| 2022 reference | +181,19 | 156 | 1 | Development, chưa qualified |
| 2022 stress | +117,61 | 156 | 1 | Development, chưa qualified |
| Null control | 0,00 | 0 | 0 | Flat đúng như dự kiến |
| 2023 reference / stress | −135,92 / −227,68 | 151 mỗi scenario | 3 mỗi scenario | Không đạt retention |
| 2024 reference / stress | −150,81 / −233,37 | 147 mỗi scenario | 1 mỗi scenario | Không đạt retention |

Plannedrisk25USD/lệnh(0,25%vốnbanđầu),1position;sourceM1Bid/AskUSA500,
geometry1USD/point/lot/leverage10 và phí/slippage **declared**,chưa targetbroker
verified. Entry từ signal M1close sau delay1minute;hardSLoppositeband,scheduled
flat1minute trước cashclose,khôngTP/VWAP. Không paperSPYreplication hoặc native
tickDD/prop compliance. Giữ source/config/calendar/protocol/rawevidence snapshots.

## Kết quả và giới hạn

- Reference84wins/71losses/1flat;stress83wins/73losses. Winrate không là proof.
  Stressmean+0,754USD/lệnh,5besttrades+182,72USD >totalnet117,61USD; bỏ5lệnh
  đó còn−65,11USD. Đây là concentrationdiagnostic,không lý do xoátrades.
- Source thiếu12cashminutes ở4days;4missingminutes xảyra trong1position
  `index-18`. Netcủatradeđó−1,58/−1,82USD, được tính đủ vàđánh dấu unresolvedpath;
  không bỏ khỏi equity hoặc giả khôngảnhhưởngSL/DD.
- 20modeledintrabarSL/scenario;M1filllevel chưa firstcrossingtick.
  266slots không đủ exact14sessionhistory (bao gồm warmup/missing/halfday),
  không thay bằng14ngày códata đẹp. Tấtcả156positions đã đóng;khôngpending/
  floating cuối study. Khôngforcedendofsamplefill.
- StressmonthlyUSD:Jan−28,74;Feb+77,03;Mar−38,36;Apr+118,69;May−28,26;
  Jun+4,95;Jul−10,79;Aug+74,78;Sep−42,21;Oct+57,79;Nov−37,64;Dec−29,63.
  Mộtdevelopmentyear không đủ suy expectedpass/payout3/6/12months.

## Kiểm chứng và thời gian

Private root: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`.

| Lát | Đo thực tế | Bằng chứng |
|---|---:|---|
| Download2022 | 319,70s | `us500-development2022-v1/result.json`,8seals |
| Fullquality/calendar review | 3,63s standalone | `calendar-quality-review-v1.json` |
| Verify+load trongstudy | 4,98s | `us500-noise2022-v1/progress.json`/stdout |
| Reference | ~1,95s gồmwrite | `reference.json`,156trades |
| Stress | ~1,92s gồmwrite | `stress.json`,156trades |
| Null | ~0,41s gồmwrite | `null-control.json` |
| Fullstudy | 9,25s | `result.json`; không controllednativebenchmark |
| Research/spec/code/review củaagent | Chưa đo riêng | Không gộp thành simulationtime hoặc quota |

Focused checks:4datareviewtests,6causal/risk/filltests đạt trước numeric2022.
Firsttest run bắt lỗi pending bị xử lý trước registeredfillminute; đãsửa trước
PnL. Mộtexpectation2trades sai vì priorcloseanchor ngày2 chặnlệnh; sửa kỳvọng1
theorule,không nớisignal. Source2022 được chụp trước các thay đổi orchestration
nhậncalendar2023/24/Markdownstatus; không tự recertify2022 cho source mới.

`review_index_noise.py` recompute cost/net bằng sốhọcDecimal riêng vàkiểm
entrydecision→quote,oppositeSL/lot/risk,stopbar/gapquote,scheduledclock,cashcount,
snapshot/raw/result hashes; cả312closedtrades khớp. Artifact
`us500-noise2022-v1/arithmetic-fill-review-v1.json`. Đây là check implementation
riêng trong cùng lượt agent; **không independentreviewer/model signoff** và
không nhìn được đường giá trong missingminutes hoặc chứngminhedge.

## Kết thúc robustness và quyết định

Cả hai annualbooks đã hoàn tất, giữ cùng signal/risk/cost formulas2022. Các
delta source chỉ nhận frozen calendar/year, Markdown progress và reuse logger/
failure helper đã có. Không rerun2022 để trang trí timing hoặc đổi phí sau outcome.

| Lát | 2023 | 2024 |
|---|---:|---:|
| Download M1 Bid/Ask | 307,07s | 291,75s |
| Rows mỗi side | 332.236 | 335.016 |
| Cash phút có/dự kiến | 97.032/97.140 | 97.678/97.740 |
| Ngày có gap | 9 | 9 |
| Full study: verify/load +2costs +null | 8,56s | 9,27s |
| Closed trades mỗi scenario | 151 | 147 |
| Gap-affected positions mỗi scenario | 3 | 1 |

Tổng ba **annualbooks riêng**, không tài khoản liên tục: reference−105,54USD,
stress−343,44USD;454closedtrades/scenario,908trades đã đối soát riêng về số học/
quote/cost/SL/clock/quantity/cash và artifact hashes. Null control cả3năm đúng0.
Không openposition hoặc pendingaction cuối cácbooks. Source2024 thêm chặn reviewer
đóng dấu closed-book nếu còn open/pending; không tự công nhận floating chưa kiểm.

Download controller20976 đã kết thúc598,85s cho hai năm,16/16seals; numeric
workers2023/24 cũng đã kết thúc, không lock còn sống. Mỗi năm có `result.json`,
`data-review.json`, `arithmetic-fill-review-v1.json` và source/protocol/calendar
snapshots trong `us500-noise<year>-v1`. 2024 có `events.jsonl`35events với sequence/
phase/counters, cùng `PROGRESS.md`/`progress.json`; không giả thêm log lịch sử
cho những lượt source trước chưa ghi loại file này.

Focused tests cuối:5data/calendar +7strategy/orchestration +4reviewer =16tests
đạt theo các lát thay đổi. Negative CLI smoke `us500-failure-smoke-v1` cố tình
thiếu input: dừng trước simulation, giữ failed-stage/sourceframes, không text/
locals nhạy cảm,2events đúng thứ tự, release lock và không có result giả.

**Quyết định:** giữ negative version; không đưa bản này vào challenge hoặc mở
holdout để cứu. Dữ liệu/loader/calendar/cost primitives/checker/logs tái sử dụng
cho hypothesis khác; không đếm thêm cost/year/null runs thành edges độc lập.
C1 còn thiếu edge đủ bền; C2 còn thiếu native index execution/path-gap/target
broker và prop verification. Lần tới chọn cơ chế khác có nguồn/cost/data fit
trước khi code, không thêm parameter grid cho bản vừa thất bại.2025+ vẫn đóng,
không broker/model calls trong các lượt này.
