# Admission H1 cho chuyển giao cơ chế: GBPUSD/AUDUSD, không PnL

Sau [R056riskbook](PRE-ECB-SESSION-RISK-RESULTS-20261108.md), khôngSLgrid hoặc
hạfrozenretention. Hướng tiếp là kiểm nguồn cho chuyển giao fixing mechanism
sang USDquotedpairs và cuối cùng portfolio có **accountwidebudgetchung**.
Các pairscùngUSDfactor,không là independentedges hoặc quyền nhânrisk.

## Vì sao và bằng chứng trước sourcepilot

- [BoC2021-48 fullpaper](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf),
  đọc08/11§intro/data/mechanism: nghiên cứu G9currencies vàpre/postfixpattern;
  dealerorderflow không là cùng dữ liệu với retailtickvolume. Không dùng
  pricechange giả làm signedorderflow hoặc chuyển paperreturn thành botedge.
  Paraphrase cơchế, không importcode/paperdata. Paperclock/side và target
  costs phải freeze riêng trước numeric; không claim exactreplication.
- Local QDMCLI`symbols()` read-only08/11 chỉ cho EURUSD/vàng códata, chưa
  GBPUSD/AUDUSD. Không tự tạo/tải symbol vào managedQDMcache hoặc đọc2025+.
- Existing`dukascopy-node`1.51.1(MITcode) có H1monthresponse/BidAskseparate.
  [Official library cache](https://www.dukascopy-node.app/using-cache) và
  [timeframe/batching](https://www.dukascopy-node.app/custom-batching) khớp
  installedURLgeneration: `/candles/hour/{PAIR}/{SIDE}/2019/1`.
  CodeMIT không tự là datalicense cho redistribution; artifactsprivate,
  khôngcopycode/datahãng sangpublicrepository. Khônginstall/updatepackage.

## Source-onlypilot đã khóa

- Sáu requests:GBPUSD/AUDUSD/EURUSD×Bid/Ask,H1,02/01/2019UTCđến03/01UTC.
  Native transport tảiJanuary2019monthbuffer; ghi exposure cảmonthsource,
  chỉ xuất fixtureday. Không đọc2025+, không outcome/signal/weights/account.
- EURUSD là bridgecontrol với existing rawticks2019alreadyconsumed; cảhai
  directions của futurestrategy chưa được thử. GBP/AUDkhácmarket,không đo
  performance để chọn symbols rồi gọiunseen. Sources là sameDukascopyfeed.
- Nativeprovidercomponents sẵn có:validateConfigNode/normaliseDates/
  generateUrls/BufferFetcher/CacheManager/processData. ExplicitUTC/timeframeH1,
  `ignoreFlats:false`,noWAF/auth/token,hiddenretry0,cachepathprivatecampaign,
  timeout/deadline và boundedtransientrecovery helper đang có. Khôngproxy
  auth/WAF/403, không paidprovider/newaccount/OAuth hoặc rawwebscraping.
- Rootmới1writer,deadline180s,status/PID/events/failure/CANCEL; drainrequest
  trướcterminalfailure. Sourcecacheonefile/month/side/hash giữbấtbiến,
  provenance callback/rawpaths/pins,request/config/package/helper/runtime.
- Native decoder có thể chèn carriedclose/volume0; chỉ nhận **explicit source
  timestamps** từrawdelta,khônglọc mọivolume0. Sourceclockshift phải3600000ms,
  H1startUTC,known_at=barstart+1h đối vớiclose/high/low;Open làobservation
  interval `[start,start+1h)`,khôngactualfirsttick. Bid/AskOpen không chắc
  jointtick,không dựng observedmidextrema bằngmean(sideextrema).
- Reuse source decoder bằngopt-in duration H1, defaultM1guard giữ60000ms.
  Không đổi historicalM1artifacts hoặc current product/runtime. Kiểm native
  rawdeltaprices/volume/timestamps và Fractionoracle trước dùng normalizedH1.

## Acceptance và review trước PnL

Fixture cần đủ24H1timestamps mỗiside/ngày, exactno-duplicate/order/grid,
positiveOHLC/volumes,pairedOpen/close spread khôngâm. Missing vẫnexplicit,
khôngpadding hoặc nhận0PnL; dataadmission có thểinconclusive nếuchưa đủnguồn.
Sourcevalidity khôngtự là executability hoặc đủlonghistory.

- Focusedsynthetics:H1deltaomit/zero-volume/defaultM1reject;bounds/holdout;
  raw/source/native mismatch bị chặn. ExistingM1tests chỉ chạy lại phần
  decoderaffected, khôngbroadbacktest.
- Reviewcode khác tính rawintegerdelta/Fraction cho mọifixturebar/side,
  so OHLC/grid/volume và timestamp;mutations futureclock,price,misingrow,
  falseauthority. Khôngimportproducerdecodefunction làm independentoracle.
- EURUSDbridge:fullrawhash2019 rồi parse **fixturehour07UTC** Bid/AskOHLC,
  first/lasttime/count từexistingrawtickCSV. So nativeH1Open/close/extrema;
  lệchghi rõsourceversion/aggregationgap,khôngforceadmit bằngchỉnhprice.
  Sameprovider2transports không independentfeed,1hour khôngfullhistoryproof.

Chưa mua/tạochallenge,bậtbroker,hoặcregistereconomicrun. Saupilot mới quyết
định có lấyH1history2010–24 và freeze multi-marketrecipe/cost/portfolio/risk
hay không. Đợt này không thêmMCP/service/RAG/skill; hợpđồngsource và tooling
cần smoke-test thật, không chỉdoc hoặc successfulHTTP.
