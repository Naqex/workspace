# S01 — correction nguồn v2, đúng hai giờ GBPUSD

Đăng ký trước thực thi correction và trước PnL mới. Đây là sửa cách biểu diễn
nguồn đã kiểm chứng, không mở trial chiến lược hoặc đổi cổng S01.

## Quyết định và lý do

Hai giờ ngày18/10/2022 lúc12:00 và15:00UTC (`1666094400000`,
`1666105200000`) có bốn khác biệt H1 BID/ASK so với paired ticks.
Cả cached candleAPI→H1 và cached rawticks→binary đều tái hiện chính xác bằng
phép tính độc lập. H1 cũ là candleAPI, không phảiCSV hoặc tick aggregation.
Sai khác low5–8pip và close~16pip không phải sai số làm tròn.

Chọn paired ticks đãsealed làm nguồn cho đúng hai giờ này vì giữ timestamp,
Bid/Ask đồng thời và đường giá thực tế trong giờ. Không dùng kết quả giao dịch
để chọn nguồn. Toàn300signals, side, decision, naturalSL, deadline giữ nguyên
trong phép tái sinh nguồn đã đăng ký ở
`SOLO-GBP-SOURCE-DISCREPANCY-20261115.md` (zeroadded/removed/changed).

Bốn GET tái kiểm chỉ trảHTTP202, bodyrỗng: trạng tháiUNKNOWN, không thay thế
cachedraw hợp lệ. Đây vẫn là dữ liệu cùngvendor, **chưa kiểm independentfeed
và chưa chứng nhận feedFTMO**. Lưu mọi thất bại và proofcũ nguyên trạng.

## Phạm vi và đường ghi

Nguồn cũ chỉ đọc:
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S01-gbp-confirmation/`.
Chi tiết nằm trong `source-discrepancy-review/DIAGNOSIS.md`, các raw/hashreceipt
và `cohort-sensitivity/{registration,result,corrected-signals}.json`.

Output mới duy nhất là sibling `S01-gbp-confirmation-source-v2`.
Producer `tooling/ai-engines/solo_gbp_source_correction.py`:

1. Kiểm committedproducer/protocol, toàn inputpins và cohort300/3576hours.
2. Giải mã lại đúng hai rawhours; so byte-for-byte với sealedbinaries.
3. Copy2022BID/ASKbooks, thay **OHLC đúng hai hàng mỗi book**; timestamp,
   volume và mọi hàng khác giữ nguyên. Volume cũ không được gọi là tickvolume.
   Books2023 và nguyên dữ liệu gốc không sửa.
4. Correctioncard/proofmới nối originalregistration/sourceproof/manifest,
   diagnosis, failedrefetch, cohortreceipt, producerhash và correctedbookhash.
5. Reuse đủ3576rawhours+binaries, `missing_hours=[]`, **0networkcalls**.
   Chạy lại chính `solo_gbp_source.admit`, cổngH1match và heldgap nguyên vẹn.
   Không có tham số tolerance, bypass hay bỏ giờ lệch.
6. Proofv2 ghi rõ registeredcorrection và cùngvendor; proofcũ vẫn là
   `SOURCE_REVIEW_REQUIRED`. Sourcepass chưa phải economicpass/Challengepass.

## Budget và điều kiện dừng giữ nguyên

Recipe `GBPUSD.SWEEP.ASIA.LONDON.DAY`, chỉDev2022–2023; không mở2024–2026.
Không đổi entry/SL/TP/exit/filter/risk/weights; giữ nguyên lịch sửrawmarkoutâm,
112configs và ngoại lệV3. Mọi gate kinh tế, tần suất, fixedrisk, marginalA+EUR
của `SOLO-GBP-CONFIRMATION-PROTOCOL-20261115.md` vẫn áp dụng đầy đủ.

Nếu thêm bất kỳH1mismatch, kháccohort/SL, hash, census, heldgap hoặc thiếusource,
dừngsourcev2; không sửa lại registration/proofcũ hoặc mở rộng correction.
Commitprotocol+producer và review synthetictests trước `register`, rồi `admit`.
Lượt này chưa cho phép codecorrection tự chạyPnL.
