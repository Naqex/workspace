# WTI opening expansion: kiểm nguồn phiên trước khi thiết kế bot

09/11/2026, sau R091 không retained. Catalogue91/58 giữ nguyên: chỉ admission
phương pháp và nguồn, chưa R092/strategy/financial trial mới. R082/R083 event
momentum và R065 NASDAQ first5-direction giữ negatives, không retune.

## Primary paper đã đọc và giới hạn

[Umeå Economic Studies845, Holmberg/Lönnbark/Lundström2012](https://www.usbe.umu.se/digitalAssets/102/102002_ues845.pdf),
[institutional record](https://swopec.hhs.se/umnees/abs/umnees0845.htm),
[journal2013](https://doi.org/10.1016/j.frl.2012.11.001). Đã đọc toàn11trang,
render page5: ngưỡng quanh dailyOpen, không phải nến5phút đầu. Paper dùng
dailyOHLC crudeoil futures1983–2011, ngưỡng ước lượng ex-post, perfectfill,
spread/commission0, khôngSL. Kết quả tập trung giai đoạn biến động cao;
paper thừa nhận transaction costs và ít trades. Không nhận số headline là
expectededge, ngưỡng đã fit toàn mẫu là causal, hoặc stop luôn cải thiện lãi.

Đây là bản workingpaper23/08/2012, không tự đồng nhất bytes với journal.
Hai oldURL qua webreader timeout; urllibSSLverifyfail được giữ, không bypass.
PowerShell `Invoke-WebRequest` tới university HTTPS với normal certificate
validation thành công,237.045bytes/11pages/SHA
`3bbf81e2f9bfb11f1e2622077b3c064ffc541e697fa57729ba55767b375cbeee`.
Private `execution-v1/wti-orb-method-source-v1/` giữ PDF/text/render/failure;
personal reference, không redistribute paper/code/data trong Git.

## Quyết định của project trước economics

| Câu hỏi | Hành động |
|---|---|
| Có khác exact recipes đã gác? | Có: own hypothesis expansion khỏi sessionOpen của WTI, không EIA reaction hoặc first5 candle-direction; vẫn cùng broadmomentum family, chưa independentedge |
| Có chạy lại theo dailyHigh/Low rồi cho fill tại ngưỡng? | Không. Chưa biết first-side/actual overshoot từ dailyOHLC; cần causal source/timing trước, không tạo fills giả |
| Có chọn long-only Gold từ cohort đã thấy? | Chưa có nguồn mới đủ mạnh cho exact implementation; giữ Gold verdict/time-fit/cost gaps, không lấy subgroup dương làm OOS |
| Có cần full market history ngay? | Chưa. Kiểm session-open/close và sampledM5 trên6sessions; sourcecapacity trước calibration/threshold/entry/risk protocol |

Một adaptation sau này phải đăng ký train-only/rolling threshold, chỉ dùng
completedpast sessions; normal-tail cutoff nếu dùng chỉ là feature heuristic,
không thống kê chứng nhận. Quyết định chỉ từ prefix, entry sau known-at và
fees đầy đủ, missing/post-signal paths giữ rõ. Không chọn q/holding/SL từ PnL.
Pricecomponent nếu tốt mới tới account/prop/time-fit/OOS/prospective/handover.

## Session/source mapping cần kiểm

[CME WTI overview](https://www.cmegroup.com/education/courses/event-contracts-underlying-markets/wti-overview)
ghi Globex17–16Chicago, tương ứng18–17NewYork. [Dukascopy trading-session guide](https://wiki.dukascopy.com/en/manuals/jforex4-desktop/trading-sessions)
ghi LIGHT.CMD18–17NY, có disclaimer general/outdated. Metadata hiện hành không
chứng minh historicalquote có đúng openingminute hoặc giờ riêng của quỹ.
Calendar2019/2022/Sunday/Monday/DST/holiday vẫn phải kiểm nguồn thực.

Chọn [source fixture](WTI-SESSION-SOURCE-PROTOCOL-20261109.md) để hỏi nguồn
đã có có giữ được own18NY→16:55NY reference window không. 16:55 là planned
proxy trước break, không officialsettlement/close auction. Chưa tính returns,
không áp CME1000barrels hoặc Dukascopy100barrels thành contract FTMO/The5ers.
Reuse installednative1.51.1/helpers, không newprovider/dependency/account/MCP.
