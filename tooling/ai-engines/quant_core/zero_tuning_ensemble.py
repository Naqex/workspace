"""One deterministic medoid composition; no subset, weight, side or horizon search."""
import numpy as np


def cumulative_drawdown(daily):
    equity=np.r_[0.,np.cumsum(np.asarray(daily,dtype=float))]
    return float(np.max(np.maximum.accumulate(equity)-equity))


def mechanical_composition(components, *, max_sleeves=8):
    """Correlation is a supplied Development proxy, not a claim of independent bets."""
    rows=sorted(components,key=lambda r:r["id"])
    if len({r["id"] for r in rows})!=len(rows):
        raise ValueError("duplicate_component_id")
    if not rows:
        return dict(selected=[],clusters=[],blocked=[],ids=[],correlation=[],overlap=[],
                    weights=None,subset_search=False)
    daily=np.asarray([r["daily"] for r in rows],dtype=float)
    if daily.ndim!=2 or daily.shape[1]<2 or not np.isfinite(daily).all():
        raise ValueError("invalid_daily_vectors")
    centered=daily-daily.mean(axis=1,keepdims=True)
    norm=np.sqrt(np.sum(centered*centered,axis=1))
    denom=norm[:,None]*norm[None,:]
    corr=np.divide(centered@centered.T,denom,out=np.ones_like(denom),where=denom>0)
    corr=np.round(np.clip(corr,-1,1),12)
    events=[set(map(int,r["events"])) for r in rows]
    overlap=np.zeros_like(corr)
    parent=list(range(len(rows)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i in range(len(rows)):
        for j in range(i):
            overlap[i,j]=overlap[j,i]=len(events[i]&events[j])/max(1,min(len(events[i]),len(events[j])))
            if ((rows[i]["asset"],rows[i]["family"])==(rows[j]["asset"],rows[j]["family"])
                    and (corr[i,j]>=.30 or overlap[i,j]>=.50)):
                parent[find(i)]=find(j)
    groups={}
    for i in range(len(rows)):
        groups.setdefault(find(i),[]).append(i)
    representatives,clusters=[],[]
    for group in groups.values():
        winner=min(group,key=lambda i:(round(sum(1-corr[i,j] for j in group),12),rows[i]["id"]))
        representatives.append(winner)
        clusters.append(dict(members=[rows[i]["id"] for i in group],medoid=rows[winner]["id"]))
    selected,blocked=[],[]
    for i in sorted(representatives,key=lambda i:(rows[i]["asset"],rows[i]["family"],rows[i]["id"])):
        conflicts=[rows[j]["id"] for j in selected if corr[i,j]>=.30]
        if conflicts:
            blocked.append(dict(id=rows[i]["id"],reason="CORRELATION",conflicts=conflicts))
        elif len(selected)==max_sleeves:
            blocked.append(dict(id=rows[i]["id"],reason="FIXED_MAX_SLEEVES"))
        else:
            selected.append(i)
    return dict(selected=[rows[i]["id"] for i in selected],clusters=clusters,blocked=blocked,
                ids=[r["id"] for r in rows],correlation=corr.tolist(),overlap=overlap.tolist(),
                weights={rows[i]["id"]:1 for i in selected},subset_search=False,
                correlation_round_digits=12)
