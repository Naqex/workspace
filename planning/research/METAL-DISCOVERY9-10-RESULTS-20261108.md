# Gold 15 năm và intraday — outcomes và quyết định

**Chưa đủ để đề xuất challenge.** 15annualbooks riêng2010–2024, không continuous
portfolio hoặc cleanOOS; bắt đầu mỗi năm từ10k/50k. [Frozen9](METAL-LONG-HISTORY-20261108.md),
[Frozen10](METAL-INTRADAY-DISCOVERY10-20261108.md). Tất cả indicativeBidM1+
declaredAsk/costs, không nativeMetalrisk/prop/fulltickDD;2025+vẫnđóng.

## H4: normalizedsum% qua15annualbooks, không CAGR

| Rule/size | Chuẩn/cao | Stressyears dương | Closedtrades chuẩn/cao | Yếu nhất trong ba5yearbands, stress |
|---|---:|---:|---:|---:|
|Donchian10k|−5,09 / −21,79%|3/15|530/534|−10,33%|
|SMA10k|+13,58 / +5,57%|9/15|195/197|−2,19%|
|Zscore10k|−26,31 / −40,51%|1/15|1240/1245|−20,43%|
|Donchian50k|−1,84 / −21,04%|6/15|592/602|−12,39%|
|SMA50k|+18,77 / +8,07%|10/15|219/220|−1,66%|
|Zscore50k|−39,95 / −58,76%|1/15|1435/1445|−24,47%|

SMA50k làresearchsurvivor theo10/15frozen gate, không “đủedge”:8,07% là tổng
netannualbooks/50k qua15năm, **không8,07%mỗi năm**. Data-dependentselection,
floating/open cuối năm không forceclose, phase/dailyDD chưa kiểm. Tăng nominal
capital không tự nâng%return:giữ0,25% nhưngminlotfloor thaytập lệnh thực hiện.
50k0minlot skip,10kSMA40skips; không tăngriskpercent hoặc mua50kaccount.

## H1, size50k/risk0,25%: cả ba không promote

| Rule | Normalizedsum%chuẩn/cao | Stressyears dương | Closedtrades chuẩn/cao |
|---|---:|---:|---:|
|Asia→London breakout|−52,39 / −154,34%|1/15|2868/2868|
|RSIreentry|−126,98 / −209,94%|0/15|2586/2642|
|Afternoonreversal15–19London|−62,53 / −125,36%|0/15|2214/2214|

Tổngâm vượt100% là tổng15books riêng, khôngnegativeequity của mộtliveaccount.
Coarsekhông internalbrake; không dùng bảng này suy realizedcapitalpath/propbreach.
No minlot skips ởH1study50k. Không cứu bằng giảmphí, sửa giờ/threshold hoặc bỏ
failureyears. Source hypotheses/clockbenchmarks không chứng minh lợi thế.

## C2 và performance

Discovery9source6835bef8:10metaltests/9subtests,180accountingrowsverified;
Discovery10sourcedb5550d6:3newH1tests+38related/26subtests trước run,90accounting
rowsverified,32oldEURUSDquartercases exact trước outcomes. Source snapshots/
protocol/raw/runtime/specs giữ riêng từngattempt, không sửapins đểreuse.
Discovery9wall117,19s/CPU111,22s;Discovery10wall102,21s/CPU100,86s, mỗi lượt đọc
5,4millionM1mộtlần rồi chạy180/90rows. Không GPU/model/brokercalls; noasserted
speedupso nativeBid/Askfulltick. Lầnsauđổi hypothesiscó thểcacheaggregation nếu
measuredreuse đáng đầu tư;không cần nới validationđể nhanh hơn.

Private root`E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1`:
`metal-discovery9-screen/attempt-v1/summary-review.json` và
`metal-discovery10-screen/attempt-v1/summary-review.json` giữnumbers/counts/cash
checks. Currentmetalbranchf8879b32 cònfixnativeholidayentry đãtái hiện; chưa
merge/updateD:source78a8397fkhi3nativeworkerskhác cònchạy. C1/C2campaignACTIVE.
