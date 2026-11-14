# V3 — đã có một vệ tinh bổ sung, chưa đủ điều kiện mua Challenge

**Có tiến bộ về thành tích:** A gốc + EURUSD đã tạo ra 15/36 cửa sổ qua vòng 1 và 2/36 cửa sổ hoàn tất cả hai vòng dưới proxy swap bất đối xứng. **Payout vẫn bằng 0.** Hai cửa sổ hoàn tất cùng đi vào một đường funded giống nhau; không coi là hai thành công độc lập hoặc xác suất pass tương lai.

Đã hoàn tất Phase 0–4 của task `ded836a8-3f42-4204-9742-9fc0ad3c369e`. PR #80 đã merge `91dd2d5`, nhánh cũ xóa. Giữ WIP VI Dubber; không gọi broker/model/paid provider. Giá 2025–2026 tiếp tục đóng. `prop_qualified=false`; kết quả là mô phỏng offline, chưa là tài khoản quỹ thật.

## 1. Bốn cấu hình so sánh trực tiếp

Cùng 36 ngày bắt đầu tháng từ 01/2022 đến 12/2024, kết thúc trước 01/01/2025. Các cửa sổ chồng lấn, cửa sổ muộn có ít thời gian theo dõi hơn. PR #79/#80 dùng kết quả đã khóa; hai cột V3 dùng cùng bộ máy tick ghép và cùng chính sách vốn, chỉ khác việc có thêm vệ tinh.

### SYM: stress swap −40/−40

| Chỉ tiêu | PR #79: A / risk v1 | PR #80: A / risk v2 | V3: A / balanced | V3: A + EUR / balanced |
|---|---:|---:|---:|---:|
| Qua vòng 1 | 8/36 | 2/36 | 3/36 | 15/36 |
| Hoàn tất cả hai vòng | 0/36 | 0/36 | 0/36 | 0/36 |
| Số payout / USD trader | 0 / $0.00 | 0 / $0.00 | 0 / $0.00 | 0 / $0.00 |
| Lỗ ngày lớn nhất | 1.335% | 1.071% | 0.924% | 1.132% |
| Lỗ dưới vốn đầu lớn nhất | 9.321% | 6.157% | 6.283% | 6.998% |
| Sụt giảm từ đỉnh lớn nhất | 12.728% | 8.969% | 8.557% | 8.854% |
| Vi phạm trong mô hình | 0 | 0 | 0 | 0 |
| Trung vị thời gian qua vòng 1* | 11.31 tháng | 12.82 tháng | 20.59 tháng | 10.64 tháng |
| Trung vị hoàn tất hai vòng* | N/A | N/A | N/A | N/A |

### ASYM: proxy swap −45/−5

| Chỉ tiêu | PR #79: A / risk v1 | PR #80: A / risk v2 | V3: A / balanced | V3: A + EUR / balanced |
|---|---:|---:|---:|---:|
| Qua vòng 1 | 13/36 | 5/36 | 5/36 | 15/36 |
| Hoàn tất cả hai vòng | 0/36 | 0/36 | 0/36 | 2/36 |
| Số payout / USD trader | 0 / $0.00 | 0 / $0.00 | 0 / $0.00 | 0 / $0.00 |
| Lỗ ngày lớn nhất | 1.221% | 0.979% | 0.925% | 1.071% |
| Lỗ dưới vốn đầu lớn nhất | 8.899% | 6.083% | 6.052% | 6.997% |
| Sụt giảm từ đỉnh lớn nhất | 11.849% | 8.356% | 7.968% | 8.790% |
| Vi phạm trong mô hình | 0 | 0 | 0 | 0 |
| Trung vị thời gian qua vòng 1* | 10.64 tháng | 15.67 tháng | 15.67 tháng | 10.64 tháng |
| Trung vị hoàn tất hai vòng* | N/A | N/A | N/A | 21.79 tháng |

*Trung vị chỉ tính cửa sổ đã đạt, không phải thời gian dự báo cho mọi tài khoản. Cửa sổ liên tục từ 01/01/2022 chính là quan sát tháng đầu tiên, không cộng thành thử nghiệm độc lập thứ 37.

SYM/ASYM là hai giả định swap Gold đã giữ nguyên: −40/−40 và −45/−5 USD/lot/rollover. **Hai vòng chỉ hoàn tất ở ASYM; SYM vẫn 0/36.** Vì vậy chưa thể gọi kết quả vượt challenge là vững dưới mọi kịch bản phí.

