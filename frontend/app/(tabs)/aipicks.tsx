import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api';
import { colors, formatCurrency } from '../../src/theme';

interface StockRec {
  symbol: string; name: string; sector: string; price: number; change_percent: number;
  signal: string; confidence: number; rsi: number; adx: number; macd_signal: string;
  support_resistance?: any;
}
interface Summary {
  stocks_analyzed: number; buy_signals: number; sell_signals: number; hold_signals: number; market_sentiment: string;
}

export default function AIPicksScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [buyRecs, setBuyRecs] = useState<StockRec[]>([]);
  const [sellRecs, setSellRecs] = useState<StockRec[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getAutoRecommendations();
      setSummary(data.summary);
      setBuyRecs(data.buy_recommendations || []);
      setSellRecs(data.sell_recommendations || []);
    } catch (e) {
      console.error('AI Picks error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  const onRefresh = () => { setRefreshing(true); fetchData(); };

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Scanning 40+ NSE stocks...</Text>
          <Text style={styles.loadingSubtext}>Analyzing 6-month candle data with technical indicators</Text>
        </View>
      </SafeAreaView>
    );
  }

  const sentimentColor = summary?.market_sentiment === 'Bullish' ? colors.profit : summary?.market_sentiment === 'Bearish' ? colors.loss : colors.warning;

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
      >
        <View style={styles.header}>
          <Text style={styles.title}>AI Stock Picks</Text>
          <View style={styles.aiBadge}>
            <Ionicons name="sparkles" size={13} color={colors.primary} />
            <Text style={styles.aiBadgeText}>Live Scan</Text>
          </View>
        </View>

        {/* Summary Stats */}
        {summary && (
          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Analyzed</Text>
              <Text style={styles.statValue}>{summary.stocks_analyzed}</Text>
              <Ionicons name="bar-chart" size={18} color={colors.info} style={styles.statIcon} />
            </View>
            <View style={[styles.statCard, styles.statCardBuy]}>
              <Text style={styles.statLabel}>Buy Signals</Text>
              <Text style={[styles.statValue, { color: colors.profit }]}>{summary.buy_signals}</Text>
              <Ionicons name="trending-up" size={18} color={colors.profit} style={styles.statIcon} />
            </View>
            <View style={[styles.statCard, styles.statCardSell]}>
              <Text style={styles.statLabel}>Sell Signals</Text>
              <Text style={[styles.statValue, { color: colors.loss }]}>{summary.sell_signals}</Text>
              <Ionicons name="trending-down" size={18} color={colors.loss} style={styles.statIcon} />
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Sentiment</Text>
              <Text style={[styles.statValueSm, { color: sentimentColor }]}>{summary.market_sentiment}</Text>
              <Ionicons name="pulse" size={18} color={sentimentColor} style={styles.statIcon} />
            </View>
          </View>
        )}

        {/* Buy Recommendations */}
        <View style={styles.sectionHeader}>
          <View style={styles.sectionTitleRow}>
            <Ionicons name="trending-up" size={22} color={colors.profit} />
            <Text style={[styles.sectionTitle, { color: colors.profit }]}>Buy Recommendations</Text>
          </View>
          <View style={styles.countBadgeGreen}>
            <Text style={styles.countBadgeText}>{buyRecs.length} stocks</Text>
          </View>
        </View>
        <Text style={styles.sectionSub}>Stocks showing bullish signals</Text>

        {buyRecs.length === 0 ? (
          <View style={styles.emptySection}>
            <Text style={styles.emptyText}>No strong buy signals found</Text>
          </View>
        ) : (
          buyRecs.map((stock) => (
            <TouchableOpacity
              key={stock.symbol}
              style={styles.recCard}
              onPress={() => router.push(`/stock/${encodeURIComponent(stock.symbol)}`)}
              testID={`buy-rec-${stock.symbol}`}
              activeOpacity={0.7}
            >
              <View style={styles.recHeader}>
                <View style={{ flex: 1 }}>
                  <View style={styles.recTitleRow}>
                    <Text style={styles.recSymbol}>{stock.symbol.replace('.NS', '').replace('.BO', '')}</Text>
                    <View style={styles.sectorBadge}>
                      <Text style={styles.sectorText}>{stock.sector}</Text>
                    </View>
                  </View>
                  <Text style={styles.recName} numberOfLines={1}>{stock.name}</Text>
                </View>
                <View style={styles.recPriceCol}>
                  <Text style={styles.recPrice}>{formatCurrency(stock.price)}</Text>
                  <Text style={[styles.recChange, { color: stock.change_percent >= 0 ? colors.profit : colors.loss }]}>
                    {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent}%
                  </Text>
                </View>
              </View>

              {/* Confidence Bar */}
              <View style={styles.confRow}>
                <Text style={styles.confLabel}>Confidence</Text>
                <Text style={[styles.confValue, { color: colors.profit }]}>{stock.confidence}%</Text>
              </View>
              <View style={styles.confBarBg}>
                <View style={[styles.confBarFill, { width: `${Math.min(stock.confidence, 100)}%` }]}>
                  <View style={[styles.confBarBlue, { width: `${Math.min(70, stock.confidence)}%` }]} />
                  <View style={[styles.confBarGreen, { flex: 1 }]} />
                </View>
              </View>

              {/* Support / Resistance */}
              {stock.support_resistance && (
                <View style={styles.srRow}>
                  <View style={styles.srItem}>
                    <Text style={styles.srLabel}>S1</Text>
                    <Text style={styles.srValue}>{formatCurrency(stock.support_resistance?.support?.s1)}</Text>
                  </View>
                  <View style={styles.srItem}>
                    <Text style={styles.srLabel}>R1</Text>
                    <Text style={styles.srValue}>{formatCurrency(stock.support_resistance?.resistance?.r1)}</Text>
                  </View>
                  <View style={styles.srItem}>
                    <Text style={styles.srLabel}>6M High</Text>
                    <Text style={styles.srValue}>{formatCurrency(stock.support_resistance?.period_highs_lows?.high_6m)}</Text>
                  </View>
                  <View style={styles.srItem}>
                    <Text style={styles.srLabel}>6M Low</Text>
                    <Text style={styles.srValue}>{formatCurrency(stock.support_resistance?.period_highs_lows?.low_6m)}</Text>
                  </View>
                </View>
              )}

              <View style={styles.divider} />

              {/* Indicators */}
              <View style={styles.indicatorRow}>
                <Text style={styles.indicatorText}>RSI: {stock.rsi ?? '—'}</Text>
                <Text style={styles.indicatorText}>ADX: {stock.adx ?? '—'}</Text>
                <Text style={styles.indicatorText}>MACD: {stock.macd_signal}</Text>
                <Ionicons name="chevron-forward" size={18} color={colors.primary} />
              </View>
            </TouchableOpacity>
          ))
        )}

        {/* Sell Recommendations */}
        <View style={[styles.sectionHeader, { marginTop: 28 }]}>
          <View style={styles.sectionTitleRow}>
            <Ionicons name="trending-down" size={22} color={colors.loss} />
            <Text style={[styles.sectionTitle, { color: colors.loss }]}>Sell Recommendations</Text>
          </View>
          <View style={styles.countBadgeRed}>
            <Text style={styles.countBadgeText}>{sellRecs.length} stocks</Text>
          </View>
        </View>
        <Text style={styles.sectionSub}>Stocks showing bearish signals</Text>

        {sellRecs.length === 0 ? (
          <View style={styles.emptySection}>
            <Ionicons name="pulse-outline" size={40} color={colors.textMuted} />
            <Text style={styles.emptyText}>No strong sell signals found</Text>
          </View>
        ) : (
          sellRecs.map((stock) => (
            <TouchableOpacity
              key={stock.symbol}
              style={[styles.recCard, styles.recCardSell]}
              onPress={() => router.push(`/stock/${encodeURIComponent(stock.symbol)}`)}
              testID={`sell-rec-${stock.symbol}`}
              activeOpacity={0.7}
            >
              <View style={styles.recHeader}>
                <View style={{ flex: 1 }}>
                  <View style={styles.recTitleRow}>
                    <Text style={styles.recSymbol}>{stock.symbol.replace('.NS', '').replace('.BO', '')}</Text>
                    <View style={styles.sectorBadge}>
                      <Text style={styles.sectorText}>{stock.sector}</Text>
                    </View>
                  </View>
                  <Text style={styles.recName} numberOfLines={1}>{stock.name}</Text>
                </View>
                <View style={styles.recPriceCol}>
                  <Text style={styles.recPrice}>{formatCurrency(stock.price)}</Text>
                  <Text style={[styles.recChange, { color: colors.loss }]}>
                    {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent}%
                  </Text>
                </View>
              </View>

              <View style={styles.confRow}>
                <Text style={styles.confLabel}>Confidence</Text>
                <Text style={[styles.confValue, { color: colors.loss }]}>{stock.confidence}%</Text>
              </View>
              <View style={styles.confBarBg}>
                <View style={[styles.confBarFillRed, { width: `${Math.min(stock.confidence, 100)}%` }]} />
              </View>

              {stock.support_resistance && (
                <View style={styles.srRow}>
                  <View style={styles.srItem}>
                    <Text style={styles.srLabel}>S1</Text>
                    <Text style={styles.srValue}>{formatCurrency(stock.support_resistance?.support?.s1)}</Text>
                  </View>
                  <View style={styles.srItem}>
                    <Text style={styles.srLabel}>R1</Text>
                    <Text style={styles.srValue}>{formatCurrency(stock.support_resistance?.resistance?.r1)}</Text>
                  </View>
                </View>
              )}

              <View style={styles.divider} />
              <View style={styles.indicatorRow}>
                <Text style={styles.indicatorText}>RSI: {stock.rsi ?? '—'}</Text>
                <Text style={styles.indicatorText}>ADX: {stock.adx ?? '—'}</Text>
                <Ionicons name="chevron-forward" size={18} color={colors.loss} />
              </View>
            </TouchableOpacity>
          ))
        )}

        <View style={styles.disclaimer}>
          <Ionicons name="information-circle" size={14} color={colors.textMuted} />
          <Text style={styles.disclaimerText}>
            AI recommendations are based on technical analysis of 6-month candle data. Not financial advice.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40 },
  loadingText: { color: colors.text, marginTop: 16, fontSize: 16, fontWeight: '600' },
  loadingSubtext: { color: colors.textMuted, marginTop: 6, fontSize: 13, textAlign: 'center' },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 100 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 20 },
  title: { color: colors.text, fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
  aiBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(124,58,237,0.12)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(124,58,237,0.2)', gap: 5 },
  aiBadgeText: { color: colors.accent, fontSize: 12, fontWeight: '600' },
  statsRow: { flexDirection: 'row', gap: 8, marginBottom: 24 },
  statCard: { flex: 1, backgroundColor: colors.card, borderRadius: 14, padding: 12, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  statCardBuy: { borderColor: 'rgba(16,185,129,0.2)' },
  statCardSell: { borderColor: 'rgba(239,68,68,0.2)' },
  statLabel: { color: colors.textMuted, fontSize: 10, marginBottom: 4 },
  statValue: { color: colors.text, fontSize: 22, fontWeight: '800', fontVariant: ['tabular-nums'] },
  statValueSm: { fontSize: 14, fontWeight: '800' },
  statIcon: { position: 'absolute', top: 10, right: 10 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  sectionTitle: { fontSize: 18, fontWeight: '700' },
  sectionSub: { color: colors.textMuted, fontSize: 13, marginBottom: 14, marginTop: 2 },
  countBadgeGreen: { backgroundColor: colors.profit, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  countBadgeRed: { backgroundColor: colors.loss, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  countBadgeText: { color: '#FFF', fontSize: 12, fontWeight: '700' },
  emptySection: { alignItems: 'center', paddingVertical: 40, backgroundColor: colors.card, borderRadius: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.3)' },
  emptyText: { color: colors.textMuted, fontSize: 14, marginTop: 8 },
  recCard: { backgroundColor: colors.card, borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(16,185,129,0.1)' },
  recCardSell: { borderColor: 'rgba(239,68,68,0.1)' },
  recHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  recTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  recSymbol: { color: colors.text, fontSize: 16, fontWeight: '800' },
  sectorBadge: { backgroundColor: 'rgba(255,255,255,0.08)', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  sectorText: { color: colors.textSecondary, fontSize: 11, fontWeight: '600' },
  recName: { color: colors.textMuted, fontSize: 12, marginTop: 3 },
  recPriceCol: { alignItems: 'flex-end' },
  recPrice: { color: colors.text, fontSize: 16, fontWeight: '700', fontVariant: ['tabular-nums'] },
  recChange: { fontSize: 13, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 2 },
  confRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, marginBottom: 6 },
  confLabel: { color: colors.textMuted, fontSize: 12 },
  confValue: { fontSize: 13, fontWeight: '700', fontVariant: ['tabular-nums'] },
  confBarBg: { height: 8, backgroundColor: 'rgba(39,39,42,0.5)', borderRadius: 4, overflow: 'hidden' },
  confBarFill: { height: '100%', borderRadius: 4, flexDirection: 'row', overflow: 'hidden' },
  confBarBlue: { height: '100%', backgroundColor: '#3B82F6' },
  confBarGreen: { height: '100%', backgroundColor: colors.profit },
  confBarFillRed: { height: '100%', backgroundColor: colors.loss, borderRadius: 4 },
  srRow: { flexDirection: 'row', marginTop: 10, gap: 8 },
  srItem: { flex: 1, backgroundColor: 'rgba(39,39,42,0.3)', borderRadius: 8, padding: 8 },
  srLabel: { color: colors.textMuted, fontSize: 10 },
  srValue: { color: colors.text, fontSize: 12, fontWeight: '600', fontVariant: ['tabular-nums'], marginTop: 2 },
  divider: { height: 1, backgroundColor: 'rgba(39,39,42,0.3)', marginVertical: 10 },
  indicatorRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  indicatorText: { color: colors.textSecondary, fontSize: 12, fontVariant: ['tabular-nums'] },
  disclaimer: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: 20, padding: 14, backgroundColor: 'rgba(39,39,42,0.2)', borderRadius: 12 },
  disclaimerText: { color: colors.textMuted, fontSize: 11, lineHeight: 16, flex: 1 },
});
