import { useEffect, useState } from 'react';
import { wsManager } from '../websocket';

export type MarketStatus = 'open' | 'closed' | 'pre-market' | 'weekend' | 'unknown';

/**
 * Returns the current NSE market status received via WebSocket.
 */
export function useMarketStatus(): MarketStatus {
    const [status, setStatus] = useState<MarketStatus>('unknown');

    useEffect(() => {
        wsManager.connect();
        const prev = wsManager.onMarketStatus;
        wsManager.onMarketStatus = (s) => {
            if (prev) prev(s);
            setStatus(s as MarketStatus);
        };
    }, []);

    return status;
}
