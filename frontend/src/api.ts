// Firebase auth removed — no token injection

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;
const WS_BASE = (BACKEND_URL || '').replace(/^http/, 'ws');

async function request(endpoint: string, options?: RequestInit) {
  const url = `${API_BASE}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
  };


  const res = await fetch(url, {
    ...options,
    headers,
  });



  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // ── Market ──────────────────────────────────────────────────────────────
  getIndices: () => request('/market/indices'),
  getTopMovers: () => request('/market/top-movers'),
  getMarketNews: (limit = 20) => request(`/market/news?limit=${limit}`),
  getBreakouts: () => request('/market/breakouts'),
  getSectorHeatmap: () => request('/market/sector-heatmap'),

  // ── Stock ────────────────────────────────────────────────────────────────
  searchStocks: (q: string) => request(`/stocks/search?q=${encodeURIComponent(q)}`),
  getQuote: (symbol: string) => request(`/stocks/${encodeURIComponent(symbol)}/quote`),
  getHistory: (symbol: string, period = '1mo', interval = '1d') =>
    request(`/stocks/${encodeURIComponent(symbol)}/history?period=${period}&interval=${interval}`),
  getTechnicals: (symbol: string) => request(`/stocks/${encodeURIComponent(symbol)}/technicals`),
  getFundamentals: (symbol: string) => request(`/stocks/${encodeURIComponent(symbol)}/fundamentals`),
  getStockNews: (symbol: string, limit = 10) =>
    request(`/stocks/${encodeURIComponent(symbol)}/news?limit=${limit}`),

  // ── AI ───────────────────────────────────────────────────────────────────
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

  // ── Watchlist ────────────────────────────────────────────────────────────
  getWatchlist: () => request('/watchlist'),
  addToWatchlist: (symbol: string, name: string, exchange = 'NSE') =>
    request('/watchlist', { method: 'POST', body: JSON.stringify({ symbol, name, exchange }) }),
  removeFromWatchlist: (symbol: string) =>
    request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),

  // ── Portfolio ────────────────────────────────────────────────────────────
  getPortfolio: () => request('/portfolio'),
  addToPortfolio: (data: { symbol: string; name: string; exchange?: string; quantity: number; buy_price: number; buy_date?: string }) =>
    request('/portfolio', { method: 'POST', body: JSON.stringify(data) }),
  removeFromPortfolio: (id: string) =>
    request(`/portfolio/${id}`, { method: 'DELETE' }),

  // ── Options / F&O ─────────────────────────────────────────────────────────
  getOptionChain: (symbol: string, expiry?: string) =>
    request(`/options/${encodeURIComponent(symbol)}/chain${expiry ? `?expiry=${encodeURIComponent(expiry)}` : ''}`),
  getOptionGreeks: (symbol: string, strike: number, optionType: string, expiry: string) =>
    request(`/options/${encodeURIComponent(symbol)}/greeks?strike=${strike}&option_type=${optionType}&expiry=${encodeURIComponent(expiry)}`),

  // ── Broker ────────────────────────────────────────────────────────────────
  brokerConnect: (data: { provider?: string; api_key: string; client_id: string; pin: string; totp_secret: string }) =>
    request('/broker/connect', { method: 'POST', body: JSON.stringify(data) }),
  brokerDisconnect: () => request('/broker/disconnect', { method: 'POST' }),
  brokerStatus: () => request('/broker/status'),
  brokerPlaceOrder: (data: { symbol: string; exchange?: string; transaction_type: string; quantity: number; order_type?: string; price?: number; product?: string }) =>
    request('/broker/order', { method: 'POST', body: JSON.stringify(data) }),
  brokerCancelOrder: (order_id: string) =>
    request('/broker/order/cancel', { method: 'POST', body: JSON.stringify({ order_id }) }),
  brokerGetOrders: () => request('/broker/orders'),
  brokerGetPositions: () => request('/broker/positions'),
  brokerGetHoldings: () => request('/broker/holdings'),
  brokerGetFunds: () => request('/broker/funds'),
  brokerSearchSymbol: (exchange: string, q: string) =>
    request(`/broker/search-symbol?exchange=${exchange}&q=${encodeURIComponent(q)}`),

  // ── LLM Settings ─────────────────────────────────────────────────────────
  getSettings: () => request('/settings'),
  saveSettings: (data: { preferred_provider: string }) =>
    request('/settings', { method: 'POST', body: JSON.stringify(data) }),

  // ── User / Auth ───────────────────────────────────────────────────────────
  getUserProfile: () => request('/user/profile'),
  acceptDisclaimer: (version: string) =>
    request('/user/accept-disclaimer', { method: 'POST', body: JSON.stringify({ version }) }),
  getQuota: () => request('/user/quota'),
};

export { WS_BASE };
