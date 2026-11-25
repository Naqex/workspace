# Cửa kiểm chứng: bằng chứng nào cho phép kết luận gì?

Áp dụng từng cửa theo stage, không bắt research ban đầu có đủ mọi điều kiện của
broker execution. Nguồn/đối chiếu hiện hành ở
[audit khung validation](../../../../planning/research/STRATEGY-VALIDATION-FRAMEWORK-20261105.md).
PLAN/protocol và receipt vẫn own scope/outcomes; bảng này own phương pháp review.

| Cửa | Bằng chứng cần | Kết luận tối đa |
|---|---|---|
| G0. Thiết kế trước kết quả | Cơ chế giả thuyết, exact rules/baseline/cost/risk, consumed map/split, main metrics/stop/decision và bản freeze có thời điểm đáng tin | Được chạy đúng experiment đã đăng ký; hash nội dung riêng không chứng minh timing |
| G1. Dữ liệu/code/timing | Kiểm ordering/gaps/timezone/BidAsk; chỉ dùng dữ liệu đã có tại decision, fill sau decision; case tính tay/oracle đơn giản và regressions độc lập với helper bị kiểm | Implementation có bằng chứng trong scope đã kiểm; còn gap thì nêu rõ |
| G2. Simulation assumptions | Spread/commission/slippage/financing/lot/margin, stress/gap/delay, equity/cash và cuối mẫu đúng semantics, nguồn và giới hạn assumptions | Kết quả dưới assumptions đó; chưa suy broker fills hay prop compliance |
| G3. Edge ngoài mẫu | Freeze trước window chưa used, trial history gồm failures/variants, sample/exposure/dependence/regimes/uncertainty, selection-aware assessment khi đủ assumptions | Review robustness/edge; PnL dương hoặc một Sharpe threshold không tự pass |
| G4. Prop-specific | Đúng firm/program/phase/size/version, reset/DST/daily/overall equity, first breach, entry rules, sample coverage, cost/permissions | Prop-fit trong phạm vi profile đã kiểm, không đồng nhất internal budgets với luật hãng |
| G5. Forward/reconciliation | Shadow/demo đúng code/config; đối chiếu signal→order→fill/cost/risk, disconnect/restart/unknown handling, dữ liệu live theo quyền riêng | Bằng chứng vận hành và model-vs-broker gap; chưa bảo đảm lợi nhuận tương lai |
| G6. Authority | Account/scope/budget/grant còn hợp lệ và gate của execution owner | Được thực thi đúng phạm vi, không do research report tự cấp |

Trước validation research: cần G0, G1 và G2 có assumptions rõ, không nợ lỗi
material; chưa đủ realism thì chỉ được kết luận ở mức scenario. Trước đề xuất
shadow/demo cho strategy: review thêm G3/G4 theo mục tiêu, nêu remaining gaps.
Mọi gửi lệnh cần G6 riêng; system demo test không tự chứng minh strategy edge.

## Stage-0: Unconditional Markout & Scale Screen

**Chính sách sàng lọc của owner ngày 13/11/2026 cho cơ chế tín hiệu mới**, trước
khi đóng gói SL/TP/sizing, partial close hoặc filter phụ. Không áp hồi tố để
đổi sealed outcomes; chưa được runner tự enforce và không phải chuẩn thống kê
phổ quát. Bài học: US500 BR01/RS02, EURUSD Catalogue13/B0 và
[XAUUSD scale/horizon audit](../../../../planning/research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.md).

1. **Raw markout trước SL/TP/filter:** khóa tín hiệu thô, Development, cost
   stress, đơn vị và horizon chính trước outcome; khóa cả budget horizon phụ.
   Đo phân phối sau spread/commission/slippage và financing nếu có tại các mốc
   cố định phù hợp: +1h/+2h/+4h/cuối phiên hoặc +1d/+3d/+5d. Giữ count, unique
   days, overlap, từng năm, uncertainty và missing quotes; không chọn horizon
   thắng sau khi xem kết quả. Bid/Ask đã chứa spread thì không trừ lần hai.
   **Dừng Stage-0** nếu mean net stress tại horizon chính không dương ở mọi
   năm Development, hoặc nhỏ hơn mean ma sát thực thi stress trên cùng cohort,
   cùng đơn vị. Không viết tiếp biến thể SL/TP, partial close hoặc filter để
   cứu kết quả; thiếu nguồn/cost thì giữ blocked/unknown, không giả bằng 0.
