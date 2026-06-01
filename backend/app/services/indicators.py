import numpy as np
import pandas as pd
from app.services.market_data import get_history
from app.services.calculations import safe_float

def interpret(name: str, latest: float, row: pd.Series) -> str:
    if name in {'RSI','MFI'}:
        return '偏強' if latest >= 60 else '偏弱' if latest <= 40 else '震盪'
    if name in {'MACD','Momentum','ROC','OBV'}:
        return '偏強' if latest > 0 else '偏弱' if latest < 0 else '需觀察'
    if name in {'ATR','Volume MA'}:
        return '需觀察'
    close = row.get('Close', 0)
    return '偏強' if close and latest < close else '偏弱' if close and latest > close else '震盪'

def compute_indicators(symbol: str, start: str, end: str) -> dict:
    df, source, warning = get_history(symbol, start, end)
    if df.empty: raise ValueError('沒有可用價格資料')
    d = df.copy(); c=d['Close']; h=d['High']; l=d['Low']; v=d['Volume']
    d['SMA'] = c.rolling(20).mean(); d['EMA'] = c.ewm(span=20, adjust=False).mean()
    ema12=c.ewm(span=12, adjust=False).mean(); ema26=c.ewm(span=26, adjust=False).mean()
    d['MACD'] = ema12-ema26; d['MACD_signal']=d['MACD'].ewm(span=9, adjust=False).mean()
    delta=c.diff(); gain=delta.clip(lower=0).rolling(14).mean(); loss=(-delta.clip(upper=0)).rolling(14).mean()
    d['RSI'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
    low9=l.rolling(9).min(); high9=h.rolling(9).max(); d['RSV']=(c-low9)/(high9-low9).replace(0,np.nan)*100
    k=[]; dd=[]; pk=pdv=50.0
    for rsv in d['RSV'].fillna(50):
        pk = 2/3*pk + 1/3*rsv; pdv = 2/3*pdv + 1/3*pk; k.append(pk); dd.append(pdv)
    d['K']=k; d['D']=dd; d['J']=3*d['K']-2*d['D']; d['KD']=d['K']-d['D']; d['KDJ']=d['J']
    ma20=c.rolling(20).mean(); std20=c.rolling(20).std(); d['Bollinger Upper']=ma20+2*std20; d['Bollinger Lower']=ma20-2*std20
    tr=pd.concat([(h-l),(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); d['ATR']=tr.rolling(14).mean()
    d['OBV']=(np.sign(c.diff()).fillna(0)*v).cumsum(); d['Volume MA']=v.rolling(20).mean()
    d['Momentum']=c-c.shift(10); d['ROC']=c.pct_change(10)*100
    tp=(h+l+c)/3; sma_tp=tp.rolling(20).mean(); mad=(tp-sma_tp).abs().rolling(20).mean(); d['CCI']=(tp-sma_tp)/(0.015*mad.replace(0,np.nan))
    d['Williams Percent R']=(h.rolling(14).max()-c)/(h.rolling(14).max()-l.rolling(14).min()).replace(0,np.nan)*-100
    mf=tp*v; pos=mf.where(tp>tp.shift(),0).rolling(14).sum(); neg=mf.where(tp<tp.shift(),0).rolling(14).sum(); d['MFI']=100-(100/(1+pos/neg.replace(0,np.nan)))
    d['Volume Change']=v.pct_change()*100
    d = d.replace([np.inf,-np.inf], np.nan).ffill().bfill().fillna(0)
    last=d.iloc[-1]
    names=['SMA','EMA','MACD','RSI','KDJ','KD','Bollinger Upper','Bollinger Lower','ATR','OBV','Volume MA','Momentum','ROC','CCI','Williams Percent R','MFI','Volume Change']
    latest=[{'name': n, 'value': safe_float(last[n]), 'interpretation': interpret(n, safe_float(last[n]), last)} for n in names]
    sma5=c.rolling(5).mean().iloc[-1]; sma20=c.rolling(20).mean().iloc[-1]; sma60=c.rolling(60).mean().iloc[-1]
    latest.append({'name':'均線排列','value': safe_float(sma5-sma60), 'interpretation':'偏強' if sma5>sma20>sma60 else '偏弱' if sma5<sma20<sma60 else '震盪'})
    prev=d.iloc[-2] if len(d)>1 else last
    latest.append({'name':'黃金交叉','value': safe_float(last['MACD']-last['MACD_signal']), 'interpretation':'偏強' if prev['MACD']<=prev['MACD_signal'] and last['MACD']>last['MACD_signal'] else '需觀察'})
    latest.append({'name':'死亡交叉','value': safe_float(last['MACD']-last['MACD_signal']), 'interpretation':'偏弱' if prev['MACD']>=prev['MACD_signal'] and last['MACD']<last['MACD_signal'] else '需觀察'})
    chart_cols=['Date','Close']+[n for n in names if n in d.columns]
    history=[{**{'date': r['Date'].strftime('%Y-%m-%d')}, **{col: safe_float(r[col]) for col in chart_cols if col!='Date'}} for _,r in d[chart_cols].iterrows()]
    return {'symbol': symbol.upper(), 'source': source, 'warning': warning, 'latest': latest, 'history': history}
