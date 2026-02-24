import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Alert } from 'react-native';
import { api } from './api';

interface BrokerStatus {
    connected: boolean;
    client_id?: string;
    provider?: string;
}

interface ConnectParams {
    provider?: string;
    api_key: string;
    client_id: string;
    pin: string;
    totp_secret: string;
}

interface BrokerContextType {
    status: BrokerStatus;
    loading: boolean;
    connect: (params: ConnectParams) => Promise<boolean>;
    disconnect: () => Promise<void>;
    refresh: () => Promise<void>;
}

const BrokerContext = createContext<BrokerContextType | null>(null);

export function BrokerProvider({ children }: { children: ReactNode }) {
    const [status, setStatus] = useState<BrokerStatus>({ connected: false });
    const [loading, setLoading] = useState(false);

    const refresh = async () => {
        try {
            const data = await api.brokerStatus();
            setStatus(data);
        } catch { /* ignore */ }
    };

    useEffect(() => { refresh(); }, []);

    const connect = async (params: ConnectParams): Promise<boolean> => {
        setLoading(true);
        try {
            const data = await api.brokerConnect(params);
            setStatus({ connected: true, client_id: data.client_id, provider: data.provider });
            return true;
        } catch (e: any) {
            Alert.alert('Connection Failed', e?.message || 'Could not connect to broker.');
            return false;
        } finally {
            setLoading(false);
        }
    };

    const disconnect = async () => {
        setLoading(true);
        try {
            await api.brokerDisconnect();
            setStatus({ connected: false });
        } catch { /* ignore */ } finally {
            setLoading(false);
        }
    };

    return (
        <BrokerContext.Provider value={{ status, loading, connect, disconnect, refresh }}>
            {children}
        </BrokerContext.Provider>
    );
}

export function useBroker(): BrokerContextType {
    const ctx = useContext(BrokerContext);
    if (!ctx) throw new Error('useBroker must be used inside <BrokerProvider>');
    return ctx;
}
