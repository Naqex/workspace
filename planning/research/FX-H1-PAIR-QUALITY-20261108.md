# H1 Bid/Ask không được mặc định là joint quote hợp lệ

Sau khi kiểm đủ373.652sourcebars,review phát hiện30H1timestamps cóBidOpen>
AskOpen hoặcBidClose>AskClose. Các giá từngside khớprawintegerdelta; chưa có
bằng chứng lỗidecoderprice. Nguyênnhânprovider/asynchrony/revision/nguồn cũ
chưa xácminh. Không flip/clamp/spread0/carry hoặc tự gọi làquotejointthật.

Đây là **admissiongap**,không làm yếu check để fullhistorypass. Raw/native
exports giữbấtbiến; sourcefieldprice/volume có thể được kiểm trongscope
biếnđổi, nhưngpairedinputs chưaadmitđầyđủ. Giữ30flags theo timestamp/field,
negativeOpen vànegativeClose riêng;không xóa rows khỏi sourcehistory.

Sourcequalitydiagnostic trướcPnL:trong các giờtarget02NY/14Berlin,0entryOpen
bịcross và1exitOpenbịcross(AUDUSD28/04/2010,12UTC,Bid0,92067/Ask0,92064).
Giữ eventunknown nếu cần dùng endpoint đó;futureexitbad không được làm đổi
entryeligibility. CácnegativeClosekhông tự làmOpenhợplệ thànhactualtick;
endpointprice study chỉ được dùngsourceOpen đãqua fieldguard vàgiữallweekday
denominator/missing/crossed statuses. Đây chưa accountcarrysafe model.

KhôngPnL hoặc chọnside/riskthreshold trongdiagnostic. Nếusurvivor cần native
qualification,resolveaffectedsource bằngregisteredrawtick/independentpath
check;khôngsuy1EURUSDbridgehour khớp choAUDUSDallhistory. MissingAskJan2013
vẫnunknown,khôngliênquan đếncrossedhours. Sourcehistoryfulladmission vẫn
inconclusive; báo riêng verifiedsourcevalues,usableinputroles vàunknowns.
