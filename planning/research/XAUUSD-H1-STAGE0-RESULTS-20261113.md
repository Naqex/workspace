# XAUUSD H1 — Stage-0 Raw Markout Discovery 2022–2023

**Ưu tiên kiểm tiếp: A — phá biên Á, BOTH, giữ 48 giờ.** Mean net markout sau spread, commission, slippage stress và swap proxy đạt +1,767/+1,326 USD/oz năm 2022/2023, trên 63/65 tín hiệu có giá đo. H1 đã cải thiện quy mô stop/chi phí ở A và C, nhưng **chưa có case đủ bằng chứng để đóng gói bot hoặc thi quỹ**.

Cần tách hai kết luận: (1) Có các ô 48h dương trong cả hai năm quan sát được; (2) các horizon chính 8h/24h đã khóa trước kết quả đều chưa qua screen. 48h là phát hiện từ ma trận phụ đã đăng ký, chưa validation ngoài mẫu. Không đổi nhãn primary sau khi nhìn số liệu. Mẫu 48h thiếu nhiều endpoint cuối tuần và khoảng bất định còn qua 0; mean trên phần có giá chưa chứng minh kỳ vọng trên toàn bộ tín hiệu.

## 1. Scope, luật và đơn vị

[Protocol](XAUUSD-H1-STAGE0-PROTOCOL-20261113.md) giữ một baseline cho mỗi cơ chế, không quét tham số. Chỉ giá2022–2023, seedNov2021, không mở giá2024–2026. Cả ba dùng H4SMA20/slope3 làm bias, H1 đã đóng để phát tín hiệu trong08:00–15:00UTC. H4 là lựa chọn trong yêu cầu D1/H4, không chạy thêm D1 variant.

- **A:** phá close khỏi vùng Á00–06UTC theo H4; stop geometry ở phía đối diện vùng Á, có0,10ATRH1; first signal/day của BOTH.
- **B:** H1 từ dưới SMA20 lấy lại đường này bằng nến tăng trong H4BUY, SELL đối xứng; stop ở extreme hai nến, có0,10ATRH1.
- **C:** H1 tiến ít nhất1ATR theo bias, thân nến cùng hướng và lows3nến cao dần (SELL: highs giảm dần); stop ở extreme ba nến, có0,10ATRH1.
- **BUY là subset của BOTH**, không cộng thành hai mẫu độc lập; ba họ tín hiệu cũng có thể chồng lấn. Tổng608raw records của3recipe, không phải910cơ hội độc lập khi cộng các view.
- Chưa SL/TP orders, sizing, portfolio, floating-DD hoặc prop evaluation. NaturalSL chỉ là thước đo cấu trúc, không phải lệnh đã đặt. Markout không loại tín hiệu bởi cost gate.

Net markout là biến động giá thanh lý Bid/Ask trên 1 oz, trừ commission proxy 0,0007% giá trị danh nghĩa mỗi chiều, slippage stress 0,40 USD/oz cả vòng và funding proxy 40 USD/lot/rollover (=0,40 USD/oz tại 100 oz/lot), ngày thường lúc 22:00 UTC, thứ Tư ×3. Chuẩn dùng slippage 0 và funding 20 USD/lot. Đây là kịch bản bảo thủ kế thừa, **chưa phải biểu phí/swap đúng tài khoản đích**. [MT5 phân biệt Long/Short, mode và ngày triple swap](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants); không gán proxy đối xứng thành phí FTMO thực tế. Gross Bid/Ask đã chứa spread, không trừ lặp.

## 2. Tần suất, natural stop và tỷ lệ giữ tín hiệu

Số raw trước cost filter. SL và tỷ lệ phí đều USD/oz, cùng raw cohort; entry missing/invalidstop được giữ trong mẫu số. Cap12% là screen chính đã khóa;15% chỉ diagnostic. 40raw/năm là sàn lượt này,80 là ưu tiên; raw signals không đồng nghĩa filled trades hoặc gate60fills/năm của prop profile.

