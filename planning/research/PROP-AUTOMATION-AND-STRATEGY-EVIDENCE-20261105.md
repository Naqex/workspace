# Chiến lược prop và lựa chọn mức tự động hóa

**Ngày đối chiếu nguồn: 05/11/2026, Asia/Saigon.** Bản này lưu hai lượt research
đã đọc nguồn trực tiếp trong phiên; lượt lưu context không chạy lại thí nghiệm
hoặc kiểm broker. `DOCUMENTATION-ONLY`: nguồn đã đọc không đồng nghĩa hiệu quả
chiến lược đã được kiểm chứng. Nguồn/scope và điều kiện refresh bên dưới.

Scope/acceptance thuộc [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md);
protocol thuộc [round 1](PROP-STRATEGY-ROUND1-20261105.md); kết quả thực thi thuộc
[receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md). Bản này giữ lập
luận và bằng chứng tham khảo, không là một ledger hoặc risk grant mới.

## Câu hỏi và mục tiêu của owner

- Người tìm vốn prop dùng chiến lược gì, có kết quả công khai đáng tin không?
- Nên trade tay, bán tự động hay tự động giao dịch?
- Ưu tiên tiếp cận/giữ quy mô prop, kiểm soát rủi ro và tổng phí thử lại;
  không lấy tốc độ pass challenge làm mục tiêu duy nhất.
- Tập trung FTMO CFD 2-Step Swing trước và The5ers High Stakes đối chiếu.
  Owner cho biết máy có thể chạy liên tục; chưa giới hạn holding period,
  phản ứng trước drawdown/chuỗi lỗ cần quan sát trong demo. Không suy ra owner
  trực máy 24/7 hoặc đã có lợi thế chọn tín hiệu thủ công.

## Kết luận và trạng thái quyết định

| Kết luận | Trạng thái / giới hạn |
|---|---|
| Có trader prop dùng EA breakout và trend continuation sau pullback [S1] | Trường hợp công khai do quỹ phỏng vấn, không phải nghiên cứu đại diện |
| Price action/order flow/liquidity xuất hiện trong phỏng vấn [S2] | Chưa chứng minh tự động; không suy từ thành tích trade tay sang bot |
| Chưa tìm thấy so sánh công khai đủ mạnh xếp hạng chiến lược auto hoặc tỷ lệ thành công semi-auto vs auto tại hai quỹ | Giới hạn của khảo sát này, không khẳng định không có nghiên cứu ở đâu khác |
| Khảo sát có chọn lọc quy tắc sẵn có rồi tự tái hiện/kiểm chứng | Khuyến nghị; chưa chứng minh candidate nào có edge |
| Ưu tiên auto vào/ra và risk theo quy tắc, có owner giám sát | Khuyến nghị ban đầu; owner sau đó giao thực thi đề xuất research05/11: nhận làm hướng triển khai offline, chưa là grant broker/qualification |
| Dùng semi-auto nếu kỹ năng chọn/bỏ tín hiệu thêm giá trị được đo, hoặc để kiểm triển khai ban đầu | Không mặc định duyệt từng lệnh an toàn hơn; không bắt buộc một giai đoạn kéo dài |

Ba mẫu Donchian/SMA/z-score của round 1 là baseline/comparator kiểm được,
không phải chiến lược prop tốt nhất được tuyển từ thống kê. Ưu tiên khảo sát
pullback-trend và session breakout là hướng tìm hiểu, chưa thay shortlist,
tham số, split, trial count hoặc protocol đã freeze. Không tự chạy thí nghiệm mới.

## Phân biệt mức tự động và vai trò AI

| Cách vận hành | Người quyết định | Phần máy làm |
|---|---|---|
| Trade tay có công cụ | Từng entry/exit | Tính lot/cảnh báo/hỗ trợ đặt lệnh |
| Semi-auto duyệt tín hiệu | Nhận/bỏ từng setup | Tìm tín hiệu và thực thi sau duyệt |
| Semi-auto chọn hướng/phiên | Chọn bias, thời gian hoặc strategy bật | Entry/exit trong phạm vi đó |
| Auto giao dịch có giám sát | Chiến lược, risk budget, triển khai/dừng/sửa bản mới | Entry/exit/risk thông thường theo quy tắc đã kiểm |
| Bỏ mặc hệ thống | Hầu như không quản lý | Không được đề xuất; automation vẫn cần vận hành |

