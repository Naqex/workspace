# Sau WTI: khảo sát chênh lệch S&P–Nasdaq, chưa thiết kế bot

10/11/2026. [WTI gapreview](WTI-GAP-TICK-RESULTS-20261110.md) không tìm được
tick để lấp6sampledholes. Không lặp source đó. Chọn một **pair cố định** vì
hai chỉ số cùng thị trường Mỹ nhưng khác độ tập trung ngành; đây là câu hỏi
về quan hệ tương đối, không cược cảhai sẽ lên. Khác các exact momentum/hour
recipes đã gác, cùng broadrelativevalue family củaR035/R067, chưa chứng minh
independentedge. Không mở universe/pairsearch hoặc chọn theo PnL.

## Primary method đã đọc và chưa thể copy thành recipe

[Baek etal.2020, publisherPDF](https://mdpi-res.com/d_attachment/sustainability/sustainability-12-06791/article_deploy/sustainability-12-06791.pdf),
DOI10.3390/su12176791: đọc§§2.3–2.5/3.4/4, xemrenderpage7. Futuresdaily,
train2015–17/test2018–July2020, chọnpair/hedgeratio trước test. Rule dùng
rolling15days nhưng§2.4.1 ghi **plusSD cho cả ngưỡngshort và ngưỡnglong**;
§3.4 lại phân biệt lower/upperbound. Không tự sửa thànhminus rồi gọi exact
replication. Theoreticaltargetfills được tác giả thừa nhận; chưa đủ executable
cost/roll/synchronization recipe. Paperfuturesratio0,72 không là CFDlotratio.

PDF24pagesSHA`0ea87f5c2e3a1eebfbdb3ff008ae4b2dd7f62a0fb935e3c1e663996ed96ae54e`.
Private`execution-v1/index-pair-method-source-v1/` giữ publisherPDF/text/layout/
page7render. HTTPSnormalvalidation, không bypass429 của publisherHTML.
Consolecp1252print lỗi sau khi đã lưutext; receipt giữ, dùngUTF8đọc tiếp,
không tải lạiPDF. Đã xem source phương pháp/giới hạn, không fullappendix hoặc
independentaudit/replication. Không lấy headlineperformance làm expectededge.

[UOWpaper](https://documents.uow.edu.au/content/groups/public/@web/@inf/@math/documents/doc/uow177508.pdf)
chỉ đọc abstract/context tronglượt: **sameindex futures–spot**, khác haiindex
CFD; chưa dùng để xác định rule hoặc nêu cost/return của project.
GitHubdemo search đãthấy nhưng chưa audit/license, không clone/import/data.

## Quyết định riêng của project trước số liệu mới

Chưa nhận exacttradingrule từ paper. Bước được nhận là **source admission**
cho USA500.IDX/USD vàUSATECH.IDX/USD trên cùng clock. Native1.51.1metadata
đã kiểm local: tick/grid/source availability không là xác minh targetcontract.
Mỗi CFDcó Bid/Ask/funding/dividends/lotgeometry riêng; tương quan cao chưa là
equilibrium, hedgekhông bảo đảm giảm tailrisk hoặc đủdaily/overallheadroom.

[Sourceprotocol](INDEX-PAIR-SOURCE-PROTOCOL-20261110.md) khóa calendar2018/21,
8H1exports/96monthsideinputs. ReuseacceptedNASwarmup8raws theo exacthash;
không pairoutcome/tuning/statistics/returns/PnL trongbướcnguồn. Xem source/sample
census trước khi đăng ký diagnostics; không đổi sampleclock sau coverage.

Nếu nguồn đủ, bước sau mới khóa formation method và review riêng trước tính
statistics. Nếu quan hệ đáng nghiên cứu, recipeowncode phải chốt rollingpast,
exit/stop, twoleg delayedfills/partialunknown, exposure/margin/funding/costs
và controls trước economics. Chưa quyết định SVM/OLS/Kalman/model hoặc thresholds.
Không dùng pvalueđẹp thay edge; chưaR092/accountpolicy/challengecandidate.
Gold/FXpair negatives và catalogue91/58 giữ. Existing skills đủ, không cần
package/MCP/provider/account mới hoặc mở holdout2025+.
