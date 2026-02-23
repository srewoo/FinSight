const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

async function request(endpoint: string, options?: RequestInit) {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getIndices: () => request('/market/indices'),
  getTopMovers: () => request('/market/top-movers'),
  searchStocks: (q: string) => request(`/stocks/search?q=${encodeURIComponent(q)}`),
  getQuote: (symbol: string) => request(`/stocks/${encodeURIComponent(symbol)}/quote`),
  getHistory: (symbol: string, period = '1mo', interval = '1d') =>
    request(`/stocks/${encodeURIComponent(symbol)}/history?period=${period}&interval=${interval}`),
  getTechnicals: (symbol: string) => request(`/stocks/${encodeURIComponent(symbol)}/technicals`),
  getAIAnalysis: (symbol: string, timeframe = 'short') =>
    request(`/stocks/${encodeURIComponent(symbol)}/ai-analysis`, {
      method: 'POST', body: JSON.stringify({ timeframe }),
    }),
  getAutoRecommendations: () => request('/ai/auto-recommendations'),
  deepScan: () => request('/ai/deep-scan', { method: 'POST' }),
  analyzeChartImage: (image_base64: string, context = '') =>
    request('/ai/analyze-chart-image', {
      method: 'POST', body: JSON.stringify({ image_base64, context }),
    }),
  getWatchlist: () => request('/watchlist'),
  addToWatchlist: (symbol: string, name: string, exchange = 'NSE') =>
    request('/watchlist', { method: 'POST', body: JSON.stringify({ symbol, name, exchange }) }),
  removeFromWatchlist: (symbol: string) =>
    request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
  getPortfolio: () => request('/portfolio'),
  addToPortfolio: (data: { symbol: string; name: string; exchange?: string; quantity: number; buy_price: number; buy_date?: string }) =>
    request('/portfolio', { method: 'POST', body: JSON.stringify(data) }),
  removeFromPortfolio: (id: string) =>
    request(`/portfolio/${id}`, { method: 'DELETE' }),

  // LLM Settings
  getSettings: () => request('/settings'),
  saveSettings: (data: { provider: string; model: string; api_key: string }) =>
    request('/settings', { method: 'POST', body: JSON.stringify(data) }),
  testConnection: () => request('/settings/test', { method: 'POST' }),
};
