import math
from dataclasses import asdict, dataclass
import numpy as np
import pandas as pd
from app.models.schemas import DCARequest, BacktestRequest, PortfolioRequest, GoalRequest
from app.services.market_data import get_history

@dataclass
class Metrics:
    total_return: float
    annual_return: float
    volatility: float
    sharpe: float
    max_drawdown: float

def safe_float(x, default=0.0):
    try:
        if pd.isna(x) or np.isinf(x): return default
        return float(x)
    except Exception:
        return default

def calc_metrics(values: pd.Series, invested: float, risk_free_rate: float = 0.02) -> Metrics:
    values = pd.to_numeric(values, errors='coerce').dropna()
    if len(values) < 2 or invested <= 0:
        return Metrics(0,0,0,0,0)
    years = max((values.index[-1] - values.index[0]).days / 365.25 if hasattr(values.index[-1], 'day') else len(values)/252, 1/365)
    total_return = values.iloc[-1] / invested - 1
    annual_return = (values.iloc[-1] / invested) ** (1 / years) - 1 if values.iloc[-1] > 0 else -1
    rets = values.pct_change().replace([np.inf,-np.inf], np.nan).dropna()
    vol = safe_float(rets.std() * math.sqrt(252))
    sharpe = safe_float((annual_return - risk_free_rate) / vol) if vol else 0
    peak = values.cummax()
    mdd = safe_float(((values - peak) / peak).min())
    return Metrics(safe_float(total_return), safe_float(annual_return), vol, sharpe, mdd)

def next_trade(df: pd.DataFrame, date) -> pd.Series | None:
    rows = df[df['Date'] >= pd.to_datetime(date)]
    return None if rows.empty else rows.iloc[0]

def fee_for(amount: float, fees, sell=False) -> float:
    commission = max(amount * fees.commission_rate, fees.min_fee if amount > 0 else 0)
    tax = amount * fees.tax_rate if sell else 0
    return commission + tax + fees.platform_fee

def shares_for(cash: float, price: float, mode: str) -> float:
    if price <= 0: return 0
    raw = cash / price
    if mode == 'whole': return math.floor(raw)
    if mode == 'odd': return math.floor(raw * 1000) / 1000
    return raw

def run_dca(req: DCARequest) -> dict:
    df, source, warning = get_history(req.symbol, req.start, req.end)
    if df.empty: raise ValueError('沒有可用價格資料')
    purchases, total_cost, total_fees, shares = [], 0.0, 0.0, 0.0
    dates = pd.date_range(req.start, req.end, freq='MS')
    if req.initial_amount > 0:
        first = next_trade(df, req.start)
        if first is not None:
            price = float(first['Close']) * req.fees.exchange_rate
            fee = fee_for(req.initial_amount, req.fees)
            qty = shares_for(max(req.initial_amount - fee, 0), price, req.fees.share_mode)
            shares += qty; total_cost += req.initial_amount; total_fees += fee
            purchases.append({'date': first['Date'].strftime('%Y-%m-%d'), 'amount': req.initial_amount, 'price': price, 'shares': qty, 'fee': fee})
    for d in dates:
        buy_date = d.replace(day=req.buy_day)
        if buy_date < pd.to_datetime(req.start) or buy_date > pd.to_datetime(req.end): continue
        row = next_trade(df, buy_date)
        if row is None: continue
        price = float(row['Close']) * req.fees.exchange_rate
        fee = fee_for(req.monthly_amount, req.fees)
        qty = shares_for(max(req.monthly_amount - fee, 0), price, req.fees.share_mode)
        shares += qty; total_cost += req.monthly_amount; total_fees += fee
        purchases.append({'date': row['Date'].strftime('%Y-%m-%d'), 'amount': req.monthly_amount, 'price': price, 'shares': qty, 'fee': fee})
        if req.reinvest_dividends and float(row.get('Dividends', 0)) > 0:
            div_cash = shares * float(row['Dividends']) * req.fees.exchange_rate
            div_qty = shares_for(div_cash, price, req.fees.share_mode)
            shares += div_qty
            purchases.append({'date': row['Date'].strftime('%Y-%m-%d'), 'amount': div_cash, 'price': price, 'shares': div_qty, 'fee': 0, 'type': 'dividend_reinvest'})
    values = pd.Series((df['Close'].values * req.fees.exchange_rate * shares), index=pd.to_datetime(df['Date']))
    current_value = safe_float(values.iloc[-1]) if len(values) else 0
    metrics = calc_metrics(values, total_cost)
    avg_cost = total_cost / shares if shares else 0
    return {'symbol': req.symbol.upper(), 'source': source, 'warning': warning, 'total_invested': total_cost,
            'current_value': current_value, 'profit': current_value-total_cost, 'total_return': metrics.total_return,
            'annual_return': metrics.annual_return, 'max_drawdown': metrics.max_drawdown, 'shares': shares,
            'average_cost': avg_cost, 'total_fees': total_fees, 'fee_impact': total_fees / total_cost if total_cost else 0,
            'purchases': purchases, 'equity_curve': [{'date': k.strftime('%Y-%m-%d'), 'value': safe_float(v)} for k,v in values.items()]}

