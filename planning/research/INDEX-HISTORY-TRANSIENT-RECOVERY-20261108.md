# Tiếp tục exact data scope khi gặp timeout/HTTP5xx có giới hạn

V3đãgiữ9/74quarter-sides, timeout1đượccache-resume; sauđódừngđúngpolicyvì
HTTP500ởASK15/11/2013. Không phải403/WAF/rate-limit vàkhông làschemafailure.
Khôngrestartdataset hoặc sửaoutcome. V4adoptmọiseal/partialcacheV3→V2→V1.

Policytransport mới trước V4: idempotentGET cóthể tiếp tụctốiđa2lần/part với
timeouttypes đãđịnh hoặc **plainError HTTP500/502/503/504**. Wait10/20s,
draininflight. 403/WAF/challenge/429/rate-limit/501/schema/decode/empty vẫn
failclosed, không retry. Nativecache giữrawbytes trước decode, canonical
`ignoreFlats:false` riêng mới cóthể thànhstrategyinput. Không auth/URLrotation/
bypass/providerswitch,không mua data. LỗiV1unknowngiữunknown,khôngclaimfixed.

Cumulativeknowntransientcount bắt đầu3(V2timeout1,V3timeout1+5001),trần24 và
deadline3600s;perpart2retries, khôngresetbudgetđể retryvôhạn. Counter/history
đượcghi. Khi hếtbudget hoặc persistent500 phải dừng lane vàgiữdataunavailable,
không giảfileempty/mấtquote hoặcmarkcomplete. CANCELgiữarequests/attempts.
Financialrules/PnLkhông thay. Source/cachedatesđúngQ4/2012–2021,2025+closed.
