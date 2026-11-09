# R033 pilot ba đồng tiền: không giữ exact adaptation

[Protocol](FX-CROSS-SECTION-PILOT-PROTOCOL-20261108.md) đã commit `2612718`
trước compute. Đã hoàn tất source-panel/numeric/review. **Primary không đạt
tiêu chí giữ**; không ưu tiên mở rộng universe hoặc chọn opposite control để
cứu exact adaptation này. Chưa có chiến lược challenge-qualified.

## Ý tưởng và kết quả

Mỗi đầu tháng: mua đồng mạnh nhất, bán đồng yếu nhất của EUR/GBP/AUD theo
completed-month return vừa qua. Giữ một tháng, full roll. Dữ liệu 2014–2024,
132 monthly contributions; mỗi leg có notional cố định5.000USD, không compound.
Đây là continuous allocation component, **không account 10k, risk0,25%, SL
hoặc causal tick backtest**. Không gọi tổng âm là drawdown của tài khoản thật.

| Primary, 132months | Phí chuẩn | Phí cao |
|---|---:|---:|
| Gross sau BidAsk embedded, trước explicit costs | −1.331,62USD | −1.331,62USD |
| Commission cộng | 67,87USD | 67,87USD |
| Slippage cộng | 0,00USD | 54,32USD |
| Funding debit cộng | 4.149,47USD | 8.298,88USD |
| Net, gồm final floating | **−5.548,94USD** | **−9.752,64USD** |
| Cohort years net dương | 0/11 | 0/11 |
| Final floating còn mở | −149,86USD | −149,86USD |

Net native được round từ biểu thức unrounded; tổng các cost fields đã round
có thể chênh vài cent. Reviewer kiểm đúng từng biểu thức và từng field, không
ép net bằng cộng/trừ các displayed fields. Funding là **scenario khai báo**
10/20USD/lot/ngày, cả hai side, weekday22UTC/Wed×3; chưa target broker swaps.
Kết quả không chỉ yếu vì funding: gross sau spread đã âm. Không hạ phí để
tạo winner. Không ngoại suy từ ba currencies sang toàn bộ momentum family.

| Stress block | Net USD của contributions |
|---|---:|
| 2014–2016 | −2.289,04 |
| 2017–2019 | −2.542,89 |
| 2020–2024 | −4.920,71 |

Mỗi cost book có131 closed monthly components +1 final open mark với2 legs.
Không force close December2024; final mark chỉ chịu entrycost và funding,
không exitcost. Cash contribution tổng chuẩn/cao−5.399,08/−9.602,78USD;
cash+floating khớp net. Không là tiền có thể rút hoặc actual account equity.

## Chuẩn hóa data đã thực thi ở lát này

Panel **864 rows** =3 instruments×144months×2roles, có instrument/units/role,
target/known-at, price basis, source bindings, quality/exposure và authority.
EURUSD giữ exact observed quotes từ panel đã review. GBP/AUD signal dùng H1
Close kết thúc tại cutoff; entry dùng H1 Open và known-at upper bound+1h.
Chưa actual joint quote hoặc execution fill. Hai rows AUDUSD January2013 thiếu
vẫn explicit; nằm ngoài mọi feature/entry/exit của window đã đăng ký trước
outcome. 132months tính được, không bỏ tháng vì kết quả thiếu/xấu.

Data flow: **raw/sealed parent → panel theo role/known-at → xếp hạng causal →
monthly contribution/cost → separate review**. Metadata không trộn với quyền
gửi lệnh. Parent data/snapshots bất biến; output mới có parent hashes và source
snapshots. Không migration, rewrite raw, database hoặc RAG/service mới.

## Correctness và hậu kiểm

| Lát | Bằng chứng và quyết định |
|---|---|
| Trước outcomes | Side/flatcost, rank/tie, missing signal, future-known-at rejection, funding boundaries/triple, finalmark noexitcost đều qua preflight |
| Source/causality | Parent seals, 864rows, original clocks/known-at/side/units, mọi ranking132months được kiểm lại |
| Financial review | Fraction và rounding/calendar code khác, 4books/528monthlyrows/1.056trade-cost cases/22.944funding events; khớp native costs/cash/floating/cohorts/blocks |
| Mutations | 9 lỗi giá, fake tick, missing row, rank, future signal, funding, side, false challenge và false OOS đều bị reject |
| Numeric | 2,288s wall /2,219s CPU; bao gồm panel preparation, pins và serialization |
| Review | 1,560s wall; không đọc lại toàn raw tick history hoặc chạy lại simulation |
| Reliability | PID26248 và reviewer terminal0; không failure/retry hoặc active research worker của lượt này |

**Sai lệch so với protocol:** preflight trước compute chưa thực thi riêng hai
nhánh missing entry/future exit đã hứa. Lượt numeric thực tế đủ input nên
không đi vào các nhánh này. Đã kiểm bổ sung **sau run**, bằng cách thực thi
nguyên thân loop từ AST của runner đã freeze trên6cases synthetic: missing
entry, missing exit leg1/leg2, missing signal, tie-flat và terminal open-mark.
Cả6đạt trong0,037s; case leg2 giữ partial trade để chẩn đoán nhưng không tính
net của tháng thiếu. Đây là bằng chứng bổ sung, **không sửa lịch sử thành đã
preflight đầy đủ**. Không sửa/rerun numeric; negative verdict vẫn giữ.

Same provider/agent với code paths khác không là independent human/model audit.
NYSE calendar kế thừa parent đã review, không recompute độc lập trong reviewer
mới. Chưa source feed độc lập, tick/SL/prop equity, actual funding hoặc clean OOS.
Correct arithmetic không biến negative economics thành một strategy có edge.

Không producer bug mới trong scope đã kiểm. Tối ưu có ích hiện tại là reuse
sealed panels/caches thay vì parse/tải lại raw; chưa bottleneck cần GPU/Rust,
đa máy hoặc vectorDB. Workflow hiện có trong research/qualification/evidence/
retrospective skills đã đủ, không tạo skill quản lý khác chỉ cho lượt này.

## Evidence và bước tiếp

Private campaign root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/fx-cross-section-pilot-v1` giữ panel/source-admission/decisions,
4books/result/review/config/manifest/source-snapshot/progress/events.
Runner `run-fx-cross-section-pilot-v1.py`, reviewer
`check-fx-cross-section-pilot-v1.py` được snapshot/pin trước outcomes.
`missing-transition-review.json` và
`check-fx-cross-section-missing-transitions-v1.py` giữ6checks bổ sung và
deviation ở trên. Lượt sau phải có receipt các nhánh trước job economic mới.
ResultSHA `964542e26d45d701db477b02ce1a81de89bc12f0dfaa10d088bdd0bb0f67f9fe`;
reviewerSHA `b6889f9691dfb528f27269bccf8a364527324392f6770ea4816487c2f3930ca6`.
0network/model/broker calls, không 2025+ hoặc thay authority.

Catalogue vẫn **60hồ sơ /42research policy versions**: R033 thêm component
evidence, chưa là account policy mới. Không đạt frozen8/11years/all3blocks/net
gate. Không đảo control, đổi lookback/universe hoặc hạ funding để cứu bản này.

Goal C1/C2 vẫn active. Lát kế tiếp: quay lại hypothesis R019 đã deferred để
chốt một stateful break→retest recipe có expiry/invalidation, so với parent
R015; admission phải giải thích vì sao state mới có thể lọc false breaks và
tách H1 diagnostic khỏi actual tick execution. Không cần paper chứng minh sẵn
exact thresholds, nhưng phải freeze logic/trial/cost/risk trước outcomes.
