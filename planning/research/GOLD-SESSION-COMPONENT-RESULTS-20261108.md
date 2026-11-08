# Hai phiên vàng chưa vượt được phí giao dịch

Đã hoàn tất [protocol](GOLD-SESSION-COMPONENT-PROTOCOL-20261108.md), commit
`af3afff` trước số thật, implementation `c5efeba`. **Không giữ R054/R055 exact
versions để viết risk wrapper.** Goal tìm ứng viên vẫn active. Không chọn
opposite controls làm winner, sửa giờ hoặc giảm spread sau khi thấy kết quả.

## Kết quả dễ đọc

Đơn vị dưới đây là tổng USD của các cơ hội **mỗi cơ hội 1 ounce vàng**, không
phải lãi/lỗ tài khoản 10k, 0,25% risk hoặc khoản được phép giao dịch thật.
Giá nguồn là Bid M1 Open; Ask/spread/slippage là kịch bản khai báo, chưa là
historical/current FTMO/The5ers. Không có SL/account equity/prop hay clean OOS.

| Giả thuyết primary, 2010–2024 | Số ngày đủ giá / toàn weekdays | Net phí chuẩn | Net phí cao | Năm dương, chuẩn/cao |
|---|---:|---:|---:|---:|
| R054: mua 00–08 UTC | 3.755 / 3.913 | −1.976,17 | −4.604,73 | 3/15; 0/15 |
| R055: bán 10:30–15:00 London | 3.871 / 3.913 | −1.967,33 | −4.677,05 | 1/15; 0/15 |

Cả năm block 3 năm đều âm ở stress cho cả hai. R054 còn chỉ149/261 ngày
đủ endpoint trong 2010, không đạt coverage≥200/năm đã khóa. Giữ158/42 ngày
unresolved, không fill giá gần nhất hoặc coi là giao dịch lãi/lỗ0. Không xác
định mọi missing là ngày nghỉ sàn hay lỗi feed; kết luận chỉ áp resolved mask.

Giá đi thuận theo primary trước mọi spread/phí có tổng xấp xỉ840,13 USD cho
R054 và935,93 USD cho R055; không phải bản zero-cost đã được đề xuất. Với
phí chuẩn, spread+commission+slippage là0,75 USD/cơ hội, lớn hơn giá đi thuận
trung bình khoảng0,224/0,242 USD. Đây là chẩn đoán trên mask đã thấy, không
bảo đảm giảm được costs thực tế hoặc dùng làm threshold chọn giờ mới.

Funding0 ở đây do windows không đi qua22UTC rollover đã khai báo, không phải
xóa phí của lệnh giữ qua đêm. Không sửa giả định của các monthly books âm.
Literature khác sample/định nghĩa; kết quả không bác bỏ mọi session strategy,
hoặc mọi broker/spread/holding. Nguồn và thông tin mâu thuẫn được giữ ở protocol.

## Đã kiểm và tối ưu trong phạm vi nào?

| Lát | Bằng chứng / kết quả |
|---|---|
| Fixture trước numeric |3 tests đạt: DST/weekdays/holdout, exact endpoint/Ask, tính tay hai sides/cost/missing census |
| Nguồn |Hash toàn5.399.878 rows đúng; sparse selected Open, order/bounds/census;275 missing endpoint targets giữ explicit |
| Code đối chiếu riêng |CSV reader khác kiểm15.377 selected Open/sequence; calendar arithmetic kiểm7.826 schedule rows |
| Tiền và quyết định |Fraction kiểm30.504 event×scenario outcomes,120 annual summaries, counts/blocks/retention |
| Mutations |5 reject: sai source price, sai net, bịa Ask, false authority, mất source row |
| Giới hạn review |Cùng agent/provider, khác implementation; không independent human/feed hoặc actual broker/tick/SL validation |

Numeric có7.826 planned rows,7.626 resolved,2candidates×2views×2costs; các
costs/views không nhân thành independent edges. Endpoint completeness chưa
chứng minh đường giá giữa giờ hoặc một bot giữ lệnh an toàn.

| Thời gian thực đo | Giây |
|---|---:|
| Source hash + sparse endpoint scan |4,876|
| Tính economics + summary |0,882|
| Toàn numeric, gồm ghi artifacts |7,408 wall /7,250 CPU|
| Separate source/clock/Fraction review |16,062|

Review đọc toàn raw bằng CSV reader chậm hơn sparse scan nhưng chỉ mất16s;
chưa cần GPU/Rust/framework. Kho nguồn và observations tách khỏi calculations,
không thêm database/RAG/service hoặc duplicate dashboard. Đợt này không lỗi
numeric/retry; cả numeric PID26376 và review session79656 đã terminal0.
0network/model/broker calls trong numeric/review, không đọc2025+.

Private `execution-v1/gold-session-component-v1` dưới campaign root giữ
config/manifest/source snapshots/schedule/source-observations/rows/summary/
result/events/progress/review. Runner/reviewer ở campaign root.
ResultSHA `89c23ffbcc2887ae55713d177632e33b9f289b05d0652fdc86acb850964d7710`;
reviewerSHA `b6c33a18beb5c9b4b7fae0807c412bdd45fe13da5efdc76091c7a5a37339abd1`.

## Quyết định tiếp theo

Ghi hai hồ sơ mới vào catalogue như price components, không tăng41 account
policy versions. Source/cost checks có bằng chứng nhưng edge/prop/forward/
authority chưa đạt. Không cần thêm skill: workflow nghiên cứu/kiểm định/hậu
kiểm hiện có đã bao phủ; chưa có bài học mới đòi thêm instruction.

Ưu tiên xem độ bền dài hạn của **PreECB price component với clock/side/cost
giữ nguyên**, trước khi cân nhắc cách thoát/risk mới. [Attribution](PRE-ECB-WRAPPER-ATTRIBUTION-RESULTS-20261108.md)
và [path risk](PRE-ECB-PATH-RISK-RESULTS-20261108.md) chỉ xác nhận2019/2022:
phần giá dương trong scope đó, stop hiện tại làm giảm kết quả, nhưng bỏ SL
không an toàn. Mở rộng years là exposed robustness, không OOS hoặc permission
đổi stop. Chốt windows/cost/coverage/retention trước số mới, giữ parent parked.
