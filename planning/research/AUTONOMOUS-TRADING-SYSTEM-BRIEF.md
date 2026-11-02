# Hệ thống giao dịch tự chủ — brief hiện hành

Cập nhật: **02/11/2026 (Asia/Saigon)**.
**WORK: DRAFT · REVIEW: DOCUMENTATION-ONLY · DOC: FULL.**
Owner đã giao nghiên cứu kiến trúc/workflow và lưu context; sau đó giao prototype
UI trong Trader để xem trước. Backend/services tiếp sau feedback UI. Brief giữ
mục tiêu, lựa chọn và câu hỏi đang bàn; không là
execution plan, acceptance ledger hoặc hợp đồng cấp quyền giao dịch.

## 1. Mục tiêu và bối cảnh do owner xác nhận

- Mục tiêu dài hạn: tìm kiếm lợi nhuận trên thị trường bằng hệ thống, dùng AI
  để tự động hóa cả nghiên cứu và vận hành giao dịch.
- Trader hiện tại đi theo luồng giao dịch tay tham khảo FXReplay, kết hợp AI chat;
  owner muốn nghiên cứu cách tiến tới hệ thống tự chủ hoàn chỉnh.
- Owner tự đánh giá cảm quan Trader đã hoàn thành khoảng **80% trên nền FXReplay**.
  Đây không phải kết quả audit, phần trăm acceptance toàn sản phẩm hoặc bằng chứng
  sẵn sàng live; các gate hiện hành tiếp tục ở Product Plan/ledger của chúng.
- Ưu tiên nền dài hạn, có thể duy trì và mở rộng. Các lát thực hiện sau này phải
  đóng góp cho kiến trúc đích; tránh làm bản ngắn hạn chỉ để có tính năng.
- **Hướng hiện hành — owner chốt sau khảo sát, 02/11:** ưu tiên nghiên cứu
  **Forex major qua MT5**, lấy **FTMO 2-Step Swing** làm chuẩn mô phỏng cho nguồn
  vốn prop firm. Bắt đầu offline, sau đó free trial khi có bằng chứng và setup
  phù hợp; chưa mua challenge. [Khảo sát và quyết định](PROP-FIRM-FIT-20261102.md).
  Chưa chốt cặp tiền, timeframe, cỡ tài khoản hoặc risk budget cụ thể; lựa chọn
  này không mở quyền kết nối broker, đặt lệnh hoặc chi phí challenge.
- Owner mới ra trường, hiện có 15 triệu đồng. Chưa rõ khoản này có bao gồm quỹ
  sinh hoạt/dự phòng; không tự cấp ngân sách retry. The5ers là phương án thử phí
  thấp để xét sau, chưa là lệnh mua. HyroTrader giữ làm nhánh crypto tham khảo.
- Lịch sử cùng ngày: owner từng đồng ý ưu tiên crypto cho pilot ban đầu.
  Crypto spot và các kết quả đã có tiếp tục làm baseline nghiên cứu; ưu tiên
  triển khai prop ở trên thay hướng thị trường trước đó, không xóa nghiên cứu cũ.
- [Khảo sát thị trường 02/11](AI-MARKET-PRIORITY-20261102.md) đề xuất ưu tiên
  BTC/ETH spot khung ngày cho workflow nghiên cứu đầu tiên, theo data/chi phí
  triển khai và tài sản workspace. Owner đang hỏi rõ spot so với futures;
  khuyến nghị sản phẩm khởi đầu vẫn là spot không vay/không leverage, long/cash.
  Chưa có quyết định mở futures, bằng chứng lợi nhuận hơn Forex hoặc quyền live.
- Nhịp giao dịch **chưa chốt**: owner muốn đề xuất theo tính khả thi. D1/H4 mới
  là khuyến nghị của assistant, chưa là lựa chọn được owner chốt.
- Owner đã chốt bộ nền ban đầu: **Paperclip** quản lý công việc/agents,
  **RD-Agent** nghiên cứu, **TradingAgents** phân tích/phản biện và **LangGraph**
  làm runtime workflow bên trong engine. Chọn fork Paperclip gốc để mở rộng i18n;
  fork tiếng Trung chỉ là reference. Đây là quyết định chọn công nghệ để triển
  khai/thử dùng, chưa là bằng chứng engine phù hợp nhất hoặc acceptance tích hợp.
  Cho phép thay từng engine sau trải nghiệm thực tế; giữ contract và dữ liệu
  do workspace quản lý để giảm chi phí thay thế. UI trước, backend/services sau
  vẫn là thứ tự thực hiện. Chi tiết ở
  [khảo sát và quyết định adoption](PAPERCLIP-LOCALIZATION-INTEGRATION-SURVEY-20261031.md).

## 2. Lựa chọn A/B — ý muốn dài hạn đã chốt

Ở đây A/B chỉ nói về **đưa phiên bản chiến lược mới vào chạy bằng tiền thật**,
không nói về duyệt từng lệnh hoặc quyền tự nâng tổng ngân sách.

| Chế độ | Ai quyết định đưa chiến lược mới vào chạy? |
|---|---|
| **A — Chờ duyệt** | Hệ thống nghiên cứu và trình bằng chứng; owner quyết định |
| **B — Tự quyết có giới hạn** | Hệ thống tự quyết khi đạt tiêu chí và nằm trong phạm vi owner đã cấp |

**Owner thích B làm đích dài hạn và muốn có thể chuyển sang A khi cần.**
Khả năng chuyển chế độ là yêu cầu thiết kế; chi tiết contract chưa được chốt.
Lựa chọn B trong brief không tự cấp quyền broker/live, vốn, tài khoản hoặc deploy.

Đề xuất để tiếp tục thảo luận, chưa là hành vi đã triển khai:

- Dùng chung pipeline nghiên cứu/kiểm chứng; chính sách duyệt quyết định bước
  phát hành chiến lược. Giữ phiên bản chính sách và lịch sử quyết định.
- B → A: các quyết định phát hành mới chờ duyệt. Chuyển chế độ không tự đóng
  vị thế, hủy lệnh đã gửi hoặc dừng chiến lược đang chạy; quyền vận hành hiện có
  và kiểm soát rủi ro tiếp tục áp dụng. Dừng khẩn cấp là thao tác riêng.
- A → B: chỉ tự quyết trong phạm vi đã cấp; phải kiểm lại bằng chứng, dữ liệu
  và hạn mức hiện hành, không tự chạy hàng loạt đề xuất đang chờ.
- Tranh chấp chuyển chế độ/dispatch và xử lý yêu cầu đang thực thi cần được
  đặc tả trước implementation. Không suy rằng thay một công tắc UI là đủ.

### Khởi đầu nghiên cứu và điều kiện dùng tiền — owner đã đồng ý

Phân biệt **phạm vi nghiên cứu** với **quyền phát hành chiến lược dùng tiền thật**;
không dùng cùng nhãn A/B cho hai chiều này trong các phần giải thích tiếp theo.

