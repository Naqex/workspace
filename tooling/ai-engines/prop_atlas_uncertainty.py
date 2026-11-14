"""Registered moving-day-block bootstrap, no selection or new strategy trials."""
import zlib
import numpy as np
from prop_atlas_core import JOB,event
from prop_campaign_source import read,write_json


def intervals(values,seed,replications=50000,cells=112):
    a=np.asarray(values,dtype='float64');n=len(a)
    if n<5:return dict(n=n,status='TOO_FEW_FOR_BLOCK_DIAGNOSTIC')
    length=5;k=(n+length-1)//length;remainder=n-length*(k-1)
    wrapped=np.r_[a,a[:length]];p=np.r_[0.,np.cumsum(wrapped)]
    sums=p[np.arange(n)+length]-p[np.arange(n)]
    tail=p[np.arange(n)+remainder]-p[np.arange(n)]
    rng=np.random.default_rng(seed)
    indices=rng.integers(0,n,size=(replications,k))
    sample=(sums[indices[:,:-1]].sum(axis=1)+tail[indices[:,-1]])/n
    alpha=.05/cells
    return dict(n=n,mean=float(a.mean()),ordinary95=list(map(float,np.quantile(sample,[.025,.975]))),
        bonferroni112_95_per_year_model=list(map(float,np.quantile(sample,[alpha/2,1-alpha/2]))),
        bootstrap_replications=replications,block_length_observed_signal_days=length,
        seed=seed,tail_resolution=1/replications,status='DESCRIPTIVE_NOT_PROVEN_EDGE')


def run():
    atlas=read(JOB/'atlas-stage0.json');result=[]
    for i,c in enumerate(atlas['cells']):
        name=c['cell']['id'];raw=read(JOB/f'stage0-{name}.json')['rows']
        for year in (2022,2023):
            rows=[r for r in raw if r['day'].startswith(str(year))]
            for model in ('SYM_FLAT','ASYM_FLAT'):
                valid=[r for r in rows if 'money' in r]
                if len(valid)!=len(rows):
                    out=dict(status='ENDPOINT_INCOMPLETE_NO_FULL_SAMPLE_INTERVAL',n=len(valid))
                else:
                    seed=zlib.crc32(f'{name}:{year}:{model}'.encode())
                    out=intervals([r['money'][model]['net'] for r in valid],seed)
                result.append(dict(cell=name,year=year,model=model,**out))
        if i%16==0:event('bootstrap_intervals',cells=i,total=112)
    write_json(JOB/'atlas-uncertainty.json',dict(rows=result,
        correction_scope='112 catalog cells per year/model, not a global guarantee across all views',
        historical_validation_already_exposed=True,selection_changed=False))


if __name__=='__main__':run()
