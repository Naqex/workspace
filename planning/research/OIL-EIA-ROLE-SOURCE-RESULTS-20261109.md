# Oil role-source: WTI fixture đủ, USO vẫn có gap trong holding role

Theo [protocol](OIL-EIA-ROLE-SOURCE-PROTOCOL-20261109.md), commit `2e8bc55`
trước geometry/returns mới. Reuse8oldrawURLs, **0newmarketrequests**, không
strategy/PnL hoặc thay raw/frozen98%gate. Newtiming15:31→15:59 là own adaptation,
không replicationclosingauction hoặc sửa nhãn old16:00Openmissing thành đạt.

| Asset/date | Featureminutes | Holdingminutes | 4endpoints | Verdict |
|---|---:|---:|---|---|
|USO09/01/2019|31/31|24/29|Đủ|Thiếu5holdingminutes, chưaadmitted|
|WTI09/01/2019|31/31|29/29|Đủ|Đủ fixture này|
|USO13/07/2022|31/31|29/29|Đủ|Đủ fixture này|
|WTI13/07/2022|31/31|29/29|Đủ|Đủ fixture này|

Tổng4asset-days vẫn **roles_admitted=false**. Không drop5minutes, dùng
futurequality làm entryfilter hoặc nớiendpoint để cứu USO. HaiWTIdates đủ
không chứng minh ETF→CFD economics, toànhistory hoặc targetexecution.

Full raw/native/Fractionreview35.280OHLCVfields, clock/grid/side/sourcepins;
5mutations missingBid/missingAsk/crossedrole/nativeprice/nativetime bịchặn.
Source interpretation sameprovider/agent, không independentfeed/human signoff.

## Lỗi đã sửa và recovery

Attemptv1 dừng0,032s ởsourcepins, trước geometry: bốn code/protocol files
đổi LF/CRLF sau checkout. Snapshot cũ có đúng hashes frozen; nội dung sau
chuẩn hóa newline khớp hoàn toàn. V2 bind **snapshot hash gốc**, thêm hashes
code đang dùng và representation-change map, không sửa originalmanifest hoặc
đổi hash để ép pass. Contentdrift khácnewline tiếp tục bịchặn. Giữfailurev1;
chỉ chạy lại consumerreview0,811s, khôngfetch/replay thị trường.

Private `execution-v1/oil-eia-role-source-v1/` failed và`...-v2/` completed,
manifest/resolvedbindings/source-snapshot/progress/events/result đầy đủ.
ReviewerSHA`a182903b56f2d44bd7e9f6e9ae7795a4072a8e5e9216cbc7b8591c764a8ee7cf`.

**Quyết định:** USO chưa vàofullhistory; khôngdeclareoldtransferadmitted.
[WTI-onlyconditionaldiagnostic](WTI-WEDNESDAY-COMPONENT-PROTOCOL-20261109.md)
đăng ký riêng sau source review, nhằm kiểm ownCFDpriceassociation trước đầu tư
fullPIT. Không dùng ngoại lệ đó để giả causalstrategy hoặc đạt C1/C2.
