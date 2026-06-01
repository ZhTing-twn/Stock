from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from app.services.cache import load_history, save_history
from app.utils.sample_data import sample_history, SAMPLE_QUOTES

PRICE_COLUMNS = ['Open','High','Low','Close','Adj Close','Volume','Dividends']

def clean_history(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=['Date'] + PRICE_COLUMNS)
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    if 'Date' not in df.columns:
        df = df.reset_index()
    if 'Adj Close' not in df.columns and 'Close' in df.columns:
        df['Adj Close'] = df['Close']
    if 'Dividends' not in df.columns:
        df['Dividends'] = 0.0
    for col in PRICE_COLUMNS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['Date','Close']).sort_values('Date')
    df[PRICE_COLUMNS] = df[PRICE_COLUMNS].ffill().bfill().fillna(0)
    return df[['Date'] + PRICE_COLUMNS]

def get_history(symbol: str, start: str, end: str | None = None) -> tuple[pd.DataFrame, str, str | None]:
    end = end or datetime.utcnow().strftime('%Y-%m-%d')
    symbol = symbol.upper().strip()
    try:
        cached = load_history(symbol, start, end)
        if len(cached) > 5:
            return clean_history(cached), 'sqlite-cache', None
    except Exception:
        pass
    try:
        raw = yf.download(symbol, start=start, end=(pd.to_datetime(end) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), progress=False, auto_adjust=False, actions=True, threads=False)
        df = clean_history(raw)
        if not df.empty:
            save_history(symbol, df)
            return df, 'yfinance', None
        raise ValueError('empty data')
    except Exception as exc:
        df = sample_history(symbol, start, end)
        return clean_history(df), 'sample-fallback', f'外部資料取得失敗，已使用本地範例資料：{exc}'

def get_quote(symbol: str) -> dict:
    end = datetime.utcnow().date()
    start = (end - timedelta(days=370)).isoformat()
    df, source, warning = get_history(symbol, start, end.isoformat())
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    change = float(last['Close'] - prev['Close'])
    pct = float(change / prev['Close'] * 100) if prev['Close'] else 0.0
    meta = SAMPLE_QUOTES.get(symbol.upper(), {'name': symbol.upper()})
    return {
        'symbol': symbol.upper(), 'name': meta.get('name', symbol.upper()), 'price': float(last['Close']),
        'change': change, 'change_percent': pct, 'volume': float(last['Volume']),
        'year_high': float(df['High'].max()), 'year_low': float(df['Low'].min()),
        'updated_at': pd.to_datetime(last['Date']).isoformat(), 'source': source, 'warning': warning,
    }

def frame_to_records(df: pd.DataFrame) -> list[dict]:
    return [{
        'date': pd.to_datetime(r['Date']).strftime('%Y-%m-%d'), 'open': float(r['Open']), 'high': float(r['High']),
        'low': float(r['Low']), 'close': float(r['Close']), 'adj_close': float(r['Adj Close']),
        'volume': float(r['Volume']), 'dividends': float(r.get('Dividends', 0)),
    } for _, r in df.iterrows()]
