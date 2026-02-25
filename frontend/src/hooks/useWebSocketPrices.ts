/**
 * WebSocket hook for real-time stock price updates.
 * Usage: const { subscribe, unsubscribe, connected, prices } = useWebSocketPrices();
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { WS_BASE } from '../api';

export interface PriceUpdate {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
}

export interface WebSocketPriceState {
  connected: boolean;
  prices: Record<string, PriceUpdate>;
  subscribe: (symbols: string[]) => void;
  unsubscribe: (symbols: string[]) => void;
  error: string | null;
}

export function useWebSocketPrices(): WebSocketPriceState {
  const [connected, setConnected] = useState(false);
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const subscribedSymbolsRef = useRef<Set<string>>(new Set());

  const connect = useCallback(() => {
    if (!WS_BASE) {
      setError('Backend URL not configured');
      return;
    }

    try {
      const ws = new WebSocket(`${WS_BASE}/api/ws/prices`);
      
      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setConnected(true);
        setError(null);
        
        // Re-subscribe to previously subscribed symbols
        if (subscribedSymbolsRef.current.size > 0) {
          ws.send(JSON.stringify({
            type: 'subscribe',
            symbols: Array.from(subscribedSymbolsRef.current)
          }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          switch (message.type) {
            case 'initial_prices':
              setPrices(message.data || {});
              break;
              
            case 'price_update':
              setPrices(prev => ({
                ...prev,
                [message.symbol]: message.data
              }));
              break;
              
            case 'subscribed':
              console.log('[WebSocket] Subscribed to:', message.symbols);
              break;
              
            case 'unsubscribed':
              console.log('[WebSocket] Unsubscribed from:', message.symbols);
              break;
              
            case 'pong':
              // Heartbeat response
              break;
              
            default:
              console.log('[WebSocket] Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('[WebSocket] Error:', err);
        setError('Connection error');
      };

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        setConnected(false);
        
        // Attempt reconnection after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WebSocket] Attempting reconnection...');
          connect();
        }, 3000);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WebSocket] Failed to connect:', err);
      setError('Failed to connect');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnected(false);
  }, []);

  const subscribe = useCallback((symbols: string[]) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      // Queue symbols for when connection is established
      symbols.forEach(s => subscribedSymbolsRef.current.add(s));
      if (!connected) {
        connect();
      }
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'subscribe',
      symbols
    }));

    symbols.forEach(s => subscribedSymbolsRef.current.add(s));
  }, [connected, connect]);

  const unsubscribe = useCallback((symbols: string[]) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'unsubscribe',
      symbols
    }));

    symbols.forEach(s => subscribedSymbolsRef.current.delete(s));
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();
    
    // Send heartbeat every 30 seconds to keep connection alive
    const heartbeatInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      disconnect();
      clearInterval(heartbeatInterval);
    };
  }, [connect, disconnect]);

  return {
    connected,
    prices,
    subscribe,
    unsubscribe,
    error
  };
}

export default useWebSocketPrices;
