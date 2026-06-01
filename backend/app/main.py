from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models.schemas import DCARequest, BacktestRequest, PortfolioRequest, GoalRequest
from app.services.market_data import get_quote, get_history, frame_to_records
from app.services.calculations import run_dca, run_backtest, run_portfolio, run_goal
from app.services.indicators import compute_indicators
from app.services.business_cycle import get_business_cycle
from app.services.fundamentals import get_fundamentals, get_analysis_summary
from app.services.indicator_guide import get_indicator_guide
from app.services.cache import init_db

app = FastAPI(title='Stock Investment Analyzer API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.on_event('startup')
def startup(): init_db()

@app.get('/api/health')
def health(): return {'status': 'ok'}

@app.get('/api/quote')
def quote(symbol: str = Query(..., min_length=1)):
    try: return get_quote(symbol)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@app.get('/api/history')
def history(symbol: str, start: str, end: str):
    try:
        df, source, warning = get_history(symbol, start, end)
        return {'symbol': symbol.upper(), 'source': source, 'warning': warning, 'prices': frame_to_records(df)}
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@app.post('/api/dca')
def dca(req: DCARequest):
    try: return run_dca(req)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@app.post('/api/backtest')
def backtest(req: BacktestRequest):
    try: return run_backtest(req)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@app.get('/api/indicators')
def indicators(symbol: str, start: str, end: str):
    try: return compute_indicators(symbol, start, end)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))


@app.get('/api/fundamentals')
def fundamentals(symbol: str = Query(..., min_length=1)):
    try: return get_fundamentals(symbol)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@app.get('/api/analysis-summary')
def analysis_summary(symbol: str = Query(..., min_length=1)):
    try: return get_analysis_summary(symbol)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@app.get('/api/indicator-guide')
def indicator_guide(): return get_indicator_guide()

@app.get('/api/business-cycle')
def business_cycle(): return get_business_cycle()

@app.post('/api/portfolio')
def portfolio(req: PortfolioRequest):
    try: return run_portfolio(req)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@app.post('/api/goal')
def goal(req: GoalRequest):
    try: return run_goal(req)
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))
