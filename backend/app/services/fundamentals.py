from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
import math
import yfinance as yf

from app.services.market_data import get_quote
from app.services.indicator_guide import get_indicator_guide
from app.services.indicators import compute_indicators
from app.services.calculations import run_backtest
from app.models.schemas import BacktestRequest, BacktestAsset

MISSING = '資料暫缺'

FUNDAMENTAL_EXPLANATIONS = {
    'company_name': '公司名稱可幫助確認代號是否正確，避免看錯股票或 ETF。',
    'industry': '產業別代表公司主要所屬領域，可用來理解它受哪些景氣或市場因素影響。',
    'market': '市場別代表股票主要掛牌交易的市場，例如台股、美股或其他交易所。',
    'price': '股價是目前市場成交附近的價格，只代表當下價格，不代表公司完整價值。',
    'market_cap': '市值是股價乘以股數，常用來看公司規模大小。',
    'pe': '本益比 PE 是股價相對每股盈餘的倍數，可粗略觀察市場願意付多少價格換取獲利。',
    'pb': '股價淨值比 PB 是股價相對每股淨值的倍數，常用來看價格相對帳面資產是否偏高。',
    'ps': '股價營收比 PS 是市值相對營收的倍數，常用於獲利尚不穩定但有營收的公司。',
    'eps': 'EPS 是每股盈餘，代表公司獲利分攤到每一股的金額。',
    'roe': 'ROE 是股東權益報酬率，用來看公司運用股東資金產生獲利的效率。',
    'roa': 'ROA 是資產報酬率，用來看公司用全部資產創造獲利的效率。',
    'gross_margin': '毛利率看產品或服務扣除直接成本後還剩多少比例，反映基本獲利空間。',
    'operating_margin': '營業利益率看本業經營扣除營運費用後的獲利能力。',
    'net_margin': '淨利率看所有成本與費用後，營收最後能留下多少利潤。',
    'revenue_growth': '營收成長率看收入是否擴大，能幫助理解公司規模是否成長。',
    'earnings_growth': '盈餘成長率看獲利是否增加，比營收更接近股東能分到的成果。',
    'debt_ratio': '負債比率看公司資金中有多少來自負債，比例越高通常財務壓力越需要留意。',
    'current_ratio': '流動比率看短期資產是否足以支應短期負債，是觀察短期安全性的指標。',
    'free_cash_flow': '自由現金流代表公司營運與投資後可自由運用的現金，反映現金創造能力。',
    'dividend': '股利是公司分配給股東的現金或股票，可能受盈餘與政策影響而變動。',
    'dividend_yield': '殖利率是股利相對股價的比例，可觀察現金配息相對目前價格的程度。',
    'payout_ratio': '配息率看公司把盈餘拿出多少比例分配，過高時需留意是否能長期維持。',
    'beta': 'Beta 代表股價相對大盤的波動程度，大於 1 通常表示波動比大盤更大。',
    'year_high': '近一年高點可幫助理解目前價格在最近一年區間中的相對位置。',
    'year_low': '近一年低點可幫助理解目前價格在最近一年區間中的下緣位置。',
}

FIELD_LABELS = {
    'company_name': '公司名稱', 'industry': '產業別', 'market': '市場別', 'price': '股價', 'market_cap': '市值',
    'pe': '本益比 PE', 'pb': '股價淨值比 PB', 'ps': '股價營收比 PS', 'eps': 'EPS', 'roe': 'ROE', 'roa': 'ROA',
    'gross_margin': '毛利率', 'operating_margin': '營業利益率', 'net_margin': '淨利率', 'revenue_growth': '營收成長率',
    'earnings_growth': '盈餘成長率', 'debt_ratio': '負債比率', 'current_ratio': '流動比率', 'free_cash_flow': '自由現金流',
    'dividend': '股利', 'dividend_yield': '殖利率', 'payout_ratio': '配息率', 'beta': 'Beta', 'year_high': '近一年高點', 'year_low': '近一年低點'
}