2. **Natural stop và quy mô phí:** trên raw cohort trước lọc phí, đo stop
   tự nhiên theo cấu trúc nhân quả; `median(F_stress) / median(natural_SL)`
   phải ≤ trần đã khóa trong **12%–15%** (ưu tiên 12%, không quá 15%). Hai vế
   phải cùng đơn vị giá, ví dụ USD/oz hoặc pip; không chia USD tiền tài khoản
   cho khoảng giá, không trộn phí nhóm fills với SL nhóm rejects. Đây là screen
   quy mô, khác `Friction/R0` trên từng intent; trần intent 12% hiện hành vẫn giữ.
3. **Không dùng cost gate để đổi bản chất mẫu:** cấm bộ lọc `Friction/R`
   loại **>50%** tín hiệu tự nhiên. Mẫu số là raw signals đã đăng ký, không
   thu hẹp bằng filter phụ rồi tính lại. Giữ funnel và lý do loại; vượt ngưỡng
   thì dừng recipe, không nới SL nhân tạo, tăng risk hoặc hạ stress sau outcome.
   Tỷ lệ loại lớn là rủi ro chọn lọc quy mô/nến cực đoan, chưa tự chứng minh
   exhaustion hoặc nguyên nhân nhân quả của khoản lỗ.

Qua Stage-0 chỉ cho phép xét đầu tư tiếp đúng protocol; raw markout có thể
chồng lấn, không là account PnL hay chứng minh edge/OOS/prop. G0–G6 vẫn áp dụng.

### Luật thực thi & chống ảo giác bổ sung (23/11/2026 · từ Pass 10–12 & Clean-Room Intel)

1. **Straight-to-M1 Bid/Ask cho lệnh chờ/SL trong ngày:** Mọi chiến lược dùng
   `Pending Stop`/`Limit` nội phiên hoặc SL hẹp **bắt buộc** đo trực tiếp trên
   M1/Tick Bid–Ask với quy tắc bảo thủ `SL hit first` khi trùng phút. Không dùng
   H1 làm bước lọc trung gian cho intraday pending stop (bài học Pass 11: GBPUSD
   London ORB đạt +181,24R trên H1 nhưng rơi về −7,45R trên M1 do 172 ngày quét
   hai biên).
2. **FTMO Real-Cost & Swap-3× Pre-Mortem:** Mọi chiến lược giữ qua đêm hoặc qua
   cuối tuần phải trừ swap có dấu và triple-swap đúng ngày theo snapshot tài
   khoản đích (`36f1535` Standard / `8fd77ef` Swing) ngay tại Stage-0 (bài học
   Pass 10: US500 TOM lãi gộp +521 USD nhưng swap ăn −545 USD).
3. **Alpha vs Beta Null Test & Độ bền tham số:**
   - Chiến lược 2 chiều: giữ đối chứng `Fade` cùng timestamp/quote thực thi.
   - Chiến lược 1 chiều (Long-only/Short-only trên tài sản có drift dài hạn như
     XAUUSD/US500): bổ sung **Monte Carlo Random-Entry Null Test** (300–1.000 lần
     xáo trộn cùng số lệnh & luật thoát, `p < 0,05`) để tách Alpha khỏi Beta.
   - Sau Stage-0: kiểm độ bền tham số ±30% và xét hiệu chỉnh đa thử nghiệm
     (FDR/DSR) theo tổng lịch sử trial của chiến dịch.
4. **Air-Gap với kho intel bên ngoài (`strategy-intel`):** Kho thu thập ý tưởng
   bên ngoài chỉ bàn giao **đặc tả toán học thuần túy** (`external_concept_ref`)
   vào protocol preregister; **cấm** đọc file/import code xuyên repo hoặc dùng
   số liệu từ `01/01/2025` trở đi để chọn ứng viên. Mọi nguồn ngoài luôn ở mức
   `SOURCE_CLAIM_ONLY` cho đến khi tái lập trên M1 Bid/Ask + phí thật trong
   workspace.
