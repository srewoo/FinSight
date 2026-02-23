import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, RefreshControl, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api';
import { colors, formatCurrency } from '../../src/theme';

interface WatchlistStock {
  id: string; symbol: string; name: string; exchange: string; added_at: string;
}

export default function WatchlistScreen() {
  const router = useRouter();
  const [watchlist, setWatchlist] = useState<WatchlistStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchWatchlist = useCallback(async () => {
    try {
      const data = await api.getWatchlist();
      setWatchlist(data.watchlist || []);
    } catch (e) {
      console.error('Watchlist error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchWatchlist(); }, [fetchWatchlist]);

  const onRefresh = () => { setRefreshing(true); fetchWatchlist(); };

  const removeItem = (symbol: string) => {
    Alert.alert('Remove Stock', `Remove ${symbol.replace('.NS', '').replace('.BO', '')} from watchlist?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove', style: 'destructive', onPress: async () => {
          try {
            await api.removeFromWatchlist(symbol);
            setWatchlist(prev => prev.filter(w => w.symbol !== symbol));
          } catch (e) { console.error(e); }
        }
      },
    ]);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
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
        <View style={styles.header}>
          <Text style={styles.title}>Watchlist</Text>
          <Text style={styles.count}>{watchlist.length} stocks</Text>
        </View>

        {watchlist.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="eye-outline" size={56} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>Empty Watchlist</Text>
            <Text style={styles.emptyDesc}>Search for stocks and add them to your watchlist to track them here</Text>
            <TouchableOpacity
              style={styles.emptyBtn}
              onPress={() => router.push('/(tabs)/search')}
              testID="watchlist-search-btn"
            >
              <Ionicons name="search" size={18} color="#FFF" />
              <Text style={styles.emptyBtnText}>Search Stocks</Text>
            </TouchableOpacity>
          </View>
        ) : (
          watchlist.map((stock) => (
            <TouchableOpacity
              key={stock.id}
              style={styles.stockRow}
              onPress={() => router.push(`/stock/${encodeURIComponent(stock.symbol)}`)}
              testID={`watchlist-item-${stock.symbol}`}
              activeOpacity={0.7}
            >
              <View style={styles.stockLeft}>
                <View style={styles.symbolBadge}>
                  <Text style={styles.symbolBadgeText}>
                    {stock.symbol.replace('.NS', '').replace('.BO', '').slice(0, 3)}
                  </Text>
                </View>
                <View style={styles.stockInfo}>
                  <Text style={styles.stockSymbol}>{stock.symbol.replace('.NS', '').replace('.BO', '')}</Text>
                  <Text style={styles.stockName} numberOfLines={1}>{stock.name}</Text>
                </View>
              </View>
              <View style={styles.stockRight}>
                <View style={[styles.exchangeBadge, stock.exchange === 'BSE' ? styles.bseBadge : null]}>
                  <Text style={[styles.exchangeText, stock.exchange === 'BSE' ? styles.bseText : null]}>{stock.exchange}</Text>
                </View>
                <TouchableOpacity
                  onPress={() => removeItem(stock.symbol)}
                  style={styles.removeBtn}
                  testID={`remove-watchlist-${stock.symbol}`}
                >
                  <Ionicons name="trash-outline" size={18} color={colors.loss} />
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 100 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 8, marginBottom: 24 },
  title: { color: colors.text, fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
  count: { color: colors.textMuted, fontSize: 14 },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyTitle: { color: colors.text, fontSize: 20, fontWeight: '700', marginTop: 16 },
  emptyDesc: { color: colors.textMuted, fontSize: 14, textAlign: 'center', marginTop: 8, lineHeight: 20, paddingHorizontal: 20 },
  emptyBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.primary, paddingHorizontal: 24, paddingVertical: 14, borderRadius: 30, marginTop: 24, gap: 8 },
  emptyBtnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },
  stockRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: colors.card, borderRadius: 14, padding: 16, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(39,39,42,0.3)' },
  stockLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  symbolBadge: { width: 44, height: 44, borderRadius: 12, backgroundColor: 'rgba(124,58,237,0.1)', alignItems: 'center', justifyContent: 'center' },
  symbolBadgeText: { color: colors.primary, fontSize: 13, fontWeight: '800' },
  stockInfo: { marginLeft: 14, flex: 1 },
  stockSymbol: { color: colors.text, fontSize: 15, fontWeight: '700' },
  stockName: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  stockRight: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  exchangeBadge: { backgroundColor: 'rgba(59,130,246,0.12)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, borderWidth: 1, borderColor: 'rgba(59,130,246,0.2)' },
  exchangeText: { color: colors.info, fontSize: 11, fontWeight: '700' },
  bseBadge: { backgroundColor: 'rgba(245,158,11,0.12)', borderColor: 'rgba(245,158,11,0.2)' },
  bseText: { color: colors.warning },
  removeBtn: { padding: 8 },
});