## 2. Danh mục hiện tại làm gì?

| Thành phần | Luật dễ hiểu | Vai trò |
|---|---|---|
| Core: XAUUSD A gốc | H1 phá biên phiên Á theo hướng H4, SL tự nhiên, không TP cứng; giữ tối đa 48h lịch, chặn cuối tuần/ngày đóng sớm | Theo nhịp giá đi tiếp |
| Vệ tinh: EURUSD Asia/London sweep DAY | Trong 08:00–11:00 UTC, H1 quét qua đáy Á rồi đóng tăng trở lại trên đáy Á thì BUY; quét đỉnh Á rồi đóng giảm trở lại dưới đỉnh Á thì SELL | Khai thác cú quét rồi quay lại qua biên |

Vùng Á dùng 00:00–06:00 UTC đã hoàn tất. EUR vào ở quote đầu tiên sau nến H1 xác nhận, tối đa một cơ hội đăng ký/ngày. SL ngoài cực trị nến tín hiệu, thêm 0,1 ATR14 H1 biết trước nến; không nới SL để qua cổng phí. Đóng khi chạm SL hoặc 20:30 UTC cùng ngày/ngày lễ sớm hơn. Không có TP cứng, trailing hay partial close mới. Chỉ nhận khi ma sát/SL ≤15%. Chiều BUY/SELL đều giữ, không chọn lại theo 2024.

Phí EUR giữ commission $5 + slippage $4/lot/vòng, cộng spread Bid/Ask quan sát; không trừ spread hai lần. Swap EUR bằng 0 vì đóng thật trước rollover trong mô hình, không phải đặt biểu phí qua đêm bằng 0. Gold giữ spread quan sát, commission 0,0007% notional/side, slippage 0,20 USD/oz/side và hai kịch bản swap cũ. Các mức này vẫn là profile nghiên cứu, chưa xác minh đủ spec tài khoản đích.

### Kết quả EUR đã xác nhận bằng tick, ở risk tham chiếu $150

| Năm | BUY / SELL | Tổng lệnh | Net R | Mean Net R/lệnh | Win rate | Net R bỏ top 3 |
|---|---:|---:|---:|---:|---:|---:|
| 2022 | 56 / 56 | 112 | +3.771 | +0.0337 | 31.2% | -12.881 |
| 2023 | 60 / 64 | 124 | +10.562 | +0.0852 | 35.5% | -6.662 |
| 2024 | 30 / 37 | 67 | +6.337 | +0.0946 | 41.8% | -9.957 |

1R ở bảng này = $150 để so cơ chế tín hiệu. Trong tài khoản thi, EUR dùng ngân sách nhỏ hơn Core; không cộng thẳng các R tham chiếu để dự báo % lợi nhuận tài khoản. 2024 có 78 cơ hội thô, 67 lệnh vào và 11 cơ hội rớt cổng phí; tần suất thấp hơn 2022–2023 đã được giữ nguyên.

Lợi nhuận vẫn tập trung ở ít lệnh thắng lớn: bỏ ba lệnh tốt nhất thì mỗi năm đều âm. Win rate thấp không tự bác chiến lược, nhưng các con số này chưa chứng minh nguồn thu đều hoặc lợi thế bền vững. Đó là lý do EUR chỉ được dùng ở ngân sách vệ tinh, không thay Core.

Bản M1 ban đầu cho EUR khoảng +15,964R gộp Dev. Tick gốc cho **+14,334R**, thấp hơn khoảng 1,63R nhưng vẫn qua cổng. Không dùng số M1 đẹp hơn khi đã có số tick.

## 3. Vì sao giữ A gốc thay vì D1 scaling?

Chỉ thử một quy tắc: D1 SMA50 với độ dốc 5 ngày đã đóng; tín hiệu Core ngược xu hướng D1 giảm còn 0,5x risk. Nến D1 chưa đóng không được dùng. Không thử thêm SMA/ADX hoặc ngắt hẳn SELL sau khi thấy kết quả.

| Phí | Cấu hình | Net R 2022 | Net R 2023 | Gộp hai năm | Equity DD gộp (R) | Net/DD |
|---|---|---:|---:|---:|---:|---:|
| SYM | A_Original | +4.050 | +13.795 | +17.845 | 22.177 | 0.805 |
| SYM | A_RegimeScaled | +5.371 | +7.408 | +12.779 | 19.847 | 0.644 |
| ASYM | A_Original | +5.901 | +16.462 | +22.363 | 20.893 | 1.070 |
| ASYM | A_RegimeScaled | +7.111 | +9.670 | +16.781 | 18.664 | 0.899 |

