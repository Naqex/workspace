# Gold continuous — B1 amendment v1.1

13/11/2026. Review AR01–03 tại `gold-eurusd-portfolio-stageA-20261113-v1/astra-review.json`
được áp trước kết quả mới. [v1 JSON](GOLD-CONTINUOUS-PORTFOLIO-PROTOCOL-V1-20261113.json)
và Markdown cũ giữ nguyên, không ghi đè hash. [v1.1 JSON](GOLD-CONTINUOUS-B1-AMENDMENT-V1P1-20261113.json)
là contract của B1; private registration giữ timestamp và SHA trước chạy.

| Review | Sửa trước đo |
|---|---|
| AR01 | Seed toàn bộ H4 hợp lệ từ 01/11/2009; không cắt 100 nến, không reseed vào đầu năm/tài khoản. Trước start chỉ cập nhật indicator; không tạo vị thế/pending. |
| AR02 | Tách cash balance/reset anchor khỏi chất lượng giá. Quote cũ không là giá tại reset. Gap và stop-minute không rõ thứ tự giữ unknown dù giá sau đó phục hồi. Không dùng extrema sau thoát làm MAE thực. |
| AR03 | First trade + 14 ngày × 24 giờ là giả định eligibility sớm nhất, sau đó đợi flat/pending0 tự nhiên. Không lịch rút bắt buộc mỗi 14 ngày. Eligible profit, potential reward, approved receivable và received cash là trạng thái riêng. |

Đợt này chỉ chạy 01/01/2010 UTC → 01/04/2010 exclusive, 50k và hai budget
125/200 USD; một lane legacy stress: spread1 USD/oz, commission2,50/lot/side,
slip0,20/oz/side, swap debit40/40/lot/weekday22UTC, Wednesday×3. Đây là
counterfactual đã khai báo, chưa phải phí lịch sử FTMO. Không bỏ Short, đổi SL,
exit, tín hiệu, start hoặc mở giá2025–26. Chưa rolling120cases/portfolio/funded series.

Reuse `ResearchH4Candidate`, `H4Builder`, `MetalStudyMarket`, sizing/stop/cost
helpers, typed position, native money/calendar/lifecycle. Authoritative imports
từ `D:/ANNAM/TradingWorkspace/projects/trader/foundation_v2`, không mutableC:.
Source manifest khóa dependencies và harness; candidate/cost modules trùng frozen
bytes, hai thành phần market cần dùng trùng AST. Snapshot cũ giữ nguyên.

H1 chỉ được đưa vào builder ở mốc đóng danh nghĩa, không dùng phần nến chưa đóng.
H4 intent được fill ở M1 open kế tiếp có dữ liệu; protective gap ưu tiên trước
strategy exit. Stop loss intraminute dùng level model, cash posting cuối phút−1ms;
thứ tự tick thật chưa biết. Không lấy high/low của phút đó làm extrema vị thế.
Commission/slippage hai chiều settle khi đóng; floating liquidation reserve cả
hai chiều. Swap debit bằng tiền tại lịch đã khóa, anchor reset lấy balance trước
phí cùng thời điểm. Margin giữ legacy10:1/fixed50k, chưa là targetbroker margin.

Giới hạn native: event `approximate` chặn pass **và không tiến clock/anchor**.
B1 không giả `full_for_declared_model` để vượt chặn. Native money/calendar
oracles cung cấp cash anchor và witness vi phạm tại điểm có giá trong model;
quality ledger giữ unknown. Actual prefix luôn inconclusive về survival/prop;
synthetic fixtures mới dùng full-quality để kiểm min-days/flat/reset phase2.
Đây là đo thử adapter, chưa là tích hợp challenge lifecycle hoàn chỉnh.

Floating tại M1 open và close proxy tách khỏi conditional held-minute envelope.
Envelope đi high-equity trước low-equity để cho bound bảo thủ, không biết thứ tự
thực. Giữ riêng daily loss, static initial loss và peak-to-trough DD. Profile
legacy dùng `<` tại5%/10%; internal caps strict `<2,5%`/`<6,5%` không thay profile.
Không chứng nhận an toàn từ coverage, không fill/drop gap. Supported breach vẫn
latch dù lịch sử khác unknown; absence of witness không là absence of breach.

900s/case; status/checkpoint/cancel mỗi10.000 source rows. Complete checkpoint
serialization được thử synthetic split/resume, không quảng cáo tự resume CLI.
Giữ failure attempts và output mới; không đổi protocol sau outcome để cứu PnL.
CF01–09 có fixture đúng scope; CF10 hoãn. Fixedprefix chỉ sau fixtures đạt.

Latest owner steering: hoàn thành B1 rồi dừng; **không gửi thêm prompt/message
cho ASTRA**. PR69 giữ mở, không merge. Existing skills đủ; không thêm manager,
skill hoặc sửa source/pin/runtime Trader chỉ để chạy diagnostic.
