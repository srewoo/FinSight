// Firebase auth removed — no token injection

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;
const WS_BASE = (BACKEND_URL || '').replace(/^http/, 'ws');

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 800;

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

export const setToken = async (value: string) => {
  if (Platform.OS === 'web') {
    localStorage.setItem('userToken', value);
  } else {
    await SecureStore.setItemAsync('userToken', value);
  }
};

export const getToken = async () => {
  if (Platform.OS === 'web') {
    return localStorage.getItem('userToken');
  } else {
    return await SecureStore.getItemAsync('userToken');
  }
};

export const removeToken = async () => {
  if (Platform.OS === 'web') {
    localStorage.removeItem('userToken');
  } else {
    await SecureStore.deleteItemAsync('userToken');
  }
};

async function request(endpoint: string, options?: RequestInit, retries = MAX_RETRIES): Promise<any> {
  const url = `${API_BASE}${endpoint}`;

  // Try to attach token automatically
  let token = null;
  try {
    token = await getToken();
  } catch (e) {
    // Ignore secure store errors
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options?.headers as Record<string, string> || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers });

    if (!res.ok) {
      const text = await res.text();
      let message = text;
      try {
        const json = JSON.parse(text);
        message = json?.detail || json?.message || text;
      } catch { /* not JSON — use raw text */ }
      const errMsg = message || `Request failed: ${res.status}`;
      // Don't retry client or known business errors (4xx, 503 quota/config)
      if (res.status >= 400 && res.status < 500) throw new Error(errMsg);
      if (res.status === 503) throw new Error(errMsg);
      throw new Error(errMsg);
    }
    return res.json();
  } catch (err: any) {
    const isNetworkError = err?.message === 'Network request failed' || err?.name === 'TypeError';
    const isServerError = err?.message?.includes('Server error');
    if (retries > 0 && (isNetworkError || isServerError)) {
      await sleep(RETRY_DELAY_MS * (MAX_RETRIES - retries + 1));
      return request(endpoint, options, retries - 1);
    }
    throw err;
  }
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
  getEarnings: (symbol: string) => request(`/stocks/${encodeURIComponent(symbol)}/earnings`),
  getFundamentals: (symbol: string) => request(`/stocks/${encodeURIComponent(symbol)}/fundamentals`),
  getStockNews: (symbol: string, limit = 10) =>
    request(`/stocks/${encodeURIComponent(symbol)}/news?limit=${limit}`),
  getMorningBrief: () => request('/market/morning-brief'),

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

  // ── Alerts ─────────────────────────────────────────────────────────────────
  getAlerts: (active_only = true) => request(`/alerts?active_only=${active_only}`),
  createAlert: (data: { symbol: string, target_price: number, condition: string, note?: string }) => request('/alerts', { method: 'POST', body: JSON.stringify(data) }),
  deleteAlert: (id: string) => request(`/alerts/${id}`, { method: 'DELETE' }),
  getTriggeredAlerts: () => request('/alerts/triggered'),
  markAlertRead: (id: string) => request(`/alerts/${id}/read`, { method: 'POST' }),

  // ── News & Sentiment ──────────────────────────────────────────────────────
  getMarketNews: (limit = 20) => request(`/news/market?limit=${limit}`),
  getStockNews: (symbol: string, limit = 10) =>
    request(`/news/${encodeURIComponent(symbol)}?limit=${limit}`),
  getSentimentSummary: () => request('/sentiment/summary'),

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
  saveSettings: (data: { preferred_provider: string; preferred_model?: string }) =>
    request('/settings', { method: 'POST', body: JSON.stringify(data) }),
  getApiKeys: () => request('/settings/api-keys'),
  saveApiKeys: (data: { openai_key?: string; gemini_key?: string; claude_key?: string }) =>
    request('/settings/api-keys', { method: 'POST', body: JSON.stringify(data) }),

  // ── Extended API Keys (FMP, Zerodha, Groww, Firebase) ───────────────────
  getExtendedApiKeys: () => request('/settings/extended-api-keys'),
  saveExtendedApiKeys: (data: {
    fmp_key?: string;
    zerodha_api_key?: string;
    zerodha_access_token?: string;
    groww_api_key?: string;
    firebase_device_token?: string;
    device_platform?: string;
  }) => request('/settings/extended-api-keys', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  validateApiKey: (service: string, apiKey: string) =>
    request(`/settings/validate-api-key?service=${service}`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey })
    }),

  // ── User / Auth ───────────────────────────────────────────────────────────
  login: (data: URLSearchParams) => request('/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: data.toString()
  }),
  getUserProfile: () => request('/user/profile'),
  acceptDisclaimer: (version: string) =>
    request('/user/accept-disclaimer', { method: 'POST', body: JSON.stringify({ version }) }),
  getQuota: () => request('/user/quota'),
};

export { WS_BASE };
