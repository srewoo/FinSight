import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { colors, formatCurrency } from '../theme';
import { api } from '../api';

interface OptionRow {
    strike_price: number;
    option_type: string;
    expiry_date: string;
    open_interest: number;
    change_in_oi: number;
    volume: number;
    implied_volatility: number;
    ltp: number;
    bid: number;
    ask: number;
}

interface OIAnalysis {
    total_call_oi: number;
    total_put_oi: number;
    pcr: number;
    pcr_signal: string;
}

interface Props {
    symbol: string;
    chain: OptionRow[];
    underlying_price: number;
    max_pain: number | null;
    oi_analysis: OIAnalysis | null;
    expiry_dates: string[];
    selected_expiry: string | null;
    onSelectExpiry: (expiry: string) => void;
    loading: boolean;
}

const OptionChainTable: React.FC<Props> = ({
    symbol, chain, underlying_price, max_pain, oi_analysis,
    expiry_dates, selected_expiry, onSelectExpiry, loading,
}) => {
    const [selectedStrike, setSelectedStrike] = useState<number | null>(null);

    if (loading) {
        return (
            <View style={styles.center}>
                <ActivityIndicator color={colors.primary} />
                <Text style={styles.loadingText}>Loading option chain...</Text>
            </View>
        );
    }

    // Group by strike
    const strikes = Array.from(new Set(chain.map(r => r.strike_price))).sort((a, b) => a - b);

    // Find ATM
    const atm = strikes.reduce((prev, cur) =>
        Math.abs(cur - underlying_price) < Math.abs(prev - underlying_price) ? cur : prev,
        strikes[0] ?? 0
    );

    const calls: Record<number, OptionRow> = {};
    const puts: Record<number, OptionRow> = {};
    chain.forEach(r => {
        if (r.option_type === 'CE') calls[r.strike_price] = r;
        else puts[r.strike_price] = r;
    });

    return (
        <View>
            {/* OI Analysis */}
            {oi_analysis && (
                <View style={styles.oiCard}>
                    <View style={styles.oiRow}>
                        <View style={styles.oiStat}>
                            <Text style={styles.oiLabel}>Call OI</Text>
                            <Text style={[styles.oiVal, { color: colors.loss }]}>
                                {(oi_analysis.total_call_oi / 1e5).toFixed(1)}L
                            </Text>
                        </View>
                        <View style={styles.oiStat}>
                            <Text style={styles.oiLabel}>Put OI</Text>
                            <Text style={[styles.oiVal, { color: colors.profit }]}>
                                {(oi_analysis.total_put_oi / 1e5).toFixed(1)}L
                            </Text>
                        </View>
                        <View style={styles.oiStat}>
                            <Text style={styles.oiLabel}>PCR</Text>
                            <Text style={styles.oiVal}>{oi_analysis.pcr}</Text>
                        </View>
                        {max_pain && (
                            <View style={styles.oiStat}>
                                <Text style={styles.oiLabel}>Max Pain</Text>
                                <Text style={styles.oiVal}>{formatCurrency(max_pain)}</Text>
                            </View>
                        )}
                    </View>
                    <View style={styles.pcrSignal}>
                        <Text style={styles.pcrText}>{oi_analysis.pcr_signal}</Text>
                    </View>
                </View>
            )}

            {/* Expiry tabs */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.expiryRow}>
                {expiry_dates.slice(0, 6).map(exp => (
                    <TouchableOpacity
                        key={exp}
                        style={[styles.expiryTab, selected_expiry === exp && styles.expiryTabActive]}
                        onPress={() => onSelectExpiry(exp)}
                    >
                        <Text style={[styles.expiryText, selected_expiry === exp && styles.expiryTextActive]}>
                            {exp}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            {/* Chain table header */}
            <View style={styles.tableHeader}>
                <Text style={[styles.headerCell, { flex: 1.5 }]}>Call OI</Text>
                <Text style={[styles.headerCell, { flex: 1 }]}>LTP</Text>
                <Text style={[styles.headerCell, { flex: 1.2, color: colors.text }]}>Strike</Text>
                <Text style={[styles.headerCell, { flex: 1 }]}>LTP</Text>
                <Text style={[styles.headerCell, { flex: 1.5 }]}>Put OI</Text>
            </View>

            {/* Strike rows */}
            {strikes.map(strike => {
                const call = calls[strike];
                const put = puts[strike];
                const isATM = Math.abs(strike - atm) < 0.01;

                return (
                    <TouchableOpacity
                        key={strike}
                        style={[styles.strikeRow, isATM && styles.atmRow,
                        selectedStrike === strike && styles.selectedRow]}
                        onPress={() => setSelectedStrike(selectedStrike === strike ? null : strike)}
                    >
                        {/* Call side */}
                        <View style={{ flex: 1.5 }}>
                            <Text style={styles.oiCell}>{call ? `${(call.open_interest / 1e5).toFixed(1)}L` : '—'}</Text>
                            {call && call.change_in_oi !== 0 && (
                                <Text style={[styles.oiChange, { color: call.change_in_oi > 0 ? colors.profit : colors.loss }]}>
                                    {call.change_in_oi > 0 ? '+' : ''}{(call.change_in_oi / 1e5).toFixed(1)}L
                                </Text>
                            )}
                        </View>
                        <Text style={[styles.ltpCell, { flex: 1, color: colors.loss }]}>
                            {call ? call.ltp : '—'}
                        </Text>

                        {/* Strike */}
                        <View style={[styles.strikeCell, { flex: 1.2, backgroundColor: isATM ? 'rgba(124,58,237,0.15)' : 'transparent' }]}>
                            <Text style={[styles.strikeText, isATM && { color: colors.primary }]}>
                                {strike}
                            </Text>
                            {isATM && <Text style={styles.atmLabel}>ATM</Text>}
                        </View>

                        {/* Put side */}
                        <Text style={[styles.ltpCell, { flex: 1, color: colors.profit }]}>
                            {put ? put.ltp : '—'}
                        </Text>
                        <View style={{ flex: 1.5, alignItems: 'flex-end' }}>
                            <Text style={styles.oiCell}>{put ? `${(put.open_interest / 1e5).toFixed(1)}L` : '—'}</Text>
                            {put && put.change_in_oi !== 0 && (
                                <Text style={[styles.oiChange, { color: put.change_in_oi > 0 ? colors.profit : colors.loss }]}>
                                    {put.change_in_oi > 0 ? '+' : ''}{(put.change_in_oi / 1e5).toFixed(1)}L
                                </Text>
                            )}
                        </View>
                    </TouchableOpacity>
                );
            })}
        </View>
    );
};

const styles = StyleSheet.create({
    center: { alignItems: 'center', paddingVertical: 30 },
    loadingText: { color: colors.textMuted, marginTop: 10 },
    oiCard: { backgroundColor: 'rgba(39,39,42,0.4)', borderRadius: 14, padding: 14, marginBottom: 10 },
    oiRow: { flexDirection: 'row', justifyContent: 'space-between' },
    oiStat: { alignItems: 'center' },
    oiLabel: { color: colors.textMuted, fontSize: 11 },
    oiVal: { color: colors.text, fontSize: 15, fontWeight: '700', marginTop: 3, fontVariant: ['tabular-nums'] },
    pcrSignal: { marginTop: 10, backgroundColor: 'rgba(124,58,237,0.1)', borderRadius: 8, padding: 6, alignItems: 'center' },
    pcrText: { color: colors.accent, fontSize: 12, fontWeight: '600' },
    expiryRow: { marginBottom: 12 },
    expiryTab: { paddingHorizontal: 12, paddingVertical: 6, marginRight: 8, borderRadius: 20, backgroundColor: 'rgba(39,39,42,0.4)', borderWidth: 1, borderColor: 'transparent' },
    expiryTabActive: { backgroundColor: 'rgba(124,58,237,0.12)', borderColor: 'rgba(124,58,237,0.4)' },
    expiryText: { color: colors.textMuted, fontSize: 12 },
    expiryTextActive: { color: colors.accent, fontWeight: '700' },
    tableHeader: { flexDirection: 'row', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.5)', marginBottom: 4 },
    headerCell: { color: colors.textMuted, fontSize: 10, fontWeight: '600', textAlign: 'center' },
    strikeRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.2)' },
    atmRow: {},
    selectedRow: { backgroundColor: 'rgba(124,58,237,0.05)' },
    oiCell: { color: colors.textSecondary, fontSize: 11, fontVariant: ['tabular-nums'] },
    oiChange: { fontSize: 9, fontVariant: ['tabular-nums'] },
    ltpCell: { textAlign: 'center', fontSize: 12, fontWeight: '600', fontVariant: ['tabular-nums'] },
    strikeCell: { borderRadius: 6, alignItems: 'center', paddingVertical: 4 },
    strikeText: { color: colors.text, fontSize: 12, fontWeight: '700', fontVariant: ['tabular-nums'] },
    atmLabel: { color: colors.primary, fontSize: 8, fontWeight: '800', marginTop: 2 },
});

export default OptionChainTable;
