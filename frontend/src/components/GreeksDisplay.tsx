import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme';

interface Greeks {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    price: number;
}

interface Props {
    greeks: Greeks;
    symbol: string;
    strike: number;
    optionType: string;
    expiry: string;
    underlying_price: number;
    implied_volatility: number;
    time_to_expiry_days: number;
}

const GreeksDisplay: React.FC<Props> = ({
    greeks, strike, optionType, expiry, underlying_price, implied_volatility, time_to_expiry_days,
}) => {
    const greekRows = [
        {
            name: 'Delta (Δ)',
            value: greeks.delta,
            description: 'Price change per ₹1 move in underlying',
            color: greeks.delta > 0 ? colors.profit : colors.loss,
        },
        {
            name: 'Gamma (Γ)',
            value: greeks.gamma,
            description: 'Rate of change of Delta',
            color: colors.info,
        },
        {
            name: 'Theta (Θ)',
            value: greeks.theta,
            description: 'Daily time decay (₹/day)',
            color: greeks.theta < 0 ? colors.loss : colors.profit,
        },
        {
            name: 'Vega (ν)',
            value: greeks.vega,
            description: 'Price change per 1% IV move',
            color: colors.accent,
        },
    ];

    return (
        <View style={styles.container}>
            {/* Header info */}
            <View style={styles.infoRow}>
                <View style={styles.infoItem}>
                    <Text style={styles.infoLabel}>Underlying</Text>
                    <Text style={styles.infoVal}>₹{underlying_price.toFixed(2)}</Text>
                </View>
                <View style={styles.infoItem}>
                    <Text style={styles.infoLabel}>Implied Vol</Text>
                    <Text style={styles.infoVal}>{implied_volatility.toFixed(1)}%</Text>
                </View>
                <View style={styles.infoItem}>
                    <Text style={styles.infoLabel}>DTE</Text>
                    <Text style={styles.infoVal}>{time_to_expiry_days}d</Text>
                </View>
                <View style={styles.infoItem}>
                    <Text style={styles.infoLabel}>B-S Price</Text>
                    <Text style={[styles.infoVal, { color: colors.accent }]}>₹{greeks.price}</Text>
                </View>
            </View>

            {/* Greeks */}
            {greekRows.map(({ name, value, description, color }) => (
                <View key={name} style={styles.greekRow}>
                    <View style={styles.greekLeft}>
                        <Text style={styles.greekName}>{name}</Text>
                        <Text style={styles.greekDesc}>{description}</Text>
                    </View>
                    <Text style={[styles.greekVal, { color }]}>{value.toFixed(4)}</Text>
                </View>
            ))}

            <Text style={styles.note}>
                * Black-Scholes model. Assumes continuous dividends and constant volatility.
            </Text>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {},
    infoRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
    infoItem: { alignItems: 'center' },
    infoLabel: { color: colors.textMuted, fontSize: 10 },
    infoVal: { color: colors.text, fontSize: 13, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 2 },
    greekRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.3)' },
    greekLeft: {},
    greekName: { color: colors.text, fontSize: 14, fontWeight: '700' },
    greekDesc: { color: colors.textMuted, fontSize: 11, marginTop: 2 },
    greekVal: { fontSize: 16, fontWeight: '800', fontVariant: ['tabular-nums'] },
    note: { color: colors.textMuted, fontSize: 10, marginTop: 12, lineHeight: 16 },
});

export default GreeksDisplay;
