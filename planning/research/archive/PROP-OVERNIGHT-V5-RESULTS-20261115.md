# V5 — không nâng cấp ứng viên Challenge; payout vẫn bằng 0

**Kết quả:** V5 chỉ qua cả hai vòng ở 1/36 cửa sổ ASYM, 0/36 SYM, so với 3/36 và 2/36 của V4. Peak-to-valley vẫn khoảng 12,96% vốn đầu, chưa đạt mục tiêu < 8,5–9,5%. Sàn bảo vệ lợi nhuận giảm rủi ro trả lại lãi ở một số đường, nhưng làm nhiều tài khoản đứng lại trước đích.

Đã thực thi các workstream trong phạm vi dữ liệu/công cụ hiện có, **không tuyên bố mọi acceptance đã đạt**: GBP không có M1/tick 2022–2024 để dựng ledger thật; một số nguồn vẫn thiếu; bootstrap 10.000 đường chỉ là stress surrogate theo ngày, chưa tương đương tick V5. Không chứng minh chiến lược có lãi bền, payout thật hoặc thu nhập chính.

Task `36b050c6-aa94-4b8c-bb1d-8c5520b23a61`; PR82 đã merge `5beeb75`, xóa branch V4, làm trên `codex/prop-overnight-v5`. Ngày bàn giao 15/11/2026 Asia/Saigon. Giữ VI Dubber WIP và Trader pin; không broker/model/paid-provider hoặc tải thêm lịch sử từ nguồn mới.

## 1. Sáu cột so sánh 2022–2024

| Chỉ tiêu | V3 ASYM | V4 ASYM | V4 SYM | V5 ASYM | V5 SYM | V5 + sleeve3 |
|---|---:|---:|---:|---:|---:|---:|
| Qua vòng 1 | 15/36 | 14/36 | 13/36 | 6/36 | 4/36 | N/A |
| Qua cả hai vòng | 2/36 | 3/36 | 2/36 | 1/36 | 0/36 | N/A |
| Trung vị hoàn tất hai vòng* | 21.79 tháng | 7.68 tháng | 8.14 tháng | 3.81 tháng | N/A | N/A |
| Số payout mô phỏng | 0 | 0 | 0 | 0 | 0 | N/A |
| USD trả trader trong mô hình | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | N/A |
| Worst daily loss | 1.071% | 1.280% | 1.341% | 1.280% | 1.341% | N/A |
| Worst static loss | 6.997% | 7.994% | 7.995% | 7.994% | 7.995% | N/A |
| Peak-to-valley DD | 8.790% | 14.365% | 14.468% | 12.957% | 12.773% | N/A |
| Modeled breaches | 0 | 0 | 0 | 0 | 0 | N/A |
| Đường funded riêng biệt | 1 | 1 | 1 | 1 | 0 | N/A |

*Chỉ những cửa sổ đạt, không dự báo thời gian cho mọi tài khoản. Cửa sổ tháng chồng lấn và cùng dữ liệu tương lai; một đường funded riêng biệt cũng chưa là một phép thử thống kê độc lập. Cột sleeve3 N/A vì không có nguồn/ứng viên đạt, không sao chép số V5 để lấp cột. DD% trong bảng chia cho vốn đầu 50k; peak-to-valley khác static floor.

V5 ASYM hoàn tất từ mốc 01/07/2023; funded cuối mẫu còn $49.683,57, không payout. V5 không cải thiện điểm nghẽn kinh tế bằng việc thêm bộ điều khiển. Không mở trial 3 hoặc giảm tiêu chí sau kết quả.

## 2. GBPUSD và 28 cấu hình thiếu giá

- Rà filenames ở backup E:, workspace D: và Trader worktree C:; QDM chỉ list EUR/XAU đang cache. GBP có H1 từ nghiên cứu cũ nhưng không có M1/tick 2022–2024 đủ phạm vi. Fixture upstream GBP chỉ tháng 02/2012, AUD tick chỉ 30–31/01/2020, USDJPY 2013/2019; loại vì sai thời kỳ, không dùng làm lịch sử thật. Không dựng M1 từ H1 hoặc bịa Ask.
- 28 cấu hình ban đầu là **24 US500 + 4 AUDUSD**, không phải 28 chiến lược GBP. Tái dùng V3 đã sửa clock của US500: khôi phục 715/732 endpoint thiếu ban đầu; 17 còn unknown trên ngày lễ/đóng sớm. Không đếm thành 715 giao dịch mới hoặc nhận công khôi phục đó cho V5.
- Bốn AUD chỉ có nguồn H1 với các khoảng thiếu, chưa có M1/tick thay thế. US500 còn carry/dividend/spec và scale/retention chưa đủ; GBP chưa vượt cổng source nên chưa thể chạy Stage-0/1 chuẩn mới.