- AI được tìm cả ý tưởng mới ngoài các trường phái owner đã biết ngay từ đầu;
  owner vẫn có thể giao đề tài cụ thể. Mỗi đợt nghiên cứu giới hạn phạm vi và
  ngân sách, rồi mở rộng theo bằng chứng; chưa chốt con số hoặc thị trường.
- Khởi đầu: có dữ liệu đáng tin → mốc so sánh đơn giản → AI tìm cách cải thiện.
  Mốc so sánh là công cụ đánh giá, không mặc định là chiến lược để dùng tiền thật.
- Giai đoạn đầu chỉ **mô phỏng và tài khoản demo của broker**. Mô phỏng tính kết
  quả trong môi trường kiểm soát; demo giúp quan sát luồng dữ liệu/lệnh qua broker.
  Kết quả mô phỏng, demo và tiền thật phải ghi riêng, không coi chất lượng khớp
  lệnh demo là bằng chứng tương đương live.
- Owner chỉ muốn dùng tiền thật khi đã có chiến lược tốt. Tiêu chí cụ thể cho
  chữ "tốt" còn cần thống nhất; kết quả backtest đẹp riêng lẻ chưa đủ để kết luận.
- Bước tiền thật ban đầu chờ owner duyệt sau khi có bằng chứng. Đích dài hạn vẫn
  là tự quyết trong phạm vi được cấp và chuyển được về chờ duyệt khi cần.
- Đây là quyết định về lộ trình/thiết kế. Chưa chạy mô phỏng/demo, kết nối tài
  khoản, đặt lệnh hoặc cấp quyền live trong cuộc trao đổi này; các thao tác đó
  cần scope và quyền thực thi tương ứng khi triển khai.

## 3. Khung kiến trúc để nghiên cứu tiếp

Giả thuyết → kiểm chứng → phiên bản được phép chạy → vận hành → giám sát → cải tiến.

- Vòng nghiên cứu: AI đề xuất, viết code/tạo mô hình trong môi trường cô lập,
  chạy thí nghiệm và học từ cả kết quả đạt lẫn thất bại.
- Vòng vận hành: chạy chiến lược được phép, kiểm soát danh mục/rủi ro,
  thực thi và đối soát trạng thái broker/exchange.
- Trader là ứng viên giao diện điều hành; Quant Lab và TradingAgents có tài sản
  để reuse. Đây là hướng nghiên cứu, chưa chốt module/engine hoặc bằng chứng tích hợp.
- AI, ML và bot có thể cùng tham gia. Số agents hoặc độ phức tạp không chứng minh
  lợi thế giao dịch; cần so baseline, chi phí và kết quả ngoài mẫu/forward.

### Workflow kiểm chứng và lỗi phổ biến — yêu cầu bổ sung của owner

Owner yêu cầu hệ thống có phương án cho overfitting, underfitting và các lỗi
phổ biến; hiện ưu tiên chốt workflow hợp lý, chưa tối ưu chi tiết hoặc triển khai.
Kiểm chứng độ đúng cần nằm trong workflow từ đầu và lặp theo từng phiên bản;
tối ưu hiệu quả/hiệu năng chuyên sâu có thể làm sau. Chưa có bước kiểm nào được
coi là đã triển khai/đạt chỉ từ việc ghi brief.

Luồng đề xuất: **kiểm tra data → tạo/huấn luyện ứng viên → kiểm chứng độc lập
→ mô phỏng theo thời gian thực/demo → xét quyền tiền thật → giám sát**.
Kết quả không đạt quay về sửa giả thuyết/data/code hoặc loại ứng viên, không
bắt buộc tối ưu tới khi có báo cáo lợi nhuận đẹp. Việc giám sát áp dụng cả demo.

| Nhóm lỗi | Yêu cầu cần cụ thể hóa sau khi chốt workflow |
|---|---|
| Overfitting | So kết quả train/validation theo thời gian, độ nhạy tham số và ngoài mẫu; ghi mọi lần thử, giới hạn vòng tối ưu và giữ test cuối ngoài quyền chỉnh chiến lược |
| Underfitting | Chẩn đoán mô hình không học đủ quan hệ bằng kết quả train/validation và baseline; kiểm tra feature/data/mức ràng buộc. Hiệu quả giao dịch kém không tự chứng minh underfitting hoặc buộc tăng độ phức tạp; có thể chưa tìm thấy edge |
| Data leakage/look-ahead | Tách dữ liệu theo thời gian, thời điểm công bố và thời điểm thực thi; preprocessing chỉ fit trong phần được phép. Validation đã dùng để chọn mô hình không thay thế test cuối độc lập |
| Mẫu sai/lợi nhuận giả | Kiểm data thiếu/sai, số mẫu hữu hiệu, thiên lệch chọn tài sản, phí/spread/slippage và khác biệt mô phỏng/demo/live |
| Lỗi vận hành/hiệu quả thay đổi | Theo dõi freshness, lỗi/trùng lệnh, đối soát vị thế và hiệu quả theo thời gian; có xử lý dừng/quay về review theo policy được cấp |

Giữ version, data cutoff, config và kết quả thất bại để điều tra/tái lập.
Không mở hoặc dùng lại holdout để sửa chiến lược khi chưa có policy tương ứng.
Ngưỡng, phương pháp thống kê và bộ kiểm chi tiết còn mở; không có phép kiểm
đơn lẻ nào bảo đảm loại hết sai lệch hoặc bảo đảm lợi nhuận tương lai.