D1 scaling giúp 2022 nhưng cắt mất nhiều lợi nhuận 2023; tỷ số gộp giảm trong cả hai mô hình phí. Vì vậy chọn **A_Original** trước mở 2024. Không dùng SELL lỗ năm 2024 làm lý do hồi tố tắt SELL. Trên baseline đã sửa holiday, SELL 2022 là +6,934R, không còn số +11,19R của bản cũ.

## 4. Top 10 và lý do chỉ chọn một vệ tinh

V2 có 84 cấu hình đủ endpoint nhưng đã rớt Stage-0, chưa tới cổng +6R/năm. V3 là thí nghiệm mới được owner cho phép kiểm Natural SL và đóng góp danh mục trên cùng 112 công thức. Không sửa lại verdict cũ, không thêm tín hiệu/horizon sau kết quả.

Bảng xếp hạng dùng mô hình có tổng Net R thấp hơn giữa SYM/ASYM. Các dòng H1/nguồn thiếu chỉ là screen có điều kiện, không phải ứng viên đã đủ điều kiện. Dòng EUR được cập nhật bằng tick; các dòng khác giữ bản screen đã đăng ký. DD screen là biên bảo thủ của M1/H1, khác DD tick chính xác ở bảng vòng đời. Đầy đủ hai mô hình và 112 cấu hình trong JSON.

| # | Asset | Cơ chế / vùng / phiên | Giữ | Lệnh 2022/23 | Đạt phí 2022/23 | Net R 2022 | Net R 2023 | Tổng | Max R-DD | Corr với A | Nguồn / cổng chặn |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | GBPUSD | Quét Á / London | Ngày | 142/144 | 96.6%/94.1% | +5.617 | +26.075 | +31.692 | 18.778 | -0.014 | Chỉ H1; chưa đủ M1/tick |
| 2 | XAUUSD | Quét ngày trước / London | Ngày | 23/22 | 45.1%/39.3% | +17.099 | +9.930 | +27.029 | 6.879 | 0.113 | Giữ chỉ 39–45% raw; thiếu ask/path |
| 3 | XAUUSD | Quét ngày trước / London | +24h | 23/22 | 45.1%/39.3% | +11.460 | +13.061 | +24.522 | 7.357 | 0.102 | Giữ chỉ 39–45% raw; thiếu ask/path |
| 4 | XAUUSD | Quét ngày trước / London | +48h | 23/22 | 45.1%/39.3% | +5.754 | +17.241 | +22.994 | 10.739 | 0.121 | Giữ chỉ 39–45% raw; thiếu ask/path |
| 5 | US500 | Quét ngày trước / New York | +48h | 51/30 | 67.1%/33.0% | +12.337 | +8.163 | +20.501 | 11.287 | -0.009 | Không đạt scale/retention; carry đích chưa đủ |
| 6 | EURUSD | Quét Á / London | Ngày | 112/124 | 94.9%/96.1% | +3.771 | +10.562 | +14.334 | 35.757 | 0.100 | Tick đã xác nhận; được chọn |
| 7 | GBPUSD | Quét ngày trước / London | Ngày | 70/67 | 90.9%/91.8% | +14.361 | -1.973 | +12.388 | 14.649 | -0.065 | Chỉ H1; chưa đủ M1/tick |
| 8 | US500 | Quét ngày trước / London | +48h | 18/2 | 30.0%/4.4% | +5.785 | +4.928 | +10.713 | 10.263 | 0.012 | Không đạt scale/retention; carry đích chưa đủ |
| 9 | US500 | Quét ngày trước / London | +24h | 18/2 | 30.0%/4.4% | +6.171 | +2.819 | +8.990 | 6.151 | 0.032 | Không đạt scale/retention; carry đích chưa đủ |
| 10 | US500 | Quét ngày trước / New York | +24h | 51/30 | 67.1%/33.0% | +8.881 | -0.470 | +8.411 | 9.885 | -0.028 | Không đạt scale/retention; carry đích chưa đủ |

SWEEP = quét qua biên rồi quay lại; CONT = phá biên đi tiếp; ASIA/PREVDAY = vùng phiên Á/ngày trước; DAY = đóng cùng ngày. Các horizon của cùng cohort không độc lập.