5. **Phân loại 3 tầng song hành (ưu tiên tuyệt đối FTMO, không vứt nhầm edge cho tài khoản riêng):**
   Trong cùng một lượt kiểm định (không thêm chi phí tính toán và không hạ chuẩn
   FTMO Challenge), gắn thêm nhãn mục đích sử dụng cho mọi ứng viên đã test:
   - `TIER_1_FTMO_READY`: Có lợi thế thống kê thật (`MC Null p < 0,05`, qua kiểm
     chỉnh đa kiểm định khi sàng lọc hàng loạt, dương cả 2 cụm thời gian), sống
     khỏe dưới phí + Swap 3× FTMO thực tế (`36f1535`/`8fd77ef`) và đáp ứng rào
     rủi ro/DD của mục tiêu FTMO Challenge hiện hành.
   - `TIER_2_PERSONAL_VAULT`: Có **lợi thế giá thật đã chứng minh** (`MC Null
     p < 0,05`, dương bền vững cả 2 cụm, chịu được spread/commission thực tế
     kiểu Exness Raw/Pro — `EXNESS_WEBSITE_SNAPSHOT_UNMEASURED_DEMO`), nhưng
     trượt FTMO chỉ vì Swap 3× FTMO quá nặng hoặc tốc độ/underwater chậm hơn
     khung thi Challenge. Cất riêng làm kho dự trữ dài hạn cho tài khoản vốn
     riêng; **không** dựa mù quáng vào Exness Extended Swap-Free (vì đây là ưu
     đãi có điều kiện có thể bị sàn thu hồi nếu bot lạm dụng giữ qua đêm).
   - `TIER_3_DEAD_NO_EDGE`: Không thắng nổi chọn ngẫu nhiên (`p >= 0,05`) hoặc
     lỗ ngay từ tín hiệu giá trước Swap. Xóa sổ vĩnh viễn cho mọi sàn.
6. **Hiệu chuẩn Control & Bắt buộc xác nhận M1 Bid/Ask cho mọi ứng viên H4/D1 (từ Pass 19 & 21):**
   - Mọi lượt sàng lọc nhanh trên H4/D1 phải chạy kèm ít nhất **1 mẫu đối chứng dương đã có kết quả M1 thật** (ví dụ `CONTROL_USDJPY`) để phát hiện sớm lỗi thứ tự giá trên chính cây nến vào lệnh (pre-trigger false-SL).
   - Kết quả dương trên H4/D1 chỉ có giá trị **đề xuất tải dữ liệu M1**, **không bao giờ** là bằng chứng lên `TIER_1` hay ghép danh mục (bài học Pass 21: `GBPJPY EXP080` đạt `+9,28R` trên H4 nhưng rơi về `-9,52R` trên M1 Bid/Ask thật do spread `1,4–2,4 pip` và quét SL nội nến).
7. **Kỷ luật Discovery Cụm A → Blind OOS Cụm B & BH FDR toàn không gian (từ Pass 20–22):**
   - Khi quét hệ thống nhiều biến thể (`m_total > 1`), chỉ được chọn ứng viên dựa trên **Cụm A (`2018–2020`)**; **Cụm B (`2021–2024`)** giữ mù hoàn toàn để đánh giá OOS và tính **BH FDR trên toàn bộ `m_total` đã quét** (không chỉ trên nhóm sống sót).
   - Ứng viên giữ lệnh dài ngày hoặc ăn Carry dương phải qua thêm **Matched-Hold Timing Permutation Null** để tách alpha thời điểm vào lệnh khỏi drift/carry chung (bài học Pass 20: `DON20_POS` trượt timing null `p = 0,14–0,97` và `0/12` ô 2D).
8. **Outlier/Crisis Stress & Mặt phẳng 2D kép trước khi thăng hạng động cơ (từ Pass 22):**
   - Trước khi thăng hạng động cơ vào danh mục cốt lõi hoặc xuất `.mq5`, phải qua: (a) **Outlier Stress** — vẫn dương ròng sau khi bỏ Top-3/Top-5 lệnh thắng lớn nhất và loại đồng thời các giai đoạn sốc cực đoan liên quan (như COVID 03/2020, UK Gilt 09–10/2022); (b) **Mặt phẳng 2D kép** — kiểm cả lưới cốt lõi (`trigger × SL`) lẫn lưới bộ lọc phụ (`trigger × filter`), ghi nhận trung thực vùng nhạy nếu có thay vì ẩn sau một lưới đẹp.
