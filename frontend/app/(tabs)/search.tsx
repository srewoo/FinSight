import React, { useState, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, ActivityIndicator,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api';
import { colors, formatCurrency } from '../../src/theme';

interface SearchResult {
  symbol: string; name: string; exchange: string;
}

export default function SearchScreen() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const searchStocks = useCallback(async (q: string) => {
    if (q.trim().length < 1) { setResults([]); setSearched(false); return; }
    setLoading(true);
    try {
      const data = await api.searchStocks(q);
      setResults(data.results || []);
      setSearched(true);
    } catch (e) {
      console.error('Search error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = (text: string) => {
    setQuery(text);
    if (text.length >= 2) {
      searchStocks(text);
    } else {
      setResults([]);
      setSearched(false);
    }
  };

  return (
    <SafeAreaView style={styles.screen}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <View style={styles.headerSection}>
          <Text style={styles.title}>Search Stocks</Text>
          <Text style={styles.subtitle}>NSE & BSE Listed Companies</Text>
        </View>

        <View style={styles.searchBar}>
          <Ionicons name="search" size={20} color={colors.textMuted} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search by name or symbol..."
            placeholderTextColor={colors.textMuted}
            value={query}
            onChangeText={handleSearch}
            autoCapitalize="characters"
            testID="stock-search-input"
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => { setQuery(''); setResults([]); setSearched(false); }} testID="clear-search-btn">
              <Ionicons name="close-circle" size={20} color={colors.textMuted} />
            </TouchableOpacity>
          )}
        </View>

        {loading && (
          <View style={styles.loaderWrap}>
            <ActivityIndicator size="small" color={colors.primary} />
          </View>
        )}

        <ScrollView contentContainerStyle={styles.scrollContent}>
          {!searched && !loading && (
            <View style={styles.emptyState}>
              <Ionicons name="search-outline" size={48} color={colors.textMuted} />
              <Text style={styles.emptyTitle}>Find Any Stock</Text>
              <Text style={styles.emptyDesc}>Type a stock name or NSE/BSE symbol to get AI-powered analysis and predictions</Text>
              <View style={styles.suggestionsWrap}>
                <Text style={styles.suggestLabel}>Popular Searches</Text>
                {['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'SBIN', 'ITC'].map((s) => (
                  <TouchableOpacity key={s} style={styles.suggestChip} onPress={() => handleSearch(s)} testID={`suggest-${s}`}>
                    <Text style={styles.suggestChipText}>{s}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          {searched && results.length === 0 && !loading && (
            <View style={styles.emptyState}>
              <Ionicons name="alert-circle-outline" size={48} color={colors.textMuted} />
              <Text style={styles.emptyTitle}>No Results</Text>
              <Text style={styles.emptyDesc}>Try a different search term</Text>
            </View>
          )}

          {results.map((stock) => (
            <TouchableOpacity
              key={stock.symbol}
              style={styles.resultRow}
              onPress={() => router.push(`/stock/${encodeURIComponent(stock.symbol)}`)}
              testID={`search-result-${stock.symbol}`}
              activeOpacity={0.7}
            >
              <View style={styles.resultLeft}>
                <View style={styles.symbolBadge}>
                  <Text style={styles.symbolBadgeText}>
                    {stock.symbol.replace('.NS', '').replace('.BO', '').slice(0, 3)}
                  </Text>
                </View>
                <View style={styles.resultInfo}>
                  <Text style={styles.resultSymbol}>{stock.symbol.replace('.NS', '').replace('.BO', '')}</Text>
                  <Text style={styles.resultName} numberOfLines={1}>{stock.name}</Text>
                </View>
              </View>
              <View style={styles.resultRight}>
                <View style={[styles.exchangeBadge, stock.exchange === 'BSE' ? styles.bseBadge : null]}>
                  <Text style={[styles.exchangeText, stock.exchange === 'BSE' ? styles.bseText : null]}>{stock.exchange}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  headerSection: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 16 },
  title: { color: colors.text, fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
  subtitle: { color: colors.textMuted, fontSize: 14, marginTop: 2 },
  searchBar: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.card, marginHorizontal: 20, borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14, borderWidth: 1, borderColor: colors.border, gap: 10 },
  searchInput: { flex: 1, color: colors.text, fontSize: 16 },
  loaderWrap: { alignItems: 'center', paddingVertical: 16 },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 100, paddingTop: 16 },
  emptyState: { alignItems: 'center', paddingTop: 40 },
  emptyTitle: { color: colors.text, fontSize: 18, fontWeight: '700', marginTop: 16 },
  emptyDesc: { color: colors.textMuted, fontSize: 14, textAlign: 'center', marginTop: 6, lineHeight: 20, paddingHorizontal: 20 },
  suggestionsWrap: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', marginTop: 24, gap: 8 },
  suggestLabel: { color: colors.textSecondary, fontSize: 13, fontWeight: '600', width: '100%', textAlign: 'center', marginBottom: 8 },
  suggestChip: { backgroundColor: colors.card, paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20, borderWidth: 1, borderColor: colors.border },
  suggestChipText: { color: colors.text, fontSize: 13, fontWeight: '600' },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: colors.card, borderRadius: 14, padding: 16, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(39,39,42,0.3)' },
  resultLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  symbolBadge: { width: 44, height: 44, borderRadius: 12, backgroundColor: 'rgba(124,58,237,0.1)', alignItems: 'center', justifyContent: 'center' },
  symbolBadgeText: { color: colors.primary, fontSize: 13, fontWeight: '800' },
  resultInfo: { marginLeft: 14, flex: 1 },
  resultSymbol: { color: colors.text, fontSize: 15, fontWeight: '700' },
  resultName: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  resultRight: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  exchangeBadge: { backgroundColor: 'rgba(59,130,246,0.12)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, borderWidth: 1, borderColor: 'rgba(59,130,246,0.2)' },
  exchangeText: { color: colors.info, fontSize: 11, fontWeight: '700' },
  bseBadge: { backgroundColor: 'rgba(245,158,11,0.12)', borderColor: 'rgba(245,158,11,0.2)' },
  bseText: { color: colors.warning },
});
