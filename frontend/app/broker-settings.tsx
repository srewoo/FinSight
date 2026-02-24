import React, { useState, useEffect } from 'react';
import {
    View, Text, TextInput, TouchableOpacity, ScrollView,
    StyleSheet, ActivityIndicator, Alert, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../src/theme';
import { useBroker } from '../src/broker-context';
import { api } from '../src/api';

type Provider = 'angelone';

interface FormState {
    provider: Provider;
    api_key: string;
    client_id: string;
    pin: string;
    totp_secret: string;
}

export default function BrokerSettingsScreen() {
    const router = useRouter();
    const { status, loading, connect, disconnect } = useBroker();

    const [form, setForm] = useState<FormState>({
        provider: 'angelone',
        api_key: '',
        client_id: '',
        pin: '',
        totp_secret: '',
    });
    const [showPin, setShowPin] = useState(false);
    const [showTotp, setShowTotp] = useState(false);
    const [funds, setFunds] = useState<any>(null);
    const [positions, setPositions] = useState<any[]>([]);
    const [holdings, setHoldings] = useState<any[]>([]);
    const [dataLoading, setDataLoading] = useState(false);
    const [activeSection, setActiveSection] = useState<'positions' | 'holdings' | 'funds'>('funds');

    // Load broker data when connected
    useEffect(() => {
        if (status.connected) {
            loadBrokerData();
        }
    }, [status.connected]);

    const loadBrokerData = async () => {
        setDataLoading(true);
        try {
            const [fundsRes, posRes, holdRes] = await Promise.all([
                api.brokerGetFunds(),
                api.brokerGetPositions(),
                api.brokerGetHoldings(),
            ]);
            setFunds(fundsRes);
            setPositions(posRes.positions || []);
            setHoldings(holdRes.holdings || []);
        } catch (e: any) {
            console.warn('Broker data error:', e?.message);
        } finally {
            setDataLoading(false);
        }
    };

    const handleConnect = async () => {
        const { api_key, client_id, pin, totp_secret } = form;
        if (!api_key.trim() || !client_id.trim() || !pin.trim() || !totp_secret.trim()) {
            Alert.alert('Missing Fields', 'Please fill in all fields to connect.');
            return;
        }
        const ok = await connect(form);
        if (ok) {
            Alert.alert('Connected ✓', `Successfully connected as ${form.client_id}`);
        }
    };

    const handleDisconnect = () => {
        Alert.alert(
            'Disconnect Broker',
            'Are you sure you want to disconnect your broker account?',
            [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Disconnect', style: 'destructive', onPress: () => disconnect() },
            ]
        );
    };

    const field = (
        label: string,
        key: keyof FormState,
        opts?: { secure?: boolean; show?: boolean; toggle?: () => void; placeholder?: string; keyboardType?: any }
    ) => (
        <View style={styles.fieldGroup} key={key}>
            <Text style={styles.fieldLabel}>{label}</Text>
            <View style={styles.fieldRow}>
                <TextInput
                    style={[styles.input, { flex: 1 }]}
                    value={String(form[key])}
                    onChangeText={v => setForm(f => ({ ...f, [key]: v }))}
                    placeholder={opts?.placeholder || `Enter ${label.toLowerCase()}`}
                    placeholderTextColor={colors.textMuted}
                    secureTextEntry={opts?.secure && !opts?.show}
                    autoCapitalize="none"
                    autoCorrect={false}
                    keyboardType={opts?.keyboardType || 'default'}
                />
                {opts?.toggle && (
                    <TouchableOpacity onPress={opts.toggle} style={styles.eyeBtn}>
                        <Ionicons name={opts.show ? 'eye-off' : 'eye'} size={18} color={colors.textMuted} />
                    </TouchableOpacity>
                )}
            </View>
        </View>
    );

    return (
        <SafeAreaView style={styles.screen}>
            <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

                {/* Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                        <Ionicons name="arrow-back" size={22} color={colors.text} />
                    </TouchableOpacity>
                    <View style={{ flex: 1 }}>
                        <Text style={styles.title}>Broker Integration</Text>
                        <Text style={styles.subtitle}>Connect your Angel One account</Text>
                    </View>
                </View>

                {/* Connection Status Banner */}
                <View style={[styles.statusBanner, {
                    backgroundColor: status.connected ? 'rgba(16,185,129,0.08)' : 'rgba(113,113,122,0.08)',
                    borderColor: status.connected ? 'rgba(16,185,129,0.3)' : 'rgba(113,113,122,0.2)',
                }]}>
                    <View style={[styles.statusDot, { backgroundColor: status.connected ? colors.profit : colors.neutral }]} />
                    <View style={{ flex: 1 }}>
                        <Text style={[styles.statusTitle, { color: status.connected ? colors.profit : colors.textMuted }]}>
                            {status.connected ? 'Connected' : 'Not Connected'}
                        </Text>
                        {status.connected && (
                            <Text style={styles.statusSub}>
                                {status.provider?.toUpperCase()} · {status.client_id}
                            </Text>
                        )}
                    </View>
                    {status.connected && (
                        <TouchableOpacity onPress={handleDisconnect} style={styles.disconnectBtn}>
                            <Text style={styles.disconnectText}>Disconnect</Text>
                        </TouchableOpacity>
                    )}
                </View>

                {/* Connect Form (show only when not connected) */}
                {!status.connected && (
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Angel One SmartAPI</Text>
                        <Text style={styles.cardSubtitle}>
                            Enter your API credentials. Your PIN is never stored — only the session JWT is kept encrypted.
                        </Text>

                        {field('API Key', 'api_key', { placeholder: 'Your SmartAPI API key' })}
                        {field('Client ID', 'client_id', { placeholder: 'e.g. A123456', keyboardType: 'default' })}
                        {field('MPIN / Login PIN', 'pin', {
                            secure: true, show: showPin, toggle: () => setShowPin(p => !p),
                            keyboardType: 'number-pad', placeholder: '4–6 digit PIN',
                        })}
                        {field('TOTP Secret (Base32)', 'totp_secret', {
                            secure: true, show: showTotp, toggle: () => setShowTotp(p => !p),
                            placeholder: 'Base32 secret from authenticator app',
                        })}

                        <View style={styles.noticeRow}>
                            <Ionicons name="shield-checkmark" size={14} color={colors.profit} />
                            <Text style={styles.noticeText}>
                                Credentials are Fernet-encrypted before storage. Your PIN is never saved.
                            </Text>
                        </View>

                        <TouchableOpacity
                            style={[styles.connectBtn, loading && styles.connectBtnDisabled]}
                            onPress={handleConnect}
                            disabled={loading}
                            activeOpacity={0.8}
                        >
                            {loading ? (
                                <ActivityIndicator color="#FFF" />
                            ) : (
                                <>
                                    <Ionicons name="link" size={18} color="#FFF" />
                                    <Text style={styles.connectBtnText}>Connect Account</Text>
                                </>
                            )}
                        </TouchableOpacity>
                    </View>
                )}

                {/* Connected: Show account data */}
                {status.connected && (
                    <View>
                        {/* Refresh button */}
                        <TouchableOpacity style={styles.refreshBtn} onPress={loadBrokerData} disabled={dataLoading}>
                            {dataLoading ? (
                                <ActivityIndicator color={colors.primary} size="small" />
                            ) : (
                                <>
                                    <Ionicons name="refresh" size={16} color={colors.primary} />
                                    <Text style={styles.refreshText}>Refresh</Text>
                                </>
                            )}
                        </TouchableOpacity>

                        {/* Section tabs */}
                        <View style={styles.sectionTabs}>
                            {(['funds', 'positions', 'holdings'] as const).map(tab => (
                                <TouchableOpacity
                                    key={tab}
                                    style={[styles.sectionTab, activeSection === tab && styles.sectionTabActive]}
                                    onPress={() => setActiveSection(tab)}
                                >
                                    <Text style={[styles.sectionTabText, activeSection === tab && styles.sectionTabTextActive]}>
                                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                                    </Text>
                                </TouchableOpacity>
                            ))}
                        </View>

                        {/* Funds */}
                        {activeSection === 'funds' && funds && (
                            <View style={styles.card}>
                                <Text style={styles.cardTitle}>Available Funds</Text>
                                {[
                                    { label: 'Net Available', value: funds.net, color: colors.profit },
                                    { label: 'Used Margin', value: funds.used_margin, color: colors.warning },
                                    { label: 'Available Cash', value: funds.available_cash },
                                    { label: 'SPAN Margin', value: funds.span_margin },
                                    { label: 'Exposure Margin', value: funds.exposure_margin },
                                    { label: 'Total Collateral', value: funds.total_collateral },
                                ].map(({ label, value, color }) => value != null && (
                                    <View key={label} style={styles.fundRow}>
                                        <Text style={styles.fundLabel}>{label}</Text>
                                        <Text style={[styles.fundValue, color ? { color } : {}]}>
                                            ₹{Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                                        </Text>
                                    </View>
                                ))}
                            </View>
                        )}

                        {/* Positions */}
                        {activeSection === 'positions' && (
                            <View style={styles.card}>
                                <Text style={styles.cardTitle}>Open Positions ({positions.length})</Text>
                                {positions.length === 0 ? (
                                    <Text style={styles.emptyText}>No open positions</Text>
                                ) : (
                                    positions.map((pos, i) => (
                                        <View key={i} style={styles.posRow}>
                                            <View style={{ flex: 1 }}>
                                                <Text style={styles.posSymbol}>{pos.symbol || pos.tradingsymbol}</Text>
                                                <Text style={styles.posMeta}>{pos.product} · Qty: {pos.quantity}</Text>
                                            </View>
                                            <View style={{ alignItems: 'flex-end' }}>
                                                <Text style={styles.posLtp}>₹{pos.ltp}</Text>
                                                <Text style={[styles.posPnl, { color: (pos.unrealised_pnl ?? 0) >= 0 ? colors.profit : colors.loss }]}>
                                                    {(pos.unrealised_pnl ?? 0) >= 0 ? '+' : ''}₹{pos.unrealised_pnl ?? 0}
                                                </Text>
                                            </View>
                                        </View>
                                    ))
                                )}
                            </View>
                        )}

                        {/* Holdings */}
                        {activeSection === 'holdings' && (
                            <View style={styles.card}>
                                <Text style={styles.cardTitle}>Holdings ({holdings.length})</Text>
                                {holdings.length === 0 ? (
                                    <Text style={styles.emptyText}>No holdings</Text>
                                ) : (
                                    holdings.map((h, i) => (
                                        <View key={i} style={styles.posRow}>
                                            <View style={{ flex: 1 }}>
                                                <Text style={styles.posSymbol}>{h.symbol || h.tradingsymbol}</Text>
                                                <Text style={styles.posMeta}>Qty: {h.quantity} · Avg: ₹{h.average_price}</Text>
                                            </View>
                                            <View style={{ alignItems: 'flex-end' }}>
                                                <Text style={styles.posLtp}>₹{h.ltp}</Text>
                                                <Text style={[styles.posPnl, { color: (h.pnl ?? 0) >= 0 ? colors.profit : colors.loss }]}>
                                                    {(h.pnl ?? 0) >= 0 ? '+' : ''}₹{h.pnl ?? 0}
                                                </Text>
                                            </View>
                                        </View>
                                    ))
                                )}
                            </View>
                        )}
                    </View>
                )}

                {/* Info / Disclaimer */}
                <View style={styles.disclaimer}>
                    <Ionicons name="information-circle" size={16} color={colors.textMuted} />
                    <Text style={styles.disclaimerText}>
                        FinSight does not store your broker PIN. All API calls are made over HTTPS.
                        Ensure you trade responsibly. FinSight is not SEBI-registered as a broker.
                    </Text>
                </View>

            </ScrollView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bg },
    scroll: { paddingHorizontal: 20, paddingBottom: 60 },
    header: { flexDirection: 'row', alignItems: 'center', paddingTop: 8, paddingBottom: 24, gap: 12 },
    backBtn: { padding: 8 },
    title: { color: colors.text, fontSize: 22, fontWeight: '800' },
    subtitle: { color: colors.textMuted, fontSize: 13, marginTop: 2 },

    statusBanner: {
        flexDirection: 'row', alignItems: 'center', borderRadius: 16, borderWidth: 1,
        padding: 16, marginBottom: 20, gap: 10,
    },
    statusDot: { width: 10, height: 10, borderRadius: 5 },
    statusTitle: { fontSize: 14, fontWeight: '700' },
    statusSub: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
    disconnectBtn: { backgroundColor: 'rgba(239,68,68,0.1)', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 7, borderWidth: 1, borderColor: 'rgba(239,68,68,0.25)' },
    disconnectText: { color: colors.loss, fontSize: 13, fontWeight: '700' },

    card: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
    cardTitle: { color: colors.text, fontSize: 16, fontWeight: '700', marginBottom: 6 },
    cardSubtitle: { color: colors.textMuted, fontSize: 13, lineHeight: 19, marginBottom: 20 },

    fieldGroup: { marginBottom: 16 },
    fieldLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: '600', marginBottom: 7, textTransform: 'uppercase', letterSpacing: 0.5 },
    fieldRow: { flexDirection: 'row', alignItems: 'center' },
    input: {
        backgroundColor: 'rgba(39,39,42,0.5)', borderRadius: 12, borderWidth: 1,
        borderColor: 'rgba(63,63,70,0.6)', color: colors.text, fontSize: 14,
        paddingHorizontal: 14, paddingVertical: 13,
    },
    eyeBtn: { padding: 12, marginLeft: 4 },

    noticeRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 20, marginTop: 4 },
    noticeText: { color: colors.textMuted, fontSize: 11, lineHeight: 16, flex: 1 },

    connectBtn: {
        flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        backgroundColor: colors.primary, borderRadius: 30, paddingVertical: 15, gap: 10,
    },
    connectBtnDisabled: { opacity: 0.5 },
    connectBtnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

    refreshBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginBottom: 14, padding: 8 },
    refreshText: { color: colors.primary, fontSize: 14, fontWeight: '600' },

    sectionTabs: { flexDirection: 'row', gap: 8, marginBottom: 12 },
    sectionTab: { flex: 1, paddingVertical: 10, borderRadius: 12, backgroundColor: 'rgba(39,39,42,0.4)', alignItems: 'center', borderWidth: 1, borderColor: 'transparent' },
    sectionTabActive: { backgroundColor: 'rgba(124,58,237,0.12)', borderColor: 'rgba(124,58,237,0.4)' },
    sectionTabText: { color: colors.textMuted, fontSize: 13, fontWeight: '600' },
    sectionTabTextActive: { color: colors.accent, fontWeight: '700' },

    fundRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 11, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.3)' },
    fundLabel: { color: colors.textMuted, fontSize: 13 },
    fundValue: { color: colors.text, fontSize: 14, fontWeight: '700', fontVariant: ['tabular-nums'] },

    posRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.2)' },
    posSymbol: { color: colors.text, fontSize: 14, fontWeight: '700' },
    posMeta: { color: colors.textMuted, fontSize: 11, marginTop: 3 },
    posLtp: { color: colors.text, fontSize: 14, fontWeight: '700', fontVariant: ['tabular-nums'] },
    posPnl: { fontSize: 12, fontWeight: '600', fontVariant: ['tabular-nums'], marginTop: 3 },

    emptyText: { color: colors.textMuted, fontSize: 14, textAlign: 'center', paddingVertical: 20 },

    disclaimer: { flexDirection: 'row', gap: 8, backgroundColor: 'rgba(39,39,42,0.3)', borderRadius: 12, padding: 14, marginTop: 8, alignItems: 'flex-start' },
    disclaimerText: { color: colors.textMuted, fontSize: 11, lineHeight: 17, flex: 1 },
});
