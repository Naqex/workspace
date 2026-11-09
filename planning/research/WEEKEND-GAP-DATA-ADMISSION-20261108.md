# R024: kiểm dữ liệu cuối/đầu tuần trước strategy outcomes

## Vì sao chọn câu hỏi này?

Sau source correction và [FTMOcontract review](FTMO-SYMBOL-AND-CLOCK-ADMISSION-20261108.md),
chọn R024 như **hypothesis chưa triển khai**, khác các hourlyindicator losers.
Không đảo chiều losers hoặc gọi researchnày đã có edge. Primarypublisher
[weekendoverreaction paper](https://www.sciencedirect.com/science/article/pii/S1042444X16300998)
có searchabstract liên quan; fullpaper và [authorrepositoryPDF](https://irep.ntu.ac.uk/35555/1/13113_Dao.pdf)
trả403/unavailable08/11. [Gapspaper2025](https://www.mdpi.com/1911-8074/18/3/132)
trả429; không retry/bypass hoặc tự nhận đã đọc method/chi phí. Chưa exactrecipe,
strategyimplementation hoặc numerical/PnL protocol. R019 giữ alternative,
R026data/calendar gaps chưa tự được giải quyết.

## Scope khóa trước endpoint diagnostics

Chỉ EURUSD2019 và2022 đã consumed, chọn một năm trước và một năm trong nhóm
gần đây đã có cache, không chọn từ gap/PnL outcome. Hai sourceboundobservedH1
caches từ `execution-v1/eurusd-observed-history-v2/<year>/completed.json` và
parent`result.json`→`hourly_cache`. Source/root/runtime cũ giữ, không sửa binding
theo currentreplaycode. Không đọc2023/24khác trong lượt này, không2025+.

- Rehash config/completed/result/rawseal, raw tick CSV và H1cache; kiểm payload
  checksum, parentbindings và orderedtime/sequence/tickcounts/schema bằng
  reader hiện có hoặc independentmetadatareview. Không rebuildH1/rawexport.
- Sourceproducer snapshot đã pin3files của cache; kiểm hash snapshot thay vì
  cập nhật cache/source hashes cho currentcode. Đây là reuse oldsourcebound
  evidence, không currentnumericalcodeparity hoặc revalidationtoànrawticks.
- Referenceclock **declareddataadmission**, chưa targetbrokercontract: Friday
 17:00 và Sunday17:00America/New_York. Enumerate tất cảFriday/Sundaypaired
  weekends nằm trọn trong cùng năm; holidays không drop khỏi denominator.
- Với mỗi weekend, tìm lastobservedH1quote trongFriday15:00–18:00NY và
  firstobservedH1quote trongSunday16:00–20:00NY, lấy `last_time_msc` và
  `first_time_msc`, giữ timestamp/sequence/sourcehour locator. Ghi missing,
  seconds từ referenceboundary, weekendticks nếu cache có, không tự điền.
- Chỉ counts/clock/availability/type/endpoints; không tính pricegap, return,
  gapfillrate, candidatePnL, threshold/risk/RR/exit/timinggrid hoặc dùng later
  prices đánh giá tín hiệu. Giá trong existingcache đã exposed trước campaign,
  reviewnày không làm dữ liệu trở thành unseen/holdout.
- H1 extrema không có thời điểm bên trong. Có first/lasttime không chứng minh
  fulltickpath, quote after latency, tradability hoặc exactgapclose TP; bất kỳ
  strategy sau này vẫn phải register source/costs/causalfill/stop/uncertainty.

## Quyết định hữu hạn

Báo allweekends/available/missing và endpoints ngoài referencehours, theo từng
năm, không cắt holidays hoặc coi thiếuquote=marketclosed. Tối đa kết luận
**endpointmetadata đủ/chưa đủ để viết spec tiếp**, không promote strategy.
Nếu binding/schemafail, giữ failure và dừng; không sửa olddata hoặc fetch mới.

Private `execution-v1/weekend-gap-data-admission-v1`: source/protocol/input
pins, script, progress/events/log, deadline300s/CANCEL, một read-onlyworker.
Hash/validate/clock timers riêng, không benchmark lại simulation hoặc dựng
cachehiệu suất mới. Negativecases cho wrongbinding/order, clockfixture qua
US DST nếu code tự phân loại. Không newbroker/model/networkmarketdata calls.
Researchworkflow/qualification/evidencecontinuity hiện có đủ, không cần
skill/engine/ledger/UI mới. Chưa C1/C2 và chưa quyền broker/holdout/account.