9. **Kiểm định tích lũy trước Holdout — Cumulative DSR & Tail Correlation (từ Pass 28 / Pre-Holdout Audit):**
   - Trước khi mở khóa Holdout (`>= 2025-01-01`), bắt buộc đo **Deflated Sharpe Ratio (DSR / PSR)** theo tổng ngân sách thử nghiệm tích lũy toàn chiến dịch (`M = 1, 40, 250, 600`) và **Worst-5% Tail Correlation** giữa các động cơ trên những ngày lỗ sâu nhất của danh mục (via `quant_factory.eval_pipeline`), kèm kiểm tra xu hướng suy giảm theo từng năm (`2018 → 2024`).
10. **Ràng buộc vận hành Prop Payout & MT5 Backtest-to-Live Parity (từ Pre-Holdout Audit):**
   - Với danh mục nhiều động cơ trên cùng một mã (như `US100` E4+E5, `USDJPY` E1+E2+E7), phải đo tác động của **Per-Symbol Concurrent Risk Cap** (`<= 1,00%–1,25%` mỗi mã) để phòng luật gộp *"trade idea bundle"* khi FTMO/The5ers duyệt payout, đồng thời kiểm **khóa tin đỏ `±5 phút` chính thức (`224` sự kiện FOMC/CPI/NFP)**.
   - Mọi bản EA đưa lên Demo/Live phải thừa kế/khớp hợp đồng an toàn của `Naqex_PropGuard.mqh`: tự nhận `ORDER_FILLING_*`, sizing theo `SYMBOL_TRADE_TICK_VALUE_LOSS`, xử lý lệch `TimeGMT()` trong Strategy Tester, tự đóng trước giờ đóng sớm ngày lễ Mỹ (`SymbolInfoSessionTrade`), lưu trạng thái qua `GlobalVariable` chống VPS restart, và xác minh `TRADE_RETCODE_DONE`.
11. **Cổng theo Sự kiện/Mẫu thực & Tách Nhánh Song song (Fast-Path không hạ chuẩn an toàn):**
   - Khi đề xuất lộ trình hoặc xét chuyển pha `G5/G6`, tách rạch ròi **ràng buộc bất biến** (niêm phong Holdout, `0` lỗi khớp/SL/swap, không sửa tham số v1 đang chạy live) khỏi **đệm ngày lịch tùy ý**.
   - Ưu tiên định nghĩa cổng theo **sự kiện/mẫu thực tế tối thiểu** (số lệnh đóng sạch qua đủ phiên, rollover và tin đỏ) kèm phương án **micro-canary giới hạn lỗ nhỏ** (khi được hãng chấp thuận bằng văn bản) để rút ngắn thời gian chờ mà vẫn giữ nguyên biên an toàn; không buộc các nhánh độc lập về kỹ thuật (Own-Book, R&D v2 trên Dev, hạ tầng VPS/Cockpit) phải chờ tuần tự cổng forward của nhánh khác.
12. **Kiểm chứng điều khoản gốc & chống bẫy kỳ vọng lệch cho Contest / Promo Prop SKU (từ đợt FTMO/The5ers Black Friday 2026):**
   - Trước khi chạy thử hay gắn EA vào bất kỳ cuộc thi hoặc gói khuyến mãi nào của quỹ, bắt buộc đối chiếu điều khoản gốc hiện hành (`EA allowed`, giới hạn số lệnh mở đồng thời, phân biệt `Standard` vs `Swing`, danh sách tin đỏ hạn chế đầy đủ bao gồm `FOMC Meeting Minutes`, chính sách hoàn phí). Nếu cuộc thi cấm EA hoặc chỉ cho tối đa `1` lệnh mở (như The5ers Trading Contest), chỉ khai thác ở chế độ **quét thông số sàn chỉ đọc (`OrderSend = 0`)**, không gắn bot và không tăng rủi ro kiểu đánh bạc để đua bảng xếp hạng.
   - Không bao giờ chọn gói khuyến mãi phí rẻ nhiều vòng hẹp DD (như Bootcamp `3` vòng `6%` / tĩnh `5%`) chỉ dựa trên `EV/Phí` trung bình: bắt buộc báo đồng thời **trung vị lãi ròng 24 tháng**, **xác suất lỗ `P(net <= 0)`**, **tỷ lệ vượt đủ các vòng** và **trung vị ngày lịch tới lần rút thưởng đầu tiên**.
