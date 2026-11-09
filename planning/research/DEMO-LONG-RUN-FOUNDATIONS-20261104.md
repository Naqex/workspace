# Nền vận hành dài hạn cho Trader — research 04/11/2026

**Trạng thái: đề xuất, chưa khởi chạy job qua đêm hoặc mở quyền thực thi mới.**

Owner đã duyệt gói qua đêm và các phần nền liên quan lúc22:42VN04/11. Đoạn
trên và các nhận xét "chưa khởi chạy" bên dưới giữ thời điểm research; trạng
thái triển khai/run hiện hành đọc trong AI plan/receipt/native task được dẫn tới.
Scope/acceptance nằm trong [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md);
kết quả đã đạt nằm trong [receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Tài liệu này giữ lý do và thứ tự đề xuất, không tạo progress ledger thứ hai.

## Kết luận

Giữ Paperclip native, Rust lifecycle/API, Python SDK/reducer và PostgreSQL hiện
có. Ưu tiên làm rõ cách một run kéo dài qua nhiều đoạn, nguồn dữ liệu/cấu hình,
khả năng quan sát và phục hồi; chưa có bằng chứng cần thêm workflow platform.
Qua đêm có ích cho hành vi môi trường thật còn thiếu; offline injection dùng
cho các lỗi xác định được, không lặp suite đã đạt để lấp thời gian.

## Đối chiếu hiện trạng với yêu cầu dài hạn

Nguồn local: workspace `a9d1376`, Trader `62cd94bd`; source/docs đã đọc, không
phải audit toàn bộ sản phẩm. Chưa đo capacity toàn máy hoặc RTO production.

| Nền | Đã có bằng chứng | Khoảng cần củng cố / quyết định |
|---|---|---|
| Run → attempt → đoạn dữ liệu | Manifest/hash/cursor/checkpoint, resume không resend; shadow có continuation theo H1, chain có giới hạn | Bộ điều phối hữu hạn nối predecessor hoàn tất với successor, cùng source/generation/deadline; job lỗi không tự tạo run mới. Execution vẫn tối đa15phút, không ghép các grant để giả quyền giao dịch liên tục |
| Dữ liệu và thời gian | UTC normalization, broker clock profile, settled H1, raw observations và ordered-quote policy | Một contract chỉ rõ Bid/Ask/mid, timestamp đầu/cuối nến, known-at, gap/market closure và lineage. Native Bid H1 và QDM/shadow midpoint hiện khác basis; không so output như cùng input |
| Theo dõi tình trạng thật | Lifecycle heartbeat, cursor/pages/ticks/error, native observer/task riêng; publication không sở hữu capture | Đối chiếu heartbeat với data progress, latency/error và resource headroom. Trạng thái thị trường đóng/bảo trì chỉ được phân loại khi có nguồn lịch đã xác minh; broker session schedule hiện còn unknown |
| Dung lượng và tài nguyên | Capture/page/checkpoint/window có bounds; nhiều phiên tách process/state | Các file runner mới chưa có kiểm free-space/retention tổng cho nhiều đợt. Đo bytes/tốc độ tăng/log/CPU/RAM trước khi đặt capacity; chặn khởi chạy khi không đủ headroom. Chưa tự prune dữ liệu/evidence đang dùng hoặc failed attempts |
| Cập nhật và tái lập | Build/source/SDK/config pin, idle guard, rollback local, account generation fences | Checklist release tách bản đang chạy với candidate: bản mới dùng cho run mới; run cũ giữ pin, không chỉnh expected hash để resume. Compatibility fixtures cho adapter/model thay đổi, chưa cần registry service mới |
| Backup/restore | Bundle Trader DB/artifacts có helper, backup local03/11 có receipt; fixture PG crash/restore47bảng đã đạt | Đo restore theo bundle/môi trường mục tiêu; toàn bộ Studio còn có Paperclip DB/storage/config và proxy authentication. Fixture1,359s không là RTO production. Backup hiện tại cần stopped writers, không thực hiện giữa capture chỉ để có snapshot mới |
| Nhiều phiên giao dịch | Một execution grant active cho workspace/login/server, idempotency/reservation/receipt, unknown reconcile | Trước nhiều chiến lược/account hoặc tự gia hạn phải có ownership vị thế và ngân sách tổng/ngày không reset theo segment. Hedging/netting cần contract riêng; hiện final guard yêu cầu Demo hedging |
| AI/provider dài hạn | Native usage/provider_usage, pin raw requested/reported IDs, bounded retry và unknown accounting | Contract fixtures/cases lưu ngoài chat; model thay đổi phải qua cùng dữ liệu/case. Đo usage thật trước budget; không suy cache/subscription quota từ giá API hoặc dùng LLM trong heartbeat |

## Bổ sung đáng làm trong gói qua đêm

1. **Preflight và nhận diện run:** đóng băng source/config/runtime binding;
   kiểm account hiện tại, resource headroom, đầu ra trên ổ đã chọn, input ngoài
   output và deadline. Dùng một run ID nối task, manifest, lifecycle, log,
   snapshot/receipt; reuse các ID hiện có trước khi tạo format mới.
2. **Một lần H1 handoff thật trên Exness:** predecessor kết thúc đúng H1,
   settlement và hoàn tất rồi successor nhận frozen report. Stop giữa giờ
   resume cùng phiên, không bỏ prefix; không liên tục retry bằng capture mới.
3. **Lane FTMO song song:** kiểm read-only broker clock/identity riêng và
   progress qua nhiều giờ. Không reconnect terminal khi phiên khác đang chạy;
   đổi generation/source/SDK hoặc dữ liệu sửa thì dừng đúng lane.
4. **Lane offline chọn lỗi mới:** tập trung mất publication trong khi capture
   vẫn tiến, lỗi commit/ghi đĩa tại boundary handoff, nguồn/cấu hình thay đổi khi
   cold resume, sibling failure và báo cáo cuối không nhận thiếu dữ liệu là đạt.
   Fault injection nằm trong fixture/cluster riêng; không tắt API/DB/MT5 owner.
   Không lặp6579virtual-time cases hoặc restore suite đã đạt nếu code không đổi.
5. **Bàn giao sáng:** một báo cáo native tổng hợp, task/doc riêng từng lane,
   thời điểm dữ liệu cuối, source/config hash, lỗi đầu tiên, checkpoint/resume,
   coverage đạt và phần chưa được chứng minh. Đo thời gian/bytes/tài nguyên cho
   đợt thật; không tự chọn một tỷ lệ % hoàn thành hoặc uptime giả định.

Đây vẫn là gói hữu hạn chỉ đọc, không scheduler/service24/7, không OrderCheck /
OrderSend. Lane offline làm xong thì kết thúc. Mốc07:00 ngày05/11 chỉ là giờ
đề xuất trong chat; chưa cài lịch hoặc khởi chạy từ tài liệu này.

## Thứ tự sau đợt qua đêm

### Trước vận hành tự động dài ngày

- Từ số liệu đợt thật, chốt giới hạn tài nguyên và policy lưu/archival có owner;
  lỗi disk-full phải giữ checkpoint tốt và báo rõ, không im lặng mất log/data.
- Chuẩn hóa runbook: restart từng lớp, sửa publication riêng, xử lý unknown,
  đổi account generation, restore, release/rollback; một đường vận hành được
  dẫn từ OPERATIONS thay cho các private script hard-code từng milestone.
- Đối soát replay/live với cùng input/basis/cutoff và phiên bản; tách khác biệt
  data/timing/chi phí/fill. Không dùng độ khớp P&L làm bằng chứng toàn hệ thống.
- Định nghĩa authority của run dài hơn, stop/close/reconcile khi permission hết
  hạn và budget ngày/tổng tồn tại độc lập với restart/segment. Chưa bật tự renew.
- Đo recovery trên đích phục hồi thực rồi mới chọn RPO/RTO phù hợp; không biến
  một lần restore fixture thành cam kết phục hồi cả máy.

### Khi có nhu cầu scale đã đo được

- Nhiều chiến lược cùng account: account/portfolio-level risk và position
  ownership; netting cần semantics phân bổ riêng vì broker gộp vị thế theo symbol.
- Nhiều máy: execution owner duy nhất với fencing, failover/reconcile và nguồn
  dữ liệu nhất quán; hai máy cùng gửi lệnh không phải dự phòng an toàn.
- Off-machine backup và external alert: theo lựa chọn đích/kênh của owner;
  hai phần này đã được hoãn, chưa tự chọn cloud/OAuth/provider hoặc bật G copy.
- Workflow platform/collector chuyên dụng chỉ xét khi state/queue nhiều host,
  fan-out/dependency/retry hoặc truy vết vượt khả năng vận hành đã có. Benchmark
  migration/rollback và domain guarantees trước khi thay nền.

## Nguồn chính thức và cách áp dụng

- [Temporal: idempotency and durable execution](https://temporal.io/blog/idempotency-and-durable-execution):
  recovery/retry vẫn cần identity và chống tác dụng phụ trùng tại ranh giới
  ứng dụng. Trader đã có native request IDs/receipts; không cần cài Temporal
  chỉ để thêm retry. Context7 official documentation cũng nêu deterministic
  replay, Activities cho external calls và code versioning; migration không
  tự giải quyết broker reconciliation hoặc permission của mình.
- [Google SRE: monitoring distributed systems](https://sre.google/sre-book/monitoring-distributed-systems/):
  kết hợp tín hiệu nội bộ với hành vi người dùng/consumer quan sát được; latency,
  traffic, errors và saturation. Áp vào heartbeat + cursor/data freshness + tài
  nguyên, chưa cần dựng một monitoring stack lớn cho một máy.
- [QuantConnect: reconciliation](https://www.quantconnect.com/docs/v2/writing-algorithms/live-trading/reconciliation):
  phân biệt sai lệch từ dữ liệu, mô hình, broker, warmup/restart và lịch thực.
  Áp vào fixtures/diagnostic so cùng input và timing, không chuyển platform hoặc
  tuyên bố replay/SDK broker fill phải hoàn toàn giống nhau.
- [OpenTelemetry: context propagation](https://opentelemetry.io/docs/concepts/context-propagation/):
  context/trace identity giúp nối các sự kiện qua process/service. Áp trước
  bằng run/task/attempt/command IDs đã có; chỉ triển khai collector khi có nhu
  cầu truy vết/khối lượng thực tế.
- [MetaTrader5: position accounting](https://www.metatrader5.com/en/terminal/help/trading/general_concept):
  netting và hedging có semantics vị thế khác nhau do broker/account quyết
  định. Không bật nhiều chiến lược chung account bằng cách bỏ foreign-exposure
  guard hoặc chỉ đổi magic number.
- [PostgreSQL: backup and restore](https://www.postgresql.org/docs/current/backup.html):
  backup cần chọn phương thức phù hợp với consistency/recovery. Project đã có
  quiesced bundle helper; online WAL/PITR là lựa chọn cần thiết kế/kiểm riêng,
  chưa được triển khai bằng việc đồng bộ folder DB.

Đây là đề xuất của agent sau đối chiếu primary sources và source local; không
phải một bộ stack bắt buộc hoặc cam kết loại hết sự cố/lợi nhuận.
