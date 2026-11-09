# Discovery4: kết quả và hậu kiểm — 08/11/2026

**Chưa có ứng viên đủ để vào challenge.** Bước kiểm code/tick đã đạt trong
scope; economics đổi rõ giữa Q1/2022 và2023. [Campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md)
vẫn ACTIVE, không dừng ở việc tìm một backtest đẹp.

Giữ8H4rules cũ và thêm8H1recipes frozen ở
[protocol](CHALLENGE-DISCOVERY-ROUND4-20261108.md). Tổng16rules implemented,
không16edge độc lập. Mỗi dòng/cost là tài khoản mô phỏng riêng, initial10.000USD,
planned25USD/lệnh; không cộng các dòng thành portfolio hoặc vốn owner.

## Sàng lọc xấp xỉ trước và qua thời kỳ khác

Các ô là net equity USD gồm floating, **phí chuẩn / phí cao**, từ H1model.
Không có full tick internal risk/prop lifecycle hoặc intrabar DD trong bảng này.

| H1recipe | Q1/2022 | Năm2023 | Năm2024 |
|---|---:|---:|---:|
| RSI14 re-entry |−44,81 / −83,46|−102,78 / −267,89|+59,68 / −252,42|
| Shock reclaim |−72,22 / −74,66|−75,58 / −106,69|+14,28 / −11,59|
| Prior-day breakout |+6,79 / −6,16|+259,76 / +184,82|−650,30 / −724,84|
| Prior-day fade |−40,15 / −58,18|−169,05 / −246,02|+37,64 / −60,13|
| Bollinger re-entry |+283,74 / +213,84|−449,67 / −737,42|−508,14 / −875,99|
| Pullback20/80 |−2,56 / −111,91|+650,96 / +292,10|−602,70 / −1067,48|
| Europe morning short |−172,74 / −195,04|−125,62 / −280,14|−82,51 / −248,89|
| London post-fix long |−154,93 / −175,76|+401,03 / +282,52|+221,75 / +68,22|

Pullback còn1position cuối2023 và2024; RSI còn1position cuối2024.
Không force-close để làm đẹp số. Cả hai periods đã consumed trong project;
recipes frozen trước outcome không biến chúng thành cleanOOS. 2023year screen
đã có [registration](H1-HISTORICAL-SCREEN-2023-20261108.json) trước numerical run.

BB dươngQ1 nhưng âm2023 nên chưa được đưa vào challenge. Giá trị−737USD là
kết quả coarse chưa internal brake500USD; native account có thể dừng trước
đó, không suy đây là một live account path đã verified. Các bản dương2023 cũng
chưa có đủ evidence về edge, risk, time-fit hoặc khả năng pass hai phases.

## Kiểm tick thật: positive, near-zero và negative control

Không gửi lệnh broker. Cả5.837.028observed ticks của quý được xử lý mỗi scenario;
native input/source/accounting/seals đã inspect với source snapshot phù hợp.

| Bản | Native phí chuẩn/cao USD | Lệnh đóng | Coarse trừ native, chuẩn/cao USD |
|---|---:|---:|---:|
| Bollinger re-entry |+283,13 / +213,23|61 /61|+0,61 / +0,61|
| Prior-day breakout |+3,03 / −9,83|38 /38|+3,76 / +3,67|
| RSI14 control |−47,31 / −85,92|39 /39|+2,50 / +2,46|

6/6scenarios khớp decisions/counts/open/pending; independent cash/accounting
đạt,0risk stops/rejections trong những paths này. Sai số modeledstops nằm
trong budget engineering6,25USD đã khóa trước đối chiếu. Budget này không
là statistical threshold hoặc error bound của năm khác. Tick maximum DD chưa
được tính đầy đủ khi không có prop observer; minimum equity/ledger DD không
được đổi tên thành full drawdown.

Ngoài ra8legacy native prefix cases và16legacy coarse quarter cases exact;
16newH1prefix cases khớp counts/decisions, maxdelta0,42USD. Đây là correctness
scope, không16bài OOS hoặc independent alpha validations.

## Vòng hậu kiểm đã thực hiện