13. **Thước đo 1 vé, mẫu số trung thực, kiểm biên 2 phía & nhất quán số học kế hoạch (từ Kiểm toán Astra Vòng 1–3, 26/11/2026):**
   - **Tách riêng 1 vé không thử lại (`single-ticket zero-retry`) và đủ mẫu số:** Mọi báo cáo Prop phải kèm đồng thời: ngày chờ không điều kiện trên **mọi vé** (chặn `365d`/`730d`), tỷ lệ hỏng Funded trên **cửa sổ cố định 12 tháng kể từ ngày vào Funded** với mẫu số là *vé đã vào Funded* (công bố số ca bị cắt cụt theo dõi, tách tiền chờ xử lý vs tiền đã nhận, và ghi cảnh báo cần ~`299` quan sát độc lập để chứng minh cận trên `95% < 1%`), số tháng không có payout và chuỗi tháng dài nhất không có tiền về. Bảng mô phỏng vòng đời cấp ngày bắt buộc gắn nhãn **`XẤP XỈ CẤP NGÀY`**.
   - **Kiểm biên 2 phía & tách Bot tự phanh vs Vi phạm quỹ:** Kiểm cả 2 phía của ngưỡng `5%` ngày và `10%` tổng (`+0,01 USD` không vi phạm, `0,00 USD` đúng sàn phân định rõ `<` của quỹ vs `<=` của mô hình, `-0,01 USD` vi phạm, và `gap-through`), kiểm chuyển giờ mùa hè/đông Prague `00:00` và ca đạt mục tiêu khi còn vị thế mở; luôn báo riêng cột `BOT_AUTO_KILL` vs `FIRM_HARD_BREACH`.
   - **Kỷ luật nhãn dữ liệu, xung đột khối & số học mục tiêu:** Bỏ vĩnh viễn chữ `BLIND` sau khi đã xem `Cluster B` để loại/chọn ứng viên, và ghi vết mọi nhánh từng tiếp xúc Holdout trước đó; gắn nhãn `MODEL_ASSUMPTION` cho giả định giá khuyến mãi/giữ bill chưa có cam kết hợp đồng; khóa trước luật đọc `7d` vs `28d` (trái kết luận -> `CHƯA ĐỦ BẰNG CHỨNG`); không đặt mục tiêu mâu thuẫn mẫu số (tách ngày 180 thành `Đậu / Rớt / Còn chờ` tổng `100%`, không nhầm đa dạng hóa `N` nhánh `+r%` là nhân lợi suất không đòn bẩy), và không tạo probe thực địa lệch quy mô stop thực tế của chiến lược.
14. **Phản biện mã nguồn trước thực thi & Mô hình `1 Executor + 1 Independent Raw Verifier` (26/11/2026):**
   - Trước các sprint kiểm định dài giờ, tự đối chiếu mọi phản biện độc lập trực tiếp vào dòng mã nguồn thực tế, sửa kế hoạch đến khi khóa sạch tiêu chí nghiệm thu rồi mới chạy; ưu tiên **`1` Executor + `1` Independent Verifier tái tính toàn bộ bảng trực tiếp từ log gốc** (HTML/XML/CSV/deal logs/`.tkc`/danh sách tệp truy cập) thay vì để nhiều agent cùng đọc chung một file JSON tóm tắt.
   - Khóa mốc dừng cứng: nếu còn sai lệch ảnh hưởng quyết định/lot/equity **hoặc thiếu log xác minh hai bên có khớp không**, dừng phần chấm kinh tế — báo cáo tái hiện sai lệch đầu tiên kèm trạng thái trước/sau là đầu ra hợp lệ; `system_doctor` xanh là kiểm tra sức khỏe phần mềm, không phải chứng nhận có edge; kết quả đạt trên Dev đã xem chỉ cho phép tiếp tục nghiên cứu.