Tham chiếu đối chiếu ngày31/10:
[scikit-learn: validation/learning curves](https://scikit-learn.org/stable/modules/learning_curve.html),
[Freqtrade: lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/).
Đây là nguồn kỹ thuật cho thiết kế kiểm chứng, không phải quyết định thêm dependency.

### Nhóm AI nghiên cứu — đề xuất vai trò và đầu ra

Phần 4 của trao đổi đã giới thiệu ba trách nhiệm: nhóm AI nghiên cứu, bộ kiểm
chứng và bộ vận hành; Trader là ứng viên giao diện điều hành. Tách trách nhiệm
không có nghĩa phải tạo ba service hoặc thêm ba framework.

Phần 5 đi riêng vào nhóm nghiên cứu. Thiết kế đề xuất:

| Vai trò | Việc làm | Đầu ra |
|---|---|---|
| Người đề xuất | Đọc dữ liệu/tài liệu được phép, đặt giả thuyết có thể kiểm tra | Giả thuyết, lý do, data cần dùng và kế hoạch thử |
| Người triển khai | Chuyển giả thuyết thành code/feature/model trong môi trường cô lập | Ứng viên có phiên bản, cấu hình và đầu vào xác định |
| Người phản biện | Đọc bằng chứng gốc, tìm lỗi và đề xuất giữ/sửa/loại | Nhận xét có nguồn và đề xuất bước tiếp theo |

Bộ kiểm chứng riêng thực hiện phép tính/test và xuất kết quả theo tiêu chí;
nhận xét của AI phản biện không thay metric hoặc tự chứng nhận gate đã đạt.
Một vai trò không mặc định cần một model/agent thường trực; chọn topology sau
khi đánh giá dependency, chất lượng và chi phí. Điều phối có ngân sách/điểm dừng,
bao gồm kết luận chưa có edge; không tối ưu vô hạn hoặc mở test cuối cho mọi vòng.

Hồ sơ thí nghiệm giữ giả thuyết, phiên bản code/model/config, data cutoff,
metrics/artefacts gốc và kết quả thất bại để nối các vòng nghiên cứu qua restart.
Đầu ra bàn giao là ứng viên và hồ sơ kiểm chứng; quyền chạy demo/live nằm ở
policy/service tương ứng, không nằm trong lời kết luận của agent.

Reference đối chiếu ngày31/10: [RD-Agent(Q) paper](https://arxiv.org/abs/2505.15155)
mô tả vòng Research → Development → feedback từ thí nghiệm; [upstream](https://github.com/microsoft/RD-Agent)
là ứng viên khảo sát phần research engine. Ba vai trò ở trên là đề xuất cho
workspace, không phải tuyên bố mapping nguyên xi các agent của upstream.
Chưa chọn/cài/tích hợp RD-Agent; chưa tái lập benchmark hoặc xác minh profitability.

### Bộ kiểm chứng — bàn giao ứng viên và kết luận theo giai đoạn

Phần 6 đề xuất bộ kiểm chứng nhận ứng viên có phiên bản, data reference/cutoff,
phạm vi được phép và cấu hình đánh giá đã chốt trước run (baseline, costs,
splits, tiêu chí/giới hạn). AI không tự đổi tiêu chí để ứng viên của nó được đạt.
Code ứng viên và code evaluator có ownership riêng; evaluator chạy công cụ tính
toán/kiểm tra đáng tin, lưu raw results và nguồn, không chấp nhận lời tự báo PnL
của agent làm bằng chứng. Chi tiết interface và ngưỡng còn cần đặc tả.

Kết quả gồm số liệu, lỗi/cảnh báo, evidence refs và kết luận cho **đúng giai đoạn**:

| Kết luận | Ý nghĩa / bước tiếp |
|---|---|
| Đạt tiêu chí giai đoạn | Đủ điều kiện đề xuất sang bước kế tiếp theo policy; không tự mở demo/live hoặc cấp thêm vốn |
| Không đạt | Có bằng chứng vi phạm tiêu chí; phản biện/sửa hoặc loại ứng viên |
| Chưa đủ bằng chứng | Dữ liệu/mẫu/độ chắc chắn chưa đủ để kết luận; bổ sung trong phạm vi cho phép hoặc giữ chờ |
| Lỗi kiểm chứng | Run lỗi hoặc dữ liệu/artefact không hợp lệ; sửa/reconcile trước khi đánh giá, không coi như kết quả chiến lược |

AI phản biện giải thích và đề xuất, còn kết luận theo tiêu chí do evaluator/policy
có phiên bản xác định. Đạt backtest không đồng nghĩa đã đạt demo/live; quyết định
phát hành tiếp tục theo quyền A/B riêng. Khi kết quả không chắc chắn, giữ trạng
thái chưa đủ bằng chứng thay vì mặc định đạt hoặc ép tối ưu thêm.

### Bộ vận hành — đề xuất phần 7

Sau khi owner tạm dừng UI audit ngày31/10, tiếp phần7: bộ vận hành nhận phiên
bản chiến lược/model/config được phép chạy, dữ liệu mới và phạm vi account/risk.
Luồng đề xuất: data mới → tín hiệu/đề xuất → kiểm tra quyền/rủi ro bằng code
→ thực thi mô phỏng hoặc demo → xác nhận/đối soát → giám sát.

AI/model có thể tạo tín hiệu động hoặc hỗ trợ phân tích; không bắt buộc gọi LLM
cho mỗi tick/nến. Quy tắc quyền, giới hạn, số tiền và vòng đời lệnh do code sở hữu.
Đang chạy bản1 thì bản2 được nghiên cứu riêng; chỉ thay qua policy/kiểm chứng,
không tự sửa logic đang chạy rồi tiếp tục dùng danh nghĩa proof bản1. Khi kết quả
gửi lệnh chưa rõ, đối soát trước, không tự gửi lại. Chưa chốt engine/threshold,
chưa cấp quyền kết nối hay giao dịch. Đây là thiết kế đang giải thích.

Reference: [Nautilus architecture](https://nautilustrader.io/docs/latest/concepts/architecture/)
tách DataEngine/RiskEngine/ExecutionEngine và cập nhật trạng thái theo events;
tham khảo ranh giới trách nhiệm, chưa quyết định adoption.

### Giám sát và phục hồi — đề xuất phần 8

Bộ giám sát theo dõi ba nhóm riêng: sức khỏe data/kết nối/worker; trạng thái
lệnh/vị thế/quyền/hạn mức; hiệu quả chiến lược so với tiêu chí đã định. Một chuỗi
thua ngắn không tự chứng minh chiến lược hỏng; ngưỡng/số mẫu và quyền phục hồi
còn cần chốt. AI có thể điều tra/giải thích, nhưng kiểm freshness, trạng thái lệnh
và hạn mức phải có cơ chế code độc lập với lời tự báo của strategy/agent.

Phản ứng theo sự cố: cảnh báo; ngừng mở lệnh mới; hoặc xử lý rủi ro khẩn cấp theo
policy riêng. Ngừng mở lệnh không đồng nghĩa bỏ quản lý vị thế hoặc đóng hết.
Mất kết nối không được giả định lệnh đã hủy/SL đã có; giữ unknown và đối soát.
Sau restart: phục hồi phiên bản/config/intent → đọc broker orders/positions/fills
→ reconcile → kiểm data/quyền/hạn mức → mới xét mở lệnh. Không chạy lại tín hiệu
cũ hoặc resend submission chưa rõ kết quả. Hiệu quả suy giảm được đưa về research
như evidence; không tự đổi chiến lược đang chạy hoặc mở holdout để chữa kết quả.

Đề xuất dài hạn: tự phục hồi sự cố tạm thời khi các phép kiểm xác nhận đủ; trạng
thái tài khoản/lệnh chưa rõ hoặc vi phạm chính sách thì giữ dừng và báo owner.
Đây là đề xuất kiến trúc, chưa cấp quyền tự resume/close hay giao dịch.
Reference: [Nautilus live lifecycle/reconciliation](https://nautilustrader.io/docs/latest/concepts/live/).

### Vòng đời chung — tổng hợp phần 9

Khung đề xuất: mục tiêu/phạm vi/ngân sách → data đáng tin → nghiên cứu ứng viên
→ kiểm chứng độc lập → xét quyền chạy → mô phỏng realtime/demo → giám sát và
phản hồi. Không đạt thì sửa hoặc loại; chưa đủ evidence thì giữ chờ/bổ sung theo
policy, không ép ra chiến lược. Sau demo mới xét quyền tiền thật riêng.

Hai nhịp chạy cùng tồn tại: nghiên cứu tạo/kiểm phiên bản mới; vận hành xử lý
data/tín hiệu/risk/lệnh của phiên bản đã được phép. Chúng trao đổi bằng version
và evidence, không để nghiên cứu sửa bản đang vận hành trực tiếp. Các trách nhiệm
này chưa đòi hỏi nhiều service hoặc agent thường trực; topology chốt sau benchmark.

Trader là ứng viên bàn điều hành để xem run, chiến lược, account, lệnh, cảnh báo
và quyền; hồ sơ bền vững giữ phiên bản, data/config/cutoff, thử nghiệm và quyết
định. UI/chat không là nguồn trạng thái duy nhất. Chưa chọn engine hoặc giao
implementation; bước tiếp map tài sản hiện có với phần còn thiếu trước chọn reuse.

### Workspace đã có gì — đối chiếu phần 10

Đọc lại canonical README/source ngày31/10; không chạy engine, provider hoặc
broker. Bảng này xác nhận tài sản source/tài liệu, không chứng nhận integrated
autonomy hoặc runtime hiện hành. Receipts audit Trader là bằng chứng có ngày/
source/scope riêng; không mặc định áp cho HEAD mới.

| Trách nhiệm | Tài sản đã thấy | Phần còn cần nối/kiểm chứng cho mục tiêu autonomy |
|---|---|---|
| Bàn điều hành/data/trading | Trader: chart/replay, journal/analytics, MT5, native research/OOS | Góc nhìn toàn vòng đời ứng viên, quyết định chuyển giai đoạn và vận hành tự chủ trọn chuỗi |
| Tính toán/kiểm chứng | Quant Lab: costs/causal/OOS primitives; Trader research_jobs/oos.rs | Bộ tiêu chí/evaluator contract dùng cho từng loại ứng viên, ownership data/test cuối, cross-project parity |
| AI phân tích/phản biện | TradingAgents graph/report/provenance, execution_capability=false | Không tự đồng nhất phân tích tài sản với engine tự tạo/huấn luyện chiến lược mới |
| AI chạy công việc | Trader ai_runs.rs durable lifecycle; ai_workflows.rs fixed LangGraph pilot | Nối research tools/experiment artifacts/evaluator/promotion theo quyền; fixed pilot không là factory hoàn chỉnh |
| Giám sát/vận hành lâu dài | Demo lifecycle receipts Trader; Quant paper_soak.py offline contract | Chưa có proof được dẫn tới cho trọn hệ thống tự nghiên cứu→đánh giá→demo→phục hồi liên tục |

Read-set: ba repo README, TradingAgents trading_graph.py,
Quant src/quant_trading/paper_soak.py, Trader api-rust/src/{ai_runs.rs,
ai_workflows.rs,research_jobs/oos.rs}, owner-system-audit requirements-matrix.
Paper-soak contract tự ghi PREP_ONLY_OFFLINE; không coi đó là soak đã quan sát.

Khuyến nghị thiết kế: giữ ownership ba repo theo nghiệp vụ, nối bằng input/output
có phiên bản (ứng viên → evidence → quyết định → run). Reuse theo vai trò, không
gộp toàn source/database hoặc ép TradingAgents gánh mọi khâu. Phần cần khảo sát
engine tiếp là research loop tự tạo/thử ứng viên; scope hiện tại vẫn discussion.

### RD-Agent cho vòng nghiên cứu — phần 11

Research primary sources ngày31/10: [upstream](https://github.com/microsoft/RD-Agent),
[RD-Agent(Q) paper](https://arxiv.org/abs/2505.15155),
[Finance Quant Agent docs](https://rdagent.readthedocs.io/en/latest/scens/quant_agent_fin.html).
Chưa cài/chạy/tái lập benchmark; kết quả paper không là profitability của owner.

RD-Agent(Q) có vòng Research (giả thuyết/task) → Development (sinh code/chạy
thí nghiệm) → feedback để chọn hướng tiếp. Trọng tâm tài chính được mô tả là
cùng cải thiện factor và model; factor là đại lượng tính từ data làm tín hiệu/
đầu vào, không mặc định là chiến lược hoàn chỉnh. Ví dụ minh họa riêng của mình:
thử feature biến động/khối lượng, huấn luyện model rồi so baseline sau chi phí.

Finance scenario có module hypothesis/coder/runner/feedback, gắn Qlib trong docs;
mẫu mặc định là dữ liệu/danh mục cổ phiếu CSI300. README ghi Linux-only và Docker
cho phần lớn scenario. Do đó chưa thể coi đây là plugin MT5/crypto chạy ngay trên
Windows, hoặc dùng factor research để kết luận mọi strategy family được hỗ trợ.

Đề xuất placement: RD-Agent là candidate research worker; nhận data/phạm vi/
budget được cấp, trả versioned candidate + experiment artifacts; bộ kiểm chứng
độc lập của workspace vẫn quyết định đủ bằng chứng theo policy. Internal feedback
giúp tối ưu trên development/validation, không thay final evaluator/holdout.
Broker, tiền/risk, promotion authority và toàn lifecycle demo nằm ngoài quyền
mặc định của research worker. Adapter/interface/version/license/runtime cost
cần audit/benchmark trước adoption; hiện chưa quyết định reuse nguyên engine hay
chỉ adapt một phần. Bước tiếp: quan hệ RD-Agent/TradingAgents/Paperclip/LangGraph
theo vai trò, không xếp hạng thành một danh sách “tốt nhất”.

### Upstream cập nhật liên tục — giải đáp sau phần 11

Owner lo dependency/repo ngoài thay đổi hằng ngày. Đề xuất: upstream thay đổi
không tự đổi bản đang chạy; chọn release/commit cụ thể, khóa dependencies và
image digest khi có, lưu config/prompt/model/data refs theo run. Git submodule
ghi commit cụ thể; branch trong .gitmodules không tự làm runtime theo latest.
Đây là đề xuất quản lý adoption, chưa bật bot/schedule hay nâng dependency.

Reuse library chính thức qua adapter nhỏ trước; chỉ fork khi cần sửa lõi thật.
Custom domain ở code mình; fork giữ upstream history/attribution/license và patch
nhỏ có inventory để giảm merge conflict. Không copy nhiều core rồi mất provenance.
Giữ input/output contract riêng của workspace để giảm phạm vi sửa khi upstream
đổi; adapter không bảo đảm mọi semantic change đều tương thích.

Upgrade flow: review release/diff/license/security/dependencies → candidate cô lập
→ contract/correctness/cutoff/financial parity → cùng workload chất lượng/cost/
latency → demo/shadow khi thích hợp → promote theo gate. Không đổi engine giữa
run; jobs cũ hoàn tất hoặc chuyển theo migration/checkpoint compatibility được
kiểm. Engine mới có thể sinh ứng viên mới nhưng ứng viên vẫn đi qua evaluator.
Giữ artifact/binary/config và backup matching schema để rollback; đổi binary
không hoàn tác migration hoặc broker side effects.

Nhịp gợi ý: gom review thường theo tuần hoặc nhu cầu; security/bug nghiêm trọng
triage sớm theo exposure, có thể cách ly/disable khi chưa vá an toàn. Không cần
merge mỗi ngày và không freeze bỏ mặc vô hạn. Automation có thể mở update PR,
không tự deploy/merge vào trading runtime. Chưa tạo automation trong trao đổi này.

Pin code không pin SaaS weights/API/data ngoài: dùng model version/snapshot nếu
provider hỗ trợ, ghi resolved identity, đánh dấu unknown và re-evaluate khi drift.
Đây là giới hạn reproducibility cần giữ rõ trong research evidence.

Primary refs: [Git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules),
[PyPA environment pins](https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/),
[Dependabot schedule/groups](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).

### Phân biệt các công cụ theo trách nhiệm — phần 12

Primary README/docs đã đối chiếu ngày31/10; đây là mapping đề xuất, chưa chọn
stack hoặc tích hợp. Các công cụ có phần giao nhau, không là bốn tầng bắt buộc.

| Công cụ | Vai trò đáng xem xét trong workspace |
|---|---|
| [RD-Agent](https://rdagent.readthedocs.io/en/latest/scens/quant_agent_fin.html) | Worker nghiên cứu: tạo/thử factor/model và trả ứng viên cùng artifacts |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Workflow phân tích/phản biện tài chính; chỉ gọi khi phù hợp giả thuyết |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Runtime chạy workflow có state, persistence/resume và human checkpoints |
| [Paperclip](https://github.com/paperclipai/paperclip) | Quản lý mục tiêu/tasks/đội agents, điều phối heartbeat, approvals và ngân sách |

TradingAgents đã dùng LangGraph; không mặc định cần thêm một bản điều phối nữa.
Local fork ghi execution_capability=false, dù upstream mô tả simulated exchange.
Role Risk Manager của agent không thay code kiểm tra quyền/risk trước execution.
RD-Agent có loop nội bộ riêng; outer lifecycle có thể coi nó là bounded job,
không cần bọc lại từng bước khi chưa có nhu cầu phục hồi/quan sát cụ thể.

Paperclip có orchestration thật, gồm task checkout/locks, wakeups và adapters;
không chỉ là org-chart UI. Tuy nhiên cần so với AI control layer hiện có trước
khi adoption. Mỗi concern phải có một authority rõ: task/run status, dispatch/
retry, approvals và budget không được hai hệ thống tự quyết độc lập cho cùng job.
Spend limits dựa trên usage được báo cáo, có độ trễ/in-flight work; không coi
đó là broker-risk limit hoặc quyền dùng tiền. Chưa audit đủ license/dependencies/
runtime để chốt adoption.

Ví dụ luồng đề xuất: mục tiêu nghiên cứu → job có phạm vi/budget → worker thử
ứng viên → evaluator độc lập trả verdict → bàn điều hành hiển thị/chuyển giai
đoạn theo policy. TradingAgents được gọi nếu phân tích tin tức/bối cảnh hữu ích;
không bắt mọi numeric experiment đi qua tranh luận đầy đủ.

Khuyến nghị hiện tại: dùng tài sản Trader/Quant/AI lifecycle làm baseline;
đánh giá RD-Agent cho research worker, TradingAgents theo nhu cầu phân tích;
Paperclip là candidate quản lý công việc cấp ngoài, cần chứng minh giá trị reuse
so với overlap trước thêm. Chưa chốt mọi candidate phải cùng tồn tại. Bước tiếp:
một vòng nghiên cứu cụ thể đi từ đầu vào đến quyết định, rồi xác định contract
bàn giao tối thiểu; không mở thêm danh sách framework.

### Một job nghiên cứu từ đầu đến cuối — phần 13

Ví dụ hoàn toàn giả định, không chốt thị trường/khung thời gian/chiến lược:
đã có baseline theo xu hướng; thử giả thuyết “bộ lọc biến động có giúp cải thiện
kết quả sau chi phí không?”. Nếu chưa có data/baseline đáng tin, job đầu tiên
là xây và kiểm tra chúng; không mặc định hệ thống đã có chiến lược sinh lời.

| Điểm bàn giao | Hồ sơ tối thiểu đề xuất | Ai chịu trách nhiệm |
|---|---|---|
| Giao nghiên cứu | Câu hỏi, baseline version, data/cutoff, phạm vi được chỉnh, giới hạn lượt thử/thời gian/chi phí và tiêu chí đánh giá định trước | Bộ điều phối theo policy/quyền được cấp |
| Nộp ứng viên | Code/config version, data refs, giả thuyết, dependency/runtime identity, nhật ký mọi lượt thử và kết quả development/validation | Worker nghiên cứu |
| Trả đánh giá | Candidate identity, evaluator/data version, so sánh baseline cùng điều kiện, costs/stress/correctness và verdict có lý do | Bộ kiểm chứng độc lập |
| Xét demo | Phiên bản đã đánh giá, evidence refs, quyền/risk/account demo cụ thể và quyết định cho phép; code/data thay đổi phải xét lại bằng chứng liên quan | Policy/admission; bộ vận hành chỉ nhận bản được phép |

Worker được chỉnh trên development/validation theo budget. Bộ kiểm chứng giữ
final holdout ngoài quyền worker; không liên tục trả kết quả cuối để AI sửa rồi
thử lại trên cùng holdout. Ghi nhận mọi lần truy cập và xem phần dữ liệu đã lộ
kết quả là đã dùng trong quá trình chọn ứng viên; cần protocol mới trước khi
coi lần đánh giá sau là độc lập. Không xóa các thử nghiệm thua để chỉ giữ bản đẹp.

Verdict không đạt → lưu lý do và có thể mở job nghiên cứu khác trong budget;
chưa đủ bằng chứng → thu thêm bằng chứng theo protocol; lỗi run → sửa vận hành/
data/code rồi chạy lại phù hợp, không ghi thành chiến lược thua. Đạt đánh giá
chỉ cho phép xét bước kế tiếp theo policy, không tự cấp quyền tiền thật.

Demo theo dõi execution/reconciliation, costs và hành vi ngoài mẫu; không dùng
demo ngắn để tự chứng nhận profitability. AI phát triển v2 ở job riêng, trong khi
demo giữ nguyên v1 cho tới quyết định chuyển bản. Mỗi stage ghi artifact/trạng
thái bền vững, nối bằng job/candidate/evaluation/run identity, không phụ thuộc
việc chat còn nhớ. Bước tiếp: đặt tiêu chí đánh giá đủ rõ để evaluator quyết
định theo bằng chứng; chưa đặt ngưỡng lợi nhuận/drawdown hoặc cấp quyền cụ thể.

### Tổng hợp bốn phần còn lại — trao đổi gộp theo yêu cầu owner

Owner yêu cầu giải thích/trao đổi phần còn lại trong một lượt. Phần này tổng hợp
đề xuất kiến trúc; chưa là owner acceptance của ngưỡng, thị trường, engine hoặc
quyền thực thi. Không tiếp audit UI hoặc triển khai hệ thống từ trao đổi này.

#### 1. Tiêu chí chiến lược đạt theo từng giai đoạn

Thiết kế evaluator gồm: correctness/data/causal timing; kết quả sau chi phí và
so baseline cùng mức risk/exposure phù hợp; rủi ro/drawdown/concentration; độ bền
qua các khoảng thời gian/biến động tham số/chi phí; mức đủ bằng chứng và forward
behavior. Tiêu chí định trước cho mỗi stage và version, không chỉnh theo bản thắng.
Không dùng một con số win rate/return hoặc một backtest để tự chứng nhận đạt.
Backtest drawdown là quan sát lịch sử, không phải trần lỗ tương lai.

Overfit: xem chênh lệch development/validation/OOS, sensitivity, multiple trials
và test contamination. Underfit: chẩn đoán model/features/data từ learning curves
và baseline; kết quả trading thấp có thể do không có edge, không tự bắt tăng độ
phức tạp. Bảo vệ final holdout, ghi mọi lượt thử và thời điểm dữ liệu khả dụng;
LLM historical knowledge cũng có thể làm sai tính độc lập của phép thử.

Không có universal trade-count/calendar threshold. Cần xét số quan sát hữu hiệu,
độ phụ thuộc giữa giao dịch, số lần thử và các điều kiện thị trường đã quan sát.
Thời gian demo chỉ là một phần bằng chứng. Bốn verdict tiếp tục là đạt stage,
không đạt, chưa đủ bằng chứng, lỗi run. Hệ thống được kết luận chưa tìm thấy edge.

#### 2. Phạm vi nghiên cứu đầu tiên — khuyến nghị, chưa chốt

Đã đọc lại Quant README: crypto spot D1, long/cash không leverage, costs/causal/
OOS primitives. Đề xuất dùng đúng phạm vi này làm pilot nghiên cứu offline,
với universe nhỏ định trước có chính sách tránh selection bias; không tự mở key
hoặc tài khoản. H4 là hướng mở rộng sau, chưa chạy đồng thời nhiều khung/market.
Đây là lựa chọn giảm việc tích hợp dựa trên tài sản hiện có, không phải kết luận
crypto dễ có lợi nhuận, ít rủi ro hơn hoặc bắt buộc dùng RD-Agent.

MT5 Forex/vàng tiếp tục là candidate khi ưu tiên broker demo và reuse Trader;
cần model spread/commission/swap/contract/leverage theo đúng account và data
nguồn thực thi. Crypto spot pilot cần phí/slippage/liquidity/exchange rules và
giám sát vận hành phù hợp. Không chuyển nguyên kết quả giữa hai thị trường.

Data contract giữ source/instrument/venue, UTC/event/availability time, revision,
OHLCV hoặc ticks theo chiến lược, gaps/duplicates, costs và version/cutoff.
Bar data không đủ mô tả mọi thứ xảy ra trong nến; tăng độ chi tiết khi logic
fill/stop cần. D1 giảm số thời điểm quyết định trong pilot nhưng tích lũy forward
evidence chậm; không suy rằng quan sát vài tuần là đủ hoặc ít quyết định là ít lỗ.

#### 3. Quyền tự quyết, ngân sách và vận hành

Đề xuất quyền riêng: research/sandbox trong budget được cấp; evaluator access
với data tách biệt; demo admission theo policy; tiền thật ban đầu owner duyệt;
B dài hạn chỉ tự promotion trong phạm vi tiền/quyền được cấp, chuyển được về A.
Lựa chọn B không cấp quyền nâng vốn, đổi account, vượt budget hoặc mở holdout.

Tách research costs (model/compute/data, limits lượt thử/concurrency/time) khỏi
trading risk (capital/exposure/concentration/loss/account scope). Dừng worker
và tính chi phí in-flight; reported token usage không là hard financial lock.
Research code chạy cô lập không có broker secrets; quyền ghi broker nằm ở
execution boundary, kiểm bằng code trước lệnh và đối soát sau lệnh.

Data cũ/lỗi quyền/lệch vị thế/chưa rõ lệnh thành công thì ngừng cấp lệnh mới theo
policy, đối soát trước retry/resume. Quản lý vị thế đang mở vẫn theo contract;
không mặc định đóng tất cả hoặc bỏ quản lý. Hiệu quả giảm cần quan sát/đánh giá
theo tiêu chí định trước, không tự thay model sau vài giao dịch thua.

#### 4. Kiến trúc đích và lộ trình đề xuất

Vòng nghiên cứu: mục tiêu/budget → data chuẩn hóa → worker nghiên cứu → ứng viên
→ evaluator → quyết định xét demo/live. Vòng vận hành: phiên bản được phép →
signal → permission/risk → execution → reconciliation/monitoring. Monitoring
gửi vấn đề về hàng đợi nghiên cứu; không tự hot-swap chiến lược đang chạy.

Trader là console; Quant và native research/OOS là tài sản evaluator cần parity;
AI lifecycle hiện có là baseline điều phối. Hồ sơ bền vững nối data/candidate/
evaluation/policy/run identity, lưu failures và lineage. Tách trách nhiệm logic
trước, không tự tách mọi phần thành microservices hoặc gộp các repo/database.
RD-Agent là candidate research worker cần thích nghi/benchmark; TradingAgents
phân tích chọn lọc; Paperclip so với current control layer trước adoption.
LangGraph hiện hữu được reuse khi phù hợp, tránh nhân đôi authority/retry.

Lộ trình theo bằng chứng: (1) một baseline + data + evaluator tái lập offline;
(2) nối một AI research worker qua một job có budget, nộp candidate và evidence;
(3) forward simulation/demo cố định version, kiểm phục hồi/đối soát/alerts;
(4) nếu đủ bằng chứng, owner xét tiền thật quy mô/risk cụ thể; (5) mở B từng
quyền theo acceptance rồi mới mở rộng strategies/markets/agents. Từng lát giữ
contract của kiến trúc đích; không cam kết deadline kiếm tiền hoặc phải có
chiến lược thắng khi đến cuối giai đoạn.

Primary refs đối chiếu cho phần kiểm chứng:
[learning/validation curves](https://scikit-learn.org/stable/modules/learning_curve.html),
[lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/),
[backtest assumptions/forward testing](https://www.freqtrade.io/en/stable/backtesting/),
[MT5 bars/history/UTC](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py).
Nguồn xác nhận các constraint kỹ thuật, không chứng nhận stack hoặc profitability.

Trạng thái cuối cuộc trao đổi: đã hình thành proposal tổng thể để owner review.
Còn mở thị trường/khung đầu tiên, ngưỡng evaluator, capital/risk/research budget,
engine adoption và contracts implementation. Bước tiếp khi owner giao: viết
execution PLAN có scope/acceptance/versioned contracts sau khi resolve các lựa
chọn ảnh hưởng scope; chưa chạy worker, provider, broker, migration hoặc deploy.

### Cách triển khai để owner review được sớm — AI-first

Owner nhấn mạnh vibe-coding/AI-first và hỏi lại việc để agent làm toàn bộ lõi
rồi cuối cùng mới thấy UI. Điều chỉnh proposal: thêm UI/workflow review sớm,
triển khai từng lát xuyên suốt UI→API→engine→stored evidence; roadmap nghiệp vụ
ở trên không có nghĩa hoàn tất toàn backend trước khi làm giao diện.

Đề xuất vòng làm việc: (1) prototype tương tác của một hành trình nghiên cứu
giao việc→tiến độ→bằng chứng→quyết định, reuse Trader/design system; (2) owner
góp ý workflow/ngôn ngữ/thông tin cần thấy, agent đồng thời kiểm khả thi engine
bằng spike offline nhỏ; (3) nối một hành trình với data/engine thật, gồm lỗi,
chưa đủ bằng chứng, hủy/dừng và phục hồi phù hợp; (4) review hành vi rồi mở rộng.
Prototype dùng fixture phải ghi rõ dữ liệu minh họa; chưa nối tính năng thì
không trình bày như job đã chạy hoặc bằng chứng profitability. Không tự mở
provider/broker/money quyền chỉ vì thao tác prototype đã có nút tương ứng.

Owner review các quyết định workflow/UI quan trọng trên sản phẩm; agent tự xử
lý implementation thường lệ trong scope. Các tính toán, causal timing, risk và
data contracts vẫn kiểm độc lập; review UI không thay acceptance kỹ thuật.
Chỉ cần skeleton kiến trúc/contract đủ cho lát đầu, điều chỉnh theo feedback;
không dựng mọi màn hình hoặc chốt toàn engine trước vòng sử dụng đầu tiên.
Đây là điều chỉnh phương pháp đề xuất, chưa giao xây prototype và không resume
UI audit đang pause. Bước tiếp khi được giao implementation là lát có UI sớm.

## 4. Reuse tài liệu hiện có

| Tài liệu | Vai trò và cách dùng |
|---|---|
| [Nền AI chung, 23/10](AI-WORKSPACE-ARCHITECTURE-2026-10-23.md) | Kiến trúc AI runs, worker, provider/admission và ownership. Giữ làm baseline hạ tầng; không coi lựa chọn LangGraph là đã chốt trading engine |
| [Money engine, 27/09](../checkpoints/workspace-next-stage/MONEY-ENGINE-ARCHITECTURE-2026-09-27.md) | Tham khảo risk, reconciliation và promotion; đây là packet lịch sử PREP_ONLY, gồm cả nhánh doanh thu sản phẩm ngoài scope lần này |
| [Autonomy feasibility, 28/09](AUTONOMY-2-YEAR-FEASIBILITY-2026-09-28.md) | Tham khảo recovery/vận hành vắng chủ; các giả định thời gian và hoàn cảnh cũ không tự áp cho brief dài hạn hiện tại |
| [Product Plan Trader](../trader/PRODUCT-COMPLETION-PLAN.md) và [current scope](../trader/CURRENT-SCOPE-20261029.md) | Tiếp tục giữ phạm vi và acceptance Trader; brief này không sửa trạng thái các gate |

Các giới hạn iteration đầu trong research 23/10 tiếp tục được đọc trong scope
hạ tầng AI khi đó; không dùng chúng để loại trước hướng nghiên cứu AI tự viết
chiến lược hoặc kiến trúc dài hạn đang được bàn. Thay đổi implementation vẫn cần
plan/contract và quyền tương ứng. Không khởi động lại plan/worker cũ từ brief này.

## 5. Nguồn ngoài đã khảo sát trong cuộc trao đổi 31/10

Đây là bản đồ reference từ README/docs/paper; chưa chạy engine hoặc benchmark
các ứng viên với cùng workload. Chưa có căn cứ xếp hạng lợi nhuận hay chốt stack.

| Nguồn | Phần đáng nghiên cứu/reuse |
|---|---|
| [RD-Agent](https://github.com/microsoft/RD-Agent), [Qlib](https://github.com/microsoft/qlib) | AI nghiên cứu factor/model, vòng lặp thí nghiệm định lượng |
| [Freqtrade/FreqAI](https://www.freqtrade.io/en/stable/freqai/) | Luồng crypto có ML, backtest/dry/live và tái huấn luyện |
| [NautilusTrader architecture](https://nautilustrader.io/docs/latest/concepts/architecture/), [LEAN](https://github.com/QuantConnect/Lean) | Trading engine, ranh giới data/risk/execution và vận hành theo sự kiện |
| [FinRL-X](https://github.com/AI4Finance-Foundation/FinRL-Trading) | Contract tỷ trọng danh mục nối chiến lược với thực thi |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents), [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Workflow phân tích tài chính bằng agents |
| [Paperclip](https://github.com/paperclipai/paperclip) | Quản lý mục tiêu, công việc và đội agents; cần phân biệt với trading engine |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Temporal activities](https://docs.temporal.io/activity-definition#idempotency) | Workflow có trạng thái/phục hồi; retry không tự bảo đảm broker effect chỉ xảy ra một lần |
| [Nghiên cứu LLM look-ahead bias](https://aclanthology.org/2026.emnlp-main.510/) | Kiểm soát việc mô hình có thể biết kết quả lịch sử từ pretraining |

Refresh đúng version, license, capability và platform trước khi chọn engine;
không đọc danh sách này như quyền cài/chạy toàn bộ.

## 6. Điểm tiếp tục cuộc trao đổi

Khảo sát đội agents theo yêu cầu owner: [đội Paperclip cho nghiên cứu giao dịch
(31/10)](PAPERCLIP-QUANT-TEAM-RESEARCH-20261031.md). Đề xuất khởi đầu 3 vai trò:
điều phối, nghiên cứu và kiểm chứng độc lập; RD-Agent/TradingAgents là engine
theo nhiệm vụ bên trong. Đã đối chiếu docs/source và mẫu cộng đồng; chưa chốt
model, áp cấu hình hoặc bật agent/job. Đây là proposal để review, chưa thay đổi
quyền demo/live hoặc thứ tự UI trước, backend/services sau.

Khảo sát tiếp theo: [bản dịch Paperclip, cấu hình và vị trí engine (31/10)](PAPERCLIP-LOCALIZATION-INTEGRATION-SURVEY-20261031.md).
Chưa có bản VI hoàn chỉnh được chấp nhận; plugin DOM có giới hạn đã tái hiện
trên fixture riêng. Owner đã chọn fork Paperclip gốc, mở rộng i18n và bộ engine
ở §1; Codex chuẩn bị cấu hình kỹ thuật, owner quyết định mục tiêu/ngân sách/quyền.
Owner đồng ý hướng gom source integration; chưa di chuyển repo hoặc bật engine/
agents. Lát thực hiện vẫn cần xử lý paths/runtime và giữ rollback.
Owner sau đó giao thực hiện: source fork/adoption và runtime relocation được
ghi ở [checkpoint integration](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Đọc checkpoint trước khi tiếp implementation; không lấy câu "chưa di chuyển"
phía trên làm trạng thái hiện hành. UI audit rộng vẫn pause.

Owner muốn giải thích **từng phần nối tiếp như giảng bài**, ngắn, có ví dụ;
không liệt kê toàn bộ framework/kiến trúc trong một lượt. Có thể hỏi một câu
khảo sát khi câu trả lời ảnh hưởng thiết kế. Đây là preference cho cuộc trao đổi
kiến trúc, không tự cập nhật tiến độ khóa học trong education/.

Đã trao đổi phần 1: B dài hạn, chuyển được về A. Phần 2 đã chốt AI được tìm ý
tưởng rộng từ đầu, triển khai nghiên cứu theo phạm vi nhỏ; có data và baseline
trước khi đánh giá cải thiện. Owner xác nhận giai đoạn đầu chỉ mô phỏng/demo,
có chiến lược tốt mới xét tiền thật. Phần 3 đã giới thiệu quá khứ → dữ liệu chưa
dùng để chỉnh → mô phỏng/demo. Owner bổ sung yêu cầu xử lý overfit/underfit/lỗi
phổ biến và muốn chốt workflow trước khi đi sâu tối ưu. Phần 4 giới thiệu ba
trách nhiệm của hệ thống; phần 5 giải thích nhóm nghiên cứu bằng vòng đề xuất
→ triển khai → thử nghiệm/phản biện, với RD-Agent(Q) làm reference. Chưa chốt
topology, số agent hoặc framework. Phần 6 đề xuất input/output của bộ kiểm chứng,
phân biệt đạt/không đạt/chưa đủ bằng chứng/lỗi run và quyền phát hành riêng.
Phần7 giải thích bộ vận hành nhận phiên bản được phép và chạy demo,
tách tín hiệu AI khỏi kiểm tra quyền/risk và xác nhận lệnh. Phần8 đề xuất giám
sát sức khỏe/vị thế/hiệu quả, dừng mở mới khác đóng vị thế, đối soát trước resume
và phản hồi về nghiên cứu. Chưa chốt ngưỡng hoặc cấp quyền thực thi.
Phần9 tổng hợp vòng đời, phân biệt hai nhịp nghiên cứu/vận hành và vị trí Trader
như bàn điều hành. Phần10 đối chiếu source hiện có: Trader đã có research/OOS và
AI lifecycle/pilot bên cạnh UI; Quant có numeric validation; TradingAgents có
analysis graph. Chưa có proof trọn vòng autonomy. Phần11 nghiên cứu primary docs
RD-Agent(Q), giải thích R→D→feedback/factor-model và placement research worker;
chưa adoption hoặc profitability claim. Sau phần11 giải đáp upstream updates:
pin bản chạy, adapter/fork nhỏ, candidate review/benchmark/promotion và rollback,
không auto-update runtime; SaaS model drift không được pin code giải quyết hoàn toàn.
Phần12 phân biệt RD-Agent (research worker), TradingAgents (phân tích/phản biện),
LangGraph (workflow runtime) và Paperclip (quản lý/điều phối công việc agents).
Đây là mapping đề xuất, chưa adoption; giữ một authority cho mỗi concern và tránh
trùng dispatch/retry/approvals với AI lifecycle hiện có. Phần13 minh họa job thử
bộ lọc biến động trên baseline theo xu hướng; bốn điểm bàn giao giữ task spec,
candidate/artifacts, evaluation và demo admission. Giữ mọi lượt thử, bảo vệ final
holdout khỏi vòng chỉnh lặp; demo chạy phiên bản cố định. Đây vẫn là thiết kế
đề xuất, không là job đã chạy. Bước tiếp: tiêu chí đánh giá chiến lược và cách
phân biệt đạt/không đạt/chưa đủ bằng chứng/lỗi run qua một ví dụ đơn giản.
Sau đó owner yêu cầu gộp bốn phần còn lại trong một lượt; proposal tổng hợp ở
cuối §3 bao gồm evaluator, pilot/data, authority/budgets và architecture/roadmap.
Khuyến nghị pilot crypto spot D1 từ Quant hiện có là đề xuất mới, chưa owner chốt;
không dùng phần này để ghi acceptance, cấp execution hoặc tự tiếp UI audit.
Phần giải thích khung đã tổng hợp; tiếp theo review/chỉnh proposal hoặc chuyển
sang PLAN khi owner giao, không tự kéo dài danh sách bài/framework.
Owner tiếp tục nhấn mạnh AI-first/vibe-coding: đã bổ sung cách làm prototype UI
sớm và các lát UI→API→engine→evidence; chờ giao scope thực hiện, không tự build.
Sau đó owner giao làm UI trước, cho phép thử CLIProxyAPI/Gemini nhưng yêu cầu
xem workflow trước khi làm backend/services. Lát hiện hành ở
[AI Research UI prototype](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md): mục AI→
Nghiên cứu, dữ liệu minh họa/local browser state, không inference hay engine thật.
Receipt được plan dẫn giữ bằng chứng scoped; UI audit cũ vẫn pause. Bước tiếp là
owner xem prototype và góp ý, không tự chuyển sang backend/services.
Prototype source checkpoint `5aafd680` trong repo Trader; preview riêng tại
`http://127.0.0.1:5218/?workspace=tenant-a&view=ai&area=ai&section=research&lang=vi`.
Owner review tiếp theo sửa hướng UI: thiết kế từ khung/điều hướng tổng thể vào
trong, ưu tiên nhúng UI gốc Paperclip như CLIProxyAPI. Prototype riêng phía trên
chỉ còn là khám phá workflow, chưa là giao diện đích được chấp nhận. Phần điều
chỉnh trong [plan UI](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope và
các điểm cần xác minh trước khi nhúng. Sau đó owner đã giao nối UI thật và lưu
source trong `projects/`: triển khai native UI ở `projects/paperclip` (submodule
upstream pin `42fd568`), UI/API local17860 và database riêng17861, nhúng vào Trader
preview5218 tại `section=paperclip`. Receipt `paperclip-ui-20261031` trong Trader
giữ bằng chứng/giới hạn; chưa nối engine hoặc chạy agent/model. Đây không là
acceptance cho autonomy hoặc rollout Trader API. UI audit rộng vẫn pause.
Không hỏi lại các lựa chọn đã biết hoặc
tự chuyển sang implementation.

Các điểm còn mở, hỏi lần lượt khi tới phần liên quan: tiêu chí đạt của chiến lược,
phạm vi quyền tự quyết, ngân sách/vốn/rủi ro, thời gian owner có thể giám sát,
thị trường/nhịp giao dịch cuối cùng và cách xử lý sự cố. Chưa đặt con số thay owner.
