from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class FeeSettings(BaseModel):
    commission_rate: float = 0.001425
    min_fee: float = 20
    tax_rate: float = 0.003
    platform_fee: float = 0
    exchange_rate: float = 1
    share_mode: Literal['whole','odd','fractional'] = 'fractional'

class DCARequest(BaseModel):
    symbol: str
    monthly_amount: float = Field(gt=0)
    initial_amount: float = Field(ge=0, default=0)
    start: str
    end: str
    buy_day: int = Field(ge=1, le=28, default=1)
    reinvest_dividends: bool = False
    fees: FeeSettings = FeeSettings()

class BacktestAsset(BaseModel):
    symbol: str
    weight: float

class BacktestRequest(BaseModel):
    assets: List[BacktestAsset]
    start: str
    end: str
    method: Literal['lump_sum','dca'] = 'dca'
    initial_amount: float = 100000
    monthly_amount: float = 10000
    rebalance_frequency: Literal['none','monthly','quarterly','yearly'] = 'none'
    risk_free_rate: float = 0.02
    reinvest_dividends: bool = False

class PortfolioRequest(BaseModel):
    assets: List[BacktestAsset]
    start: str
    end: str
    risk_free_rate: float = 0.02

class GoalRequest(BaseModel):
    mode: Literal['time','monthly']
    target_amount: float = Field(gt=0)
    initial_amount: float = Field(ge=0)
    monthly_amount: Optional[float] = None
    years: Optional[float] = None
    annual_return: float = 0.05
