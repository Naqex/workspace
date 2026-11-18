"""Closed-H1 formula ports; no bot execution, inferred volume, or tuned defaults."""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from prop_v10_signals import rolling
from quant_core.corpus_signals import wilder_rsi

PATTERNS = ("Engulfing","Harami","Hammer","BlackCrows","MeetingLines","StarDoji")
OSCILLATORS = ("RSI","CCI","Stoch","MFI")


def lag(values, count):
    values=np.asarray(values,dtype=float)
    return np.r_[np.full(count,np.nan),values[:-count]] if count else values


def pattern(frame, name):
    o,h,l,c=(np.asarray(frame[k],dtype=float) for k in ("o","h","l","c"))
    o2,c2,o3,c3=(lag(v,n) for v,n in ((o,1),(c,1),(o,2),(c,2)))
    body=rolling(abs(c-o),12,"mean",prior=False)
    midpoint=(h+l)/2
    middle2,middle3=lag(midpoint,1),lag(midpoint,2)
    trend=rolling(c,5,"mean",prior=True)
    if name=="Engulfing":
        sell=(o2<c2)&(o-c>body)&(c<o2)&((o2+c2)/2>trend)&(o>c2)
        buy=(o2>c2)&(c-o>body)&(c>o2)&((o2+c2)/2<trend)&(o<c2)
    elif name=="Harami":
        sell=(c<o)&(c2-o2>body)&(c>o2)&(o<c2)&(middle2>trend)
        buy=(c>o)&(o2-c2>body)&(c<o2)&(o>c2)&(middle2<trend)
    elif name=="Hammer":
        upper=np.minimum(o,c)>h-(h-l)/3
        sell=(midpoint>trend)&upper&(c>c2)&(o>o2)
        buy=(midpoint<trend)&upper&(c<c2)&(o<o2)
    elif name=="BlackCrows":
        sell=(o3-c3>body)&(o2-c2>body)&(o-c>body)&(middle2<middle3)&(midpoint<middle2)
        buy=(c3-o3>body)&(c2-o2>body)&(c-o>body)&(middle2>middle3)&(midpoint>middle2)
    elif name=="MeetingLines":
        sell=(c2-o2>body)&(o-c>body)&(abs(c-c2)<.1*body)
        buy=(o2-c2>body)&(c-o>body)&(abs(c-c2)<.1*body)
    elif name=="StarDoji":
        small=abs(c2-o2)
        rising=(c3-o3>body)&(c2>c3)&(o2>o3)
        falling=(o3-c3>body)&(c2<c3)&(o2<o3)
        sell=rising&(((small<.1*body)&(o<c2)&(c<c2))|
                     ((small<.5*body)&(c<(o3+c3)/2)))
        buy=falling&(((small<.1*body)&(o>c2)&(c>c2))|
                     ((small<.5*body)&(c>(o3+c3)/2)))
    else:
        raise ValueError("UNKNOWN_CORPUS_PATTERN")
    return np.where(sell,-1,np.where(buy,1,0)).astype("int8")


def oscillator(frame,name,volume=None):
    close=np.asarray(frame["c"],dtype=float)
    if name=="RSI":
        return wilder_rsi(close,37)
    if name=="CCI":
        out=np.full(len(close),np.nan)
        if len(close)>=37:
            windows=sliding_window_view(close,37)
            mean=windows.mean(axis=1)
            deviation=abs(windows-mean[:,None]).mean(axis=1)
            out[36:]=np.divide(close[36:]-mean,.015*deviation,
                               out=np.zeros(len(mean)),where=deviation!=0)
        return out
    if name=="Stoch":
        low=rolling(frame["l"],47,"min",prior=False)
        high=rolling(frame["h"],47,"max",prior=False)
        numerator=rolling(close-low,13,"mean",prior=False)
        denominator=rolling(high-low,13,"mean",prior=False)
        main=np.divide(100*numerator,denominator,out=np.full(len(close),100.),
                       where=denominator!=0)
        return rolling(main,9,"mean",prior=False)
    if name=="MFI":
        if volume is None:
            raise ValueError("ADMITTED_TICK_VOLUME_REQUIRED")
        volume=np.asarray(volume,dtype=float)
        if len(volume)!=len(close) or np.any(~np.isfinite(volume)) or np.any(volume<0):
            raise ValueError("INVALID_TICK_VOLUME")
        typical=(np.asarray(frame["h"])+np.asarray(frame["l"])+close)/3
        delta=typical-lag(typical,1)
        positive=rolling(np.where(delta>0,typical*volume,0),37,"mean",prior=False)
        negative=rolling(np.where(delta<0,typical*volume,0),37,"mean",prior=False)
        result=np.divide(100*positive,positive+negative,out=np.full(len(close),100.),
                         where=positive+negative!=0)
        result[:37]=np.nan
        return result
    raise ValueError("UNKNOWN_CORPUS_OSCILLATOR")


def signals(frame,pattern_name,oscillator_name,volume=None):
    direction=pattern(frame,pattern_name)
    values=oscillator(frame,oscillator_name,volume)
    low,high={"RSI":(40,60),"CCI":(-50,50),"MFI":(40,60),"Stoch":(30,70)}[oscillator_name]
    return np.where((direction==1)&(values<low),1,
                    np.where((direction==-1)&(values>high),-1,0)).astype("int8")
