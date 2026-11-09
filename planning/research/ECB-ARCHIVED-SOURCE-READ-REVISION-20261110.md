# EA-MPD: phân biệt hyperlink trích nguồn với external data connection

10/11/2026, sau [sourceprotocol](ECB-ARCHIVED-SURPRISE-SOURCE-PROTOCOL-20261110.md).
3sources đãtải/giữexactGitblob; reviewerv1 dừng`external_relationship` trước
numericcolumns, giữfailure vàsourcepins, khôngdownloadlại. Numericoutcomes/
features/tradingPnL chưađọc ởcheckpointnày; khôngđổifinancial/sourcepricegate.

MetadataZIPđãkiểm chỉ1externalrelationship:
`xl/worksheets/_rels/sheet1.xml.rels`,rId1,typehyperlink,target
`https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx`.
Đây làsourcecitation, không externalworkbook/formula/data connection.
Installedopenpyxl3.1.5`ExcelReader.read_worksheets` vớiread_only dùng
ReadOnlyWorksheet/continue trướcbindhyperlinks; khôngresolveURL. Không dựa
licensehoặcREADMEđểtựchoembeddedcodechạy.

**Revision riêng trước numericread:**
- Giữoldprotocol/failure/raw/v1script, outputreviewv2 mới tại
  `execution-v1/ecb-archived-surprise-review-v2/`; sourcev1khôngđổi.
- Vẫnrejectmacro/vba/externalLinks/formulas/oversizedZIP/pathtraversal và
  externalrelationships. Chỉallowđúngtuplepath/ID/type/target/TargetModeởtrên
  nhưinertmetadata; khôngfollowURL, khôngđọcworkbookcurrent/2025+.
- Readonly/data_only/keep_linksFalse, socketDNS/connect bịchặn trongreview;
  testwrongtarget/wrongtype/wrongpart bịreject trước đọcvalues. Đây làguard
  chínhxáchơn, khôngtắtprotectionhoặcbỏqua sourcebinding/authority/knownat.
- Datefirstchecks phảiđượcdùngchoactualrowsvàmutations; injected2025date
  chặn ởcùngfunction, khôngtestmộtassertgiảkhôngđiqualuồngthật.
- Snapshots/pinsnewreader/protocol+oldsource/raw/result/reviewer giữ, kếtquả
  numeric/metadata/causalitycóthểvẫnfailhoặcunknown; khônghứapass.

Sourcecorrectness chưaedge; catalogue92/58giữ, khôngbroker/model/ownholdout.
Sửa phạm vi securityreadguard cóevidence đủ, khôngcầnskill/framework/plugin mới.