EUR giữ 94,9% / 96,1% cơ hội qua cổng phí trong Dev. Bản tick có +3,771R / +10,562R, tổng ≥8R, hai năm đều dương, tương quan ngày khoảng 0,10. Ghép ở ngân sách $75 so với Core $150 cải thiện Net/DD từ 0,805 lên 0,982 ở SYM và 1,070 lên 1,232 ở ASYM. Không có vệ tinh thứ hai đạt đủ nguồn, scale, kinh tế và đóng góp biên.

GBPUSD Asia/London sweep DAY có screen H1 dương đáng chú ý nhưng thiếu đường M1/tick; chưa được gọi là edge hoặc đưa vào portfolio. Các Gold sweep dương đã loại hơn một nửa tín hiệu bởi phí, nên không được cứu bằng nới SL. US500 còn vướng scale/retention và carry/cổ tức đích. USDJPY vẫn thiếu nguồn liên tục, không bị gán nhãn thua kinh tế.

Đã khôi phục 715/732 endpoint US500 cũ bằng nguồn đã có và clamp trước giờ nghỉ NY; 17 mốc còn thiếu được giữ unknown. Không lấy quote đầu tiên sau giờ nghỉ để làm giá đóng trước giờ nghỉ. Các khoảng thiếu AUDUSD không được lấp. Bản Natural-SL có 42 cấu hình đủ đường cho M1 scenario; phần còn lại có điều kiện, thiếu nguồn hoặc lot grid. Đủ endpoint và đủ đường giữ lệnh là hai việc khác nhau.

## 5. Đi vốn, trần rủi ro và trade-off

| Phase | Core | Vệ tinh EUR |
|---|---:|---:|
| Vòng 1 | 0,40% / $200 | 0,20% / $100 |
| Vòng 2 | 0,35% / $175 | 0,20% / $100 |
| Funded | 0,25% / $125 | 0,15% / $75 |

Tổng rủi ro ban đầu đến SL của mọi vị thế ≤1% ($500). Không net rủi ro BUY/SELL hoặc khác tài sản để lách cap. Mức lỗ equity hiện tại so với vốn đầu đạt 4% hạ trần risk lệnh mới còn $150; đạt 6% còn $90; không nâng risk vệ tinh vì cap. Lỗ đã thực hiện trong ngày chạm −2% thì ngừng mở mới đến reset Prague. Vị thế cũ giữ size. Cổng reserve còn yêu cầu SL + phí + funding dự kiến không chạm mức equity $46.500. Cổng funding hiện chỉ dùng deadline khóa trước, không dùng thời điểm SL/thoát lệnh biết sau.

| Phí | Open risk lớn nhất | Chặn bởi cap 1% | Chặn bởi reserve 7% | Chặn lỗ ngày 2% |
|---|---:|---:|---:|---:|
| SYM | 0.997344% | 87 | 1071 | 0 |
| ASYM | 0.997344% | 85 | 718 | 0 |

Counts là tổng lượt trên các tài khoản chồng lấn, không là cơ hội thị trường độc lập. Reserve thực sự chặn nhiều lệnh trong V3; không gọi các lệnh đó là bị bỏ qua ngẫu nhiên. Cổng 7% có thể làm tài khoản giao dịch thưa hoặc chờ hồi phục. **Worst static khoảng 6,998% rất sát ngưỡng nội bộ 7%**, dù vẫn còn khoảng 3 điểm phần trăm tới trần overall 10% của profile. Gap, swap và khớp lệnh ngoài mô hình có thể làm mất buffer này. Không tăng risk hoặc đổi cổng sau khi nhìn kết quả.

## 6. Vì sao đã qua hai vòng nhưng chưa có payout?

Hai mốc bắt đầu 01/01/2022 và 01/02/2022 dưới ASYM cùng qua vòng 1 ngày 29/09/2023, qua vòng 2 ngày 10/11/2023. Từ phase funded trở đi chúng có cùng state/đường lệnh; chỉ có **một đường hoàn tất hai vòng riêng biệt**, không phải hai lần thành công độc lập.

| Mốc bắt đầu | Vào funded* | Net funded cuối 2023 | Net funded năm 2024 | Balance cuối | Payout proxy |
|---|---|---:|---:|---:|---:|
| 2022-01-01 | 2023-11-13 | $-1,096.26 | $847.82 | $49,751.56 | $0 |
| 2022-02-01 | 2023-11-13 | $-1,096.26 | $847.82 | $49,751.56 | $0 |

