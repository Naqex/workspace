# H1 native volume được round4, không phải raw equality

Phát hiện trongreviewhistoryattempt3 trướcPnL. SourcefixtureJanuary2019 không
có caseđủprecisionđểlộ mấtchữsố; fullhistoryreview chặnGBPUSD2010H1timestamp
1292796000000:rawvolume1543,528449millions,nativeexport1543,5284. Không có
kếtluậnpricebug từvolumecomparison này; vẫn phải kiểm toànOHLCriêng.

Installed`dukascopy-node`1.51.1`dist/index.js`:processData→normalise→aggregate,
`getOHLC`→`roundNum(volume)`→`Number(value.toFixed(4))`;formatVolumeởmillions
khôngrescale. NativeH1aggregation vẫnroundvolume dù sourcehour không đổi.
Đây làlossyrepresentation cócăn cứsourcecode, không đặt tolerance rộng để
che sai lệch. Volume không là signeddealerorderflow hoặc tradeabilityproof.

Reviewcorrection:rawintegerdelta/Fraction so4OHLCvớiexport nhưđãđăngký;
volumeexport so **exact deterministic4decimalrounding củaIEEE754rawnumber**,
không so rawvalueđầyđủ rồi chấpnhậnsai sốtùyý. Giữ rawcache/unroundedvolume
bấtbiến,đếmrowsbịround vàghi volume_basis trongsupplementalmetadata/receipt.
Không sửa request/quotes/rows/seals/manifest hoặc downloadlại. Original
protocol/pins vẫn nguyên. Phiênbảnmới không được tự xemnativevolume là raw.

Nếucầnvolume-fullprecision chofeature sau này, đọcrawboundsource hoặc tạo
versionnormalization mới vàkiểm;không giảphục hồitừ4decimals. Price-only
component cũng phải cite datarepresentation vàkhônginferorderflowtừvolume.
Mutationvolume ngoài phép biếnđổi dựkiến phải bịchặn; source/permissongates
giữ nguyên. Chưa tính PnL/signals/weights/correlation hoặc mở2025+.