def portfolio_series(assets, start, end):
    series, warnings = [], []
    for a in assets:
        df, src, warn = get_history(a.symbol, start, end)
        if warn: warnings.append(f'{a.symbol}: {warn}')
        s = df.set_index('Date')['Close'].astype(float)
        s = s / s.iloc[0] * float(a.weight)
        series.append(s.rename(a.symbol.upper()))
    merged = pd.concat(series, axis=1).ffill().dropna()
    return merged.sum(axis=1), merged, warnings

def run_backtest(req: BacktestRequest) -> dict:
    total_weight = sum(a.weight for a in req.assets) or 1
    for a in req.assets: a.weight = a.weight / total_weight
    norm, components, warnings = portfolio_series(req.assets, req.start, req.end)
    invested = req.initial_amount
    buy_records = []
    if req.method == 'lump_sum':
        values = norm * req.initial_amount
        buy_records.append({'date': norm.index[0].strftime('%Y-%m-%d'), 'amount': req.initial_amount, 'type': 'lump_sum'})
    else:
        values = pd.Series(0.0, index=norm.index); units = 0.0
        for d in pd.date_range(req.start, req.end, freq='MS'):
            rows = norm[norm.index >= d]
            if rows.empty: continue
            px_date, px = rows.index[0], rows.iloc[0]
            amount = req.initial_amount if not buy_records else req.monthly_amount
            if amount <= 0: continue
            units += amount / px; invested += 0 if not buy_records else amount
            buy_records.append({'date': px_date.strftime('%Y-%m-%d'), 'amount': amount, 'type': 'dca'})
        values = norm * units
    metrics = calc_metrics(values, invested, req.risk_free_rate)
    daily = values.pct_change().dropna()
    monthly = values.resample('ME').last().pct_change().dropna()
    yearly = values.resample('YE').last().pct_change().dropna()
    win_rate = safe_float((monthly > 0).mean())
    peak = values.cummax(); dd = (values - peak) / peak
    return {'metrics': asdict(metrics), 'invested': invested, 'final_value': safe_float(values.iloc[-1]), 'win_rate': win_rate,
            'warnings': warnings, 'buy_records': buy_records,
            'equity_curve': [{'date': k.strftime('%Y-%m-%d'), 'value': safe_float(v)} for k,v in values.items()],
            'drawdown_curve': [{'date': k.strftime('%Y-%m-%d'), 'drawdown': safe_float(v)} for k,v in dd.items()],
            'monthly_returns': [{'period': k.strftime('%Y-%m'), 'return': safe_float(v)} for k,v in monthly.items()],
            'yearly_returns': [{'year': k.strftime('%Y'), 'return': safe_float(v)} for k,v in yearly.items()]}

def run_portfolio(req: PortfolioRequest) -> dict:
    total_weight = sum(a.weight for a in req.assets) or 1
    for a in req.assets: a.weight = a.weight / total_weight
    norm, components, warnings = portfolio_series(req.assets, req.start, req.end)
    values = norm * 100000
    metrics = calc_metrics(values, 100000, req.risk_free_rate)
    returns = components.pct_change().dropna()
    corr = returns.corr().fillna(0)
    contrib = [{'symbol': c, 'weight': next((a.weight for a in req.assets if a.symbol.upper()==c), 0), 'return': safe_float(components[c].iloc[-1]-components[c].iloc[0])} for c in components.columns]
    return {'metrics': asdict(metrics), 'warnings': warnings, 'correlation': corr.reset_index().rename(columns={'index':'symbol'}).to_dict('records'),
            'contributions': contrib, 'weights': [{'symbol': a.symbol.upper(), 'weight': a.weight} for a in req.assets],
            'equity_curve': [{'date': k.strftime('%Y-%m-%d'), 'value': safe_float(v)} for k,v in values.items()]}

def run_goal(req: GoalRequest) -> dict:
    monthly_rate = (1 + req.annual_return) ** (1/12) - 1
    if req.mode == 'time':
        months, value = 0, req.initial_amount
        monthly = req.monthly_amount or 0
        while value < req.target_amount and months < 1200:
            value = value * (1 + monthly_rate) + monthly; months += 1
        return {'months': months, 'years': months // 12, 'remaining_months': months % 12, 'estimated_final': value}
    years = req.years or 1; months = max(int(round(years * 12)), 1)
    future_initial = req.initial_amount * ((1 + monthly_rate) ** months)
    if abs(monthly_rate) < 1e-9:
        monthly_needed = (req.target_amount - future_initial) / months
    else:
        monthly_needed = (req.target_amount - future_initial) * monthly_rate / (((1 + monthly_rate) ** months) - 1)
    return {'monthly_needed': max(0, monthly_needed), 'months': months, 'years': months/12}
