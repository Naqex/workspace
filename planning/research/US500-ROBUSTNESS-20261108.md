# US500 noise14 — exposed robustness 2023/2024 trước outcome

Sau development2022 của [bản frozen](US500-NOISE-STUDY-20261108.md), tiếp tục
đúng candidate `us500-m1-noise14-opposite-hardstop-r025-v1` và hai costscenarios.
2022 chuẩn+181,19/stress+117,61USD/156trades;5beststress trades+182,72USD,
vượt tổngnet. Mộtgapaffectedtrade; chưaedge, chưa C1. Không chọn/tune lại
lookback, thời gian, hardstop, leverage, risk hoặc costs sau outcome này.

## Exact scope

- Hai independent annualbooks2023 và2024, mỗi book10k/plannedrisk25USD,
 14cashsessions warmup đầu năm, không cộngPnLwarmup; không continuous2yearbook.
- ExistingpublicDukascopy `usa500idxusd`, M1Bid/Ask,UTC01/01/2023→01/01/2025
 **exclusive**,4quarter/year×2sides=16requests. Không đọc2025+ hoặc mởholdout.
 03/01/2023 đã đọc boundeddatafixture, paper cũng đã côngbố sample tới2024;
 2023/24 ở đây là exposedrobustness, không cleanOOS/independentvalidation.
- Reusepinnedpackage1.51.1,lock/SRI,Node và existingtransportoptions đãreview:
 batch2,interval/pause300ms,retry0,WAFoff/tokencachefalse. Singlecontroller,
 status/PID/log/quarterseals;totaldeadline1800s;CANCELgiữarequests. Dừng403,
 empty/timeout/error;khôngfallbacksource hoặcbrowserbypass. Giữpartialfiles.
- LịchNYSE2023:holidays02/01,16/01,20/02,07/04,29/05,19/06,04/07,04/09,
 23/11,25/12;halfday03/07 và24/11 đóng13:00NY.
 2024:01/01,15/01,19/02,29/03,27/05,19/06,04/07,02/09,28/11,25/12;
 halfday03/07,29/11,24/12 đóng13:00NY. Source[NYSE/ICE](https://ir.theice.com/press/news-details/2021/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar/default.aspx),
 đọc08/11. Cashcalendar chỉreference,khôngbrokerCFDhours.

## Thực thi và đánh giá

Chỉcode delta đểnhận frozen2023/24calendar/year và status/readonlyreview;
không đổisignal/risk/fillformulas. Qualityreviewrawhash/OHLC/grid/pairs/gaps
như2022; gaps giữnguyên và áp dụngexactcausalpolicy. Dùng data mới chỉsau
calendar/source/protocol binding và focusedtests; từngresult cósourceversion.
Không rerun2022 nếu chỉđổi orchestration/calendarcapability không ảnhhưởnglogic.

Báo cả hai năm/từngscenario, tradecounts, months/concentration/gapexposure,
modeledstoplimit và cashreconcile. Ngưỡngnextreview: mỗi năm net dương cả2costs,
khôngmaterialimplementationdefect; nếu đạt chỉđủđềnghị tick/native/riskstudy
mới, khôngcertifypayout/pass. Nếu khôngđạt giữnegativeversion vàđánhgiá cơchế
khác, khôngchọnchỉnămthắng hoặc thayrisk đểcứu. Không mua challenge/brokerorders.