YF_MAP = {
    'company_name': ['longName', 'shortName'], 'industry': ['industry', 'sector'], 'market': ['exchange', 'market'],
    'market_cap': ['marketCap'], 'pe': ['trailingPE', 'forwardPE'], 'pb': ['priceToBook'], 'ps': ['priceToSalesTrailing12Months'],
    'eps': ['trailingEps', 'forwardEps'], 'roe': ['returnOnEquity'], 'roa': ['returnOnAssets'],
    'gross_margin': ['grossMargins'], 'operating_margin': ['operatingMargins'], 'net_margin': ['profitMargins'],
    'revenue_growth': ['revenueGrowth'], 'earnings_growth': ['earningsGrowth'], 'debt_ratio': ['debtToEquity'],
    'current_ratio': ['currentRatio'], 'free_cash_flow': ['freeCashflow'], 'dividend': ['dividendRate', 'lastDividendValue'],
    'dividend_yield': ['dividendYield'], 'payout_ratio': ['payoutRatio'], 'beta': ['beta'],
    'year_high': ['fiftyTwoWeekHigh'], 'year_low': ['fiftyTwoWeekLow'],
}

PERCENT_FIELDS = {'roe','roa','gross_margin','operating_margin','net_margin','revenue_growth','earnings_growth','dividend_yield','payout_ratio'}


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if value == 'None':
        return None
    return value


