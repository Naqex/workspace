# XAUUSD H1 — SL-active, Friday clamp và chi phí theo cơ chế lệnh

**Giữ A BOTH / Natural SL / không TP cứng làm ứng viên nghiên cứu; gác A TP 2R và C.** A có lãi trong năm 2022 và phần đã định giá năm 2023 ở cả mô hình phí cũ lẫn proxy bất đối xứng, nhưng lãi phụ thuộc một số lệnh thắng lớn. Chưa đủ điều kiện Challenge/payout: một lệnh A năm 2023 chưa định giá thoát, lịch nghỉ lễ/tin và thông số tài khoản đích chưa hoàn thiện.

PR76 đã merge vào main (`7ab3311`), nhánh cũ đã xóa. Lượt này chỉ dùng Development 2022–2023, giữ đóng giá 2024–2026. [Protocol đã khóa](XAUUSD-H1-EXECUTION-PROTOCOL-20261113.md) / [JSON đối soát](XAUUSD-H1-EXECUTION-RESULTS-20261113.json). Ngày mở nghiên cứu 13/11; hoàn tất báo cáo 14/11/2026 giờ Việt Nam.

A = H1 phá vùng phiên Á theo hướng H4. C = H1 tăng/giảm mạnh theo ATR, kèm cấu trúc thuận hướng H4. Các luật tín hiệu và mức SL giữ nguyên PR #76.

## 1. Đã đo gì

Tín hiệu/SL của PR76 → entry Bid/Ask quan sát → tick theo thứ tự gốc → SL hoặc TP 2R hoặc hạn thời gian → commission/slippage/swap → equity chung khi các lệnh chồng nhau. Dùng 48 **giờ lịch**, chặn thứ Sáu 20:30 UTC; không cộng 48 giờ thị trường mở. Cả 608 tín hiệu, gồm B, được kiểm giá thoát; 356 tín hiệu A/C được chạy hai cách thoát có SL.

Hai cách thoát: Natural SL + giữ tới hạn; Natural SL + TP 2R + giữ tới hạn. Không TP 3R, trailing, filter mới hay tối ưu risk. BUY/SELL là phân rã cùng A, không thêm alpha độc lập.

R0 = 150 USD trên tài khoản 50.000 USD, cố định, không compounding. Khối lượng chung giữa các mô hình = floor(150 / natural SL) oz; 100 oz/lot, bước 0,01 lot. Đây là **risk giá tới stop**, chưa gồm phí/gap/swap. Sổ nghiên cứu nhận mọi tín hiệu gốc và cho phép nhiều vị thế mở cùng lúc; chưa áp kiểm tra margin, giới hạn nhận lệnh hoặc vòng Challenge/payout.

| Cost cell | Swap BUY/SELL (USD/lot/đơn vị rollover) | Slip entry; SL/time/Friday; TP (USD/oz) |
|---|---|---|
| SYM_FLAT — đối chứng cũ | -40 / -40 | .20; .20; .20 |
| SYM_ORDER | -40 / -40 | .20; .20; 0 |
| ASYM_FLAT | -45 / -5 | .20; .20; .20 |
| ASYM_ORDER — proxy yêu cầu | -45 / -5 | .20; .20; 0 |

Spread nằm trong tick Bid/Ask; commission = 0,0007% notional mỗi chiều, làm tròn cent mỗi leg. Swap tạm tính lúc 22:00 UTC các ngày trong tuần, thứ Tư nhân 3; chưa xác minh lịch swap FTMO từng ngày và giờ mùa hè. TP khớp đúng mức khi Bid/Ask tương ứng chạm hoặc vượt mức; SL khớp tại quote đầu tiên chạm mức, có thể xấu hơn mức SL và chịu thêm trượt giá stress. Các tick cùng mili giây giữ thứ tự nguồn.