| Recipe/View | Năm | Raw | Ngày riêng | Median SL | Median F stress | Fmedian/SLmedian | Đạt12% | Đạt15% |
|---|---|---|---|---|---|---|---|---|
| A/BUY | 2022 | 54 | 54 | 11,986 | 0,797 | 6,65% | 90,7% | 96,3% |
| A/BUY | 2023 | 57 | 57 | 8,905 | 0,748 | 8,39% | 80,7% | 93,0% |
| A/BOTH | 2022 | 103 | 103 | 11,512 | 0,792 | 6,88% | 90,3% | 97,1% |
| A/BOTH | 2023 | 107 | 107 | 8,667 | 0,747 | 8,62% | 76,6% | 92,5% |
| B/BUY | 2022 | 54 | 40 | 5,593 | 0,764 | 13,67% | 35,2% | 63,0% |
| B/BUY | 2023 | 66 | 49 | 5,897 | 0,766 | 12,99% | 42,4% | 68,2% |
| B/BOTH | 2022 | 116 | 90 | 6,245 | 0,769 | 12,31% | 47,4% | 65,5% |
| B/BOTH | 2023 | 136 | 105 | 6,224 | 0,757 | 12,17% | 47,8% | 70,6% |
| C/BUY | 2022 | 25 | 21 | 15,127 | 0,807 | 5,34% | 96,0% | 100,0% |
| C/BUY | 2023 | 46 | 35 | 13,654 | 0,765 | 5,60% | 97,8% | 97,8% |
| C/BOTH | 2022 | 61 | 49 | 12,336 | 0,780 | 6,32% | 95,1% | 98,4% |
| C/BOTH | 2023 | 85 | 67 | 10,970 | 0,749 | 6,83% | 92,9% | 97,6% |

A và C giữ được phần lớn tín hiệu ở cap 12%, cải thiện đáng kể vấn đề scale từng gặp ở M15. B có SL khoảng 5,6–6,2 USD/oz: ở 12% chỉ giữ 35–48%, vượt giới hạn loại 50%; ở 15% giữ 63–71% nhưng chưa được tự đổi cap sau kết quả. Momentum BUY năm 2022 chỉ có 25 tín hiệu thô, thiếu cadence.

## 3. Mean net markout stress tại bốn mốc

Đơn vị **USD/oz/tín hiệu có observed endpoint**. Đã trừ swap theo thời gian giữ; không có SL/TP bảo vệ trong phép đo. N ở mỗi ô không bằng raw N khi endpoint rơi vào cuối tuần/phiên nghỉ/thiếu giá.

| Recipe/View | Năm | +4h | +8h | +24h | +48h |
|---|---|---|---|---|---|
| A/BUY | 2022 | -1,142 | -2,891 | -0,497 | 1,943 |
| A/BUY | 2023 | 0,885 | -0,005 | 1,313 | 2,542 |
| A/BOTH | 2022 | -0,372 | -0,626 | 0,064 | 1,767 |
| A/BOTH | 2023 | -0,739 | 0,040 | -0,527 | 1,326 |
| B/BUY | 2022 | -0,571 | -0,677 | -0,124 | 0,823 |
| B/BUY | 2023 | -0,029 | -1,162 | 2,682 | 1,151 |
| B/BOTH | 2022 | -2,092 | -2,327 | -2,971 | -0,098 |
| B/BOTH | 2023 | -0,430 | -0,485 | 0,996 | -1,609 |
| C/BUY | 2022 | -0,648 | -6,238 | -6,001 | 1,207 |
| C/BUY | 2023 | 1,649 | -1,439 | -3,010 | 0,993 |
| C/BOTH | 2022 | -1,948 | -3,409 | -4,935 | 1,334 |
| C/BOTH | 2023 | 0,672 | -1,009 | -1,358 | 2,742 |

Không có recipe/view nào dương cả hai năm ở 4h, 8h hoặc 24h. Chỉ 48h có những mean dương đều trên phần có giá đo. Không chuyển phát hiện 48h thành kết luận đã xác nhận cho primary 8h hoặc 24h.

## 4. Các ô48h dương trong cả hai năm