*Ngày giao dịch funded đầu tiên; phase reset xảy ra ngày 10/11/2023. Lãi vòng thi được bỏ khỏi sổ khi sang phase mới, không phải tiền trả cho trader. Funded khởi đầu lại $50.000, lỗ $1.096,26 cuối 2023 rồi thu lại $847,82 trong 2024, cuối mẫu còn $49.751,56.

Proxy reward giữ nguyên 30 ngày, đã đóng hết vị thế và lãi đóng ≥$20, trừ 100% lợi nhuận khỏi account rồi chia 80% trader/20% firm. Đây không phải xác minh lịch payout hiện hành của hãng. Chẩn đoán đọc sổ theo mốc 14 ngày cũng không tìm thấy thời điểm flat có lợi nhuận dương; không chạy lại chính sách rút tiền 14 ngày hoặc gán nó thành kết quả payout khác. Chưa tính phí mua/retry Challenge, chi phí vận hành và thuế. Chưa có tiền thật được nhận.

## 7. Kiểm chứng và giới hạn còn lại

- 197 tests hồi quy đạt, trong đó 21 fixtures V3 về D1 causal, funding theo deadline, Bid/Ask thiếu, SL gap, lot grid, cash book hai tài sản, daily halt, cap rủi ro và reward debit.
- 420 quyết định D1 được dựng lại từ prefix ngày đã đóng; 12 sổ D1 khớp oracle đường giá/cash.
- 112 Natural-SL screens, 24526 phép đối chiếu chi phí bằng phân số; giữ cả các screen âm/nguồn thiếu.
- 25,447,523 tick EURUSD / 3929 giờ khớp từng dòng CSV gốc, bao gồm thứ tự bản ghi cùng millisecond.
- 144 tài khoản khớp cách hạch toán khác: oracle trả funding vào cash và tổng hợp exposure theo tài sản, trong khi producer giữ funding trong floating.
- Oracle kiểm 30,648 quyết định nhận và 12,320 quyết định từ chối, không chỉ kiểm các lệnh đã vào; đối chiếu phase, loss floors và chi phí.
- 104,985,511 cập nhật quote ghép được kiểm lại bằng phép tìm timestamp của từng nguồn; không lấy giá tương lai của tài sản kia.

**Cùng một implementer, dùng cách tính khác; không có reviewer người/model độc lập và không gửi Astra.** Không đổi data/rules để cứu một kết quả kiểm định không khớp.

### Freeze và Historical Validation

Composition được commit tại `ec602f737405dd5cad1cdcd60b72e8dd2e6c75e8` trước release `2026-11-14T16:05:19.953750+00:00`. Mọi tham số Core/Satellite/risk và code/rule hashes được kiểm lại trước Phase 3. Git LF và file Windows CRLF được bind bằng cả hash byte riêng và nội dung JSON; khác nội dung thì gate từ chối.

2024 đã có exposure từ các đợt trước; ý tưởng D1 cũng được gợi bởi phân rã cũ năm 2024. V3 chỉ dùng 2022–2023 để chọn, commit trước lần replay mới, nhưng **2024 không trở thành clean OOS**. 112 cấu hình, các horizon gần nhau và lịch sử thử trước đây gây selection bias. Tương quan thấp trong Dev không bảo đảm thấp trong tương lai.

Các gate chưa đủ cho Challenge/funded thật: spec/commission/swap và margin/leverage đích, lịch tin hạn chế lịch sử, phiên/ngày đóng sớm đúng feed tài khoản, độ mới quote ở reset khi thị trường nghỉ, forward/shadow và bàn giao vận hành. Cùng timestamp UTC không chứng minh hai feed có cùng latency như broker. Account mode và các nguồn USD là assumptions đã khai báo. Không có quyền gửi lệnh từ báo cáo này.

### Hậu kiểm kỹ thuật

