from datetime import datetime
import pandas as pd
import numpy as np

SAMPLE_QUOTES = {
    '2330.TW': {'name': '台積電範例資料', 'base': 820.0},
    '0050.TW': {'name': '元大台灣50範例資料', 'base': 170.0},
    '00878.TW': {'name': '國泰永續高股息範例資料', 'base': 22.0},
    'VOO': {'name': 'Vanguard S&P 500 ETF Sample', 'base': 500.0},
    'QQQ': {'name': 'Invesco QQQ Sample', 'base': 450.0},
    'QQQM': {'name': 'Invesco NASDAQ 100 ETF Sample', 'base': 185.0},
    'AAPL': {'name': 'Apple Sample', 'base': 190.0},
}

def sample_history(symbol: str, start: str = '2021-01-01', end: str | None = None) -> pd.DataFrame:
    end = end or datetime.utcnow().strftime('%Y-%m-%d')
    idx = pd.date_range(start=start, end=end, freq='B')
    if len(idx) == 0:
        idx = pd.date_range(end=end, periods=260, freq='B')
    base = SAMPLE_QUOTES.get(symbol.upper(), {'base': 100.0})['base']
    seed = abs(hash(symbol.upper())) % 10000
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.00035, 0.014, len(idx))
    close = base * np.cumprod(1 + returns)
    open_ = close * (1 + rng.normal(0, 0.004, len(idx)))
    high = np.maximum(open_, close) * (1 + rng.random(len(idx)) * 0.012)
    low = np.minimum(open_, close) * (1 - rng.random(len(idx)) * 0.012)
    volume = rng.integers(800000, 9000000, len(idx))
    div = np.zeros(len(idx))
    if len(idx) > 90:
        div[::63] = close[::63] * 0.003
    df = pd.DataFrame({'Date': idx, 'Open': open_, 'High': high, 'Low': low, 'Close': close, 'Adj Close': close, 'Volume': volume, 'Dividends': div})
    return df

BUSINESS_CYCLE_SAMPLE = [
    {'date': '2024-01-01', 'score': 27, 'light': '綠燈', 'state': '穩定'},
    {'date': '2024-04-01', 'score': 31, 'light': '黃紅燈', 'state': '偏熱'},
    {'date': '2024-07-01', 'score': 29, 'light': '綠燈', 'state': '穩定'},
    {'date': '2024-10-01', 'score': 23, 'light': '黃藍燈', 'state': '需觀察'},
    {'date': '2025-01-01', 'score': 25, 'light': '綠燈', 'state': '穩定'},
    {'date': '2025-04-01', 'score': 28, 'light': '綠燈', 'state': '穩定'},
    {'date': '2025-07-01', 'score': 22, 'light': '黃藍燈', 'state': '偏弱'},
    {'date': '2025-10-01', 'score': 20, 'light': '藍燈', 'state': '偏弱'},
    {'date': '2026-01-01', 'score': 24, 'light': '黃藍燈', 'state': '需觀察'},
]