Auto có lợi về tính nhất quán, tái hiện và khả năng mở rộng; tăng yêu cầu xử lý
lỗi dữ liệu, kết nối, trùng lệnh và khôi phục. Semi-auto có thể bổ sung bối cảnh
từ người có kỹ năng; đổi lại là phụ thuộc thời gian, độ trễ và bias khi chọn/bỏ.
Máy chạy liên tục không chứng minh người chọn tín hiệu tốt hơn. Bot quy tắc
không cần LLM cho từng lệnh; nghiên cứu/giải thích của AI khác authority gửi lệnh.

## Bằng chứng và nguồn đã đọc

Các claim dưới đây được paraphrase; không lưu toàn văn bài báo. Ngày cập nhật
nguồn khác ngày đọc. Nội dung quỹ/tổ chức có thể có mục đích giới thiệu dịch vụ.

| ID / nguồn | Quan sát được | Không chứng minh |
|---|---|---|
| S1 [The5ers: Christian, 25/06/2020](https://the5ers.com/fit-your-strategies-to-the5ers-goals/) | Hai EA breakout/pullback-trend; bài nói đã vượt đánh giá, ít can thiệp | Thiếu code, full ledger độc lập và bằng chứng phù hợp High Stakes hiện tại; mức risk tác giả không là budget của owner |
| S2 [The5ers: Can, 26/03/2026](https://www.the5ers.com/jp/150k-funded-trader-can-okuyans-journey-to-consistent-profits/) | Phỏng vấn mô tả HTF flow, swing areas và liquidity | Chưa xác lập fully automated hoặc quy tắc tái hiện đầy đủ |
| S3 [FTMO: Big Algo-Trading Test, thí nghiệm bắt đầu 01/04/2018](https://ftmo.com/en/blog/a-big-test-of-algo-trading-does-it-work/) | Báo portfolio 91 hệ thống, 4.081 trade, lỗ $12.530 trên $100.000 sau một năm; max DD17,6% | Không chứng minh mọi algo thua; không phải so sánh đại diện với semi-auto; không dùng đề xuất đảo chiều/lọc hindsight trong bài làm bằng chứng OOS |
| S4 [FTMO strategies/EA FAQ](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/) | Chấp nhận discretionary/algo/EA có điều kiện; cảnh báo allocation với EA bên thứ ba | Được phép không đồng nghĩa được quỹ chứng nhận có lãi |
| S5 [The5ers EA FAQ, 22/07/2026](https://the5ers.com/faqs/can-i-use-an-ea-expert-advisor-can-i-set-a-stealth-mode-stop-loss/) | Yêu cầu source ownership/SL hiển thị và hạn chế một số kiểu EA | FAQ này chưa nêu đủ yêu cầu phê duyệt ở S6 |
| S6 [The5ers Terms §11, 28/10/2026](https://the5ers.com/terms-and-conditions/) | Yêu cầu thông báo và approval bằng văn bản trước dùng automated software; hạn chế phần mềm owned/developed bởi bên thứ ba | Chưa có xác nhận account/bot cụ thể; công cụ semi-auto cũng cần làm rõ phạm vi áp dụng |
| S7 [AQR: Systematic vs Discretionary, 3Q2017](https://www.aqr.com/insights/research/alternative-thinking/systematic-vs-discretionary) | Phân tích không cho rằng một nhóm manager vốn dĩ tốt hơn nhóm kia | Không là thử nghiệm bot prop hoặc tỷ lệ pass; không gọi là dữ liệu năm2026 |
| S8 [Goldman Sachs Asset Management QIS](https://am.gs.com/en-no/advisors/products/public-equity/quantitative-investment-strategies) | Mô tả quy tắc, dữ liệu, human judgement/oversight; trang có snapshot30/06/2026 | Không chứng minh retail bot có cùng hiệu quả hoặc tổ chức bỏ con người khỏi quyết định |
| S9 [FCA algorithmic controls review, 21/08/2025](https://www.fca.org.uk/publications/multi-firm-reviews/algorithmic-trading-controls-high-level-observations) | Khảo sát10 principal trading firms; triển khai có kiểm soát, pilot nhỏ, pre/post-trade controls và ownership | Không là thống kê ngành, yêu cầu trực tiếp cho trader Việt Nam hoặc chứng nhận hạ tầng của mình |

### Cộng đồng: tự thuật, chưa kiểm toán

| Nguồn | Bài học có thể dùng để đặt giả thuyết |
|---|---|
| [Tín hiệu tự động, đặt tay rồi chuyển auto](https://www.reddit.com/r/algotrading/comments/1gcl4w9/using_automated_signals_for_discretionary_trading/) | Một người kể đã duyệt tay nhiều tháng trước khi tin code; duyệt tay bị giới hạn bởi khả năng có mặt |
| [Semi-automated/discretionary bot](https://www.reddit.com/r/algotrading/comments/1qyy1cm/anyone_running_a_semiautomated_discretionary_bot/) | Có người giảm thời gian nhìn chart; người khác cảnh báo bias chuyển sang lúc bật bot; nên lưu lý do override |
| [Manual discretion in algo trading](https://www.reddit.com/r/algotrading/comments/1qh8t9y/manual_discretion_in_algo_trading/) | Một số người tự so sánh rồi nói can thiệp làm kém kết quả; chưa có full ledger để xác minh |
| [EA funded account, có edit thất bại](https://www.reddit.com/r/algotrading/comments/1op7ooq/hi_everyone_i_finally_put_my_mt5_ea_on_a_funded/) | OP kể dùng AI tạo EA, sau đó cập nhật đã cháy account; tiêu đề thành công không đủ chứng minh tồn tại lâu dài |

Không lấy upvote, ảnh payout, danh sách chỉ báo hay testimonial làm xác suất
thành công. Tách pass evaluation → giữ tài khoản → nhiều payout → lãi sau tổng
phí và các lần thất bại. Không ngoại suy futures prop sang Forex CFD/MT5.

## Delta, phần chưa biết và cách tiếp tục

- **Delta tiếp05/11:** owner giao khảo sát công cụ rồi thực thi đề xuất; scope
  [round2](PROP-STRATEGY-ROUND2-20261105.md) giữ hai giả thuyết mới, preparation
  manual journal và hướng auto có giám sát. Khảo sát [tools/MCP](PROP-AGENT-TOOLS-20261105.md)
  ghi owner chưa có TVpaid/The5ers, vì vậy kết nối đó chờ account/permission.
- **Delta05/11:** phát hiện S6 bổ sung yêu cầu mà mô tả EA ở round1 chỉ dựa
  FAQ chưa nêu. Round1 được thêm cross-reference/T7; không sửa protocol tín
  hiệu, hash/outcome hay giả nhận compliance đã đạt.
- Nếu owner muốn kiểm giá trị chọn/bỏ setup: ghi quyết định và lý do trước khi
  biết kết quả, giữ tín hiệu bot làm đối chứng; so net cost, drawdown/breach,
  lệnh bị bỏ, độ trễ và thời gian owner. Mô phỏng đối chứng không là fill broker
  thực tế; cần đủ dữ liệu mới trước kết luận. Chưa được giao chạy so sánh này.
- **Chưa biết:** tỷ lệ thành công đại diện từng cách, edge của owner khi lọc
  tín hiệu, lợi nhuận dài hạn của candidate, approval The5ers cho bot cụ thể,
  và account-specific compliance/costs. Không dùng suy đoán lấp chỗ thiếu.
- **Refresh trước hành động:** đọc lại S4/S5/S6 và đúng program/account terms
  trước promotion/mua/chạy quỹ; giữ văn bản xác nhận nếu có. Mâu thuẫn giữa
  FAQ/terms phải làm rõ với quỹ, không tự chọn nguồn dễ hơn.
- **Refresh khi input thay đổi:** quyền code/license, strategy/version,
  broker/cost/spec, lịch tin, chương trình/cỡ account hoặc khả năng vận hành
  của owner. Kết quả cộng đồng vẫn là tự thuật nếu chưa có bằng chứng mới.
- Lần sau tiếp từ đây và nguồn liên quan; không cần khảo sát lại mọi bài.
  Quyết định/mốc triển khai mới cập nhật đúng PLAN/receipt, không ghi tại đây
  như một run đã hoàn tất hoặc coi yêu cầu lưu context là duyệt auto execution.
