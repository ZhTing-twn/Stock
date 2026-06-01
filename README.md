# Stock Investment Analyzer

Stock Investment Analyzer 是一個前後端分離的股票投資計算與回測系統，提供公開市場資料查詢、定期定額試算、目標金額反推、投資組合回測、技術指標、景氣信號燈與費用設定。系統僅用於投資試算、歷史回測、資料整理與風險呈現，不提供個別操作建議或結果承諾。

## 技術架構

- Frontend：React + Vite + TypeScript
- Styling：Tailwind CSS
- Charts：Recharts
- Backend：Python FastAPI
- Market data：yfinance
- Data processing：pandas、numpy
- Local cache：SQLite

## 專案結構

```text
frontend/               React 前端
backend/                FastAPI 後端
backend/app/services/   股價、快取、計算、指標、景氣信號燈服務
backend/app/models/     API request schema
backend/tests/          後端測試
```

## 安裝與啟動

### 後端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文件：<http://localhost:8000/docs>

### 前端

```bash
cd frontend
npm install
npm run dev
```

開啟：<http://localhost:5173>

若後端不是在 `localhost:8000`，可設定 `VITE_API_BASE` 指向 API base URL。


## GitHub Pages 部署與線上版限制

本專案已設定 GitHub Pages 前端部署，push 到 `main` 分支後會自動建置 `frontend`，並將 `frontend/dist` 部署到：

<https://zhting-twn.github.io/Stock/>

GitHub Pages 只能展示前端靜態頁面，不能執行 FastAPI 後端。因此若只部署 GitHub Pages，股價查詢、基本面分析、回測、定期定額，以及其他需要呼叫 `/api` 的功能不會在線上正常運作。

若要讓股價查詢、基本面分析、回測、定期定額 API 在線上正常運作，需要另外部署 `backend`。後端可部署到 Render、Railway、Fly.io 或其他支援 Python FastAPI 的平台。部署後請在 `frontend` build 時設定 `VITE_API_BASE` 為後端 API 網址，例如：

```bash
cd frontend
VITE_API_BASE=https://your-backend.example.com npm run build
```

## 主要功能

1. **首頁儀表板**：系統簡介、常用股票、近期查詢紀錄、投資試算摘要、回測摘要與風險提醒。
2. **股票查詢頁**：查詢目前股價、漲跌、漲跌幅、成交量、近一年高低點、歷史走勢與資料更新時間。
3. **定期定額計算頁**：支援每月固定日買入、初始投入、手續費、最低手續費、交易稅、平台費、匯率、整股、零股、美股小數股與股息再投入。
4. **目標金額反推頁**：可反推達成目標所需時間，或反推每月需投入金額。
5. **回測頁**：支援單筆投入、定期定額、多標的權重、股息再投入欄位、再平衡頻率欄位、Sharpe、MDD、月報酬、年度報酬、買入紀錄、資產曲線與回撤曲線。
6. **技術指標頁**：SMA、EMA、MACD、RSI、KDJ、KD、Bollinger Bands、ATR、OBV、Volume MA、Momentum、ROC、CCI、Williams %R、MFI、成交量變化、均線排列、黃金交叉、死亡交叉。
7. **基本面分析頁**：查詢公司名稱、產業、市場、市值、PE、PB、PS、EPS、ROE、ROA、利潤率、成長率、負債、現金流、股利、殖利率、Beta 與一年高低點，並提供每個欄位的白話說明與新手判讀。
8. **股票總覽分析頁**：整合股價摘要、基本面摘要、技術面摘要、風險摘要、回測摘要、定期定額試算入口與新手總評。
9. **技術指標新手模式**：技術指標頁可切換新手模式，顯示各指標 30 到 80 字的繁體中文白話說明。
10. **景氣信號燈頁**：以服務層提供本地範例資料，包含總分、燈號、景氣狀態、歷史趨勢與分布。
11. **投資組合頁**：投資組合報酬、年化報酬、年化波動率、最大回撤、Sharpe、相關係數矩陣、權重圓餅圖、個股貢獻與常見 ETF 比較。
12. **匯率與費用頁**：輸入台幣美元匯率、券商費率、最低手續費、交易稅、平台費與交易單位模式。

## API 一覽

- `GET /api/quote?symbol=AAPL`
- `GET /api/history?symbol=AAPL&start=2024-01-01&end=2026-06-01`
- `POST /api/dca`
- `POST /api/backtest`
- `GET /api/indicators?symbol=AAPL&start=2024-01-01&end=2026-06-01`
- `GET /api/fundamentals?symbol=AAPL`
- `GET /api/analysis-summary?symbol=AAPL`
- `GET /api/indicator-guide`
- `GET /api/business-cycle`
- `POST /api/portfolio`
- `POST /api/goal`

## 計算公式

- 總報酬率：`R = (V - C) / C`
- 年化報酬率：`CAGR = (V / C) ^ (1 / Y) - 1`
- 最大回撤：`MDD = (current value - historical peak) / historical peak`
- Sharpe Ratio：`Sharpe = (portfolio return - risk free rate) / portfolio volatility`
- KDJ：
  - `RSV = (Close - n day low) / (n day high - n day low) * 100`
  - `K = 2/3 * previous K + 1/3 * RSV`
  - `D = 2/3 * previous D + 1/3 * K`
  - `J = 3 * K - 2 * D`

## 資料取得管道與快取

股價與基本面資料優先透過 `yfinance` 取得，成功後寫入 `backend/stock_cache.sqlite3` 作為本地 SQLite 快取。若快取已有足夠資料，API 會先使用快取以降低外部請求。

## Fallback 行為

若 yfinance 或外部網路暫時無法取得股價資料，後端會回傳清楚的 `warning`，並使用本地合成範例資料維持頁面、圖表與試算功能可展示。若基本面欄位在 yfinance 中不存在，該欄位會顯示「資料暫缺」，並附上來源或限制說明。範例資料不代表真實市場價格，僅供系統展示與測試。

## 資料限制與風險提醒

- yfinance 屬公開資料管道，可能受網路、頻率限制、資料延遲、交易所調整或欄位缺漏影響。
- 景氣信號燈目前採本地範例資料，服務層已獨立封裝，後續可替換為正式公開資料來源。
- 回測與技術指標以歷史資料計算，不代表未來表現。
- 本系統不處理密碼、Token、API Key、券商帳號或個人機敏資料。
- 本系統不提供投資建議，所有輸出僅供試算、學習與風險理解。

## 測試

```bash
cd backend
pytest
```

```bash
cd frontend
npm run build
```
