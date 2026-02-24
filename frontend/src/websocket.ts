/**
 * frontend/src/websocket.ts
 * WebSocketManager singleton — connects to /ws/prices, auto-reconnects,
 * heartbeat ping every 30s, and exposes subscribe/unsubscribe.
 */

import { WS_BASE } from './api';

type PriceUpdateCallback = (symbol: string, data: { price: number; change: number; volume: number }) => void;
type MarketStatusCallback = (status: string) => void;

class WebSocketManager {
    private ws: WebSocket | null = null;
    private reconnectDelay = 1000;
    private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
    private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    private subscribedSymbols: Set<string> = new Set();
    private connected = false;

    public onPriceUpdate: PriceUpdateCallback | null = null;
    public onMarketStatus: MarketStatusCallback | null = null;

    async connect() {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }
        const url = `${WS_BASE}/ws/prices`;
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            this.connected = true;
            this.reconnectDelay = 1000;
            // Re-subscribe on reconnect
            if (this.subscribedSymbols.size > 0) {
                this._send({ action: 'subscribe', symbols: Array.from(this.subscribedSymbols) });
            }
            // Heartbeat
            this.heartbeatInterval = setInterval(() => {
                this._send({ action: 'ping' });
            }, 30000);
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'price_update' && this.onPriceUpdate) {
                    this.onPriceUpdate(msg.symbol, msg.data);
                } else if (msg.type === 'market_status' && this.onMarketStatus) {
                    this.onMarketStatus(msg.data?.status ?? 'unknown');
                }
            } catch { /* ignore malformed */ }
        };

        this.ws.onerror = () => { /* reconnect handled by onclose */ };

        this.ws.onclose = () => {
            this.connected = false;
            if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
            // Exponential backoff: 1s → 2s → 4s → max 30s
            this.reconnectTimeout = setTimeout(() => {
                this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
                this.connect();
            }, this.reconnectDelay);
        };
    }

    disconnect() {
        if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
        if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
        this.ws?.close();
        this.ws = null;
        this.connected = false;
    }

    subscribe(symbols: string[]) {
        symbols.forEach(s => this.subscribedSymbols.add(s));
        if (this.connected) {
            this._send({ action: 'subscribe', symbols });
        }
    }

    unsubscribe(symbols: string[]) {
        symbols.forEach(s => this.subscribedSymbols.delete(s));
        if (this.connected) {
            this._send({ action: 'unsubscribe', symbols });
        }
    }

    private _send(msg: object) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
        }
    }

    isConnected() {
        return this.connected;
    }
}

export const wsManager = new WebSocketManager();
