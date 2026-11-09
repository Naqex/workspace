"""Fixed US cash-calendar proxy for registered NASDAQ development, not broker hours."""
from datetime import date
from sealed_m1_review import cash_sessions

HOLIDAYS={
    2018:('01-01','01-15','02-19','03-30','05-28','07-04','09-03','11-22','12-05','12-25'),
    2019:('01-01','01-21','02-18','04-19','05-27','07-04','09-02','11-28','12-25'),
    2021:('01-01','01-18','02-15','04-02','05-31','07-05','09-06','11-25','12-24'),
    2022:('01-17','02-21','04-15','05-30','06-20','07-04','09-05','11-24','12-26'),
}
EARLY={2018:('07-03','11-23','12-24'),2019:('07-03','11-29','12-24'),2021:('11-26',),2022:('11-25',)}
WINDOWS=(('warmup-2019','2018-11-01','2019-01-01'),('development-2019','2019-01-01','2020-01-01'),
         ('warmup-2022','2021-11-01','2022-01-01'),('development-2022','2022-01-01','2023-01-01'))


def calendar_for(year):
    if type(year) is not int or year not in HOLIDAYS:
        raise ValueError('unregistered_cash_calendar_year_holdout_closed')
    return dict(schema='cash-session-calendar-v1',year=year,timezone='America/New_York',open='09:30',close='16:00',
        holidays=[f'{year}-{d}' for d in HOLIDAYS[year]],early_closes={f'{year}-{d}':'13:00' for d in EARLY[year]},
        basis='declared_US_NYSE_cash_proxy_not_CFD_broker_or_exact_ETF_execution',broker_verified=False)


def sessions_for(role):
    if role not in {w[0] for w in WINDOWS}:
        raise ValueError('unregistered_cash_data_role')
    _,start,end=next(w for w in WINDOWS if w[0]==role)
    sessions=cash_sessions(calendar_for(date.fromisoformat(start).year))
    return {day:minutes for day,minutes in sessions.items() if start<=day<end}