**Không chọn sleeve #3.** `source-recovery.cells` trong JSON đối chiếu từng cấu hình với số raw/priced/fills/coverage cũ. Kết quả V2/V3 âm/unknown giữ nguyên. Đây là source blocker, không phải chứng minh GBP không có edge. Chưa hoàn tất yêu cầu dựng GBP M1/tick ledger thật.

## 3. Blind holdout audit — chỉ timestamp

| Asset | M1 records | Timestamp đầu/cuối | Ngày thường 07–21 UTC đủ timestamp* | Ngày thường còn gap/nghỉ chưa phân loại |
|---|---:|---|---:|---:|
| XAUUSD | 632140 | 2025-01-01T23:00:00+00:00 → 2026-10-13T23:58:00+00:00 | 445 | 33 |
| EURUSD | 657549 | 2025-01-01T22:00:00+00:00 → 2026-10-07T23:58:00+00:00 | 458 | 20 |
| GBPUSD | N/A | N/A → N/A | N/A | N/A |

*Trong 478 ngày thường 01/01/2025–31/10/2026, đủ timestamp ở đây chỉ có nghĩa khoảng thiếu dài nhất trong 07–21 UTC <= 15 phút. Chưa phân biệt hết ngày lễ với lỗi nguồn; không tự gán ngày thiếu là nghỉ hợp lệ. Từng ngày, gap count và các khoảng liên tiếp được lưu trong JSON.

QDM export chỉ DateTime, loader từ chối bất kỳ cột Bid/Ask/OHLC nào. Không tính indicator/tín hiệu/PnL và không update/download provider. Gold chỉ tới 13/10/2026, EUR tới 07/10; GBP chưa có nguồn. Không chứng nhận được khoảng nào có **đường Bid/Ask/tick đủ Stage-1** chỉ từ timestamp. Cần tick/M1 admission, feed/session/news/spec và exposure manifest riêng; không gọi holdout hoàn toàn sạch vì chưa chạy ở đây.

## 4. Giải phẫu 35,76R và hai trial đã khóa

Đỉnh UTC `2022-09-30T13:22:32.765000+00:00` ở $53,515.94; đáy UTC `2023-03-10T12:10:01.483000+00:00` ở $48,152.34. Risk tham chiếu $150; mức giảm 35,757R. Recovery trên tick sau đáy: 2023-10-18T14:37:20.480000+00:00, không tự chốt ngày hết drawdown tại cuối năm.

Đối chiếu cả closed+floating tại hai đầu: BUY đóng góp 17.665R, SELL 18.093R, tổng khớp 35,757R. Không phải chỉ một chiều gây lỗ. Trong 63 tín hiệu mở giữa hai mốc, 15 có biên Á > 2 ATR, tổng−6,254R; 44 đi khác H4, tổng−10,714R. Các nhóm có giao nhau và khác boundary floating, không cộng các khoản đó để gọi là tỷ lệ nguyên nhân nhân quả.

| Vị thế vẫn mở 12 UTC | Số lệnh | Net R đánh dấu 12 UTC | Net R lúc thoát thật | Chênh sau 12 UTC |
|---|---:|---:|---:|---:|
| 2022 | 76 | +40.280 | +41.484 | +1.204 |
| 2023 | 84 | +42.741 | +53.808 | +11.066 |

Ở cohort còn sống đến 12 UTC, giữ tiếp thực tế cộng thêm lợi nhuận hai năm. Đây có survivor/SL conditioning, không phải backtest mới đóng mọi lệnh 12 UTC. Chưa có bằng chứng đơn giản rằng đóng hết London giải quyết drawdown; không mở biến thể exit thứ ba.

