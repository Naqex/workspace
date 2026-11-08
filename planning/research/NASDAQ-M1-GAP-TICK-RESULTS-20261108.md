# Tick gap review: 2019 vẫn thiếu; 2022 có nguồn nhưng chưa được vá thẳng

[Protocol](NASDAQ-M1-GAP-TICK-PROTOCOL-20261108.md) đăng ký8hours trước fetch.
Đã terminal/reviewed205.676jointticks,1.028.380time/price/volumechecks khớp
rawdelta. Cả8responses có dữ liệu; source fetch4,871s, review9,598s. Không
strategy simulation, rawoverwrite hoặc accountstate clear trong bước này.

| Source issue | Kết quả đã đo | Được kết luận gì? |
|---|---|---|
|15missingcashminutes ngoài18Oct2022|Không có tick trong đúng các phút đó; maxgaps71,754–306,918s tùy hour|Không được tạo nến hoặc xác minh không có stop ở nguồn/broker khác; R0652019 vẫnunknown|
|7missingminutes18Oct2022,15:24–15:30UTC|Có tick ở cả7phút; tickhour maxgap1,388s|Có nguồn để đăng ký derivedview, chưa được tự gắn vào book|
|CommonM1 bridge|916sidebars/3.664OHLCfields, chỉ2Openfields của15:31UTC không exactfirsttick|Strict gate ban đầu không đạt; không ignore conflict hoặc gắn7patchrows rồi tuyên bốsourcepass|

15:31UTC18Oct2022: sourceM1BidOpen11068,109/AskOpen11069,561; firstjointtick
lúc15:31:00.071 cóBid11069,257/Ask11070,051. Hai sourceOpen **có xuất hiện**
trong583ticks cùng phút nhưng không là firsttick và không bằng lastpregapclose.
Vì thế chưa được gọi là stalepricebug đã chứng minh hoặc sai source decoder.
OldM1Open vốn chỉ là intervalproxy; fidelity trên2pilot hours không chứng nhận
mọi M1Open trên wholehistory là firstjointtick. H/L/C của commonminute khớp.

**Admission:** false cho proposedmissing-onlypatch như protocol đã khóa;
`proposed-patches.json` chỉ là đề xuất7minutes/14sidebars, không approvedinput.
Không chạy lại R065 sau gatefail. Giữ2019unknown/2022unknown và olddata/pins.
Price/time/order mutations reject; fullsourcehash binds cả8requests/rawproofs.
Sameprovider/agent, không independentfeed/targetbroker/continuousquote proof.

Private`execution-v1/nasdaq-M1-gap-ticks-v1` tại campaignroot giữ ticks/rawproofs/
config/manifest/census/result/review/diagnostic. ProducerPID12496 vàreviewer
terminal0. ResultSHA
`6dc324896ff217c940befe9a0f2013b3a4b207ff0b69e68767be24c21e5fd1e9`,
reviewreceiptSHA`0b3ca0ebb03454f6f0f223063e12a1887d188208870b63f79283c12ff86b1301`.

**Tiếp:** [protocol nguồn mới](NASDAQ-TICK-DERIVED-HOUR-PROTOCOL-20261108.md)
có semantics riêng: whole15:00–16:00UTC18Oct2022
derived từ jointticks, so mọi retained/changedfield với oldview và xác nhận
mọi newprice từ actualrawticks. Không sửa2oldOpen cho khớp hoặc hạ commonmatch
gate. Chỉ sau review mới tạo mixedsource2022revision rồi chạy affectedbooks
cùng exactrules/risk/cost, giữ2019unresolved. Không thêm policy/parametertrial
chỉ vì source revision; không coi input improvement là edge/challengeproof.