**TP không trượt âm là giả định đối chứng.** [FTMO giải thích trượt giá](https://ftmo.com/en/blog/slippage-order-execution/) và [order types](https://ftmo.com/en/blog/order-types/) không bảo đảm TP/limit luôn khớp đúng hoặc tốt hơn. Không gọi cell ORDER là điều kiện FTMO đã xác minh.

## 2. Giá thoát và coverage

Trước clamp: 377/608 có giá ở mốc 48h; sau clamp: **601/608=98.85%**. Khôi phục **224/231** mẫu thiếu, chưa phải 231/231. Hai mẫu thiếu gốc rơi Good Friday, 229 rơi cuối tuần; clamp khôi phục 224 mẫu cuối tuần, 5 mẫu cuối tuần/ngày nghỉ còn thiếu.

| Recipe | Năm | Tín hiệu | Giá cũ 48h | Giá sau clamp | Khôi phục |
|---|---|---:|---:|---:|---:|
| H1A_ASIA | 2022 | 103 | 63 | 102 | 39 |
| H1A_ASIA | 2023 | 107 | 65 | 105 | 40 |
| H1B_RECLAIM | 2022 | 116 | 76 | 115 | 39 |
| H1B_RECLAIM | 2023 | 136 | 80 | 133 | 53 |
| H1C_MOMENTUM | 2022 | 61 | 32 | 61 | 29 |
| H1C_MOMENTUM | 2023 | 85 | 61 | 85 | 24 |

Bảy mẫu chưa có endpoint hợp lệ (giữ unknown):

| Recipe | Ngày tín hiệu | Giờ tín hiệu UTC | Chiều | Chặn thứ Sáu? |
|---|---|---|---|---|
| H1A_ASIA | 2022-04-13 | 09:00 | BUY | Không |
| H1B_RECLAIM | 2022-04-14 | 12:00 | BUY | Có |
| H1A_ASIA | 2023-04-05 | 08:00 | BUY | Không |
| H1B_RECLAIM | 2023-04-06 | 10:00 | BUY | Có |
| H1B_RECLAIM | 2023-11-23 | 12:00 | BUY | Có |
| H1B_RECLAIM | 2023-11-23 | 15:00 | BUY | Có |
| H1A_ASIA | 2023-11-24 | 11:00 | BUY | Có |

SL/TP giúp định giá 355/356 tín hiệu cho mỗi cách thoát, tức 710/712 đường giá theo hai cách thoát. Hai A có endpoint Good Friday thiếu đã chạm SL trước đó. **A BUY ngày 24/11/2023 vẫn chưa có exit hợp lệ ở cả hai cách thoát**; không kéo sang thứ Hai, gán 0 hoặc đóng giả tại quote cuối.

## 3. Kết quả SL-active — ASYM_ORDER

†: năm 2023 A/BOTH và A/BUY chỉ là sổ con của các lệnh đã định giá (106/107 và 56/57). Net R và DD của **toàn bộ** cohort đó chưa xác định. Các sổ đầy đủ còn lại vẫn là kết quả của mô hình nguồn/chi phí đã khai báo, chưa được chứng nhận tuân thủ luật FTMO thực tế.

Daily Loss = (balance đã thực hiện tại 00:00 Europe/Prague − equity) / 50.000; swap mở và entry slip còn floating được tách khỏi realized balance. Max R-DD là đỉnh→đáy equity. Cột thủng vốn gốc là mức dưới 50.000 USD, **khác** DD từ đỉnh. Không dùng equity đầu ngày thay balance và không cộng MAE từng lệnh.

| Case | Exit | Năm | Lệnh định giá/gốc | Net USD | Net R | Mean R/lệnh | Max equity R-DD | Daily loss % | Thủng vốn gốc % |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| A Asian breakout | NO_TP | 2022 | 103/103 | +1413.21 | +9.421 | +0.091 | 16.102 | 0.698 | 1.332 |
| A Asian breakout | NO_TP | 2023† | 106/107 | +2368.34 | +15.789 | +0.149 | 20.893 | 0.731 | 2.818 |
| A Asian breakout | TP 2R | 2022 | 103/103 | -296.09 | -1.974 | -0.019 | 14.087 | 0.676 | 1.332 |
| A Asian breakout | TP 2R | 2023† | 106/107 | +556.98 | +3.713 | +0.035 | 12.900 | 0.636 | 2.757 |
| C H1 impulse | NO_TP | 2022 | 61/61 | -1977.60 | -13.184 | -0.216 | 19.569 | 0.630 | 5.837 |
| C H1 impulse | NO_TP | 2023 | 85/85 | +2435.72 | +16.238 | +0.191 | 13.414 | 0.911 | 3.945 |
| C H1 impulse | TP 2R | 2022 | 61/61 | -3062.44 | -20.416 | -0.335 | 22.613 | 0.630 | 6.750 |
| C H1 impulse | TP 2R | 2023 | 85/85 | +1630.33 | +10.869 | +0.128 | 12.993 | 0.911 | 3.760 |

A không TP cứng đạt khoảng +2,83% năm 2022 và +4,74% trên phần đã định giá năm 2023 ở R0 hiện tại. Max equity DD tương ứng 4,83% và 6,27%†; Daily Loss 0,698%/0,731%†. Chưa đo days-to-target, phase transitions hoặc payout; không suy từ PnL cuối năm thành số lần pass/fail Challenge, và không tự tăng sizing.

| Case | Exit | Năm | SL | TP 2R | TIME48H | Friday close | Chưa giá |
|---|---|---|---:|---:|---:|---:|---:|
| A Asian breakout | NO_TP | 2022 | 52 | 0 | 27 | 24 | 0 |
| A Asian breakout | NO_TP | 2023 | 58 | 0 | 35 | 13 | 1 |
| A Asian breakout | TP 2R | 2022 | 49 | 22 | 15 | 17 | 0 |
| A Asian breakout | TP 2R | 2023 | 55 | 28 | 18 | 5 | 1 |
| C H1 impulse | NO_TP | 2022 | 33 | 0 | 12 | 16 | 0 |
| C H1 impulse | NO_TP | 2023 | 35 | 0 | 39 | 11 | 0 |
| C H1 impulse | TP 2R | 2022 | 33 | 4 | 8 | 16 | 0 |
| C H1 impulse | TP 2R | 2023 | 34 | 20 | 24 | 7 | 0 |

## 4. Chi phí thay đổi bao nhiêu — cùng entry/size/path

| Case | Exit | Năm | SYM_FLAT R | SYM_ORDER R | ASYM_FLAT R | ASYM_ORDER R | Delta swap R | Delta TP slip R |
|---|---|---|---:|---:|---:|---:|---:|---:|
| A Asian breakout | NO_TP | 2022 | +7.510 | +7.510 | +9.421 | +9.421 | +1.911 | +0.000 |
| A Asian breakout | NO_TP | 2023† | +13.122 | +13.122 | +15.789 | +15.789 | +2.667 | +0.000 |
| A Asian breakout | TP 2R | 2022 | -3.744 | -3.220 | -2.498 | -1.974 | +1.246 | +0.524 |
| A Asian breakout | TP 2R | 2023† | +1.635 | +2.394 | +2.955 | +3.713 | +1.319 | +0.759 |
| C H1 impulse | NO_TP | 2022 | -14.153 | -14.153 | -13.184 | -13.184 | +0.969 | +0.000 |
| C H1 impulse | NO_TP | 2023 | +13.722 | +13.722 | +16.238 | +16.238 | +2.516 | +0.000 |
| C H1 impulse | TP 2R | 2022 | -21.328 | -21.254 | -20.491 | -20.416 | +0.837 | +0.075 |
| C H1 impulse | TP 2R | 2023 | +8.660 | +9.127 | +10.402 | +10.869 | +1.742 | +0.467 |

A không TP cứng đã dương với phí đối xứng cũ: +7,510/+13,122R†. Proxy swap nâng lên +9,421/+15,789R†, cải thiện +1,911/+2,667R†. Không TP nên cell ORDER không thay slippage ở nhánh này. Do đó lợi nhuận A không TP cứng không chỉ đến từ việc cho TP phí 0. C vẫn âm năm 2022 trong mọi cell, kể cả giả định TP thuận lợi.

So sánh đường vốn của hai đầu mô hình phí († giữ cùng giới hạn sổ con):

| Case | Exit | Năm | R-DD cũ | R-DD mới | Daily loss cũ % | Daily loss mới % |
|---|---|---|---:|---:|---:|---:|
| A | NO_TP | 2022 | 16.776 | 16.102 | 0.686 | 0.698 |
| A | NO_TP | 2023† | 22.177 | 20.893 | 0.799 | 0.731 |
| A | TP2R | 2022 | 14.336 | 14.087 | 0.669 | 0.676 |
| A | TP2R | 2023† | 13.050 | 12.900 | 0.650 | 0.636 |
| C | NO_TP | 2022 | 20.486 | 19.569 | 0.633 | 0.630 |
| C | NO_TP | 2023 | 14.449 | 13.414 | 0.930 | 0.911 |
| C | TP2R | 2022 | 23.378 | 22.613 | 0.633 | 0.630 |
| C | TP2R | 2023 | 13.712 | 12.993 | 0.930 | 0.911 |

## 5. BUY/SELL của A

| Exit | Năm | Chiều | Lệnh định giá/gốc | SYM_FLAT R | ASYM_ORDER R |
|---|---|---|---:|---:|---:|
| NO_TP | 2022 | BUY | 54/54 | -1.491 | -1.766 |
| NO_TP | 2023† | BUY | 56/57 | +2.533 | +2.185 |
| TP 2R | 2022 | BUY | 54/54 | -9.939 | -9.912 |
| TP 2R | 2023† | BUY | 56/57 | +1.265 | +1.460 |
| NO_TP | 2022 | SELL | 49/49 | +9.001 | +11.187 |
| NO_TP | 2023 | SELL | 50/50 | +10.589 | +13.604 |
| TP 2R | 2022 | SELL | 49/49 | +6.195 | +7.938 |
| TP 2R | 2023 | SELL | 50/50 | +0.370 | +2.253 |

Phần lớn lãi A không TP cứng đến từ SELL; BUY âm năm 2022 và chỉ dương nhẹ ở phần đã định giá năm 2023. Đây là attribution trên Development đã xem, chưa là bằng chứng cho một chiến lược SELL-only bền vững. Giữ cohort A BOTH gốc cho bước đối chiếu cơ học tiếp theo; thay admission/chiều cần đăng ký riêng.

## 6. Lãi tập trung và giới hạn cho mục tiêu thu nhập

| A BOTH không TP cứng | Winrate đã định giá | Lệnh lời lớn nhất R | Top 5 tổng R | Phần còn lại R | Giữ lệnh median h |
|---|---:|---:|---:|---:|---:|
| 2022 | 35.92% | +9.267 | +29.830 | -20.409 | 21.99 |
| 2023 | 35.85% | +9.654 | +31.568 | -15.780 | 12.50 |

A có dạng nhiều lỗ nhỏ, ít lãi lớn: top 5 đóng góp 29,83/31,57R, phần còn lại −20,41/−15,78R†. Điều này giải thích vì sao TP 2R làm mất nhiều lợi nhuận; nó cũng khiến hai năm dương chưa chứng minh thu nhập đều. Phép bỏ top 5 là chẩn đoán mức tập trung lợi nhuận, không luật lọc lệnh hay tiêu chí tự động bác mọi trend-following.

## 7. FTMO Standard: phần đã làm và phần còn chặn

[FTMO holding FAQ](https://ftmo.com/faq/can-i-hold-positions-overnight-or-over-the-weekend/) có ngoại lệ cho Challenge/Verification và Swing. Friday policy ở đây nhắm funded Standard. Nó chưa thay một calendar theo ngày: [FTMO30Mar2023](https://ftmo.com/en/blog/trading-updates/trading-update-30-mar-2023/) xác nhận metals nghỉ Good Friday 07Apr; [23Nov2023](https://ftmo.com/de/blog/trading-updates/trading-update-23-november-2023/) cho metals đóng 24Nov lúc 20:45 GMT+2 = 18:45 UTC, sớm hơn clamp 20:30.

Trên nguồn quan sát, hai tín hiệu A ngày 17/01/2022 và 04/07/2022 còn đi qua quote breaks 301,03 và 211,02 phút. Chưa đối chiếu toàn bộ với lịch FTMO lịch sử; không suy source gap thành FTMO closure đã chứng minh. Nhưng chỉ Friday clamp chắc chắn chưa đủ chứng nhận quy tắc mọi kỳ nghỉ >2 giờ. Không đóng tại quote cuối bằng hindsight để làm đủ 608/608.

Margin, admission/account caps, server swap clock/rates/history, news restrictions và target feed/liquidity vẫn chưa xác minh. A không TP cứng có tối đa 3 vị thế đồng thời; C không TP cứng có tối đa 4 vị thế. Đây là sổ nghiên cứu, không full prop evaluator hay quyền broker. Giá 2024–2026 tiếp tục đóng.

**Đề xuất:** giữ duy nhất A BOTH/không TP cứng cho bước kiểm tiếp calendar nghỉ lễ và profile tài khoản đích, xử lý lệnh ngày 24/11/2023 rồi kiểm lại đúng phần bị ảnh hưởng. Gác C và TP 2R hiện tại; không mở vòng vá SL/TP/filter. Sau khi khóa các semantics đó mới xem xét protocol validation/risk/prop tiếp theo. Chưa mua Challenge hoặc mở holdout từ kết quả này.

## 8. Kiểm chứng, provenance và hậu kiểm kỹ thuật

18 kiểm thử đơn vị và 12 kiểm thử hồi quy Stage-0 đạt; Nguồn toàn bộ: **55.662.238 tick/416.710 nến M1 OHLC** khớp, 0 phút M1 đã tiếp nhận thiếu tick trong các giờ đã yêu cầu; 307 giờ nguồn rỗng giữ nguyên. Đây là single-provider admission, không independent market feed. Rất nhiều tick giúp kiểm đường giá; số alpha observations vẫn chỉ 356 tín hiệu có overlap.

Self-audit riêng: **712 đường giá chạm mức đầu tiên**, **2.840 đối soát chi phí bằng Fraction**, **16 sổ ×2 mô hình phí** đối chiếu integer equity/DD/daily; **157.764.214 lần định giá tick** qua oracle (có đọc lại giữa các book, không tick độc lập mới). Không independent agent/ASTRA review.

Attempt1 dừng trong source review trước PnL để sửa reset balance: entry slip và swap mở còn thuộc floating, chưa được coi như balance realized. V1/failure/cancellation receipt giữ nguyên. V2 định giá cùng tín hiệu/stop/khối lượng, có regression riêng. [MQL5 DEAL_SWAP](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties) và [MT5 balance/equity](https://www.metatrader5.com/en/terminal/help/trading_advanced/history_report) hỗ trợ mô hình accrual; broker reopen/balance modes vẫn unknown.

Thu thập 7.256 giờ nguồn (2.742 giờ dùng lại, 4.514 giờ mới): 2.005,40 giây. V2 kiểm nguồn + đường giá/sổ equity: 638,36 giây. Không suy CPU/quota/tổng thời gian viết code từ các timer này; rework lượt kiểm nguồn đã hủy giữ riêng. Reuse provider/decoder/cache/frozen signals; chưa cần engine/framework mới. Fix thuộc code+fixtures; các skill hiện có đã yêu cầu đúng basis/cost/exposure, không cần thêm skill hoặc sửa cấu hình toàn cục.

Artifacts: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\xauusd-h1-execution-20261113`; `registration-v2.json`, `source-snapshot-v2`, `attempt-2/result.json`, `trades.json`, `coverage.json`, `source-review.json`, `arithmetic-review.json`. Result SHA256: `0c09ef18c96aac338982710ddc5814db40f2bd8126157446a244380b9a97e70c`. Config SHA256: `e60a0be7b74c8e8b80e96eaea5febeb59e9d9d7b18b76e767475b28ee828efee`. JSON công khai giữ inputs/pins/verdict/metrics; rawticks ở kho local, không đưa vào Git.

Chạy tái hiện từ workspace: `python tooling/ai-engines/xau_h1_execution.py --config <job>/registration-v2.json`; output attempt phải mới, giữ đúng snapshot/pins. Kiểm riêng: `python tooling/ai-engines/xau_h1_execution_review.py <job>/attempt-2`. Không overwrite attempt đã freeze.