def _first(info: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = _clean_value(info.get(key))
        if value is not None:
            return value
    return None


def _field(key: str, value: Any, source: str, note: str = '') -> dict[str, Any]:
    missing = value is None or value == ''
    return {
        'key': key,
        'label': FIELD_LABELS[key],
        'value': MISSING if missing else value,
        'is_missing': missing,
        'source': '資料暫缺' if missing else source,
        'note': 'yfinance 未提供此欄位，可能是台股或 ETF 資料揭露不足。' if missing else note,
        'explanation': FUNDAMENTAL_EXPLANATIONS[key],
    }


def _rate(value: Any) -> Any:
    value = _clean_value(value)
    if value is None:
        return None
    return float(value)


def _rating_from_fields(values: list[Any], scorer) -> str:
    usable = [v for v in values if isinstance(v, (int, float))]
    if not usable:
        return '資料不足'
    score = scorer(*usable)
    if score >= 2:
        return '偏佳'
    if score <= 0:
        return '偏弱'
    return '普通'


def build_beginner_assessment(raw: dict[str, Any]) -> list[dict[str, str]]:
    def val(k): return raw.get(k) if isinstance(raw.get(k), (int, float)) else None
    valuation = _rating_from_fields([val('pe'), val('pb'), val('ps')], lambda *xs: sum(1 for x in xs if x > 0 and x < 25))
    profitability = _rating_from_fields([val('roe'), val('roa'), val('net_margin')], lambda *xs: sum(1 for x in xs if x and x > 0.08))
    growth = _rating_from_fields([val('revenue_growth'), val('earnings_growth')], lambda *xs: sum(1 for x in xs if x and x > 0.05))
    safety = _rating_from_fields([val('debt_ratio'), val('current_ratio')], lambda *xs: sum(1 for x in xs if (x < 120 if x > 5 else x < 1.2)) + sum(1 for x in xs if x >= 1.2 and x <= 5))
    dividend = _rating_from_fields([val('dividend_yield'), val('payout_ratio')], lambda *xs: sum(1 for x in xs if x and x > 0) + sum(1 for x in xs if x and x < 0.8))
    risk = _rating_from_fields([val('beta')], lambda *xs: 2 if xs[0] <= 1 else 1 if xs[0] <= 1.4 else 0)
    return [
        {'category': '估值面', 'rating': valuation, 'description': '用 PE、PB、PS 粗略觀察目前價格相對獲利、淨值與營收的位置。'},
        {'category': '獲利能力', 'rating': profitability, 'description': '用 ROE、ROA、淨利率觀察公司是否能把資源轉成利潤。'},
        {'category': '成長性', 'rating': growth, 'description': '用營收與盈餘成長率觀察公司規模與獲利是否有擴大跡象。'},
        {'category': '財務安全性', 'rating': safety, 'description': '用負債與流動比率觀察短期與整體財務壓力。'},
        {'category': '股利穩定性', 'rating': dividend, 'description': '用股利、殖利率與配息率初步觀察現金分配是否有資料可參考。'},
        {'category': '波動風險', 'rating': risk, 'description': '用 Beta 與價格區間觀察波動程度，分數偏弱代表波動較需要留意。'},
    ]


def get_fundamentals(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper().strip()
    warning = None
    info: dict[str, Any] = {}
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception as exc:
        warning = f'yfinance 基本面資料取得失敗，未提供欄位會顯示資料暫缺：{exc}'
    quote = get_quote(symbol)
    raw: dict[str, Any] = {}
    fields = []
    for key in FIELD_LABELS:
        if key == 'price':
            value, source, note = quote.get('price'), quote.get('source', 'quote'), '股價使用報價服務，可能來自 yfinance、SQLite 快取或範例資料。'
        elif key == 'year_high':
            value, source, note = _first(info, YF_MAP[key]) or quote.get('year_high'), 'yfinance/quote', '若 yfinance 未提供，使用報價服務近一年資料計算。'
        elif key == 'year_low':
            value, source, note = _first(info, YF_MAP[key]) or quote.get('year_low'), 'yfinance/quote', '若 yfinance 未提供，使用報價服務近一年資料計算。'
        else:
            value, source, note = _first(info, YF_MAP.get(key, [])), 'yfinance', ''
        if key in PERCENT_FIELDS and value is not None:
            value = _rate(value)
        raw[key] = value
        fields.append(_field(key, value, source, note))
    if quote.get('warning'):
        warning = '；'.join([x for x in [warning, quote.get('warning')] if x])
    missing_keys = [f['label'] for f in fields if f['is_missing']]
    return {
        'symbol': symbol,
        'company_name': raw.get('company_name') or symbol,
        'warning': warning,
        'fields': fields,
        'beginner_assessment': build_beginner_assessment(raw),
        'data_limitations': '基本面資料優先使用 yfinance。若 yfinance 未提供、台股欄位不足或 ETF 無公司財報欄位，畫面會顯示「資料暫缺」。',
        'missing_fields': missing_keys,
    }


def get_analysis_summary(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper().strip()
    end = datetime.utcnow().date()
    start = (end - timedelta(days=365)).isoformat()
    quote = get_quote(symbol)
    fundamentals = get_fundamentals(symbol)
    indicators = compute_indicators(symbol, start, end.isoformat())
    backtest = run_backtest(BacktestRequest(assets=[BacktestAsset(symbol=symbol, weight=1)], start=start, end=end.isoformat(), method='lump_sum', initial_amount=100000, monthly_amount=0))
    indicator_map = {item['name']: item['interpretation'] for item in indicators['latest']}
    assessment = {item['category']: item['rating'] for item in fundamentals['beginner_assessment']}
    gaps = fundamentals['missing_fields'][:10]
    beginner_summary = [
        {'topic': '估值是否偏高', 'result': assessment.get('估值面', '資料不足'), 'detail': '依 PE、PB、PS 初步整理，資料不足時不做延伸推論。'},
        {'topic': '獲利能力是否穩定', 'result': assessment.get('獲利能力', '資料不足'), 'detail': '依 ROE、ROA、利潤率觀察，需搭配長期財報。'},
        {'topic': '成長性是否明顯', 'result': assessment.get('成長性', '資料不足'), 'detail': '依營收與盈餘成長率觀察是否有成長跡象。'},
        {'topic': '技術面目前狀態', 'result': indicator_map.get('均線排列') or indicator_map.get('MACD', '需觀察'), 'detail': '依均線排列、MACD、RSI 等技術指標彙整。'},
        {'topic': '波動風險高低', 'result': assessment.get('波動風險', '資料不足'), 'detail': '依 Beta、最大回撤與一年價格區間觀察。'},
        {'topic': '資料不足項目', 'result': '、'.join(gaps) if gaps else '主要欄位已有資料', 'detail': '台股或 ETF 在 yfinance 中常有部分基本面欄位缺漏。'},
    ]
    return {
        'symbol': symbol,
        'quote_summary': quote,
        'fundamental_summary': fundamentals['beginner_assessment'],
        'technical_summary': indicators['latest'][:8],
        'risk_summary': {'max_drawdown': backtest['metrics']['max_drawdown'], 'volatility': backtest['metrics']['volatility'], 'sharpe': backtest['metrics']['sharpe']},
        'backtest_summary': {'final_value': backtest['final_value'], 'total_return': backtest['metrics']['total_return'], 'annual_return': backtest['metrics']['annual_return']},
        'dca_entry': {'symbol': symbol, 'monthly_amount': 10000, 'initial_amount': 10000, 'start': start, 'end': end.isoformat()},
        'beginner_overall': beginner_summary,
        'indicator_guide': get_indicator_guide()['items'],
        'warnings': [x for x in [quote.get('warning'), fundamentals.get('warning'), indicators.get('warning')] if x],
    }