## Cách báo cáo

### Nhãn nguyên nhân dừng và phạm vi bằng chứng

Dùng nhiều nhãn khi các vấn đề cùng tồn tại; nhãn là interpretation có source,
không thay verdict/protocol đã freeze, không automatic rejection/dispatch.
Mỗi nhãn giữ candidate/version, scenario/window, stage, evidence và reason.

| Nhãn | Khi có thể dùng | Không được suy ra |
|---|---|---|
| `ECONOMIC_FAIL` | Net không đạt tiêu chí kinh tế đã đăng ký trong reference/stress, hoặc markout diagnostic yếu trong đúng cohort/horizon | Không bác toàn family; mean trong mẫu không là true expectancy. Gross/markout không tự là account PnL |
| `CADENCE_OR_SAMPLE_SHORTFALL` | Cơ hội/mẫu không đủ cho precision, time-fit hoặc vai trò đang xét; có thể cùng net dương trong mẫu | Không gọi net dương là edge đã chứng minh, không đặt minimum trades chung hoặc ép thêm lệnh |
| `PROP_TIMEFIT_REJECTED` | Exact candidate/model không đạt thời gian mục tiêu đã đo, hoặc owner gác sau review; giữ horizon, risk/cost, censoring và verdict source | Khác vi phạm DD, âm kinh tế hoặc bác toàn family; không suy mọi start/tương lai đều thất bại |
| `DATA_PATH_INCOMPLETE` | Thiếu đường giữ lệnh cho full PnL, hoặc thiếu intraminute path cần cho DD/prop | Phải ghi metric/stage bị thiếu: M1 full net đã đối soát không thành N/A chỉ vì chưa đủ tick DD |
| `PROP_UNMEASURED` | Chưa kiểm đủ rule/profile/path cho claim đang xét; ghi rõ partial checks nếu có | `prop_qualified=false`, null DD hoặc thiếu field không chứng minh đã vi phạm |
| `PROP_VIOLATED` | Có evaluator/model phù hợp profile và witness vi phạm: rule/version, thời điểm, anchor/floor, equity/cost/reset semantics | Không suy từ âm cuối kỳ, endpoint maxDD hoặc flag chưa-qualified. Modeled breach khác actual broker breach |

Tách `economic_result` (positive-in-sample / negative-in-model / unknown),
`edge_status`, `data_scope` và `prop_status`; không ép một primary label che
các blocker khác. Prop measured-within-limits chỉ đúng rules/window/coverage
đã kiểm, không tự pass G3/G5/G6. Có observed breach đủ evidence dù phần path
khác thiếu thì vẫn ghi witness; thiếu coverage cấm kết luận không-breach.
Branch chỉ chứa docs/source setup có scope not-applicable, không gán economic
failure. Technical invalidity vẫn theo G1/correctness, không gọi là alpha âm.

Case adoption: [bảng chuẩn hóa và hồ sơ ứng viên](../../../../planning/research/STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md)
bind saved outputs, giữ unknown và old verdicts. Đây là derived review view,
không taxonomy đã được runner hoặc product API tự enforce.

Mỗi cửa ghi stage applicability, status **đã kiểm trong scope / chưa kiểm /
không đạt / chưa đủ bằng chứng**, locator/version và bước sửa nhỏ nhất. Tool
`strategy_evidence.py inspect` chỉ kiểm artifact invariants/bindings; đọc
`review_checks`, không suy từ exit0/hash match thành preregistration, causality,
OOS, independent review hoặc broker realism. Không biến user labels thành proof.

- Lỗi code/clock/data → invalidate/quarantine run bị ảnh hưởng, sửa và kiểm
  case lỗi rồi rerun phần cần. Không loại luôn ý tưởng hoặc sửa parameters cho đẹp.
- Thay rules sau khi nhìn validation → trial mới; window đã nhìn là consumed,
  không còn final unseen holdout cho bản đó. Giữ negative/abandoned variants.
- Sample/precision/coverage thiếu → inconclusive, không mặc định0 hoặc pass.
- Có material bug hoặc vi phạm xác minh → reject evidence/version liên quan.
- Eligible next-stage review cần bằng chứng cho đúng stage, chưa là authority.

