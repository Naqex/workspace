# Hệ thống giao dịch tự chủ — brief hiện hành

Cập nhật: **31/10/2026 (Asia/Saigon)**.
**WORK: DRAFT · REVIEW: DOCUMENTATION-ONLY · DOC: FULL.**
Owner đã giao nghiên cứu kiến trúc/workflow và lưu context. Chưa giao triển khai
hệ thống mới. Brief này giữ mục tiêu, lựa chọn và câu hỏi đang bàn; không là
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
- Thị trường đầu tiên **chưa chốt**: so sánh Forex/vàng qua MT5 và crypto.
- Nhịp giao dịch **chưa chốt**: owner muốn đề xuất theo tính khả thi. D1/H4 mới
  là khuyến nghị của assistant, chưa là lựa chọn được owner chốt.
- Paperclip, TradingAgents và repo ngoài là đối tượng research/reference/reuse;
  owner chưa yêu cầu cài đặt, tích hợp hoặc chọn một engine cụ thể.

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
như bàn điều hành. Bước tiếp theo: map phần đã có/còn thiếu trong workspace rồi
đối chiếu engine cho từng vai trò, tránh danh sách framework dài. Không hỏi lại các lựa chọn đã biết hoặc
tự chuyển sang implementation.

Các điểm còn mở, hỏi lần lượt khi tới phần liên quan: tiêu chí đạt của chiến lược,
phạm vi quyền tự quyết, ngân sách/vốn/rủi ro, thời gian owner có thể giám sát,
thị trường/nhịp giao dịch cuối cùng và cách xử lý sự cố. Chưa đặt con số thay owner.
