import { useEffect, useRef, useState } from 'react';
import { wsManager } from '../websocket';

export interface RealtimePriceData {
    price: number | null;
    change: number | null;
    volume: number | null;
    connected: boolean;
}

/**
 * Subscribe to live price updates for a symbol via WebSocket.
 * Auto-subscribes on mount, auto-unsubscribes on unmount.
 */
export function useRealtimePrice(symbol: string): RealtimePriceData {
    const [data, setData] = useState<RealtimePriceData>({
        price: null, change: null, volume: null, connected: false,
    });
    const symbolRef = useRef(symbol);

    useEffect(() => {
        symbolRef.current = symbol;
        // Connect manager (idempotent)
        wsManager.connect();

        const prev = wsManager.onPriceUpdate;
        wsManager.onPriceUpdate = (sym, update) => {
            if (prev) prev(sym, update);
            if (sym === symbolRef.current) {
                setData({ ...update, connected: true });
            }
        };

        wsManager.subscribe([symbol]);

        return () => {
            wsManager.unsubscribe([symbol]);
        };
    }, [symbol]);

    useEffect(() => {
        setData(d => ({ ...d, connected: wsManager.isConnected() }));
    }, []);

    return data;
}
