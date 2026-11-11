"""Correct quality flags from raw coverage; keep every financial field unchanged."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import time

import us500_multiframe as study
import review_us500_multiframe as reviewer
import run_us500_multiframe as runner


def signature(book):
    copy=deepcopy(book)
    for trade in copy['trades']:
        trade.pop('unresolved')
    return json.dumps(copy,sort_keys=True,default=str)


def synthetic_parity(base):
    origin=base/'us500-multiframe-native-v2-2022'
    manifest=json.loads((origin/'manifest.json').read_text(encoding='utf-8'))
    path=next(p for p in (origin/'source-snapshot').glob('*-us500_multiframe.py'))
    pin=next(sha for name,sha in manifest['source_pins'].items() if Path(name).name=='us500_multiframe.py')
    if runner.digest(path)!=pin:
        raise ValueError('original_native_snapshot_binding')
    spec=importlib.util.spec_from_file_location('original_multiframe',path)
    old=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    sys.path.insert(0,str(Path(__file__).with_name('tests')))
    from test_us500_multiframe import fixture
    checks=[]
    for kwargs in ({'side':'BUY'},{'side':'SELL'},{'stop':True},{'gap':True},{'gap':True,'missing':49},{'missing':48}):
        pairs,prepared,_=fixture(**kwargs)
        a=old.execute(study.configurations()[0],prepared,pairs,old.quote_data(pairs),'.25')
        b=study.execute(study.configurations()[0],prepared,pairs,study.quote_data(pairs),'.25')
        if signature(a)!=signature(b):
            raise ValueError('native_quality_flag_fix_financial_parity')
        reviewer.inspect(b,pairs)
        checks.append(dict(fixture=kwargs,financial_parity=True,old_flags=[t['unresolved'] for t in a['trades']],new_flags=[t['unresolved'] for t in b['trades']]))
    return checks


def main():
    import argparse,warnings
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--amendment',type=Path,required=True)
    a=p.parse_args()
    warnings.filterwarnings('ignore',message='Timestamp.utcnow is deprecated.*')
    began=time.perf_counter()
    pins={str(path.resolve()):runner.digest(path) for path in (Path(__file__),Path(study.__file__),Path(reviewer.__file__),a.amendment)}
    checks=synthetic_parity(a.base)
    changed,total=0,0
    for year in (2022,2023,2024):
        origin=a.base/f'us500-multiframe-native-v2-{year}'
        if (origin/'controller.lock').exists():
            raise ValueError('original_cohort_still_owned')
        old_manifest=json.loads((origin/'manifest.json').read_text(encoding='utf-8'))
        old_result=json.loads((origin/'result.json').read_text(encoding='utf-8'))
        root=a.base/f'us500-multiframe-native-v3-review-{year}'
        root.mkdir(exist_ok=False)
        manifest=dict(old_manifest,postreview_pins=pins,origin_manifest_sha256=runner.digest(origin/'manifest.json'),kind='saved_native_books_quality_review_not_financial_resimulation')
        runner.save(root/'manifest.json',manifest)
        _,pairs,inputs=runner.load_year(a.data_root/str(year),year,lambda *args,**kw:None)
        if inputs!=json.loads((origin/f'input-{year}.json').read_text(encoding='utf-8')):
            raise ValueError('postreview_input_identity')
        runner.save(root/f'input-{year}.json',inputs)
        rows=[]
        year_changed=0
        for row in old_result['rows']:
            name=f'{year}-{row["candidate"]}-{row["scenario"]}'
            old_path=origin/(name+'.json')
            seal=json.loads((origin/(name+'-seal.json')).read_text(encoding='utf-8'))
            if runner.digest(old_path)!=seal['result_sha256'] or seal['manifest_sha256']!=runner.digest(origin/'manifest.json'):
                raise ValueError('postreview_original_seal')
            old=json.loads(old_path.read_text(encoding='utf-8'))
            new=deepcopy(old)
            for trade in new['trades']:
                exit_minute=(trade['exit_ns']//1000000//study.M)*study.M
                flag=any(t not in pairs for t in range(trade['entry_time'],exit_minute+1,study.M))
                year_changed+=int(flag!=trade['unresolved'])
                trade['unresolved']=flag
            if signature(old)!=signature(new):
                raise ValueError('postreview_financial_fields_changed')
            review=reviewer.inspect(new,pairs)
            metric=reviewer.metrics(new)
            for side in ('BUY','SELL','combined'):
                if metric['sides'][side]['modeled_closed_net_usd']!=row['sides'][side]['modeled_closed_net_usd']:
                    raise ValueError('postreview_modeled_net_changed')
            runner.save(root/(name+'.json'),new)
            runner.save(root/(name+'-review.json'),dict(review,origin_result_sha256=seal['result_sha256'],all_financial_fields_unchanged=True))
            revised=dict(year=year,candidate=row['candidate'],config=row['config'],scenario=row['scenario'],**metric)
            runner.save(root/(name+'-metrics.json'),revised)
            runner.save(root/(name+'-seal.json'),dict(result_sha256=runner.digest(root/(name+'.json')),review_sha256=runner.digest(root/(name+'-review.json')),manifest_sha256=runner.digest(root/'manifest.json')))
            rows.append(revised)
        total+=len(rows)
        changed+=year_changed
        runner.save(root/'result.json',dict(old_result,rows=rows,manifest_sha256=runner.digest(root/'manifest.json'),
                                           postreview=dict(changed_quality_flags=year_changed,native_resimulations=0,pins=pins)))
        print(json.dumps(dict(year=year,books=len(rows),corrected_quality_flags=year_changed,wall_seconds=time.perf_counter()-began)),flush=True)
    if total!=171 or any(runner.digest(Path(path))!=sha for path,sha in pins.items()):
        raise ValueError('postreview_census_or_source_drift')
    runner.save(a.base/'us500-multiframe-quality-review-v3.json',dict(books=total,corrected_quality_flags=changed,synthetic_native_parity=checks,
             wall_seconds=time.perf_counter()-began,pins=pins,native_financial_resimulations=0))


if __name__=='__main__':
    main()