Cặp số theo thứ tự2022/2023. Tất cả dưới đây có mean net stress≥mean executionfriction trên observed cohort; vẫn phải xét scale, sample, availability và selection exposure.

| Case48h | Có giá22/23 | Mean net22/23 | Giữ≥50% ở12% | ≥40observed/năm | Kết luận |
|---|---|---|---|---|---|
| H1A_ASIA/BUY | 33/33 | 1,943/2,542 | đạt | thiếu ít nhất1năm | chưa đủ; missing/CI/primary |
| H1A_ASIA/BOTH | 63/65 | 1,767/1,326 | đạt | đạt | chưa đủ; missing/CI/primary |
| H1B_RECLAIM/BUY | 32/39 | 0,823/1,151 | không đạt | thiếu ít nhất1năm | chưa đủ; missing/CI/primary |
| H1C_MOMENTUM/BUY | 15/31 | 1,207/0,993 | đạt | thiếu ít nhất1năm | chưa đủ; missing/CI/primary |
| H1C_MOMENTUM/BOTH | 32/61 | 1,334/2,742 | đạt | thiếu ít nhất1năm | chưa đủ; missing/CI/primary |

**Ưu tiên A/BOTH 48h:** raw 103/107, observed 63/65, SL trung vị 11,512/8,667 USD/oz; giữ 90,3%/76,6% ở cap 12%. C/BOTH 48h dương 1,334/2,742 nhưng năm 2022 chỉ có 32 quan sát và các cửa sổ chồng lấn; giữ làm hướng phụ. A/BUY chỉ có 33/33 quan sát; B/BUY không qua scale 12%; C/BUY thiếu raw năm 2022 và chỉ có 15/31 quan sát. Không chọn BUY thay BOTH chỉ vì mean cao hơn trên mẫu nhỏ.

Với A/BOTH48h, dòng chi phí minh họa từ **mean trên cùng observed cohort**:

| Năm | N | Gross sau spread | Commission | Slip | Funding | Net stress | CI95% net¹ |
|---|---|---|---|---|---|---|---|
| 2022 | 63 | 3,475 | 0,025 | .400 | 1,283 | 1,767 | -4,068 → 8,066 |
| 2023 | 65 | 3,144 | 0,027 | .400 | 1,391 | 1,326 | -3,230 → 5,540 |

¹ Bootstrap theo cụm ngày 2.000 lần, seed 20261113; các khoảng đều qua 0. Chưa giữ phụ thuộc liên ngày của cửa sổ 24/48h và chưa hiệu chỉnh nhiều lần thử. CI không chứng nhận edge tương lai. Median net A/BOTH 48h năm 2022 là −0,248 USD/oz dù mean +1,767: kết quả dựa vào đuôi winners, không phải tháng/ngày nào cũng đều lời. Chưa có matched control/bias-only benchmark để tách edge setup khỏi drift của Vàng.

## 5. Coverage và giới hạn quan trọng

Fixed elapsed hours từ **tick entry thực**, không thay bằng số nến giao dịch hoặc tự dời cuối tuần sangthứHai. Không padding giá để biến missing thành0.

| Horizon | Observed/608 | Missing | Target cuối tuần | Weekday không fresh quote |
|---|---|---|---|---|
| 4 | 607/608 | 1 | 0 | 1 |
| 8 | 504/608 | 104 | 0 | 104 |
| 24 | 488/608 | 120 | 118 | 2 |
| 48 | 377/608 | 231 | 229 | 2 |

Missing 48h chủ yếu là target vào thứ Bảy/Chủ Nhật; đây là selection theo lịch, không ngẫu nhiên. +8h có nhiều target 21:00–23:00 UTC không có quote tươi, có thể do phiên nghỉ/rollover. Chưa có lịch tài khoản đích theo ngày nên không gọi tất cả là feed lỗi. Cần protocol phù hợp phiên và quy tắc cuối tuần trước khi chuyển sang strategy có thể thực thi. Không bỏ các ngày thiếu sau khi xem PnL rồi gọi là toàn bộ mẫu đã qua cửa.

