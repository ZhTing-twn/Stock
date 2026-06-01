export const API_BASE = import.meta.env.VITE_API_BASE ?? '';
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!res.ok) { const body = await res.json().catch(() => ({})); throw new Error(body.detail || `HTTP ${res.status}`); }
  return res.json();
}
export const api = {
  quote: (symbol: string) => request<any>(`/api/quote?symbol=${encodeURIComponent(symbol)}`),
  history: (symbol: string, start: string, end: string) => request<any>(`/api/history?symbol=${encodeURIComponent(symbol)}&start=${start}&end=${end}`),
  dca: (body: any) => request<any>('/api/dca', { method: 'POST', body: JSON.stringify(body) }),
  backtest: (body: any) => request<any>('/api/backtest', { method: 'POST', body: JSON.stringify(body) }),
  indicators: (symbol: string, start: string, end: string) => request<any>(`/api/indicators?symbol=${encodeURIComponent(symbol)}&start=${start}&end=${end}`),
  fundamentals: (symbol: string) => request<any>(`/api/fundamentals?symbol=${encodeURIComponent(symbol)}`),
  analysisSummary: (symbol: string) => request<any>(`/api/analysis-summary?symbol=${encodeURIComponent(symbol)}`),
  indicatorGuide: () => request<any>('/api/indicator-guide'),
  businessCycle: () => request<any>('/api/business-cycle'),
  portfolio: (body: any) => request<any>('/api/portfolio', { method: 'POST', body: JSON.stringify(body) }),
  goal: (body: any) => request<any>('/api/goal', { method: 'POST', body: JSON.stringify(body) }),
};
