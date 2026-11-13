# Gold B1 — đối soát Q1/2010, chưa đủ kết luận đi quỹ

**B1 đã hoàn tất phép thử được giao; chưa có kết luận Gold đủ chuẩn challenge.**
Đã sửa protocol theo AR01–03, kiểm19 tình huống nhỏ rồi chạy đúng Q1/2010 ở
risk125/200USD. Không đổi tín hiệu, bỏ Short, mở giá2025–26 hoặc chạy rolling120cases.
Theo chỉ thị mới nhất của owner: kết thúc lát này rồi dừng, không gửi tin ASTRA.

[Số liệu và hashes](GOLD-CONTINUOUS-B1-RESULTS-20261113.json) ·
[Amendment v1.1](GOLD-CONTINUOUS-B1-AMENDMENT-V1P1-20261113.md) ·
[Bằng chứng đợt A](GOLD-EURUSD-PORTFOLIO-STAGE-A-20261113.md).
v1 gốc/hashes và log lần test lỗi đều giữ nguyên.

## Kết quả dễ đọc

Tài khoản mô phỏng50.000USD; một lane legacy stress40/40, chưa phải phí thật
FTMO Swing. Lệnh được tạo liên tục từ H4 SMA20/80–ATR14, seed đầy đủ Nov–Dec2009
(256H4), không dùng lại220lệnh năm để giả làm signal liên tục.

| Chỉ tiêu Q1/2010 | Risk125USD =0,25% | Risk200USD =0,40% |
|---|---:|---:|
| Vào lệnh / đã đóng / còn mở | 6 /5 /1 | 6 /5 /1 |
| Lãi/lỗ đã ghi vào số dư, gồm swap | −429,90USD | −688,19USD |
| Lãi/lỗ vị thế còn mở, đã dự phòng chi phí đóng | −59,29USD | −92,23USD |
| Tổng lãi/lỗ theo giá cuối mẫu | **−489,19USD** | **−780,42USD** |
| Swap debit đã trừ | 182,40USD | 294,00USD |
| Daily Loss lớn nhất tại các điểm đo | 122,73USD /0,24546% | 194,51USD /0,38902% |
| Lỗ sâu nhất so với50k tại các điểm đo | 527,50USD /1,055% | 840,01USD /1,68002% |
| Peak-to-trough DD tại các điểm đo | 676,39USD /1,35278% | 1.091,73USD /2,18346% |
| Conditional fully-held-minute static loss | 528,22USD /1,05644% | 841,13USD /1,68226% |
| Conditional fully-held-minute peakDD | 678,37USD /1,35674% | 1.094,89USD /2,18978% |

“Tại các điểm đo” không có nghĩa toàn bộ đường giá. Điểm open dùng trường Bid
M1 và Ask giả định Bid+1; timestamp close cuối phút là proxy. Conditional envelope
chỉ dùng extrema phút giữ trọn vị thế; giả định thứ tự thuận lợi rồi bất lợi để
tính bound, không phải tick thật. Ba phút có SL bỏ toàn bộ extrema không biết
trước/sau thoát. Vì thế không lấy các con số thấp này làm chứng nhận dư DD.

Cuối mẫu còn một SELL và một intent EXIT đúng mốc01/04 chưa fill. Không force
close và không mở giá sau cutoff. Không có margin rejection trong hai case;
margin vẫn legacy10:1 trên fixed50k collateral, chưa mô phỏng margin hãng đích.

## Độ đúng và dữ liệu còn thiếu

| Kiểm chứng | Kết quả / giới hạn |
|---|---|
| Source | SHA raw khớp; pin107module native, harness và tests. Candidate/cost byte parity; market/stop helper selected AST parity. Chỉ import authoritativeD:, khôngC:WIP. |
| So bản gốc risk125 | Cả9decisions (gồm intent tại cutoff), ATR/distance/quantity khớp;5closed trades khớp side/fill/PnL/financing; cash−429,90USD khớp sealed Q1 oracle. |
| H1→M1 | Ba stop exits thu hẹp vào phút nằm trong interval H1 gốc; hai strategy exits giữ thời điểm; không đổi cash/fill trong prefix này. Không suy parity này cho15năm chưa chạy. |
| Tính tiền | Fraction review cho10closed trades/hai case; gross,commission,slip,net,swap,cash/equity bridge đạt. Năm mutation về fee/sign/qty/intent/ATR đều bị phát hiện. Đây là review cùng agent, không independentfeed/reviewer. |
| Dữ liệu | 89.524M1/129.600phút lịch =69,0772%. Denominator gồm weekend/closure; chưa có lịch phiên độc lập để gọi phần thiếu là lỗi feed. Không fill/drop. |
| Giá khi giữ lệnh | Mỗi case có595khoảng source gap khi giữ vị thế,14reset không có giá cùng mốc và3stopminutes không biết thứ tự. Đây là số sự kiện theo từng nhóm, không cộng thành số phút hay mẫu độc lập. |
| Prop | Không có supported/conditional breach witness trong phạm vi điểm đã đo. **Survival/pass vẫn unknown**; native approximate event trả blocked_by_data, không phát phasepass. |

