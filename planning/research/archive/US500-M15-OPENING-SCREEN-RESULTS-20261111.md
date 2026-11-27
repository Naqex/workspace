# Hai bộ luật US500 M15: đã sàng lọc, chưa có ứng viên giữ lại

11/11/2026. [Protocol trước kết quả](US500-M15-OPENING-SCREEN-PROTOCOL-20261111.md)
commit `cc7a1e8`; [source-reuse correction](US500-M15-SOURCE-REUSE-AMENDMENT-20261111.md)
commit `8303852` trước PnL. Không sửa luật/SL/giờ/cost sau outcome.

## Đọc nhanh

| Ứng viên | Khi vào | Khi thoát | Kết luận đợt này |
|---|---|---|---|
| R094: phá biên | Nến M15 đầu tiên đóng ngoài đỉnh/đáy09:30–09:45NY, theo hướng phá | SL một độ rộng range từ entry; hoặc12:01NY | Chưa đủ cơ sở ưu tiên: nhạy chi phí, cả ba annual books có held-path unknown |
| R095: phá biên thất bại | Sau breakout đầu tiên, một M15 khác đóng lại trong range; vào ngược hướng breakout | Cùng widthSL và exit12:01NY | Không giữ exact version: các năm đủ path2022/2024 đều âm,2023 còn unknown |

Mỗi bản tối đa1attempt/ngày, signal tới11:00NY, khớp sau decision60giây.
Không TP cố định nên chưa có RR cài sẵn; averagewin/loss là kết quả. Đây là
hai hypothesis liên quan, không hai edge độc lập. Khoảng risk25USD/10k chỉ
là offline scenario để so công bằng, không risk thật owner đã chọn.

## Kết quả sàng lọc

USD, mỗi annual book bắt đầu10.000USD; plannedrisk25USD gồm modeled costs.
Commission0, Bid/Ask embeddedspread, extra slippage0,25/0,75point mỗi chiều.
Đây là declared scenarios, không measured FTMO fills hoặc exact broker spec.

| Bản | Năm | Net mô hình chuẩn | Net mô hình chi phí cao | Lệnh/scenario |
|---|---:|---:|---:|---:|
|Phá biên|2022|−108,25*|−394,62*|231|
|Phá biên|2023|−106,31*|−580,59*|222|
|Phá biên|2024|+329,21*|−169,41*|224|
|Phá biên thất bại|2022|−18,00|−136,17|100|
|Phá biên thất bại|2023|−220,04*|−361,43*|82|
|Phá biên thất bại|2024|−354,83|−534,59|87|

**Dấu*:** có missing held minutes hoặc carry recovery; fullannual PnL=N/A.
Các số là mô hình đi tiếp trên observed bars, không kết quả đã xác nhận cho
toàn path. Không bỏ ngày thiếu hoặc lấy knownsubset để promote. R094 có1/3/1
closed trades unresolved theo năm; R095 có0/1/0, ở cả reference/stress. R094
677entries và R095269entries mỗi cost scenario, không nhân số mẫu độc lập
bằng cách cộng các cost/null books. Hai bản có ngày/tín hiệu liên quan.

Winrate mô hình chuẩn R094 khoảng43,7–44,2%, R09534,5–48%; chưa đủ đọc edge.
R0942024 chuẩn +329,21 nhưng5trade tốt nhất +546,59: loại5trade đó còn âm,
chỉ là concentration diagnostic, không được tự xóa outlier hoặc chứng minh
mọi trend strategy kém. DD trong artifacts là **closed-balance modeled DD**,
không equity intrabar/FTMO daily/total loss qualification.

### Chi phí gây khác biệt gì?

Quote gross đã gồm embeddedspread, trước extra slippage, reference scenario:

| Bản |2022 quote gross / extra slip|2023|2024|
|---|---:|---:|---:|
|Phá biên|+44,22 /152,45|+153,96 /260,30|+596,24 /267,06|
|Phá biên thất bại|+44,52 /62,56|−131,02 /89,04|−247,71 /107,13|

Sai lệch cent nhỏ do rounding từng trade. Giá trước extra slippage đã yếu ở
R0952023/2024; R094 có margin dương trước extra slip nhưng mong manh. Không
coi chọn slip thấp hơn là tạo edge. Sizing khác giữa costs để giữ cùng risk,
không lấy stress−reference làm phí tăng trên cùng quantity cố định.