Đừng chọn một con số Sharpe/số trades/p-value làm tem chuẩn chung. PBO/DSR/
resampling cần trial/dependence/distribution assumptions phù hợp; chúng không
sửa được lookahead, dữ liệu sai hoặc chi phí hư cấu. Walk-forward không là bắt
buộc cho mọi fixed strategy; purge/embargo chỉ áp khi cấu trúc samples/labels cần.

## Khi exact run dừng vì thiếu giá

Không mặc định phải khôi phục cả archive trước khi chọn việc tiếp theo. Có thể
đăng ký một sensitivity model riêng để hỏi uncertainty có làm đổi ưu tiên
nghiên cứu không; giữ exact unknown và protocol cũ. Đây không là permission
bỏ gap, tự đóng vị thế hoặc chấp nhận dữ liệu không đạt G1/G2.

- Nêu giả định có thể bác bỏ: ví dụ hidden prices nằm trong same-side H1
  envelope và protective execution theo model không rejection. Kiểm envelope
  chứa observations đã có; điều đó chưa chứng minh không có quote/outlier mất.
- Bao gồm mọi nhánh SL/TP/survival/gap có thể theo giả định, account costs và
  eligibility trên toàn cash interval. Thiếu terminal/source hoặc các nhánh
  làm đổi entry eligibility mà chưa mô hình hóa thì giữ inconclusive.
- H1 có thời gian trước entry không xác định được thời điểm chạm barrier;
  dùng retrospective bound không được đưa tương lai vào entry/size. Outer
  bounds có điều kiện không là confidence interval/xác suất pass đã hiệu chỉnh.
- Khóa tiêu chí trước outcome mới, so unaffected trades với exact baseline
  và kiểm bằng arithmetic/path khác. Kể cả hai đầu bound bằng nhau vẫn ghi
  conditional; không sửa actual-state/unknown/edge/prop verdict thành pass.
  Upper bound âm có thể giảm ưu tiên đúng recipe theo protocol, không bác bỏ
  cả family hoặc chứng minh mất giá đã được khôi phục.

Provenance: [R065 bounds](../../../../planning/research/NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md)
và [R066](../../../../planning/research/NASDAQ-NOISE14-RESULTS-20261109.md) đã có
registered models, full Fraction reviews và retained exact unknowns. Đây là
hai cases cùng agent/provider, không universal fidelity certificate.

## Prop Target Envelope — profile owner ngày 13/11/2026

Áp dụng chiến dịch H1→M15 intraday mới trong workspace, theo
[đề xuất design-from-constraints](../../../../planning/research/PROP-DESIGN-FROM-CONSTRAINTS-PROPOSAL-20261113.md).
Đây là điều kiện thiết kế/suitability của owner, **không phải chuẩn thống kê
phổ quát, luật FTMO, bằng chứng có edge hoặc quyền chạy study**. Freeze profile
trong protocol trước outcome; không áp hồi tố để sửa sealed results. Reference
này chưa được runner tự enforce. Funded và challenge có qualification riêng.

### Đơn vị và chi phí

- `R0` = ngân sách USD/lệnh cố định theo vốn đầu phase (gồm stop-risk và cost/
  gap allowance đã khai báo); netR = netPnL/R0. Ghi thêm `R_price` = lot×contract
  × khoảng cách entry fill tới SL, vì lotrounding khiến hai mẫu số khác nhau.
- `F_stress` = spread drag có benchmark hợp lệ + commission cả vòng + slippage
  cả vòng; không gồm financing. Gross Bid/Ask đã chứa spread thì **không trừ
  spread lần hai** để tính net. Thiếu benchmark/oppositequote → unknown/bounds,
  không0. Phân biệt ex-ante reserve với chi phí realized, không dùng exitquote
  tương lai để lọc entry.

