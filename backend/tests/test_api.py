from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import DCARequest, BacktestRequest, BacktestAsset, GoalRequest
from app.services.calculations import run_dca, run_backtest, run_goal
from app.services.indicators import compute_indicators

client = TestClient(app)

def test_quote_api():
    r = client.get('/api/quote', params={'symbol': 'AAPL'})
    assert r.status_code == 200
    assert r.json()['price'] > 0

def test_history_api():
    r = client.get('/api/history', params={'symbol': 'VOO', 'start': '2024-01-01', 'end': '2024-03-01'})
    assert r.status_code == 200
    assert len(r.json()['prices']) > 0

def test_dca_calculation():
    result = run_dca(DCARequest(symbol='0050.TW', monthly_amount=10000, initial_amount=10000, start='2024-01-01', end='2024-06-30'))
    assert result['total_invested'] > 0
    assert result['shares'] > 0
    assert result['purchases']

def test_backtest_calculation():
    result = run_backtest(BacktestRequest(assets=[BacktestAsset(symbol='VOO', weight=0.6), BacktestAsset(symbol='QQQ', weight=0.4)], start='2024-01-01', end='2024-06-30'))
    assert result['final_value'] > 0
    assert result['buy_records']

def test_indicators_calculation():
    result = compute_indicators('AAPL', '2024-01-01', '2024-08-01')
    names = {x['name'] for x in result['latest']}
    assert {'SMA','EMA','MACD','RSI','KDJ','KD','ATR','OBV'}.issubset(names)

def test_goal_calculation():
    r1 = run_goal(GoalRequest(mode='time', target_amount=1000000, initial_amount=100000, monthly_amount=10000, annual_return=0.05))
    r2 = run_goal(GoalRequest(mode='monthly', target_amount=1000000, initial_amount=100000, years=5, annual_return=0.05))
    assert r1['months'] > 0
    assert r2['monthly_needed'] > 0

def test_fundamentals_api():
    r = client.get('/api/fundamentals', params={'symbol': 'AAPL'})
    assert r.status_code == 200
    body = r.json()
    assert body['symbol'] == 'AAPL'
    labels = {field['label'] for field in body['fields']}
    assert {'公司名稱', '本益比 PE', 'Beta', '近一年高點'}.issubset(labels)
    assert len(body['beginner_assessment']) == 6


def test_analysis_summary_api():
    r = client.get('/api/analysis-summary', params={'symbol': 'VOO'})
    assert r.status_code == 200
    body = r.json()
    assert body['quote_summary']['price'] > 0
    assert body['beginner_overall']
    assert 'dca_entry' in body


def test_indicator_guide_api():
    r = client.get('/api/indicator-guide')
    assert r.status_code == 200
    names = {item['name'] for item in r.json()['items']}
    assert {'SMA', 'EMA', 'MACD', 'RSI', 'KD', 'KDJ', 'Bollinger Bands', 'ATR', 'OBV', 'Volume MA', 'Momentum', 'ROC', 'CCI', 'Williams Percent R', 'MFI', '黃金交叉', '死亡交叉', '均線排列'}.issubset(names)


def test_fundamentals_missing_values_are_safe():
    r = client.get('/api/fundamentals', params={'symbol': 'UNKNOWN_TEST_SYMBOL'})
    assert r.status_code == 200
    body = r.json()
    missing = [field for field in body['fields'] if field['is_missing']]
    assert missing
    assert all(field['value'] == '資料暫缺' for field in missing)
