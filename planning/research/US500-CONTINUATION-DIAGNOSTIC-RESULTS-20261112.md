# Vì sao hai bộ phá kênh còn yếu?

12/11/2026. **Đã hoàn tất chẩn đoán: chưa thấy đà đi tiếp đủ mạnh và ổn định
để bù chi phí ở hai recipe đang xét. Chưa có căn cứ sửa cách thoát là sẽ cứu
được chúng.** Giảm ưu tiên đúng hai recipe hiện tại; không bác bỏ mọi chiến
lược continuation hoặc tuyên bố không thể có edge trên US500.

[Protocol](US500-CONTINUATION-DIAGNOSTIC-PROTOCOL-20261112.md) commit `99962a0`
trước numeric. BR01-common14/RS02, 2022–2025 đã dùng; kênh20/ATR14/buffer.10
giữ nguyên. Không mở 2026, đổi tham số, chạy native strategy mới hoặc broker.

## 1. Giá có đi tiếp sau entry không?

Giữ entry của 624 BR01 và 331 RS02; đo tại15/30/60phút sau entryopen, **không
áp stop hoặc timeexit**. Hai recipe chung nhiều ngày, ba horizon overlap;
không coi 955 entries hoặc 2.865 rows là samples độc lập.

R trong bảng là **khoảng giá 2×decisionATR**, không USD hoặc return tài khoản.
Move trước phí dùng synthetic midpoint của hai M1sideopens, không observed
synchronousmidtick. Reference/stress = BidAskspread + extra slip.25/.75point
mỗi fill, commission0 declared scenario. Tất cả means chỉ ở windows đủ M1.

| Recipe | Sau entry | Đủ M1 / thiếu / ngoài phiên | Giá trước phí (R) | Sau phí chuẩn (R) | Sau phí cao (R) | Hơn/kém đối chứng sau phí cao (R) |
|---|---:|---:|---:|---:|---:|---:|
| Vào sau phá BR01 |15phút|623 /1 /0|+0,0035|−0,0455|−0,0950|+0,0043|
| BR01 |30phút|622 /2 /0|−0,0114|−0,0604|−0,1099|−0,0109|
| BR01 |60phút|619 /5 /0|−0,0210|−0,0700|−0,1195|−0,0203|
| Chờ hồi RS02 |15phút|330 /1 /0|−0,0123|−0,0598|−0,1079|−0,0094|
| RS02 |30phút|329 /2 /0|−0,0333|−0,0808|−0,1291|−0,0317|
| RS02 |60phút|326 /3 /2|−0,0476|−0,0953|−0,1437|−0,0449|

Ở BR01,15phút gần0 trước phí;30/60phút âm trung bình. RS02 gộp4năm âm trước
phí cả3mốc. Chi phí làm yếu thêm; đây không chỉ là một đường giá có lợi thế
rõ rồi mất sạch vì fees. Tuy nhiên, kết luận là descriptive trong cohort/mô
hình này, không statistical proof toàn family hoặc một exit bất kỳ đều thất bại.
Không ngoại suy60phút ra mọi thời gian giữ: native knownsubsets2022 dương
ở study trước vẫn giữ, vì đường giá sau60phút/stop/timeexit có thể khác markout.

Mỗi năm/recipe/horizon đều giữ riêng: **24/24 annual cells có mean âm ở phí
cao**. Không chọn mốc/year đẹp rồi gọi validation mới. Missing14windows và
2windows vượt cashsession giữ riêng; không zero-fill hoặc kéo endpoint sang phiên
sau. Tổng2.849known/2.865rows, source gaps/trade unknown cũ không được phục hồi.

## 2. Đối chứng có công bằng hơn nhìn mỗi tổng PnL không?

18.194closedM15nonbreakbars: close nằm trong priorchannel±.10ATR, đủ history,
normalcashsession, không gap đã biết. Từng event so mean ở cùng năm/slotNY/
hướng BUYSELL trên **ngày khác**, bỏ eventday khỏi pool. Không dùng tương lai
sẽ lãi/lỗ hoặc cả ngày không có breakout để chọn control. Đã dựng lại controls
bằng M15 aggregation/ATR khác implementation, census từng năm khớp toàn bộ.

BR01 chỉ hơn control rất nhỏ ở15phút khi gộp, kém ở30/60. RS02 kém cả3mốc
khi gộp. Đối chứng không matching hết volatility/news/regime; R của control
dùng ATR tại controlbar, RS02 dùng ATR đã freeze khi phá. Không causalproof,
không một strategy có thể biết poolmean tương lai, không probability pass.

## 3. Có phải đang có lời rồi giữ quá lâu thành lỗ?

Trên native books phí cao đã có, kiểm **các M1bars kết thúc trước phút exit**
và actualexitfill, không lấy high/low phút stop nếu có thể xảy ra sau khi stop.
Giữ lệnh heldgapunknown; đây là side-price envelope của M1, không tickexact MFE.
0,5R ở bảng này dùng plannedrisk/quantity của actualtrade, khác R2ATR ở markout.

