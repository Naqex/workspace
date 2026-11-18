# S03 — revision nguồn v2, chỉ13giờ GBP2024

Đăng ký trước admissionv2/financial,18/11/2026. Đây là revision nguồn có
traceability; giữ nguyên recipe, cohort, naturalSL, costs/risk/target và
tiêu chí của [S03](SOLO-THREE-ASSET-VALIDATION-PROTOCOL-20261118.md).
2024historical/exposed;2025–2026đóng; không cấp broker hoặc muaChallenge.

## Căn cứ và quyết định

Sourcev1 đủ1.632hours/7.287.413ticks nhưng13hours/26sideOHLCdifferences.
Independentrawdecoder khớp67.501ticks13hours; independentmonthlyH1decoder
khớp514explicitrows/side với H1cũ. Khônglỗilocal/timezoneshift/calendarclip
đãtìmthấy; vendorinconsistency chưa cónguyênnhânxácminh.

[Sensitivity đã đăng ký](SOLO-VALIDATION-SOURCE-DISCREPANCY-20261118.md)
commit`811ac4f` thay đúng13OHLCrows/side bằngpairedticks. Kết quảvàreview
độc lập xácnhận full138raw2024/SL/deadline/1.632hours vàDev300facts khôngđổi.
ResultSHA `cc27178c2514fa1d101d4ce9f7c713b7f724bab23729d8d0a0386401783bd6dc`;
independentreviewSHA `0ce93081f17034bcfd34e2a8e5735b560b7415532c33f28c652102b1f9385720`.
RoundedSLunchanged không chứng minh ATRgiátrịunchanged.

Chọn canonicalworkingview13hours từpairedticks để signal/execution cùng
mộtrepresentation, dựa sourceproof chứkhôngPnL. Khôngkhẳngđịnhticksđúng
brokerhơnH1cũ; samevendor/targetfeed/news/margin/pathunknown giữ nguyên.

## Revision và nơi ghi

JobS03giữnguyên; `source-release.json`, `gbp-source/` (v1) vàsensitivity đều
read-only. Ghi mới `correction-release-v2.json` và `gbp-source-v2/`, có
registration/correctioncard/H1workingbooks/proof. Reuse đủ1.632rawfiles và
binaryfiles từv1 bằnghash/path, khôngdownload/refetch/copycache khôngcầnthiết.
Khôngđổi13hourlist đã đăng ký, khôngallowtolerance/bỏmismatch.

Oldreleaseproducerclosure được kiểm theo committedbytes`5ccdc6d`, oldreview
vàinputpins; không yêu cầu currentharness vẫn giốngoldharness sauv2integration.
Đây là xácminh historicalproducer rõràng, không bỏpincheck. Currentv2code/
protocol/tests/newreview được commit vàbind vào correctionrelease riêng.
Nếu dùngfilecũcho currentexecution, file đó phải khớpcảcurrentreviewpin.

`solo_validation_source.py` giữnguyên. Modulecorrectionv2 chỉ làm nguồn và
binding; financialharness reuse nguyên104/108accountpolicy, explicit
sourcefacade/releasepathv2. Không monkeypatch globalJOB/window, không
sourceautofallback vềv1 sauv2fail. Oldfinancialregistration/run chưa tồn tại;
nếu phát hiện chúng cósẵn thìdừngtrướckhithaybinding. DefaultS02 vàV3 giữnguyên.

## Cổng bắt buộc trước v2financialprepare

1. Kiểm canonicalv1failedproof/source-release/registration/manifest và
   sensitivity/result/review đúnghash/status. Kiểm138facts/fullcensusidentical,
   nonOHLCunchanged, Dev300parity; không chỉtinbooleanPASS trongreceipt.
2. Re-decode13rawhours, soexactbinary/OHLC. WorkingBID/ASKbooks chỉthayOHLC
   đúng13rows; timestamp/volume/keys/allotherrows giốngoriginal. Correctioncard
   linkoriginalbook/proof, rawtick/binary, sensitivity và newhash. Khôngsửa
   schemaoldproof giảđãhếtmismatch; derivedproofghi rõ nguồnOHLC hỗnhợp.
3. Tái sinh138raw từworkingview với producer recipe cốđịnh; kiểmfullfacts/
   SL/deadline/1.632hours vàDev300 đúngv1. Bấtkỳdelta→dừngv2, khôngtựmởrộng.
4. Đối soát đủ1.632hours vớicorrectedH1:raw→binarygrid/ordinal, expectedH1,
   emptyhours/gap/endpoints. Tấtcảsourcechecksphảiđạt, khôngskip26mismatch.
   Rawfilepaths v1 read-onlyđượcadmitexplicit; v2khônggiảđãdownloadcachemới.
5. Independentreview đủ138raw và1.632hourraw/binary/H1/path, gồmrejects; exact
   first-SL/entry/deadlinefacts đốichiếuproducer trước tiền. Oraclev1fileđóng
   băng giữnguyên; revisionreviewcode+realrelease riêng pinmới.
6. Sausourcev2PASS vàreview mới gọifinancialprepare/register/runS03 theo
   cổng cũ, unchangedGold/EUR, exactDevprefix/internalstate vànewsourcebinding.
   Sourcev2PASS khôngpricegapFTMOproof, khôngedge/propqualification.

## Kiểm thử/review và dừng

Fixture phảibắt: sourcev1failkhôngbịghiđè; fake/missing/hashmodifiedinputs,
codeold/currentmismatch;13hour/fieldtamper; unchangedSL/cohortgates; original
binaryread-only/pathscope; correctedH1provenance; no2025; khôngfallbackv1;
financialharness pinđúngv2release/proof; earlyerrorsgiữreceipt. Code+tests+
independentreview trướcnewrelease. NoPnLtrongsourceamendment/admission.

Nếu có thêm mismatch/unknown hoặc thaycohort: giữnewfailure, không tạo
correctionv3 tự động trongscope này. Báo nguyênnhân và bước hữu hạn kếtiếp.
Mọi failedv1 vàdiagnostic giữ nguyên, selectionhistory112trials/rawGBPmarkout
âm vẫn giữ. Sourcecontinuationkhôngreset lịch sử chiến lược.