| Cơ chế EUR | Net R Dev liên tục | Max DD(R) | Net R 2022/2023, giữ state qua năm | Quyết định |
|---|---:|---:|---:|---|
| PARENT | +14.334 | 35.757 | +3.771/+10.562 | Giữ baseline |
| D1 | +4.829 | 35.899 | -13.489/+18.317 | Không đạt các cổng đã khóa |
| D2 | +9.967 | 23.351 | +4.610/+5.357 | Không đạt các cổng đã khóa |

D1 bỏ EUR khi biên Á > 2 ATR14H1 biết trước entry. D2 dùng shadow canonical closedNetR riêng từng sleeve: DD >= 8R giảm nửa risk, hồi 4R từ đáy hoặc đạt đỉnh cũ thì trả lại nominal. Shadow cập nhật chỉ tại exit thật của tín hiệu gốc; không đọc netR tương lai lúc vào lệnh. NetR sổ so sánh được chuẩn hóa về cùng $150, không cộng các R có risk khác nhau rồi gọi đó là cùng một mức lợi nhuận.

D2 giảm EUR DD nhưng mất quá nhiều tốc độ 2023 và net danh mục; D1 làm 2022 âm và không giảm DD. Cổng yêu cầu giữ >= 80% net và giảm DD đã khóa trước đo, nên **chọn PARENT**, không ghép D1 + D2. Recheck sổ liên tục xác nhận cùng quyết định: annual standalone diagnostics khởi tạo cold state mới, không được dùng thay carried-state year cuts.

## 5. Ratchet/harvester đã thay gì?

- Vòng 1: equity/balance đạt +7% thì cap $125; rơi về +5% thì cap $90 và gửi yêu cầu đóng trên quote kế tiếp của từng tài sản. Lệnh mới phải giữ projected stop reserve trên +5%; không giả sàn được bảo đảm khi gap/slippage.
- Vòng 2: đạt +3,5% thì cap $100. Giữ stop tự nhiên, phase/reset owner và cổng 8% / cap 1,6% của V4.
- Funded: closed balance >= 50.500 trong 48h cuối chu kỳ 14 ngày thì freeze entry, đóng phiên trước due; >= 51.000 thì lock và thanh lý trên quote thật tiếp theo. Request chỉ khi đủ ngày, flat và lãi >= 20; debit toàn bộ profit, 80/20, không mô phỏng approval/chuyển khoản.

| Model | Ratchet armed | Sàn +5% chạm | Đóng trên quote thật | Tài khoản phase 1 còn đứng ở sàn | Harvest freeze/lock |
|---|---:|---:|---:|---:|---:|
| SYM_FLAT | 27 | 15 | 15 | 15 | 0 |
| ASYM_FLAT | 28 | 14 | 17 | 14 | 0 |

Đóng để giữ sàn có thể làm balance rơi hơi dưới 52.500 sau phí; khi flat gần sàn, không còn đủ room mở lệnh mà vẫn giữ projected floor. Vì thế nhiều tài khoản đứng lại. Tự bỏ sàn để tiếp tục sẽ là một trial khác; lượt này giữ đúng quy tắc, ghi failure rõ.

Không có chu kỳ funded nào đạt ngưỡng freeze/lock trong 72 cửa sổ. Harvester đã được kiểm bằng fixtures nhưng **chưa có lịch sử payout thành công** để xác nhận vận hành. Đóng trước due không bảo đảm tiền còn dương, quỹ duyệt hoặc tiền về 100%. Daily < 5% / static < 10% trong model không đồng nghĩa tài khoản FTMO thật đạt mọi điều kiện news, margin, quote, commission/swap hoặc session profile.

## 6. Block-bootstrap 10.000 đường — stress surrogate, chưa exact V5

Mỗi model/mỗi block có 10.000 đường 12 tháng / 252 business days; cả rổ resample cùng block 20 ngày, sensitivity 5 ngày, seed 20261115. Giữ serial order trong block và thứ tự high/low ngày đã quan sát, không trộn hai asset độc lập. Funded-start là experiment riêng, không lấy payout conditional-funded làm tiền kỳ vọng từ lúc mua Challenge.

**Giới hạn quyết định:** surrogate hiện thực hóa equity ngày thành cash flat cuối ngày, chưa tái tạo vị thế 48h/cap/reserve/lot/next-quote fill; chu kỳ 14 ngày xấp xỉ 10 business days. Nó có thể tạo payout mà exact engine không tạo. Không dùng các tỷ lệ dưới đây làm xác suất pass tương lai hoặc coi Workstream4 exact-MonteCarlo đã đạt.

