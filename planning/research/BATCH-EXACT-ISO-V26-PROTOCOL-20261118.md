# V26 — batch source-bound và nghiệm lot rời rạc, trước outcome

Owner: attachment bf657164-e109-44d0-a422-5aa85ccdec5b. PR104/head5509aa0
đã merge9ac2044; nhánhV25 được xóa. Nhánhcodex/batch-24bots-and-exact-iso-v26.
Giữ VI WIP/source lane. GBP S01 đóng trong campaign này: H1 scenario tăng DD,
không đồng nghĩa đã xác minh tick/M1 economics; không rerun/tune GBP S01.

## Phạm vi và giới hạn suy luận

1.029 là content profiles gồm nhiều Python/C#, không phải1.029 alpha độc lập.
24structural sources là6patterns×4oscillators (RSI/CCI/MFI/Stoch).
V25 c dùng saved full-precision metrics, không dùng12,21/14,67.
V26 là quyền tìm nghiệm sizing mới sau outcome V25, phải ghi selection history.
2024–2026 đã exposed trong baseline/chiến dịch cũ: chưa đo một variant không
biến lịch sử chung thành100%unconsumed OOS.

## Track1: catalog và batch

Khóa24 SHA/defaults từ V25classification-v2. Giữ Top10 rank v2 rồi14 còn lại
theo tên/hash. E1 EngulfingRSI/EURUSD/H1 reuse kết quảV25;23source còn lại
được đánh giá trên từng XAUUSD/EURUSD/US500/GBPUSD/AUDUSD, tổng115cells.
Chỉ H1, hai chiều, defaultSL/TP200point/duration10bars, không grid/timeframe
variants. Source _Symbol/_Period là chart context; khai báo context mới,
không gọi là native MT5/source-bot parity.

Review6pattern formula và4oscillator formulas trước outcome; không sửa vendor
rules để cứu kết quả. MFI cần VOLUME_TICK thật; không lấy số M1 bars làm volume.
Nguồn không có volume hoặc không có đủ2018–23/path thì ghi blocked/unknown,
không tạo input giả hoặc gọi một sample ngắn là six-year validation.
Preset/report extraction không tự thay defaults của batch đã khóa.

Stage0primary+8h lịch, secondary+4h chỉdiagnostic; cost<=12%,median<=12%,
retention>=50%,cadence>=40/năm,mean net từng năm>0 và>=mean friction.
Native stop giữ source200point và spread minimum; Digits/point ghi theo
source admission/declared context, không kéo SL theo ATR để lách phí.
Chi phí/clock/clamp reuse inherited declared contracts; target certification
unknown giữ nguyên. Missing endpoint/path không impute.
Sau Stage0pass mới SL-active với đúng sourceSL/TP/expiry, no position overlap,
lot0,01; dùng hai ordering và giữ intrabar unknown. Dualclusters2018–20 và
2021–23 phải dương. Daily correlation chỉ trên ngày đủ data và cùng marked
clock; chưa chạy SL-active thì metricsR/DD/correlation lànull, không suy từ
raw markout không SL/TP. Raw cadence không tự là account cadence.

Nếu có đủsource/path vàSL-active pass, một satelliteweight0,25×$150/cell.
Không tune weight; so baseline cùngpath/clock. Chỉ composite tăngnet,
không tăngequityDD/static/daily/openrisk,dualclusterspositive được xét later.
Nếu nhiều survivor, chọn NetR/DD cao nhất rồiNetR rồirank; tối đa1satellite
và1combination vớiISO, khóa trước khi mởlater. Không chọn bằnglater.

## Track2: một bài toán feasibility sizing, không phải edge mới

Domain c∈[0,820000;0,831000], grid1e-6, giữratioF5=1,3/F3=F4=0,7.
Bisection ghi toànprobes; DD trên lot rời rạc không bảo đảm monotone.
Vì vậy chứng nhận largest feasible trên domain bằng toàn bộ unique quantity
vectors của11.001gridpoints, không suy largest từ bisection đơn thuần.
PrepareM1path một lần; giữcents,volume_step0,01,exact rational quantity.

Hard DD<=12,2065R tương ứng<=183.097cents với$150/R (không làm tròn
183.097,5cents lên). Maxopenrisk<=31.280cents. Hai ordering phải thỏa.
Chọnc lớn nhất thỏa hai caps; sau đó kiểmNetR>23,8524 và những cổng
static/daily/dualclusters V25. Không chọn mộtc khác nếu finalgatefail.
So lại baseline/cũ để chắc quantity/cost/path semantics không đổi.
Khóa weights/profile/source/input/decision trong Git trướclater.

ChỉDevpass mới105starts+5.000commonbootstrapdraws, haiordering,
PRIMARY100/PRIMARY150/STRICT100, cóaudit ledger. So incumbent cùngsaved
draws, reports12/18/24/36month, payout mô phỏng vàsource-gap stress.
Lifecycle dùng đúng account-level weights, không chỉ đổiunit-risk tape.
Thiếu horizon trong runner thì tính từ saved phase timestamps; không bịa
36month result nếu actual MCend ngắn hơn. Không gọi bootstrap frequency là
xác suất tương lai, không promotion tự động.

## Track3: preset/report parser và inventory

Đọc bounded .set/.ini/.chr và .htm/.html/.xml nhưdata, khôngexecute/deserialize.
Giữ current/start/step/stop/optimizationflag và provenance; secret/account/
credential keys redacted, không bịa đơn vịpip nếu presetkhông cósymboldigits.
StaticHTML/XML table headers/Deals/Orders; MT5deals chưa là closedtrades:
chỉ clone khi pairing/position identity/side/volume đủ, partial/unknown giữ rõ.
Không đoán timezone hoặc đánh đồng deposit/balance rows vớitrade.
Chặn XMLDOCTYPE/entities, no externalresource; limitbytes/rows.
Rà D:/ vàE:/ metadata, khôngfollow links, pruninggenerated/systemdirs và
haiVIprotectedfixtures; ghi lỗi/exclusions, không sửaACL.
Chỉ boundedpreset/report content, không đọc marketpricecaches/credentials;
gắn association theo tên/cùngfolder cóconfidence, không tự chứng minh cùngbot.

## Track4: activation và delivery

Dùng mt5-runtime-operations để inspect owner trước mọi rollout. ReuseTraderPR33
guards, không restart shared listener/account để tạo hình thức "deploy".
Workspace research jobs cần worktree/job ownership, private output/temp/manifest,
singlewriter vàartifact atomic writes; wire thật vàoV26run, actualprocess
collision/failure probes, không chỉcheck-only. Không tạo/migrate DB hoặc
gửibrokerorders. Nếu actualnativeAPI cutover cần thiếuconfig/owner thì ghi
specificblocker, hoàn tất offline activation phần đã có; không đoán DSN.

Mọi financial artifact mới Zstd9+SHA256+roundtrip, giữfailedattempts.
Finalfull>=1.375tests/0skip,giữ1.358IDs;target<=13,2s;78smokeIDs
10freshprocess<.70s, kểstartup/I/O, không retryđểchọnstreak.
PR105 nếu còntrống,3CIđúngfinalHEAD; giữPRmở. ResultsMD/JSON bốnphần,
CURRENT-CONTEXT/README giữlocator/nextsteps, không tăngauthority.