| Recipe | Known losers | Ghi nhận từng thuận≥0,5R rồi đóng lỗ | Tỷ lệ trong known losers |
|---|---:|---:|---:|
| BR01 phí cao |344|68|19,77%|
| RS02 phí cao |190|22|11,58%|

Có nhóm đó đáng ghi nhận, nhưng tỷ lệ không chứng minh đặt TP0,5R sẽ cứu được
strategy. TP mới có thể cắt cả winner, đổi trade path/cash; extrema nhìn lại
không phải fill tại TP. Các cờ false cũng không chứng minh chưa từng thuận
trong phần phút exit bị bỏ hoặc tick chưa biết. Không kết luận phần còn lại
là “% lỗi tín hiệu”, không cộng tỷ lệ exit/fill/cost thành pie nhân quả.

## 4. Nhìn riêng gần đây, có bỏ sót điều gì không?

2025 RS02/60phút có move+0,0489R trước phí, reference+0,0061R nhưng
stress−0,0363R trên92windows đủ M1. Đây là dấu hiệu **mỏng, có điều kiện**,
không candidate challenge hoặc lý do tự promote exit60phút. 2024 cùng cell
reference−0,0111R, stress−0,0678R; không được suy gần đây luôn có lời.

Đã lưu retrospective analytic costheadroom cho **đủ24cells** để tránh chỉ
báo một cell đẹp. 2025RS02/60 break-even fixed extra adverse slip khoảng
0,322point/fill nếu mean theoR; nhưng mean theo1unit cố định thì đã âm sau
spread ngay cả chưa extra slip. Sizing/normalization làm khác trọng số của
các phiên biến động; không được tráo hai phép tính hoặc gọi một trong chúng
là actual strategy return. Đây là fixed-path revaluation, không native rerun
SL/size với costs khác, không measuredFTMOfee. Không cần mua data/provider mới
hoặc bỏ stress để làm đẹp cell này.

## Quyết định và bước tiếp

**Park việc tối ưu ATR/kênh/cách thoát của hai exact recipes hiện tại.** Chưa
thấy cơ sở đủ mạnh để quét tham số. Giữ năm2025/RS02/60 như ghi chú research,
không winner/OOS/authority. Muốn quay lại cần mechanism/cost/execution evidence
mới cụ thể và protocol riêng, không kể lại negative thành clean trial.

Ở lane continuation, bước tiếp nên là chọn **một giả thuyết có cơ chế khác
rõ hơn**, rà catalogue/negative trước; chốt điều kiện quan sát được tại entry
và feasibility dữ liệu trước financial batch. Không chọn thay sàn/market/timeframe,
tăngrisk hoặc mở reversion trong lượt này. Chưa dispatch study mới từ report.

## Kiểm chứng, lỗi, hiệu năng và locator

- 7focused tests: BUYSELL/costbridge, flat-price costloss, fullpath/prefixgap,
  outside-session, exclude-currentday controls, unknowns, cutoff exitminute,
  control priorhistory/future-prefix invariance và invalidinputs.
- Production pass: 37,041s wall/31,781sCPU; source+prepare27,132s,
  controlmarkouts5,582s, event/pathreview2,691s; persistence/final checks phần còn lại.
- Separate review: 45,627s, dựng M15/ATR/control từ M1 không nativeprepare,
  kiểm2.865eventrows/18.194controlbars,1.892known nativepath records; Fraction
  exactpoint bridges, Rnormalization sai khác tuyệt đối<1e−22 do Decimal28.
  Không áp tolerance này cho rawprice/source, không gọi sameagent là independentperson/feed.
- Reviewerattempt1 lỗi khi convert tổng Fraction có denominator rất dài thành
  string, chạm Python digit-limit. Giữ script/log lỗi; sửa so Fraction trực tiếp
  và cộng pool một lần, không tăng global limit hoặc chạy lại numerical job.
  Không có con số measuredspeedup cùng workload trước/sau để claim.
- Parentsealedbooks/source/input/protocol pins giữ nguyên; engine/rule không
  đổi. Không datarepair, newstrategyreplay/version hoặc mở2026. Khôngjob nền.
- Sourcepreparation là phase lớn nhất nhưng37s đã đủ cho scope; không mở tối ưu
  GPU/Rust/cache mới khi chưa có nhu cầu thực tế. Existing skills đủ, không tạo skill mới.

Private campaign `execution-v1/us500-continuation-diagnostics-v1/` giữ manifest,
snapshot, progress/events,4annual eventfiles/controlcensus,16pathfiles, result,
`review.json`, initialreviewfailure và `cost-headroom-review.json`. Scriptreview
được copy cạnh đó. Report/index chỉ route; numerical JSON giữ số chưa làm tròn.