| Phát hiện | Sửa/giữ và cách kiểm |
|---|---|
| H1 không được quan sát bằng warmup/clock H4 | Native CLI yêu cầu observed-H1 cache; period/proof vào manifest/reuse trước dispatch. Fixture clock/DST/restore và actual tick cases đạt |
| Tín hiệu chỉ có ý nghĩa nếu timing đúng | Nến đóng mới quyết định, quote sau mới fill. Test H1 không fill theo H4 hoặc samebar; giữ entry/SL/accounting core cũ |
| Cổng coarse ban đầu chỉ có fixedQ1 | Thêm historical registration/source/input/protocol/cost/candidate checks, vẫn reject unknown/2025+/prop-lifecycle before load. Numeric simulate_coarse AST không đổi |
| Input guard lỗi trước try có thể thiếu status | Scope failures hiện giữ failure.json/progress qua atomic writer; negative CLI cases đạt |
| Bản đẹp một quý có thể thua cả năm; gate quý cứng dễ gác ý tưởng vì sampling | [Selection-v2](H1-SELECTION-V2-AND-2024-20261108.md) khóa trước2024outcome: screen cả8, ưu tiên hai annual windows/worst stress; C1qualification không hạ chuẩn |
| Catalogue cũ có thể dẫn agent code lại RSI/BB | JSON cập nhật15implemented records/16rules, giữ versions và link đến outcomes; không coi variants độc lập |

Test evidence:177Forex tests/145subtests ở source791b9a7b,62focused CLI/dossier/
batch checks/22subtests. Sau registered-coarse plumbing:21focused/10subtests;
registry/coarse suite21/17subtests. Không rerun toàn bộ core sau mỗi metadata
registration. Một test DST ban đầu có off-by-one ở expected exit boundary đã
sửa fixture trước outcome; không nới đúng giờ exit của recipe.

## Thời gian và trạng thái tiếp

| Chặng | Actual wall | Giới hạn |
|---|---:|---|
| CachedQ1screen8×2costs |2,39s|Approximation, không tick risk/prop |
| Shared nativeQ1prep |106,875s|Quality warmup10,64s/eval43,609s; tick cache52,25s, không đọc lại cho mỗi worker |
| NativeQ1batch3workers×2costs |Khoảng8,7phút, gồm preparation|0model/broker calls trong job; kiểm positive/near-zero/negative |
| Chuẩn bị H1warmup+2023 |288,679s|Đã chạy chồng với nativeQ1; không cộng chồng thành active-time |
| Cached2023screen8×2costs |9,79s|Không annual tick speedup hoặc prop-time prediction |
| Chuẩn bị H1warmup+2024 |188,80s|Một lần cho cả8rules, không8lần đọc CSV |
| Cached2024screen8×2costs |8,76s|Approximate triage, không đủ nhận edge/DD/prop |
| Research/code/review |Chưa có active timer trọn vẹn|Không lấy Git timestamps làm thời gian xử lý |

2024 đã hoàn tất theo selection-v2; không còn numerical worker. London post-fix
là bản duy nhất dương cả hai năm ở cả hai mức phí, nhưng năm yếu stress chỉ
+68,22USD (0,68% trên10k). Giữ làm hướng nghiên cứu yếu, chưa khuyên trả phí
challenge hoặc tăng risk. Không có C1qualified. Bước tiếp mở một đợt hypothesis
khác có protocol/controls trước outcome; không tối ưu lại tám rules theo bảng
này hoặc dùng2024làm cleanOOS.2025+vẫn đóng tới exact protocol/user gate.

Private root:
`E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1`.
`bounded-comparison.json`, `q1-coarse/`, `q1-native-batch/PROGRESS.md`,
`q1-native-review.json`, `2023-preparation-result.json`, `historical-2023/`
giữ artifacts/pins/results. Source snapshots của từng giai đoạn được giữ trước
metadata-registry changes; không sửa old pins hoặc coi current drift là lỗi
của kết quả lịch sử. AI plan/receipt own state; đây là review có nguồn, không
ledger hoặc UI quản lý task cạnh tranh.
