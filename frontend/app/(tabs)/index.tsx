import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, RefreshControl, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api';
import { colors, formatCurrency } from '../../src/theme';
import SectorHeatmap from '../../src/components/SectorHeatmap';
import NewsCard from '../../src/components/NewsCard';
import { wsManager } from '../../src/websocket';
import { useMarketStatus } from '../../src/hooks/useMarketStatus';

interface IndexData {
  symbol: string; name: string; price: number; change: number; change_percent: number;
}
interface StockMover {
  symbol: string; name: string; price: number; change: number; change_percent: number;
}

const MARKET_STATUS_COLORS: Record<string, string> = {
  open: colors.profit,
  'pre-market': '#F59E0B',
  closed: colors.loss,
  weekend: colors.textMuted,
  unknown: colors.textMuted,
};

const MARKET_STATUS_LABELS: Record<string, string> = {
  open: 'Market Open',
  'pre-market': 'Pre-Market',
  closed: 'Market Closed',
  weekend: 'Weekend',
  unknown: 'Live',
};

export default function HomeScreen() {
  const router = useRouter();
  const [indices, setIndices] = useState<IndexData[]>([]);
  const [gainers, setGainers] = useState<StockMover[]>([]);
  const [losers, setLosers] = useState<StockMover[]>([]);
  const [newsArticles, setNewsArticles] = useState<any[]>([]);
  const [sectors, setSectors] = useState<any[]>([]);
  const [sectorBreadth, setSectorBreadth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const indicesRef = useRef<IndexData[]>([]);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const marketStatus = useMarketStatus();
  const statusColor = MARKET_STATUS_COLORS[marketStatus] ?? colors.textMuted;
  const statusLabel = MARKET_STATUS_LABELS[marketStatus] ?? 'Live';

  // Pulsing dot animation for live indicator
  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 900, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 900, useNativeDriver: true }),
      ])
    );
    if (wsConnected && marketStatus === 'open') pulse.start();
    else pulse.stop();
    return () => pulse.stop();
  }, [wsConnected, marketStatus, pulseAnim]);

  // WebSocket: connect and subscribe to index symbols for live price updates
  useEffect(() => {
    wsManager.connect();
    const indexSymbols = ['^NSEI', '^BSESN'];
    wsManager.subscribe(indexSymbols);

    const prevPriceHandler = wsManager.onPriceUpdate;
    wsManager.onPriceUpdate = (sym, update) => {
      if (prevPriceHandler) prevPriceHandler(sym, update);
      setWsConnected(true);
      setIndices(prev => {
        const next = prev.map(idx =>
          idx.symbol === sym
            ? { ...idx, price: update.price, change: update.change }
            : idx
        );
        indicesRef.current = next;
        return next;
      });
    };

    return () => {
      wsManager.unsubscribe(indexSymbols);
    };
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [idxRes, moversRes] = await Promise.all([
        api.getIndices(),
        api.getTopMovers(),
      ]);
      setIndices(idxRes.indices || []);
      indicesRef.current = idxRes.indices || [];
      setGainers(moversRes.gainers || []);
      setLosers(moversRes.losers || []);
    } catch (e) {
      // silently handled
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
    // Lazy-load news + heatmap (non-blocking)
    api.getMarketNews(10).then(res => setNewsArticles(res.articles || [])).catch(() => { });
    api.getSectorHeatmap().then(res => {
      setSectors(res.sectors || []);
      setSectorBreadth(res.market_breadth || null);
    }).catch(() => { });
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = () => { setRefreshing(true); fetchData(); };

  const navigateToStock = (symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading market data...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.appName} testID="app-title">FinSight</Text>
            <Text style={styles.subtitle}>Indian Market Intelligence</Text>
          </View>
          <View style={{ gap: 8, alignItems: 'flex-end' }}>
            <View style={styles.aiBadge}>
              <Ionicons name="sparkles" size={14} color={colors.primary} />
              <Text style={styles.aiBadgeText}>AI Powered</Text>
            </View>
            <View style={[styles.marketStatusBadge, { borderColor: `${statusColor}40` }]}>
              <Animated.View style={[styles.liveDot, { backgroundColor: statusColor, opacity: pulseAnim }]} />
              <Text style={[styles.marketStatusText, { color: statusColor }]}>{statusLabel}</Text>
            </View>
          </View>
        </View>

        {/* Market Indices */}
        <Text style={styles.sectionTitle}>Market Indices</Text>
        <View style={styles.indicesRow}>
          {indices.map((idx) => (
            <View key={idx.symbol} style={styles.indexCard} testID={`index-card-${idx.symbol}`}>
              <Text style={styles.indexName}>{idx.name}</Text>
              <Text style={styles.indexPrice}>{formatCurrency(idx.price)}</Text>
              <View style={[styles.changeRow, { marginTop: 6 }]}>
                <Ionicons
                  name={idx.change >= 0 ? 'trending-up' : 'trending-down'}
                  size={16}
                  color={idx.change >= 0 ? colors.profit : colors.loss}
                />
                <Text style={[styles.changeText, { color: idx.change >= 0 ? colors.profit : colors.loss }]}>
                  {idx.change >= 0 ? '+' : ''}{idx.change} ({idx.change_percent}%)
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Top Gainers */}
        <Text style={styles.sectionTitle}>Top Gainers</Text>
        {gainers.map((stock) => (
          <TouchableOpacity
            key={stock.symbol}
            style={styles.stockRow}
            onPress={() => navigateToStock(stock.symbol)}
            testID={`gainer-${stock.symbol}`}
            activeOpacity={0.7}
          >
            <View style={styles.stockInfo}>
              <Text style={styles.stockSymbol}>{stock.symbol.replace('.NS', '').replace('.BO', '')}</Text>
              <Text style={styles.stockName} numberOfLines={1}>{stock.name}</Text>
            </View>
            <View style={styles.stockPriceCol}>
              <Text style={styles.stockPrice}>{formatCurrency(stock.price)}</Text>
              <View style={styles.changeBadgeGreen}>
                <Text style={styles.changeBadgeTextGreen}>+{stock.change_percent}%</Text>
              </View>
            </View>
          </TouchableOpacity>
        ))}

        {/* Top Losers */}
        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>Top Losers</Text>
        {losers.map((stock) => (
          <TouchableOpacity
            key={stock.symbol}
            style={styles.stockRow}
            onPress={() => navigateToStock(stock.symbol)}
            testID={`loser-${stock.symbol}`}
            activeOpacity={0.7}
          >
            <View style={styles.stockInfo}>
              <Text style={styles.stockSymbol}>{stock.symbol.replace('.NS', '').replace('.BO', '')}</Text>
              <Text style={styles.stockName} numberOfLines={1}>{stock.name}</Text>
            </View>
            <View style={styles.stockPriceCol}>
              <Text style={styles.stockPrice}>{formatCurrency(stock.price)}</Text>
              <View style={styles.changeBadgeRed}>
                <Text style={styles.changeBadgeTextRed}>{stock.change_percent}%</Text>
              </View>
            </View>
          </TouchableOpacity>
        ))}

        {/* AI Promo Card */}
        <View style={styles.aiPromo}>
          <View style={styles.aiPromoInner}>
            <Ionicons name="sparkles" size={24} color={colors.aiGlow} />
            <View style={{ marginLeft: 16, flex: 1 }}>
              <Text style={styles.aiPromoTitle}>AI Stock Predictions</Text>
              <Text style={styles.aiPromoDesc}>Search any NSE/BSE stock and get AI-powered buy/sell signals with technical analysis</Text>
            </View>
          </View>
          <TouchableOpacity
            style={styles.aiPromoBtn}
            onPress={() => router.push('/(tabs)/search')}
            testID="ai-promo-search-btn"
            activeOpacity={0.8}
          >
            <Text style={styles.aiPromoBtnText}>Search Stocks</Text>
            <Ionicons name="arrow-forward" size={16} color="#FFF" />
          </TouchableOpacity>
        </View>

        {/* Sector Heatmap */}
        {sectors.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionRow}>
              <Text style={styles.sectionTitle}>Sector Performance</Text>
              <View style={styles.liveBadge}>
                <View style={styles.liveDot} />
                <Text style={styles.liveText}>5D</Text>
              </View>
            </View>
            <SectorHeatmap sectors={sectors} market_breadth={sectorBreadth} />
          </View>
        )}

        {/* Market News */}
        {newsArticles.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionRow}>
              <Text style={styles.sectionTitle}>Market News</Text>
              <Ionicons name="newspaper-outline" size={18} color={colors.textMuted} />
            </View>
            {newsArticles.slice(0, 6).map((article, i) => (
              <NewsCard key={i} article={article} />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: colors.textMuted, marginTop: 12, fontSize: 14 },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 100 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 28 },
  appName: { color: colors.text, fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
  subtitle: { color: colors.textMuted, fontSize: 14, marginTop: 2 },
  aiBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(124,58,237,0.12)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(124,58,237,0.2)' },
  aiBadgeText: { color: colors.accent, fontSize: 12, fontWeight: '600', marginLeft: 6 },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: '700', marginBottom: 14 },
  indicesRow: { flexDirection: 'row', gap: 12, marginBottom: 28 },
  indexCard: { flex: 1, backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  indexName: { color: colors.textMuted, fontSize: 13, fontWeight: '500' },
  indexPrice: { color: colors.text, fontSize: 20, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 6 },
  changeRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  changeText: { fontSize: 13, fontWeight: '600', fontVariant: ['tabular-nums'] },
  stockRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: colors.card, borderRadius: 14, padding: 16, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(39,39,42,0.3)' },
  stockInfo: { flex: 1, marginRight: 12 },
  stockSymbol: { color: colors.text, fontSize: 15, fontWeight: '700' },
  stockName: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  stockPriceCol: { alignItems: 'flex-end' },
  stockPrice: { color: colors.text, fontSize: 15, fontWeight: '700', fontVariant: ['tabular-nums'] },
  changeBadgeGreen: { backgroundColor: 'rgba(16,185,129,0.12)', paddingHorizontal: 10, paddingVertical: 3, borderRadius: 12, marginTop: 4, borderWidth: 1, borderColor: 'rgba(16,185,129,0.2)' },
  changeBadgeTextGreen: { color: colors.profit, fontSize: 12, fontWeight: '700', fontVariant: ['tabular-nums'] },
  changeBadgeRed: { backgroundColor: 'rgba(239,68,68,0.12)', paddingHorizontal: 10, paddingVertical: 3, borderRadius: 12, marginTop: 4, borderWidth: 1, borderColor: 'rgba(239,68,68,0.2)' },
  changeBadgeTextRed: { color: colors.loss, fontSize: 12, fontWeight: '700', fontVariant: ['tabular-nums'] },
  aiPromo: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginTop: 16, borderWidth: 1, borderColor: 'rgba(124,58,237,0.15)' },
  aiPromoInner: { flexDirection: 'row', alignItems: 'flex-start' },
  aiPromoTitle: { color: colors.text, fontSize: 16, fontWeight: '700' },
  aiPromoDesc: { color: colors.textMuted, fontSize: 13, marginTop: 4, lineHeight: 19 },
  aiPromoBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary, borderRadius: 30, paddingVertical: 14, marginTop: 16, gap: 8 },
  aiPromoBtnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },
  section: { marginTop: 24 },
  sectionRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  liveBadge: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: colors.profit },
  liveText: { color: colors.textMuted, fontSize: 12 },
  marketStatusBadge: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, borderWidth: 1, backgroundColor: 'rgba(0,0,0,0.3)' },
  marketStatusText: { fontSize: 11, fontWeight: '600' },
});
