import { useEffect, useState } from 'react';
import { Layout } from './components/Layout';
import { AnalysisSummaryPage, BacktestPage, CyclePage, Dashboard, DCAPage, FeesPage, FundamentalsPage, GoalPage, IndicatorsPage, PortfolioPage, QuotePage } from './pages/Pages';
const pages:any={dashboard:<Dashboard/>,quote:<QuotePage/>,overview:<AnalysisSummaryPage/>,fundamentals:<FundamentalsPage/>,dca:<DCAPage/>,goal:<GoalPage/>,backtest:<BacktestPage/>,indicators:<IndicatorsPage/>,cycle:<CyclePage/>,portfolio:<PortfolioPage/>,fees:<FeesPage/>};
function pageFromHash(){const id=window.location.hash.replace('#/','')||'dashboard'; return pages[id]?id:'dashboard'}
export default function App(){const [page,setPage]=useState(pageFromHash()); useEffect(()=>{const onHash=()=>setPage(pageFromHash()); window.addEventListener('hashchange',onHash); if(!window.location.hash)window.location.hash='/dashboard'; return()=>window.removeEventListener('hashchange',onHash)},[]); const navigate=(id:string)=>{setPage(id); window.location.hash=`/${id}`}; return <Layout page={page} setPage={navigate}>{pages[page] || <Dashboard/>}</Layout>}
