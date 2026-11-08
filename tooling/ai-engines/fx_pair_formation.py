"""Fixed formation diagnostics for R035; no returns, selection search or orders."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math

GRID = Decimal('.00001')
HOUR = 3_600_000
SYMBOLS = ('gbpusd', 'audusd')


def expected_dates(year):
    if year not in (2018, 2021):
        raise ValueError('unregistered_formation_year')
    day, end = datetime(year, 1, 1, tzinfo=timezone.utc), datetime(year+1, 1, 1, tzinfo=timezone.utc)
    dates = []
    while day < end:
        if day.weekday() < 5 and (day.month, day.day) not in ((1, 1), (12, 25)):
            dates.append(day)
        day += timedelta(days=1)
    return dates


def formation_sample(books, year):
    if set(books) != {(symbol, side) for symbol in SYMBOLS for side in ('bid', 'ask')}:
        raise ValueError('unregistered_formation_book_roles')
    indexed = {}
    for identity, rows in books.items():
        index = {}
        previous = None
        for row in rows:
            stamp = row['timestamp']
            if (type(stamp) is not int or stamp % HOUR or stamp < 0
                    or datetime.fromtimestamp(stamp/1000, timezone.utc).year != year
                    or (previous is not None and stamp <= previous)):
                raise ValueError('invalid_formation_source_clock')
            previous = stamp
            values = {k: Decimal(str(row[k])) for k in ('open', 'high', 'low', 'close')}
            if any(not p.is_finite() or p <= 0 or p % GRID for p in values.values()):
                raise ValueError('invalid_formation_source_grid')
            if not values['low'] <= min(values['open'], values['close']) <= max(values['open'], values['close']) <= values['high']:
                raise ValueError('invalid_formation_source_OHLC')
            index[stamp] = values
        indexed[identity] = index
    census, missing, samples = [], [], []
    for day in expected_dates(year):
        stamp = int(day.replace(hour=16).timestamp()*1000)
        absent = [symbol+'-'+side for (symbol, side), index in indexed.items() if stamp not in index]
        crossed = [symbol for symbol in SYMBOLS if all(stamp in indexed[symbol, side] for side in ('bid', 'ask'))
                   and any(indexed[symbol, 'ask'][stamp][key] < indexed[symbol, 'bid'][stamp][key] for key in ('open', 'close'))]
        row = dict(date=day.date().isoformat(), source_time_msc=stamp, known_at_msc=stamp+HOUR,
                   absent=absent, crossed=crossed)
        census.append(row)
        if absent or crossed:
            missing.append(row)
        else:
            samples.append(dict(**row, gbpusd_bid_close=str(indexed['gbpusd', 'bid'][stamp]['close']),
                                audusd_bid_close=str(indexed['audusd', 'bid'][stamp]['close'])))
    admitted = not missing and len(samples) >= 240
    return dict(year=year, expected_dates=len(census), observed_pairs=len(samples),
        source_admitted=admitted, missing=missing, census=census, samples=samples,
        sample_basis='weekday16UTC_sourceH1BidClose_known17UTC_excludingJan1Dec25',
        clean_oos=False, broker_calls=0, execution_authorized=False)


def diagnose(y, x):
    """Library inference is explicit; fixed lag, no search or homemade p-values."""
    import numpy as np
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tsa.stattools import adfuller, coint

    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    if (y.ndim != 1 or x.shape != y.shape or len(y) < 240 or not np.isfinite(y).all()
            or not np.isfinite(x).all() or np.std(x) <= 1e-12 or np.std(y) <= 1e-12):
        raise ValueError('invalid_formation_vectors')
    fitted = OLS(y, np.column_stack([x, np.ones(len(x))])).fit()
    residual = fitted.resid
    if np.std(residual) <= 1e-12 or fitted.rsquared >= 1-100*np.sqrt(np.finfo(float).eps):
        raise ValueError('near_collinear_formation_not_reliable')
    tstat, pvalue, critical = coint(y, x, trend='c', maxlag=1, autolag=None, return_results=False)
    def adf(values):
        t, p, used, n, crit = adfuller(values, maxlag=1, regression='c', autolag=None, result_object=False)
        return dict(tstat=float(t), pvalue=float(p), usedlag=int(used), nobs=int(n), critical_values=crit)
    legs = {name:dict(level=adf(values), difference=adf(np.diff(values))) for name, values in [('gbpusd', y), ('audusd', x)]}
    beta, intercept = map(float, fitted.params)
    phi = float(OLS(residual[1:], np.column_stack([residual[:-1], np.ones(len(residual)-1)])).fit().params[0])
    stats = [float(tstat), float(pvalue), beta, intercept, float(np.std(residual, ddof=1)), phi, *map(float, critical)]
    stats += [v[k] for leg in legs.values() for v in leg.values() for k in ('tstat', 'pvalue')]
    if not all(math.isfinite(v) for v in stats):
        raise ValueError('nonfinite_formation_statistics')
    gates = dict(coint_p_le_005=pvalue <= .05, positive_bounded_beta=.1 <= beta <= 10,
        nondegenerate_residual=np.std(residual, ddof=1) > 0,
        leg_level_nonrejection=all(leg['level']['pvalue'] >= .05 for leg in legs.values()),
        leg_difference_rejection=all(leg['difference']['pvalue'] < .05 for leg in legs.values()))
    return dict(observations=len(y), beta=beta, intercept=intercept,
        residual_sd=float(np.std(residual, ddof=1)), residual_ar1_phi=phi,
        coint_tstat=float(tstat), coint_pvalue=float(pvalue), critical_values=list(map(float, critical)),
        legs=legs, gates={k:bool(v) for k,v in gates.items()}, retained_for_economic_design=bool(all(gates.values())),
        method='fixed_EngleGranger_constant_maxlag1_autolagNone',
        clean_oos=False, broker_calls=0, strategy_simulated=False, execution_authorized=False)


def diagnose_sample(sample):
    if not sample['source_admitted']:
        return dict(status='inconclusive_missing_registered_dates_no_statistics', retained_for_economic_design=False)
    rows = sample['samples']
    return diagnose([math.log(float(r['gbpusd_bid_close'])) for r in rows],
                    [math.log(float(r['audusd_bid_close'])) for r in rows])
