# R093 tuần đáo hạn: năm 2022 âm trước phí, không giữ exact recipe

10/11/2026. [Protocol](OPTIONS-WEEK-METHOD-AND-PROTOCOL-20261110.md) và code
freeze `542ad5a` trước nguồn/outcomes. Đã chạy và review đủ **48 windows,
96 financial cases, 8 books**. Catalogue **93 hồ sơ / 58 policy-model versions**;
price component này chưa là account policy hoặc ứng viên challenge.

## Kết quả đã kiểm

USD trên **1 research unit = 1 USD/điểm chỉ số**, không lợi nhuận tài khoản10k
hoặc cùng khối lượng với các component FX. Mỗi cohort có12windows; reference/
stress là hai kịch bản trên cùng cơ hội, không24independenttrades.

| Năm / cohort | Midpoint gross | Spread embedded | Funding chuẩn / stress | Net chuẩn | Net stress |
|---|---:|---:|---:|---:|---:|
|2019 tuần đáo hạn|+361,4505|4,2785|29,88 /59,77|+321,30|**+279,41**|
|2019 tuần trước, control|+139,3520|3,8800|30,40 /60,92|+99,08|+56,56|
|2022 tuần đáo hạn|−602,4255|5,8785|41,25 /82,54|−655,56|**−708,85**|
|2022 tuần trước, control|−131,9085|5,2725|41,83 /83,58|−185,00|−238,75|

Commission0 theo declared profile đã khóa; slippage cảcohort12×0,5=6USD
reference hoặc12×1,5=18USD stress. Rounding mỗi trade giữ riêng, không ép tổng
các số chưa round thành totalcents. Midbenchmark không là executableprice.

Frozen triage primary stress>0 và>control:2019 đạt (+222,85USDincrement),
2022 không đạt (−470,10USDincrement). Primary8/12positive2019,2/12năm2022.
Đây là exacttransfer trênCFDUS500, khácOEF/S&P100 và timingQC. **Năm2022
pricecomponent đã âm; giảm phí đơn thuần không tạo priceprofit.** Không đảo
long→short hoặc thêm trendfilter từ kết quả vừa thấy. Không kết luận mọi
options-flow strategy vô dụng hoặc mọi portfolio có sleeve này đều bất khả thi.

## Nguồn, correctness và giới hạn

-96/96endpointlocators đủ,605.316jointticks/3.026.580fields khớpnative/integer
  và separateFractionrawdecoder.48cachehits/48GETmới; khôngpadding/nến giả.
-Calendar oracle dựng thirdFriday bằng lịch ngày riêng; so48specs và manual
  UTCfixtures, gồm JanuaryMLK/AprilGoodFriday/winter/summer. Thu2019/2022
  retrospectivecalendar, không fullPIT-calendarpublication audit.
-5focusedtests đạt trước market; synthetic96financialcases đủ. Initialtest
  fixture sai kỳ vọngFebruary2019Monday19 thay11 được sửa trước nguồn: third
  Friday15Feb nên Monday11Feb; privatefailure/snapshot giữ, không đổi rule.
-Actual5rawmutations và5financialmutations reject (price/time/count/authority/
  bytes;net/funding/spread/sourcequote/fundingclock). FinancialreviewFraction
  không gọi producer, đối soát cả8books/frozenverdict với ticks đãreview.
-Sameagent/provider arithmeticreview, chưa independentfeed/model/human audit.
  Sourcequotes không chứngminh executablefills; chỉ endpoints, chưa intrapath/
  SL/sizing/margin/equityDD/targetspec/prop/cleanOOS/forward. Đủsource không là
  đủedge. Khôngbroker/modelcalls hoặcown2025+.

| Phase thực đo | Wall | CPU |
|---|---:|---:|
|96sourcehours,48GET+48reuse|29,943s|4,485s|
|Fullraw/calendarreview|20,146s|20,078s|
|Economics+sealedoutputs|1,055s|0,984s|
|Financialreview+mutations|0,037s|0,031s|
|Tổng4workerphases|**51,181s**|25,579s|

Không gồm32,404sdownloadmethoddocs hoặcresearch/code/Git, khôngspeedupA/B.
Khôngworkerbackground:sourcehandle39380/review66827 vàeconomic/reviewterminal.
Tính tiền~1s; chưa có nút thắt cầnGPU/Rust hoặc tối ưu engine để tìm winner.

Privatecampaignbase`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/options-week-source-v1/` và`options-week-economics-v1/` giữ
configs/pins/snapshots/rows/locators/seals/results/reviews/progress/events;
scripts`prepare-options-week-source-v1.cjs`,`run-options-week-v1.py`,
`review-options-week-v1.py`. Originalprotocol/script pins không sửa.

-Source result SHA`770e20dfa2e9682edaf27a18fba54787dd10b1e819d4edd39a32c21abcf39929`.
-Economic result SHA`a2002b3b9566d0f257abc32301b023117381ef65b1607190e92e7cba19a3e9a9`.
-Reviewer SHA`d65b9e5b75ad7e23f88f7a4cc095bc1e11c3bbe943f44d9c61bf223cf894a1c1`.

**Quyết định:** gác exactR093, khôngtemporalbulk/feefilter/signgridcứu. Chuyển
sang [portfolio admission](PORTFOLIO-RESEARCH-AND-ADMISSION-20261110.md) theo
yêu cầuowner, giữR093negative; chưa gộp các tổngPnL khác units/timing thành
portfolio. C1/C2chưađạt. OwnerđãxóaappGoal; tiếp taskđượcgiao, khôngtựtạolại.
