# Tokyo USDJPY fixing: method admission trước source/economics

09/11, tiếp sau [R083negative](WTI-SETTLEMENT-COMPONENT-RESULTS-20261109.md).
Đây là cùnghọfixing R020/R021, **không independentedge** chỉ vì đổiEURUSD→JPY
hoặc thêmcalendarmask. ExactEURUSDpreTokyo18NY→10Tokyo đãgác vẫnnguyên.

## Điều mới đủ để kiểm

| Primarysource | Đã đọc / ý nghĩa | Không được suy |
|---|---|---|
| [Ito/YamadaNBER22820](https://www.nber.org/papers/w22820), PDFpp8–12 | TTMbank-specific côngbố10h, thamchiếu giao dịch gần09:55JST; customerflow thườngmuaUSD, mạnhhơn các ngày5/10/15/20/25/30 hoặccuốitháng; hedge cóthểbắtđầu30phúttrước | Không marketwideorderflow củaaccount mình; không retailaccess tới bankprivateorders hoặcfixrate |
| [BoC2021-48](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf), intro và§V.E | USDappreciatesprefix/depreciatespostfix; costs quantrọng, fullindicativespread cóthể xóa returns | Không giảmspread50% nhưbrokerpermission hoặcđánhđồngdealerprofit vớiclientCFD |
| [Journalversion2024](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13306), intro | Clientmarket netreturns cóthểnegative trongkhi liquiditysupplierpositive; Japanholidays lànaturalexperiment | Không chứngminh mọiUSDJPYrecipe thấtbại hoặcmidquotePnl đãđủ |
| [SMBCNikko](https://www.smbcnikko.co.jp/terms/japan/na/J0609.html) | TTMthamchiếu09:55, TTS/TTBthêmphíriêngtheobank | TTMkhônglàgiáCFDpendingorderđượcfill |
| [CabinetOfficeholidays](https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html) | OfficialCSVđọcđược38holidays2019/2022; cp932,dateparse,giữnguồn | Không fullbankclosure/PITcalendar; nationalholiday khôngbaoJan2/3/Dec31toànbank |

NBERPDFđọcquaHTTPSthôngthường khiwebreader403,khôngauth/WAFbypass; private
`execution-v1/tokyo-fix-method-source-v1/ito-yamada-w22820.pdf`1.263.360bytes,
SHA`5e86cba5b82f18d2881e5a6cabf7bb4a85be007dcb6f59e7b191e59b70d6cdb2`.
KhôngredistributePDF/code/data. Paper/diagramminute9:53→9:57 không executable
rule; khôngtradeexactspike hoặcmanipulatebenchmark. Chưaclaimfullpaperreplication.

## Chọn việc tiếp, chưa chọn winner

USDJPY hấp dẫn để**kiểm** vì nógắntrực tiếpJapaneseimporterpaymentflow,
khácEURUSDassettransfer dài18NY→10Tokyo. Ownintradayfixedwindow cóthểtránh
rollover vàdùng10:00announcementbarrierrõ; khônghứaedge. Calendarcondition
ngày5/10 chỉdùngnếufreeze vàgiảiquyếtholiday/bankclosure/shiftconvention trước
outcomes; khôngchọnGotobiwindow dựavàokếtquảbacktest cộngđồng2026.

Látngaytiếp: [USDJPYsourcefixture](USDJPY-TOKYO-SOURCE-PROTOCOL-20261109.md)
chỉhai ngày đãchọnvìcalendar/winter-summer,khôngreturns/PnL. Nếuđạt,đăngký
**một** ownprefixBUYcomponent táchpostfixSELLdiagnosticcontrols, đúngpip0.01,
USDbase/JPYquote/commissioncurrency vànoSL/accountproof. Exactwindows/cost/
calendarviews/gate phải freeze trướcpriceoutcomes, khôngtạo HFTcloneNHP.
Bankcalendar/execution/privateflowunknown khôngtựcấppermissionhoặctradeclaim.
