import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../theme';

interface SectorStock {
    symbol: string;
    name: string;
    change_pct: number;
    price: number;
}

interface Sector {
    sector: string;
    avg_change_percent: number;
    stocks_count: number;
    top_performer: SectorStock | null;
    bottom_performer: SectorStock | null;
}

interface MarketBreadth {
    positive_sectors: number;
    negative_sectors: number;
}

interface Props {
    sectors: Sector[];
    market_breadth?: MarketBreadth;
}

const SectorHeatmap: React.FC<Props> = ({ sectors, market_breadth }) => {
    const [expanded, setExpanded] = useState<string | null>(null);

    if (!sectors || sectors.length === 0) return null;

    const maxAbs = Math.max(...sectors.map(s => Math.abs(s.avg_change_percent)), 1);

    return (
        <View>
            {/* Breadth summary */}
            {market_breadth && (
                <View style={styles.breadth}>
                    <View style={[styles.breadthItem, { borderColor: 'rgba(16,185,129,0.3)' }]}>
                        <Text style={[styles.breadthNum, { color: colors.profit }]}>{market_breadth.positive_sectors}</Text>
                        <Text style={styles.breadthLabel}>Gaining</Text>
                    </View>
                    <View style={[styles.breadthItem, { borderColor: 'rgba(239,68,68,0.3)' }]}>
                        <Text style={[styles.breadthNum, { color: colors.loss }]}>{market_breadth.negative_sectors}</Text>
                        <Text style={styles.breadthLabel}>Declining</Text>
                    </View>
                </View>
            )}

            {/* 2-column grid */}
            <View style={styles.grid}>
                {sectors.map((sector) => {
                    const isPos = sector.avg_change_percent >= 0;
                    const opacity = Math.min(0.08 + (Math.abs(sector.avg_change_percent) / maxAbs) * 0.35, 0.45);
                    const bgColor = isPos
                        ? `rgba(16,185,129,${opacity})`
                        : `rgba(239,68,68,${opacity})`;
                    const textColor = isPos ? colors.profit : colors.loss;
                    const isOpen = expanded === sector.sector;

                    return (
                        <TouchableOpacity
                            key={sector.sector}
                            style={[styles.cell, { backgroundColor: bgColor }]}
                            onPress={() => setExpanded(isOpen ? null : sector.sector)}
                            activeOpacity={0.8}
                        >
                            <Text style={styles.sectorName} numberOfLines={1}>{sector.sector}</Text>
                            <Text style={[styles.sectorChange, { color: textColor }]}>
                                {isPos ? '+' : ''}{sector.avg_change_percent}%
                            </Text>
                            <Text style={styles.stockCount}>{sector.stocks_count} stocks</Text>

                            {isOpen && (
                                <View style={styles.expanded}>
                                    {sector.top_performer && (
                                        <View style={styles.perfRow}>
                                            <Text style={styles.perfLabel}>▲ </Text>
                                            <Text style={styles.perfSym}>{sector.top_performer.symbol.replace('.NS', '')}</Text>
                                            <Text style={[styles.perfPct, { color: colors.profit }]}>+{sector.top_performer.change_pct}%</Text>
                                        </View>
                                    )}
                                    {sector.bottom_performer && (
                                        <View style={styles.perfRow}>
                                            <Text style={styles.perfLabel}>▼ </Text>
                                            <Text style={styles.perfSym}>{sector.bottom_performer.symbol.replace('.NS', '')}</Text>
                                            <Text style={[styles.perfPct, { color: colors.loss }]}>{sector.bottom_performer.change_pct}%</Text>
                                        </View>
                                    )}
                                </View>
                            )}
                        </TouchableOpacity>
                    );
                })}
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    breadth: { flexDirection: 'row', gap: 10, marginBottom: 12 },
    breadthItem: { flex: 1, borderRadius: 12, borderWidth: 1, padding: 10, alignItems: 'center' },
    breadthNum: { fontSize: 22, fontWeight: '800' },
    breadthLabel: { color: colors.textMuted, fontSize: 11, marginTop: 2 },
    grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    cell: {
        width: '48%',
        minHeight: 90,
        borderRadius: 14,
        padding: 12,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.04)',
    },
    sectorName: { color: colors.text, fontSize: 12, fontWeight: '700', marginBottom: 4 },
    sectorChange: { fontSize: 20, fontWeight: '800', fontVariant: ['tabular-nums'] },
    stockCount: { color: colors.textMuted, fontSize: 10, marginTop: 2 },
    expanded: { marginTop: 8, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.1)', paddingTop: 6 },
    perfRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
    perfLabel: { color: colors.textMuted, fontSize: 10 },
    perfSym: { color: colors.text, fontSize: 11, fontWeight: '600', flex: 1 },
    perfPct: { fontSize: 11, fontWeight: '700', fontVariant: ['tabular-nums'] },
});

export default SectorHeatmap;