Post-review đã đối soát proxy mid−spread=quote gross cho1.118 strategy-exit
trade-scenarios,12rows. Chỉ subset known scheduled exits; M1sideopens không
chắc đồng thời, không đo executable spread hoặc suy attribution cho SL.
Không chia toàn bộ lỗ thành %spread/alpha nếu không có synchronous exit ticks.

## Correctness, sửa lỗi và hiệu năng

- 18/18books qua signal reconstruction riêng và financial/fill binding checks;
  6null controls0lệnh/0PnL.3actual mutations(signal/cash/earlierstop) đều reject.
  Đây là same-agent/separate-code-path review, không độc lập reviewer/feed.
- 19focused tests đạt:14policy/causal/calendar/reporting và5source-year tests.
  Fixture Ask spike ban đầu mở đúng stop nên library trả stop_loss_gap; đã sửa
  fixture để kiểm intrabar Ask-only stop. Không đổi native protective semantics.
- v1 source gate chặn CRLF/LF calendar ở0books trong0,751s. Giữ attempt; v2
  dùng exact accepted snapshot+semantic equality và đủ4quarters/hash/census,
  không normalize proof/giá hoặc mở2025+. Không raw-decoder rerun/network.
- Hậu kiểm phát hiện tên `known_closed_net_usd` bao gồm modeled unresolved
  trades. Đã tách modeledclosed và **known_resolved_closed_net_usd**, thêm
  regression; artifacts cũ giữ, post-review JSON mới bind18originalbooks và
  reviews, không tái mô phỏng. FullnetN/A không đổi; không dùng field cũ.

| Phần đo được | Wall |
|---|---:|
| Source proof/canonical validation + load3năm, dùng chung2policies |15,633s|
|18mô phỏng, gồm6null |5,695s|
|18signal/financial reviews + ghi từng book |0,810s|
|Toàn batchv2, gồm orchestration/snapshots |22,289s|
|Sửa summary từ savedbooks, không rerun |0,090s|
|3actual mutations, gồm load lại2022 |3,594s|
|Scheduled-exit decomposition, gồm load3năm |10,246s|
|Research/code/Git và thời gian sửa v1 |Chưa đo riêng; không nằm trong22,289s|

Source/load là phần lớn nhất; đã load mỗi năm một lần cho batch. Numeric
nhỏ nên chưa có cơ sở thêm GPU/Rust/worker farm/cache mới. Giữ các workflow
research/qualification/retrospective hiện có, không tạo skill mới cho một case.

## Quyết định và bước tiếp

Giữ US500 làm chính, EURUSD khảo sát nhẹ theo owner đã đồng ý; không cần
đảo lại instrument vì hai bản chưa đủ tốt. **Không có ứng viên challenge mới.**
R094inconclusive/không ưu tiên, R095exact version gác; không nói cả họORB hoặc
US500 bất khả thi. Không gridSL/TP/giờ/filter để cứu. Nếu muốn đầu tư tiếp vào
R094 phải đăng ký kiểm các missing paths và xác minh execution cost trước;
nếu không có nguồn/logic mới thì gác thay vì rerun không đổi.

EURUSD đã rà một hồ sơ: London/prior-level break–retest. R019exactH1đã gác,
R016/R018có related negatives. Chỉ đổiM15 hoặc đặt cùng giờ mởMỹ không đủ cơ sở
gọi là ý tưởng mới. Không mở financial laneEURUSD trong đợt này. Cần dossier
có cơ chế/transfer khác biệt hợp lý trước bất kỳ batch phụ nào.

### Evidence locator

Private campaignbase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/us500-m15-opening-screen-v1` giữ failure; `us500-m15-opening-screen-v2`
giữ manifest/snapshots/18books/18reviews/metrics/events/PROGRESS và postreviews.

- Result SHA:`54a0dae333b4653f2206dda808cf929ab41f2b63c747807502c5311e43c84621`.
- Corrected metrics SHA:`8f29748739ecac5bfecc577baadd6c45aa8e6177f2018de4804e9b1ed9c0322b`.
- `actual-mutation-review-v1.json`, `scheduled-exit-mid-diagnostic-v1.json` giữ
  assertions/timers/rawbook bindings, không thêm trades hoặc điều chỉnh rule.

Catalogue95records, thêm2related trials; bảo toàn93records/negatives cũ.
2022–24 exposed/unverified;2025+ reserved. Broker/model/network calls0,
không product/runtime/UI/broker rollout, không còn job phải đợi.
