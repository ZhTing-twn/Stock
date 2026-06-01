import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[2] / 'stock_cache.sqlite3'

def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS prices (
            symbol TEXT NOT NULL, date TEXT NOT NULL, open REAL, high REAL, low REAL,
            close REAL, adj_close REAL, volume REAL, dividends REAL DEFAULT 0,
            PRIMARY KEY(symbol, date))''')
        conn.commit()

def save_history(symbol: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    init_db()
    out = df.copy()
    if 'Date' not in out.columns:
        out = out.reset_index().rename(columns={'index': 'Date'})
    with sqlite3.connect(DB_PATH) as conn:
        for _, r in out.iterrows():
            conn.execute('''INSERT OR REPLACE INTO prices VALUES(?,?,?,?,?,?,?,?,?)''', (
                symbol.upper(), pd.to_datetime(r['Date']).strftime('%Y-%m-%d'), float(r.get('Open', 0) or 0),
                float(r.get('High', 0) or 0), float(r.get('Low', 0) or 0), float(r.get('Close', 0) or 0),
                float(r.get('Adj Close', r.get('Close', 0)) or 0), float(r.get('Volume', 0) or 0),
                float(r.get('Dividends', 0) or 0)))
        conn.commit()

def load_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query('''SELECT date as Date, open as Open, high as High, low as Low,
            close as Close, adj_close as "Adj Close", volume as Volume, dividends as Dividends
            FROM prices WHERE symbol=? AND date BETWEEN ? AND ? ORDER BY date''', conn, params=(symbol.upper(), start, end))
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
    return df
