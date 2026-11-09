# Phục hồi đúng đơn vị request thay vì cả quarter

V4dừng sau3lỗi ở **cácngàykhác nhau** trongcùngquarter (Nov15rồiDec11/2013).
Per-quarterretrycap làm mất cơhộitiếptục dù partialcache đãtiếntriển. Giữfailure,
khôngresetcounter hoặc gọi lànewstrategytrial.

V5reuse nativepublic`BufferFetcher.fetch([url])`, `CacheManager`, validate/
normalise/generate/process/format components của pinnedpackage1.51.1. Chỉ thêm
điềuphối2URL/batch vàper-daytimeout/500/502/503/504recovery10/20s,tốiđa2retry/
URL;trần24cumulativeknownerrors,bắtđầu6 vàdeadline3600s. Nativecacheflushsau
mỗiresponseđãdecode,không globalfetchmonkeypatch hoặcghiAPIresponsechưađượclib
decode vào canonicalcache. 403/WAF/429/schema/decode khôngretry. Drain cảbatch
trướcbáofail;CANCEL/deadlineđượckiểmgiữaURL/retry.

ExplicitignoreFlatsfalse;same74quarter-sidecachequeriesQ4/2012–2021,không2025+.
2012reuseBidcacheV1/Askdiagnosticcache riêng;2013reusepartialcacheV2;khôngfetch
những response đãcó. CácpreviewJSONfilteredcũ chỉlàlineage,đượcdecodecanonically
từsamecachedbytes,khôngadoptlàm unfilteredJSON. Runtimehelper8focusedtests
vàactualcachedquarter108780rows byte/valueexact,network0trướclaunch.
Khôngprovider/auth/source URL/headers/policyquyềnthayđổi,khôngorders/modelcalls.
