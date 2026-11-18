# S03 — chẩn đoán ảnh hưởng nguồn GBP2024 trước PnL

18/11/2026. Bổ sungsource-only sauadmissionfail, trước correction/sensitivity
và trước kết quả tài chính S03. Không sửa source-release/registration/proof
cũ. Scope2024 được mở theo [S03protocol](SOLO-THREE-ASSET-VALIDATION-PROTOCOL-20261118.md);
2025–2026đóng. Không chiến lược mới, không tăng risk hoặc chọnnguồntheoPnL.

## Bằng chứng dẫn đến phép kiểm

Source đủ1.632hours/7.287.413ticks,0emptyhours/heldgaps>15phút;26sideOHLC
differences tại13hours. Independentdecoder đã tái lập67.501ticks của13hours
raw→binaryexact và26differences giốngproducer. Lỗi không nằm ở intdecoder
trong cácgiờđãđốisoát; vẫn unknown nguồn nào phản ánhbrokerđích.

HoursUTC cốđịnh:30/12/2024 17,18,19,20;31/12/2024 09,10,11,12,13,14,15,16,17.
Tương ứngmillis:
`1735578000000,1735581600000,1735585200000,1735588800000,1735635600000,1735639200000,1735642800000,1735646400000,1735650000000,1735653600000,1735657200000,1735660800000,1735664400000`.

SourceproofSHA `5a34182d0095759628315af28212385943a6157012f121b69653c9dc5428e9ee`;
reconciliationSHA `101cf3105b5ad473e953d8e78f8d89528e2ebf1e6295166ed98aaf125be27d05`;
manifestSHA `3ffa9b04b9838930c6c25d881b455cf2e9bd2d9b3b849010f99d72666965e6e9`.
Hai rawSELLholdingsbịảnhhưởng:30/12decision08 và31/12decision09. Bar30/12sau
entry cóthểảnhhưởngATR/SL31/12; khôngsuycohortunchanged từfirstsignalparity.

## Một phép so source, budget khóa trước

1. Đăng kýprotocol/code/inputhashes trước overlay. Toàn inputcũ read-only;
   output mới riêng trong `S03-three-asset-validation/source-sensitivity-v1/`.
2. Kiểmcanonical release/registration/proof + full138raw/1.632hours. Reproduce
   originalraw138 vàDev300 đúngphép tínhđộc lập trước thay bấtkỳbar nào.
3. Một overlay duy nhất: thayOHLC của **đúng13H1rows mỗi side** bằng OHLC từ
   rawticks đã independentlyreconciled. Giữ timestamp/volume/keys vàmọirow
   khác; volume vẫn củaH1cũ, không gọi tickvolume. Không interpolation,
   tolerance, chọnclose/high/lowtừngphần hoặc bỏgiờ. Không chỉnh2021–2023.
4. Tái sinh toàn2024raw bằng recipecũ, warmup từ01/11/2021 nối hai corrections
   Dev2022; BOTH, H1Asia/London sweep, naturalSL±0,1ATR, deadlinegiữnguyên.
   So exactcount, decision, side, SL, deadline và heldhourcensus; ghi mọi
   thêm/bớt/thayđổi, kể cả thayđổi nhỏ1pricegrid. Không vàoentrygate/exitPnL.
5. Independent source-only comparison bằng codekhác; chứngminhkhôngrow
   ngoài13hoursbịđổi và fullDevprefixidentical. Không dùngcost/winrate/R/DD
   đểquyết địnhgiữoverlay. Khôngnetwork/refetch trongphépkiểmnày.

## Kết luận được phép

- Nếu exact138facts/SL/deadline/hours khôngđổi: đủ xem xét sourcecorrection
  riêng trướcfinancial, chưa tựadmit hoặc sửa oldproofthànhPASS.
- Nếu cóđổi: báo đúngảnhhưởng, giữ bảnS03H1cũ ởSOURCE_REVIEW_REQUIRED.
  Dữ liệu sửa làm thaySL/tínhiệu là revisionnguồn cóthayoutcomes tiềmnăng,
  không freePASS. Chỉđăngký correction/scenario mới sau evidence; không
  quaylại oldSL đểlấyPnLđẹp hoặc chọnsubset unchanged.
- Nếu cònmismatch ngoài13, khôngtáilậporiginal, hoặc thiếuinput/proof:
  dừngdiagnostic, khôngmởrộng danh sách sửa. Sourceverifiedcùngvendor không
  independentfeed/FTMOparity. FinancialS03 vẫn chưađượcchạy từaddendumnày.

Kết quả nguồn/kinh tế/prop táchbiệt. Đây làchẩn đoán đểgiải quyết sai khác
đãquan sát, không trialtốiưu vàkhôngcóquyền đọc2025–2026 hoặc gửiorder.