| Vấn đề | Đã xử lý và bằng chứng |
|---|---|
| Funding reserve nhìn exit tương lai | Dùng deadline biết trước; tests đổi exit không làm đổi reserve; oracle kiểm lại cả nhận/từ chối lệnh |
| Gold M1 chỉ Bid nhưng bị đọc ô Ask=0 | Dừng/quarantine lượt đầu, cấm quote không hợp lệ, giá đóng Gold lấy paired ticks; không dùng kết quả invalid |
| D1 có ngày thiếu dữ liệu | Chỉ dùng ngày đủ điều kiện đã đóng, prefix oracle kiểm causal; không biến ngày 12h thành D1 đầy đủ |
| Freeze private chưa đủ bằng chứng Git | V3 commit quyết định trước mở 2024; lần preflight LF/CRLF bị chặn trước release, sửa semantic binding rồi commit lại, không đổi lựa chọn/risk |
| M1 stop-fill khác tick | Xác nhận đúng một vệ tinh trên tick trước freeze; giữ số tick thấp hơn số screen |

Các sửa lỗi có fixture cụ thể; không tạo thêm skill/process hoặc một bộ state tài khoản song song. Account hiện có tiếp tục sở hữu phase/reset/reward, adapter bổ sung units và quote của tài sản. Không đo quota/chi phí LLM hay tuyên bố speedup không có benchmark.