| Điều kiện thiết kế | Gate trong scope này |
|---|---|
| Friction/R0 | Ưu tiên ≤10%; trần kế hoạch stress ≤12%/intent. Vùng10–12% cần ghi rõ trade-off, không nới sau outcome. Báo realized median/p90/tail/vượt cap; không xóa các lệnh phí cao hoặc hứa fill không bao giờ vượt reserve. |
| Overnight shield | Ưu tiên session-bounded, flat trước **rollover/session close đúng account/symbol/date trừ buffer thực thi**. 21:45UTC chỉ hợp lệ nếu calendar chứng minh nó đủ sớm. Không fresh exitquote/không xác nhận flat thì unknown/execution failure, không tự ghi swap0. |
| Nếu cho phép overnight | Khóa maxholding trước; financing debit ≤15% gross-positive-PnL pool của cùng closed cohort, đồng thời net sau mọi phí vẫn dương. Pool=sum(max(gross Bid/Ask trước commission/slip/swap,0)); pool0→N/A. Credits/open financing tách riêng; báo thêm net financing/gross signed, không dùng credit che debit hay mẫu số âm. |
| Cadence | Sàn suitability60 filled trades/năm đầy đủ; ưu tiên120/năm (5–10/tháng). Đếm sau mọi filter/lot/margin/news rules, giữ tháng0 và báo mức đều/tập trung/unique days/dependence. Không quota giao dịch, không chứng nhận statistical power. |
| R-velocity | +25 đến+40 netR0/năm stress là dải tham vọng ban đầu, **chưa đủ** để mặc định đạt challenge6–12tháng; dùng phép tính ngược phía dưới. Mean/R-year không thay distribution, rolling paths/OOS. |
| R-drawdown | Hướng tới cumulative peak-to-trough equityDD ≤15R0, báo static initial loss và daily loss riêng. Cần floating/cost/gap coverage; thiếu path không được pass bằng cashDD. |
| Sizing | 0,30%/0,40% là hai endpoint nghiên cứu có đăng ký, không risk thật hoặc tham số tối ưu. Core alpha dương trước review sizing; không tăng risk để cứu net âm. |

Intraday không tự tương thích100% Standard/Swing: còn news execution, market
breaks, sessions, margin và contract. Không cộng ngược8.950,80USD swap cũ vào
Gold intraday: đóng sớm còn thay chính returns/trades. Source hiện hành phải
kiểm lại khi freeze account profile, không lấy declared legacy rates làm thực.

### Tính ngược thời gian và rủi ro

Với phase targets10% rồi5%, mỗi phase reset vốn và fixed risk `r`, kế hoạch
lý tưởng cần `R_required = 10/r + 5/r` (r dùng cùng đơn vị phần trăm). Đây
chỉ là số học planning, **không time-to-pass dự báo**: chưa overshoot, min-days,
approval gap, đường lỗ/phí mới hoặc censoring. Phí đã ở netR không trừ lại.

| Risk/lệnh | R0 cần phase1 +phase2 | Pace cho12tháng | Pace cho6tháng |
|---|---|---|---|
|0,30%|33,33 +16,67 =50R0|50R0/năm|100R0/năm|
|0,40%|25 +12,5 =37,5R0|37,5R0/năm|75R0/năm|

Do đó25–40R0/năm không bảo đảm6–12tháng. Freeze **12tháng là mục tiêu chính,
6tháng là mục tiêu cao hơn**, rồi đo cả hai; không tăng lot hoặc nới DD khi
arithmetic không đạt. Với N trades/năm, cần kiểm thêm `net expectancy R0/trade
× N` so pace, không chỉ gross USD/lot. `R-Calmar = annual netR0 / maxR-DD`
là tỷ số báo riêng; annualR0 tự nó không phải Calmar.

Tại0,40%,15R0 =6,0%, **không phải <6,0%**. Nếu profile yêu cầu strict<6% thì
R-DD phải<15R0, còn allowance/gap cần buffer. DD≤15R0 không bảo đảm daily<2,5%:
phải đo riêng worstday<6,25R0 ở0,40% hoặc<8,33R0 ở0,30%, dưới cùng cash/reset
semantics. Giữ hard internal daily<2,5%, staticloss<6,5%; strict6% là mục tiêu
thiết kế chặt hơn, không đổi định nghĩa peakDD thành staticloss sau outcome.

Với payout: cần net edge, survival, reconciliation, eligibility/withdrawal và
dòng tiền sau owner costs riêng. Không áp target15% cho mỗi chu kỳ funded,
không gọi model-pass hoặc R-velocity là thu nhập chắc chắn. G0–G6 giữ nguyên.
