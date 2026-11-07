from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import forex_ml_study as m
from trading_workspace_v2.forex_h4 import Candle
from trading_workspace_v2.forex_coarse_input import CoarseHour
from trading_workspace_v2.forex_h4 import CandleState


def hour(index,price=D('1.1')):
    stamp=m.timestamp(2024)+index*3600
    spread=D('.00002')
    return CoarseHour(mid=CandleState(timestamp=stamp,open=price+spread/2,
        high=price+D('.001')+spread/2,low=price-D('.001')+spread/2,close=price+spread/2),
        bid=(price,price+D('.001'),price-D('.001'),price),
        ask=(price+spread,price+D('.001')+spread,price-D('.001')+spread,price+spread),
        first_time_msc=stamp*1000+1,last_time_msc=stamp*1000+2,
        first_sequence=index+1,last_sequence=index+1,ticks=1,maximum_spread=spread)


class MLStudyTests(unittest.TestCase):
    def test_counterfactual_label_cash_hand_arithmetic(self):
        history=[Candle((i+1)*3600,D('1.1'),D('1.101'),D('1.099'),D('1.1')) for i in range(100)]
        state=m.initial_state('reference',D(0),'a'*64,start=m.timestamp(2024)*1000).execution
        terms=m.CostModel.from_mapping(state.cost_model),m.InstrumentSpec.from_mapping(state.instrument_spec)
        result=m.label_pair(history,hour(0),hour(1),hour(5,D('1.1004')),terms=terms,calendar=[])
        # 0.08 lot, $0.40 commission, 2 points spread; labels are net/25USD.
        self.assertEqual(result,[.1056,-.1504])

    def test_purge_uses_actual_gap_endpoint_and_strict_cutoff(self):
        cutoff=m.timestamp(2024)
        rows=[dict(decision=cutoff-3600,endpoint_msc=cutoff*1000-1,x=[1],y=[1]),
              dict(decision=cutoff-7200,endpoint_msc=cutoff*1000,x=[2],y=[2]),
              dict(decision=cutoff-86400,endpoint_msc=(cutoff+86400)*1000,x=[3],y=[3]),
              dict(decision=m.timestamp(2022),endpoint_msc=cutoff*1000-1,x=[4],y=[4])]
        self.assertEqual(m.purged_training(rows,cutoff),rows[:1])

    def test_future_mutation_does_not_change_training_or_preprocessor(self):
        import numpy as np
        cutoff=m.timestamp(2024)
        rng=np.random.default_rng(2)
        rows=[dict(decision=cutoff-(250-i)*3600,endpoint_msc=(cutoff-(245-i)*3600)*1000,
             x=rng.normal(size=21).tolist(),y=rng.normal(size=2).tolist()) for i in range(270)]
        changed=deepcopy(rows)
        for row in changed:
            if row['endpoint_msc']>=cutoff*1000:
                row['x']=[10000]*21;row['y']=[1000,-1000]
        a=m.fit_fold(rows,cutoff=cutoff,algorithm='ridge',shuffled=False,fold_index=0)
        b=m.fit_fold(changed,cutoff=cutoff,algorithm='ridge',shuffled=False,fold_index=0)
        self.assertEqual(a,b)
        selected=m.purged_training(rows,cutoff)
        expected=np.mean([row['x'] for row in selected],axis=0)
        np.testing.assert_allclose(a['model']['mean'],expected,rtol=0,atol=1e-14)

    def test_safe_forest_export_library_and_actual_split_boundaries(self):
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor
        rng=np.random.default_rng(3)
        x=rng.normal(size=(600,21));y=np.column_stack((x[:,0],x[:,1]))
        estimator=RandomForestRegressor(n_estimators=80,max_depth=4,min_samples_leaf=100,
                                       random_state=42,n_jobs=1).fit(x,y)
        model=m.export_model(estimator)
        vectors=[row.tolist() for row in x]
        for tree in model['trees']:
            for feature,threshold,left,_,_ in tree:
                if left!=-1:
                    for delta in (-1e-8,0,1e-8):
                        row=[0.]*21;row[feature]=threshold+delta;vectors.append(row)
        expected=estimator.predict(np.asarray(vectors))
        actual=np.asarray([m.predict(model,row) for row in vectors])
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)

    def test_sample_causality_and_observed_not_calendar_label_horizon(self):
        hours=[hour(i,D('1.1')+D(i)/100000) for i in range(120)]
        rows=m.training_samples(hours,buy_debit=D(0),sell_debit=D(0))
        self.assertEqual(rows[0]['endpoint_msc'],hours[104].first_time_msc)
        future=deepcopy(hours)
        future[-1]=hour(119,D('1.2'))
        changed=m.training_samples(future,buy_debit=D(0),sell_debit=D(0))
        self.assertEqual(rows[:-1],changed[:-1])


if __name__=='__main__':unittest.main()