Private evidence: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\prop-portfolio-v3-20261114`. JSON đi kèm giữ 112 cấu hình, các quyết định, aggregate, 144 ledger rút gọn, source/code hashes và locators. Raw ticks/caches, lượt lỗi, full ledgers và source reviews giữ riêng.

**Quyết định tiếp:** giữ A + EUR như một ứng viên có đóng góp danh mục trong profile đã kiểm, đủ cho bước review hữu hạn tiếp theo. Chưa mua Challenge hoặc dựa vào nó làm thu nhập chính: chưa payout, thành công hai vòng chưa vững dưới stress đối xứng, thời gian pass dài và chưa có clean OOS/forward. Ưu tiên xác minh profile đích/khả năng vận hành và kiểm định tiếp đã đăng ký, không thêm bot yếu hoặc tăng risk để ép payout. GBP giữ ở mức source-readiness, chưa được promote.

## Phụ lục — toàn bộ 112 cấu hình

| Cell | M1/H1 net R 2022/23 (ASYM) | Filled 2022/23 | Đủ đường scenario | Lý do chưa chọn |
|---|---:|---:|---|---|
| XAUUSD.SWEEP.ASIA.LONDON.DAY | -6.321/-4.757 | 46/32 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.ASIA.LONDON.24H | -12.794/-1.798 | 46/32 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.ASIA.LONDON.48H | -12.309/-5.946 | 46/32 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.ASIA.NY.DAY | -18.513/+12.108 | 87/102 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.ASIA.NY.24H | -20.732/+4.820 | 87/102 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.ASIA.NY.48H | -29.440/+5.016 | 87/102 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.PREVDAY.LONDON.DAY | +17.099/+9.930 | 23/22 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15 |
| XAUUSD.SWEEP.PREVDAY.LONDON.24H | +11.542/+13.215 | 23/22 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15 |
| XAUUSD.SWEEP.PREVDAY.LONDON.48H | +6.131/+17.378 | 23/22 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15 |
| XAUUSD.SWEEP.PREVDAY.NY.DAY | -8.495/+3.883 | 65/64 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.PREVDAY.NY.24H | -12.332/+1.658 | 65/64 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.SWEEP.PREVDAY.NY.48H | -12.093/-2.773 | 65/64 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.IMPULSE.D1H4.LONDON.DAY | -2.578/-9.008 | 10/14 | Đủ trong scenario | 2022:FRICTION_RETENTION_LT60, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.IMPULSE.D1H4.NY.DAY | -2.699/+2.250 | 19/30 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.TWOBAR.D1H4.LONDON.DAY | -3.272/-10.626 | 17/19 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| XAUUSD.TWOBAR.D1H4.NY.DAY | -2.205/+6.074 | 27/26 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.ASIA.LONDON.DAY | +4.455/+11.510 | 112/124 | Đủ trong scenario | NATIVE_CONFIRMED_SELECTED |
| EURUSD.SWEEP.ASIA.LONDON.24H | -15.806/+2.046 | 112/124 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.ASIA.LONDON.48H | -13.170/-3.104 | 112/124 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.ASIA.NY.DAY | -12.652/-0.602 | 103/88 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.ASIA.NY.24H | -26.052/-11.079 | 103/88 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.ASIA.NY.48H | -39.680/-24.882 | 103/88 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.PREVDAY.LONDON.DAY | -8.049/-5.198 | 65/66 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.PREVDAY.LONDON.24H | -17.287/-11.708 | 65/66 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.PREVDAY.LONDON.48H | -17.117/-10.395 | 65/66 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.PREVDAY.NY.DAY | -3.906/+4.046 | 80/82 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.PREVDAY.NY.24H | -28.109/+3.840 | 80/82 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.SWEEP.PREVDAY.NY.48H | -19.738/-24.879 | 80/82 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.ASIA.LONDON.DAY | -3.482/+2.535 | 56/70 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.ASIA.LONDON.24H | -7.245/-1.916 | 56/70 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.ASIA.LONDON.48H | -20.930/-12.329 | 56/70 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.ASIA.NY.DAY | -9.885/-0.082 | 44/41 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.ASIA.NY.24H | -24.902/-2.629 | 44/41 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.ASIA.NY.48H | -32.285/-3.489 | 44/41 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.PREVDAY.LONDON.DAY | -3.503/+0.559 | 42/40 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.PREVDAY.LONDON.24H | -6.370/-3.917 | 42/40 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.PREVDAY.LONDON.48H | -6.641/-11.241 | 42/40 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.PREVDAY.NY.DAY | -6.192/-0.352 | 45/52 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.PREVDAY.NY.24H | -9.789/-7.719 | 45/52 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| EURUSD.CONT.PREVDAY.NY.48H | -13.115/-13.516 | 45/52 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| US500.SWEEP.ASIA.LONDON.DAY | +0.791/+0.000 | 18/0 | Đủ trong scenario | 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:TOTAL_NET_R_LT8 |
| US500.SWEEP.ASIA.LONDON.24H | +0.681/+0.000 | 18/0 | Đủ trong scenario | 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:TOTAL_NET_R_LT8, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.SWEEP.ASIA.LONDON.48H | -1.982/+0.000 | 18/0 | Đủ trong scenario | 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.SWEEP.ASIA.NY.DAY | -2.532/+1.581 | 53/3 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| US500.SWEEP.ASIA.NY.24H | -4.400/+1.617 | 53/3 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.SWEEP.ASIA.NY.48H | -2.591/+2.800 | 53/3 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.SWEEP.PREVDAY.LONDON.DAY | +1.426/+2.345 | 18/2 | Đủ trong scenario | 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:TOTAL_NET_R_LT8 |
| US500.SWEEP.PREVDAY.LONDON.24H | +6.171/+2.819 | 18/2 | Đủ trong scenario | 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.SWEEP.PREVDAY.LONDON.48H | +5.785/+4.928 | 18/2 | Đủ trong scenario | 2022:FRICTION_RETENTION_LT60, 2022:MEDIAN_FRICTION_SL_GT15, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.SWEEP.PREVDAY.NY.DAY | +7.573/-4.260 | 51/30 | Đủ trong scenario | 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| US500.SWEEP.PREVDAY.NY.24H | +8.881/-0.470 | 51/30 | Đủ trong scenario | 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.SWEEP.PREVDAY.NY.48H | +12.337/+8.163 | 51/30 | Đủ trong scenario | 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.ASIA.LONDON.DAY | +0.354/-0.543 | 22/2 | Đủ trong scenario | SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| US500.CONT.ASIA.LONDON.24H | -1.863/-0.839 | 22/2 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.ASIA.LONDON.48H | -8.118/-1.632 | 22/2 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.ASIA.NY.DAY | -12.841/+0.000 | 39/0 | Đủ trong scenario | 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| US500.CONT.ASIA.NY.24H | -17.726/+0.000 | 39/0 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.ASIA.NY.48H | -19.571/+0.000 | 39/0 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.PREVDAY.LONDON.DAY | -0.350/+0.119 | 21/2 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| US500.CONT.PREVDAY.LONDON.24H | -0.677/+0.185 | 21/2 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.PREVDAY.LONDON.48H | -3.377/+0.805 | 21/2 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.PREVDAY.NY.DAY | -0.443/+1.087 | 45/45 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| US500.CONT.PREVDAY.NY.24H | -1.655/+1.194 | 45/45 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| US500.CONT.PREVDAY.NY.48H | -5.338/+2.603 | 45/44 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY, TARGET_DIVIDEND_CARRY_UNVERIFIED |
| GBPUSD.SWEEP.ASIA.LONDON.DAY | +5.617/+26.075 | 142/144 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL |
| GBPUSD.SWEEP.ASIA.LONDON.24H | +1.308/+6.606 | 142/144 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:TOTAL_NET_R_LT8 |
| GBPUSD.SWEEP.ASIA.LONDON.48H | -17.514/+2.342 | 142/144 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.ASIA.NY.DAY | -8.939/-10.029 | 118/108 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.ASIA.NY.24H | -27.432/-13.424 | 118/108 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.ASIA.NY.48H | -35.137/-30.847 | 118/108 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.PREVDAY.LONDON.DAY | +14.361/-1.973 | 70/67 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.PREVDAY.LONDON.24H | +9.032/-2.169 | 70/67 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.PREVDAY.LONDON.48H | +3.581/-12.231 | 70/67 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.PREVDAY.NY.DAY | -7.283/-10.581 | 80/77 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.PREVDAY.NY.24H | -25.518/-12.284 | 80/77 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.SWEEP.PREVDAY.NY.48H | -33.207/-15.749 | 80/77 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.ASIA.LONDON.DAY | +5.154/+0.121 | 73/81 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:TOTAL_NET_R_LT8 |
| GBPUSD.CONT.ASIA.LONDON.24H | -5.771/-6.434 | 73/81 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.ASIA.LONDON.48H | -12.661/-11.276 | 73/81 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.ASIA.NY.DAY | -6.773/-2.626 | 53/46 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.ASIA.NY.24H | -12.407/-6.278 | 53/46 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.ASIA.NY.48H | -15.768/-18.957 | 53/46 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.PREVDAY.LONDON.DAY | +4.030/-1.254 | 45/55 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.PREVDAY.LONDON.24H | -0.270/-4.948 | 45/55 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.PREVDAY.LONDON.48H | -0.874/-5.815 | 45/55 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.PREVDAY.NY.DAY | -3.056/-2.375 | 47/49 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.PREVDAY.NY.24H | -7.050/-3.421 | 47/49 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| GBPUSD.CONT.PREVDAY.NY.48H | -8.041/-10.487 | 47/49 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.ASIA.LONDON.DAY | +9.122/-10.406 | 65/60 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.ASIA.LONDON.24H | -6.419/-17.994 | 65/60 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.ASIA.LONDON.48H | -3.093/-27.918 | 65/60 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, 2023:MEDIAN_FRICTION_SL_GT15, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.ASIA.NY.DAY | -14.514/-8.964 | 87/85 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.ASIA.NY.24H | -26.585/-27.685 | 88/86 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.ASIA.NY.48H | -39.248/-31.889 | 88/86 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.PREVDAY.LONDON.DAY | -21.724/-13.733 | 47/28 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.PREVDAY.LONDON.24H | -29.322/-12.843 | 47/28 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.PREVDAY.LONDON.48H | -35.795/-18.679 | 47/28 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, 2023:FRICTION_RETENTION_LT60, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.PREVDAY.NY.DAY | -1.962/+9.949 | 71/53 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.PREVDAY.NY.24H | -25.044/+12.036 | 72/54 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.SWEEP.PREVDAY.NY.48H | -30.141/-0.148 | 72/54 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.ASIA.LONDON.DAY | -7.324/-7.528 | 60/53 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.ASIA.LONDON.24H | -13.156/-12.478 | 60/53 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.ASIA.LONDON.48H | -21.507/-19.686 | 60/53 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.ASIA.NY.DAY | -2.581/-8.613 | 61/51 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.ASIA.NY.24H | -6.938/-13.355 | 62/51 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.ASIA.NY.48H | -21.059/-17.116 | 62/51 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.PREVDAY.LONDON.DAY | -2.364/-0.102 | 39/29 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.PREVDAY.LONDON.24H | -7.216/-2.286 | 39/29 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.PREVDAY.LONDON.48H | -13.722/-4.813 | 39/29 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.PREVDAY.NY.DAY | -2.377/-1.401 | 45/39 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.PREVDAY.NY.24H | -2.839/-1.994 | 46/39 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |
| AUDUSD.CONT.PREVDAY.NY.48H | -8.940/-8.869 | 46/39 | Có điều kiện/thiếu nguồn | SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL, SYM_FLAT:TOTAL_NET_R_LT8, SYM_FLAT:YEAR_STABILITY, ASYM_FLAT:TOTAL_NET_R_LT8, ASYM_FLAT:YEAR_STABILITY |

Các số screen có điều kiện không thay thế số tick xác nhận của EUR ở phần chính.
