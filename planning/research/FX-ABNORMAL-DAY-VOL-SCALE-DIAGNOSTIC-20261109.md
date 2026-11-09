# R089: phân biệt fixed-notional và thang biến động, không đổi verdict

Đăng ký sau temporaloutcomes đã biết, trước phép chẩn đoán mới.13extensionyears
có164selected, stressnet+549USD/unit nhưng8/13nămdương và blocks2010–12/
2016–18 âm; frozen temporal gate **not_retained**, không sửa thành pass.
Đây là D1 có giới hạn cho một parent từng qua discovery, không tối ưu mọi loser.

## Câu hỏi và phép đo khóa trước tính

Giữ mọi trade/mask/side/clock/cost. Chỉ hỏi: kết luận yếu có chủ yếu do cùng
100.000EURnotional mang mức biến động khác nhau qua các năm không?

Với mỗi selected row đã reviewed, dùng `calibration_sample_variance`20dayproxy
returns và midpointshockday20UTC. Cảhai biết trước decision00:59. ThangUSD
`prior_end_mid×100000×sqrt(prior_variance)` phải>0. Chia net và từngcomponent
cho cùng thang; tổng là **điểm chuẩn hóa không có đơn vị**, không USD/account,
1R/SL hoặc probabilitypass. Thang20hprice không là volatilityholding7h hoặc
worstloss, không cho sizing25USD, nớistop hoặc gọi đây là botvoltargeted.

Phân rã source-mid/spread/commission/slippage/funding trên cùng path, BidAsk
spread không trừ hai lần. Không scale cash rồi ghi vào ledger cũ. Paper
[Moreira/Muir — NBER primary abstract](https://www.nber.org/papers/w22208)
chỉ gợi ý volatility có thể ảnh hưởng kết quả; chưa đọc fullmethod tronglượt
này. Paper dùng một thiết kế khác, không xác nhận inverse-std20dayproxy của
project, retailCFD hoặc lợi thế quỹ. Đây là own accounting/statistical question.

## Gate cho công sức tiếp, không promotion

- Chỉ xem13extensionyears; discovery2019/22 báo riêng, không cứu dấu.
- Báo sign từngyear và nămblocks, rawUSD và standardizedscore riêng. Không
  filter bỏyear/trade thua, không tìm n/multiplier/sizing/SL tối ưu.
- Chỉ khi **cảhai block đãâm đổi sangdương** và≥9/13extensionyears standardized
  dương thì mới có lý do xét đăngký một risk-scaling hypothesis riêng; chưa
  đủ promote hoặc thay frozenparentgate. Không đạt thì chưa có basis dùng
  riêng volatilityscaling để tiếp parent; chuyển admission cơ chế khác.
- Candidate/code/data/cost/protocol/results giữ nguyên;0newtrial/rawscan/
  network/model/broker/own2025+. Decimal80producer, exactrational sqrt bounds
  từ integerisqrt40places làm oracle cho mọi trade/year/block/total và dấu;
  mutation sai score/known-at/denominator/authority phảireject. Unknown/zero
  scale làmdiagnosticunknown, khôngdropcase hoặcsubstitute1.

Saved riêngdiagnostic và review, bind oldresult/review/rows/observationshashes;
không overwriteoriginalfinancials. Đây là post-outcome diagnostic, khôngOOS
hoặc bằng chứng independentedge. Chỉ một câu hỏi hữu hạn, không mở riskgrid.

## Kết quả đã kiểm

191selectedrows gồm27discovery/164extension, không financialtrial mới.
Chuẩn hóa giữ **cảhai block2010–12 và2016–18 âm**; chỉ7/13extensionyears có
score dương, không đạt điều kiện xem riêngrisk-scalinghypothesis. Oldgate vẫn
not_retained; chưa có cơ sở dùng riêngvolatilityscaling để tiếp parent.

| Extensionblock | Rawnet USD/unit | Standardized score, làm tròn | Exactbound sign |
|---|---:|---:|---|
|2010–12|−4.389|−4,461168|Âm|
|2013–15|+1.873|+2,492396|Dương|
|2016–18|−305|−1,391876|Âm|
|2020–21|+1.538|+2,779522|Dương|
|2023–24|+1.832|+5,347198|Dương|

Score không đơn vị, không1R hoặc tiền account. Decimal80 nằm trong exact
rationalisqrtbounds cho191trades,15years/5blocks/extensiontotal.3signedsynthetic
cases/zero-scale rejection và4mutations score/scale/known-at/authority đạt.
Sameagent/differentmath, không independentfeed/human hoặc risk backtest.
0rawreads/network/broker/newtrials,0,385s gồm review; oldfinancialfiles giữ nguyên.

Privatebase campaign, `execution-v1/fx-abnormal-day-vol-scale-v1/`, saved
`diagnose-fx-abnormal-vol-scale-v1.py`. ResultSHA
`0b0b3922a5d49507b966c9739a6a2a3509687e6a8cbf4469e2090b6d0ec7d8dd`;
reviewSHA`6994c04f751ac3e64d83aa12cc68f9fad1e466c675a0bf6714704082cdee6a28`.
Kết luận chính và bước tiếp tại [temporalresults](FX-ABNORMAL-DAY-TEMPORAL-RESULTS-20261109.md).