Mỗi kết quả 48h có thể bao gồm việc giá đã xuyên natural SL trước đó rồi hồi lại. Scanner **không đo first passage, floating DD, daily loss, margin hoặc overlap account**. Vì vậy mean dương chưa phải expectancy của bot có stop, chưa chứng minh time-fit Challenge/payout hoặc cấp quyền giao dịch.

## 6. Kết luận Stage-0 và bước tiếp

- Primary đã đăng ký: A/C8h, B24h. **Không view nào qua đầy đủ Stage-0 primary**: âm/biên mỏng theo năm, missing endpoints; B thêm scale fail, C/BUY thêm cadence fail. JSON giữ nguyên verdict fail, không sửa primary sau outcome.
- **Lead khám phá ưu tiên:** A/BOTH48h vì mean dương cả hai năm, quy mô stop đủ và observed63/65 tốt hơn các lead còn lại. Đây là đề xuất cho một protocol kiểm tiếp, chưa eligibility đóng gói bot/challenge.
- Nếu mở bước kế tiếp, cần khóa trước semantics phiên/cuối tuần/rollover, cohort khả thi ở48h, raw-count/overlap và hypothesis đối chứng; rồi kiểm đường giá/naturalSL trên đúng candidate. Không quét thêm MA/ATR/TP hoặc mở2024–2026 tự động.
- H1 đã giảm nút thắt ma sát trên stop ởA/C; chưa chứng minh một điểm ngọt phổ quát hoặc rằng mọi setup H1 đều tốt. EURUSD B1 và XAUUSD B1 cũ tiếp tụcCANCELLED_BY_OWNER. Đây là3recipe mới được giao, không dùng lại quota đã hủy.

## 7. Correctness, audit và thời gian

Attempt1 đã dừng trước markout vì một M1open ngày05/12/2023 10:29UTC lệch. Native decoder parity6.997quotes xác nhận sửa2023,754→2023,635; H/L/C không đổi. H1 vàH4 arrays trước/sau identical,608signals vàstopgeometry không đổi. OriginalCSV/cache/failedattempt/snapshotv1 giữ nguyên; snapshot/configv2 bind correction trước attempt2.

Attempt2 kiểm **19.722.614ticks/2.286hours,114.803M1 OHLC khớp**, không phút cóticks mà thiếu M1. Scope chỉ các giờ cần choentry/endpoints, không independent feed hoặc toàn bộ path giữ48h. Reuse616hours và tải1670hours mới.

12fixturesH1,11baseline regression và2negative source guards đạt. Self-audit bằng Fraction/quote/rollover equations riêng:608entries,608stop/frictionratios,1.976markout cost/swap bridges,456missing endpoints giữ nguyên,48year/view/horizon summaries và6view reconciliations. Đây là self-audit, không independentagentreview.

| Phase | Wallđo được |
|---|---|
| Download/reuse tick hours | 675,63s |
| Corrected source preparation | 94,19s |
| Source + toàn bộ markout/statistics | 96,52s |
| CPU corrected scan | 73,61s |
| Code/report/manual review/failed preflight | chưa đo đầy đủ, không suy từ CPU |

Artifacts: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\xauusd-h1-stage0-20261113`; freeze `registration-v2.json`/`source-snapshot-v2`, outcome `attempt-2/result.json`, per-signal `measurements.json`, oracle `arithmetic-review.json`, reviewer `review-stage0-v1.py`. [JSON dossier](XAUUSD-H1-STAGE0-RESULTS-20261113.json) giữ hashes, matrix, missingness và selection exposure.

Hậu kiểm kỹ thuật: native provider/decoder/cache và bounded M1 loader được reuse; thêm end-scope để không decode giá2024. Lỗi source bắt trước outcome, chỉ sửa derived data; không cần GPU/framework mới. Markout tính nhanh sau source validation, giữ failures và raw cache thay vì chạy lại download. Stage-0 verdict đã được thực thi trong scanner này; không có nghĩa mọi runner khác tự enforce gate. Không sửa skills/globalconfig hoặc promote Trader/runtime.