Cash anchor Prague được tính đúng bằng tiền, tách khỏi quotequality. Gap không
được “chữa” bằng giá mới về sau. Profile declared `<` tại daily5%/overall10%,
equality chưa breach; owner internal caps strict `<2,5%`/staticloss`<6,5%` vẫn riêng.
Supported breach nếu có sẽ latch dù lịch sử khác unknown. Không có witness chưa
chứng minh không có breach. Q1 này âm, cũng chưa đủ bác edge15năm.

## Kiểm thử và giới hạn tích hợp

19unittest đạt trong0,038s (không gồm startup). CF01–08: geometry/capital và
fresh sizing, full vs truncated seed, nến đóng/intent causal, missingH1,
pending/position quaDec31, serialized split/resume, fundingdedup/Wed×3,
Prague23/25h, reset trước fee, stale/missingquote uncertainty, supported vs
conditional/equality/firstbreach, native min4entrydays/flat/pending0/phase2reset,
minlot/margin/rounding và SL postexit extrema. CF09 chỉ synthetic rewardclock:
14×24h/đợi naturalflat, lossbalance không reset, nextaccount firsttradeclock,
80%potentialreward, approval/receivedcashunknown, thiếucontract thì stop. CF10hoãn.

Lượt test đầu có3errors: hai fixture tạo OHLC không hợp lệ, một fixture quên
gọi native calendar boundary khi nhảy ngày. Đã sửa **đầu vào/cách gọi test**,
giữ assertions và logs; không phải bằng chứng phát hiện ba lỗi sản phẩm.

**Gap còn lại:** native `evaluate_prop_lifecycle_event` nhận `approximate` thì
không tiến phase clock/dailyanchor. B1 dùng native money/calendar oracles cho
cash và witness, chỉ probe lifecycle approximate để chứng minh không pass giả.
Synthetic full-quality chuyểnphase đã kiểm nhưng **chưa có nối challenge
continuous thực trên M1 có gaps**. Indicator/cash adapter serialization đã kiểm;
CLI checkpoint không đồng nghĩa có automatic CLIresume. Không thay Trader
source/pin/runtime để né contract này.

## Thời gian và bài học kỹ thuật

| Phase | Thực đo |
|---|---:|
| Shared rawhash + parse Nov2009–Q1/2010 | 3,697s |
| Case125: loop + metrics | 16,058s wall /13,813s CPU |
| Case200: loop + metrics | 21,517s wall /14,500s CPU |
| Hai case + chuẩn bị + artifacts | **41,554s** |
| Process peak working set | 129.818.624bytes ≈123,8MiB |
| Private evidence tại seal | 719.337bytes ≈702,5KiB |

Đây là compute benchmark; không tính thời gian agent viết code, research, Git,
review. Chênh wall/CPU có ảnh hưởng tải máy; không suy speedup thuật toán từ đó.
Status/checkpoint/cancel mỗi10.000source rows, deadline900s/case; lần chạy này
không timeout/cancel và không retry financial. Cancellation/deadline branches
có trong code, chưa diễn tập ngắt subprocess thực; không claim đã kiểm phần đó.

**Sửa estimate cũ5–30phút:**60quarterlystarts đến cuối2024×2risk tương đương
3.660quý-account exposure, không chỉ120quý. Ngoại suy tuyến tính16,06–21,52s/quý
cho khoảng**16,3–21,9giờ tuần tự**, chưa gồm warmup/checkpoint lớn/phasecallbacks.
Case15năm có thể vượt900s (ước16–22phút), nên không dispatch với cap hiện tại.
Đây là dự báo từ prefix, chưa fullbatch benchmark hoặc cam kết ETA.

| Mặt cần cải tiến | Quyết định sau B1 |
|---|---|
| Correctness | Đã giữ seed, cash/quality riêng và chặn pass; native cash-clock/price-quality gap cần design review trước B2. |
| Performance | Per-minute calendar và money/Pydantic calls là ứng viên nút thắt nhìn từ source; chưa profile để quy tỷ trọng. Nên đo bounded rồi reuse reset schedule/threshold đã khóa, không bỏ risk checks. |
| Reliability | Giữ source/hash, progress/checkpoint, failure attempts; không tự rerun hoặc overwrite completed output. Processcancel/CLIresume thực còn chưa chứng minh. |
| Economics | Không thêm costlane, Short-only hoặc sửa exit; phí tài khoản đích chưa đủ, EURUSD StageA không rerun, chưa counterpartportfolio. |

Bước đề xuất **chưa thực thi**: chốt tối thiểu contract native để cập nhật cash
anchor/clock mà không nâng pricequality; fixture cho supported breach vẫn latch
khi lịch sử unknown; profile bounded và đo lại cùng output trước khi xin scope
rolling. Chưa có lý do chạy120cases, fundedseries hoặc ghép một leg EURUSD âm.

Private evidence:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/gold-continuous-B1-20261113-v1/`
gồm registrations trước outcome, sourceparity/binding, logs ba lượt fixture,
hai prefix/checkpoints, verification/negativecontrols và seal. Giá raw không
commit. Một branch/PR69 giữ mở; không merge hoặc gửi prompt ASTRA.
