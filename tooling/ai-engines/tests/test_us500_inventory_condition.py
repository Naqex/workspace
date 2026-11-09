from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import us500_inventory_condition as study
import us500_euopen_component as parent
from nasdaq_cash_calendar import sessions_for


def pair(at, value):
    return tuple(dict(timestamp=at, open=str(value+offset), close=str(value+offset)) for offset in (0, 1))


def fixture():
    parents, predictors = [], []
    for year in (2019, 2022):
        sessions = sessions_for(f'development-{year}'); pairs = {}
        for stamps in sessions.values():
            pairs[stamps[-30]] = pair(stamps[-30], 100)
            pairs[stamps[-1]] = pair(stamps[-1], 99)
        parents.extend(parent.prepare(year, sessions, {})['rows'])
        predictors.extend(study.prepare(year, pairs))
    return parents, predictors


class InventoryConditionTests(unittest.TestCase):
    def test_calendar_previous_expected_session_weekend_holiday_halfday_first(self):
        _, ps = fixture(); by = {p['session']:p for p in ps}
        self.assertEqual(by['2019-01-07']['previous_session'], '2019-01-04')
        self.assertEqual(by['2019-01-22']['previous_session'], '2019-01-18')
        self.assertEqual(by['2019-01-02']['status'], 'first_session_out_of_scope')
        self.assertEqual(by['2019-07-05']['status'], 'previous_halfday_abstain')
        self.assertEqual(by['2019-07-03']['status'], 'current_halfday')

    def test_sign_zero_missing_crossed_clock_and_grid(self):
        sessions = sessions_for('development-2019'); stamps = next(iter(sessions.values()))
        for value,selected in ((99,True),(100,False),(101,False)):
            pairs = {stamps[-30]:pair(stamps[-30],100),stamps[-1]:pair(stamps[-1],value)}
            self.assertEqual(study.prepare(2019,pairs)[1]['selected'], selected)
        self.assertEqual(study.prepare(2019,{})[1]['status'],'predictor_unknown')
        p = pair(stamps[-1],99); p[1]['close']='1'
        self.assertEqual(study.endpoint(p,stamps[-1],'close')['status'],'crossed_endpoint')
        p[0]['timestamp']+=1
        with self.assertRaises(ValueError):study.endpoint(p,stamps[-1],'close')
        p=pair(stamps[-1],99);p[0]['close']='99.0001'
        with self.assertRaises(ValueError):study.endpoint(p,stamps[-1],'close')

    def test_future_unknown_costs_do_not_choose_entry_parent_is_immutable(self):
        parents,predictors=fixture(); original=deepcopy(parents)
        selected=study.select(parents,predictors)
        self.assertTrue(selected[1]['planned_trade']);self.assertFalse(selected[1]['outcomes'])
        parents[1]['exit']={'bid':'999999'};parents[1]['outcomes']={'future':'not_used_for_selection'}
        changed=study.select(parents,predictors)
        self.assertEqual([r['planned_trade'] for r in selected],[r['planned_trade'] for r in changed])
        self.assertEqual(original[1]['exit']['bid'],None)
        selected[1]['predictor']['delta_mid']='555'
        self.assertEqual(predictors[1]['delta_mid'],'-1')

    def test_census_authority_forged_condition_and_known_at_rejected(self):
        for mode in ('census','authority','selection','future'):
            parents,preds=fixture()
            if mode=='census':parents.pop()
            elif mode=='authority':parents[1]['execution_authorized']=True
            elif mode=='selection':preds[1]['selected']=False
            else:preds[1]['end']['known_at_ms']=parents[1]['entry_ms']
            with self.assertRaises(ValueError):study.select(parents,preds)

    def test_cost_waterfall_does_not_subtract_embedded_spread_twice(self):
        r=dict(entry=dict(bid='100',ask='102'),exit=dict(bid='105',ask='107'),outcomes=dict(reference=dict(primary=dict(
            costs=dict(slippage_account='.5',commission_account='0',financing_account='0'),net_usd_per_research_unit='2.50'))))
        got=study.decompose([r],'reference')
        self.assertEqual((got['mid_gross'],got['embedded_spread'],got['bidask_gross'],got['net']),('5','2','3','2.50'))
        self.assertEqual(got['rounding_residual'],'0.00')


if __name__=='__main__':unittest.main()