| Model/block | P1 trong proxy | Hai vòng <= 12 tháng proxy | Breach proxy | StaticDD P50/P75/P95 | Mean payout/năm nếu bắt đầu funded* |
|---|---:|---:|---:|---|---:|
| SYM_FLAT/20 | 27.65% | 13.08% | 8.23% | 5.38%/7.92%/10.06% | $2,432.85 |
| SYM_FLAT/5 | 28.21% | 11.66% | 7.21% | 5.19%/7.74%/10.05% | $2,555.58 |
| ASYM_FLAT/20 | 28.97% | 14.09% | 7.20% | 5.18%/7.70%/10.05% | $2,533.05 |
| ASYM_FLAT/5 | 29.78% | 12.75% | 6.39% | 5.03%/7.58%/10.03% | $2,653.61 |

*Đây là output của mô hình daily-flat lý tưởng hóa, không lời hứa thu nhập, không trừ challenge/retry/vận hành/thuế, không thay cho exact historical payout 0. Từ challenge-start, mean payout nhỏ hơn; giữ riêng trong JSON. Đổi 20 → 5 day blocks đổi kết quả; seam không giữ được tự tương quan dài hơn block. Chỉ 3 năm dữ liệu đã exposed/selected không đủ chứng nhận tail risk tương lai.

512 đường scalar đối chiếu vector đạt. Trên chuỗi lịch sử nguyên thứ tự, surrogate và exact Jan 2022 khác balance/DD (chi tiết`bootstrap_parity.historical_comparison`), nên **không claim model-equivalence**. Cần bootstrap từ event tape có carry state/quote fills và parity lifecycle trước khi dùng để qualification.

## 7. Kiểm chứng, lỗi đã giữ và trạng thái cuối

- 231 tests đạt; V5 có22 fixtures cho causal cold-state, ratchet, freeze/lock, quote freshness/ordinal, reward full-debit, timestamps và bootstrap.
- Oracle72 tài khoản: 9,532 admissions,11,952 rejections,9,532 cost bridges,32 dynamic native fills; 104,985,511 quote updates đối chiếu timestamp. Hạch toán funding vào cash thay cho floating của producer; cash/DD/phase/payout khớp. Cùng implementer, không independent human/model reviewer.
- Composition commit `c63a255474862d1928f59db4b988991b2e49f7c0` trước release `2026-11-14T17:49:30.288527+00:00` và lần traversal 2024; code/source/rule pins khớp. Chọn chỉ Dev; 2024 đã exposed, không clean OOS.
- Lỗi holiday`flat_utc=null` dừng trước output tài chính; sửa ở session owner và có fixture. Lượt reference đầu dùng nhầm prop reserve làm park signal curve: giữ nguyên dưới `development-attempt2-reference-admission-bug`, sửa reference admissions rồi chạy lại; không thêm threshold/trial. Hai output lỗi không được dùng chọn hoặc công bố như kết quả hợp lệ.
- Year-carry audit dùng continuous closed-cash cuts xác nhận D1/D2 vẫn rớt, thay cách đọc annual standalone windows. Không che sai khác warm-start của các sổ chẩn đoán năm.

**Quyết định:** No-Go nâng V5 thành ứng viên Challenge; không mua, không tăng risk, không mở holdout để cứu cấu hình đã yếu trong Dev/Historical Validation. Giữ V3/V4 làm benchmark. Chặng có ích tiếp theo là source admission GBP 2022–2024 và event-level bootstrap parity nếu được giao; không thêm lớp điều khiển vì kỳ vọng nó tự tạo alpha.

V5 đã có kết quả/review cho từng workstream nhưng **source recovery GBP/những đoạn thiếu và exact 10.000-path V5 qualification còn chưa đạt**. Đó là giới hạn được bàn giao, không được đổi nhãn thành PASS chỉ vì code/test/CI xanh.

Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\prop-overnight-v5-20261115`. Full 72 ledgers, failed attempts, EUR minute extrema, raw timestamp exports/daily coverage, scalar paths và 10.000 path outcomes giữ riêng. JSON tracked giữ summaries, source/freeze hashes, từng ngày coverage/intervals, trials và các blocker.
