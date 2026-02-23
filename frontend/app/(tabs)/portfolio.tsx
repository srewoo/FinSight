import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, RefreshControl, Alert, TextInput, Modal, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api';
import { colors, formatCurrency, formatLargeNumber } from '../../src/theme';

interface PortfolioStock {
  id: string; symbol: string; name: string; exchange: string; quantity: number;
  buy_price: number; current_price?: number; pnl?: number; pnl_percent?: number;
}
interface Summary {
  total_invested: number; total_current: number; total_pnl: number;
  total_pnl_percent: number; holdings_count: number;
}

export default function PortfolioScreen() {
  const [portfolio, setPortfolio] = useState<PortfolioStock[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ symbol: '', name: '', quantity: '', buy_price: '' });
  const [adding, setAdding] = useState(false);

  const fetchPortfolio = useCallback(async () => {
    try {
      const data = await api.getPortfolio();
      setPortfolio(data.portfolio || []);
      setSummary(data.summary || null);
    } catch (e) {
      console.error('Portfolio error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);
  const onRefresh = () => { setRefreshing(true); fetchPortfolio(); };

  const addHolding = async () => {
    if (!form.symbol || !form.quantity || !form.buy_price) {
      Alert.alert('Error', 'Please fill symbol, quantity and buy price');
      return;
    }
    setAdding(true);
    try {
      const sym = form.symbol.toUpperCase();
      const symbol = sym.includes('.') ? sym : `${sym}.NS`;
      await api.addToPortfolio({
        symbol, name: form.name || sym.replace('.NS', ''),
        quantity: parseFloat(form.quantity), buy_price: parseFloat(form.buy_price),
      });
      setShowAdd(false);
      setForm({ symbol: '', name: '', quantity: '', buy_price: '' });
      fetchPortfolio();
    } catch (e) {
      Alert.alert('Error', 'Failed to add holding');
    } finally { setAdding(false); }
  };

  const removeHolding = (id: string, name: string) => {
    Alert.alert('Remove Holding', `Remove ${name}?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: async () => {
        try { await api.removeFromPortfolio(id); fetchPortfolio(); } catch (e) { console.error(e); }
      }},
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
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Portfolio</Text>
            <Text style={styles.subtitle}>{summary?.holdings_count || 0} holdings</Text>
          </View>
          <TouchableOpacity style={styles.addBtn} onPress={() => setShowAdd(true)} testID="add-portfolio-btn">
            <Ionicons name="add" size={20} color="#FFF" />
            <Text style={styles.addBtnText}>Add</Text>
          </TouchableOpacity>
        </View>

        {/* Summary Card */}
        {summary && summary.holdings_count > 0 && (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>Total Value</Text>
            <Text style={styles.summaryValue}>{formatCurrency(summary.total_current)}</Text>
            <View style={styles.summaryRow}>
              <View style={styles.summaryCol}>
                <Text style={styles.summarySmLabel}>Invested</Text>
                <Text style={styles.summarySmValue}>{formatCurrency(summary.total_invested)}</Text>
              </View>
              <View style={styles.summaryCol}>
                <Text style={styles.summarySmLabel}>P&L</Text>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <Text style={[styles.summarySmValue, { color: summary.total_pnl >= 0 ? colors.profit : colors.loss }]}>
                    {summary.total_pnl >= 0 ? '+' : ''}{formatCurrency(summary.total_pnl)}
                  </Text>
                  <View style={[styles.pnlBadge, { backgroundColor: summary.total_pnl >= 0 ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
                    <Text style={[styles.pnlBadgeText, { color: summary.total_pnl >= 0 ? colors.profit : colors.loss }]}>
                      {summary.total_pnl_percent >= 0 ? '+' : ''}{summary.total_pnl_percent}%
                    </Text>
                  </View>
                </View>
              </View>
            </View>
          </View>
        )}

        {portfolio.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="briefcase-outline" size={56} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>No Holdings</Text>
            <Text style={styles.emptyDesc}>Add your stock holdings to track P&L and portfolio performance</Text>
          </View>
        ) : (
          portfolio.map((stock) => (
            <View key={stock.id} style={styles.holdingCard} testID={`portfolio-item-${stock.symbol}`}>
              <View style={styles.holdingHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.holdingSymbol}>{stock.symbol.replace('.NS', '').replace('.BO', '')}</Text>
                  <Text style={styles.holdingName} numberOfLines={1}>{stock.name}</Text>
                </View>
                <TouchableOpacity onPress={() => removeHolding(stock.id, stock.name)} style={styles.removeBtn} testID={`remove-portfolio-${stock.id}`}>
                  <Ionicons name="trash-outline" size={16} color={colors.loss} />
                </TouchableOpacity>
              </View>
              <View style={styles.holdingDetails}>
                <View style={styles.holdingDetailCol}>
                  <Text style={styles.detailLabel}>Qty</Text>
                  <Text style={styles.detailValue}>{stock.quantity}</Text>
                </View>
                <View style={styles.holdingDetailCol}>
                  <Text style={styles.detailLabel}>Avg Price</Text>
                  <Text style={styles.detailValue}>{formatCurrency(stock.buy_price)}</Text>
                </View>
                <View style={styles.holdingDetailCol}>
                  <Text style={styles.detailLabel}>Current</Text>
                  <Text style={styles.detailValue}>{formatCurrency(stock.current_price)}</Text>
                </View>
                <View style={styles.holdingDetailCol}>
                  <Text style={styles.detailLabel}>P&L</Text>
                  <Text style={[styles.detailValue, { color: (stock.pnl || 0) >= 0 ? colors.profit : colors.loss }]}>
                    {(stock.pnl || 0) >= 0 ? '+' : ''}{formatCurrency(stock.pnl)}
                  </Text>
                  <Text style={[styles.detailPct, { color: (stock.pnl_percent || 0) >= 0 ? colors.profit : colors.loss }]}>
                    {(stock.pnl_percent || 0) >= 0 ? '+' : ''}{stock.pnl_percent || 0}%
                  </Text>
                </View>
              </View>
            </View>
          ))
        )}
      </ScrollView>

      {/* Add Modal */}
      <Modal visible={showAdd} transparent animationType="slide">
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Holding</Text>
              <TouchableOpacity onPress={() => setShowAdd(false)} testID="close-add-modal">
                <Ionicons name="close" size={24} color={colors.text} />
              </TouchableOpacity>
            </View>
            <TextInput style={styles.input} placeholder="Symbol (e.g., RELIANCE)" placeholderTextColor={colors.textMuted} value={form.symbol} onChangeText={(t) => setForm(p => ({ ...p, symbol: t }))} autoCapitalize="characters" testID="portfolio-symbol-input" />
            <TextInput style={styles.input} placeholder="Company Name (optional)" placeholderTextColor={colors.textMuted} value={form.name} onChangeText={(t) => setForm(p => ({ ...p, name: t }))} testID="portfolio-name-input" />
            <TextInput style={styles.input} placeholder="Quantity" placeholderTextColor={colors.textMuted} value={form.quantity} onChangeText={(t) => setForm(p => ({ ...p, quantity: t }))} keyboardType="numeric" testID="portfolio-quantity-input" />
            <TextInput style={styles.input} placeholder="Buy Price (per share)" placeholderTextColor={colors.textMuted} value={form.buy_price} onChangeText={(t) => setForm(p => ({ ...p, buy_price: t }))} keyboardType="numeric" testID="portfolio-price-input" />
            <TouchableOpacity style={styles.submitBtn} onPress={addHolding} disabled={adding} testID="submit-portfolio-btn">
              {adding ? <ActivityIndicator color="#FFF" /> : <Text style={styles.submitBtnText}>Add Holding</Text>}
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 100 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 24 },
  title: { color: colors.text, fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
  subtitle: { color: colors.textMuted, fontSize: 14, marginTop: 2 },
  addBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.primary, paddingHorizontal: 16, paddingVertical: 10, borderRadius: 24, gap: 4 },
  addBtnText: { color: '#FFF', fontSize: 14, fontWeight: '700' },
  summaryCard: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginBottom: 24, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  summaryLabel: { color: colors.textMuted, fontSize: 13 },
  summaryValue: { color: colors.text, fontSize: 32, fontWeight: '800', fontVariant: ['tabular-nums'], marginTop: 4 },
  summaryRow: { flexDirection: 'row', marginTop: 16, gap: 24 },
  summaryCol: {},
  summarySmLabel: { color: colors.textMuted, fontSize: 12 },
  summarySmValue: { color: colors.text, fontSize: 16, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 2 },
  pnlBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  pnlBadgeText: { fontSize: 12, fontWeight: '700', fontVariant: ['tabular-nums'] },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyTitle: { color: colors.text, fontSize: 20, fontWeight: '700', marginTop: 16 },
  emptyDesc: { color: colors.textMuted, fontSize: 14, textAlign: 'center', marginTop: 8, lineHeight: 20, paddingHorizontal: 20 },
  holdingCard: { backgroundColor: colors.card, borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(39,39,42,0.3)' },
  holdingHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  holdingSymbol: { color: colors.text, fontSize: 16, fontWeight: '700' },
  holdingName: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  removeBtn: { padding: 6 },
  holdingDetails: { flexDirection: 'row', marginTop: 14, gap: 8 },
  holdingDetailCol: { flex: 1 },
  detailLabel: { color: colors.textMuted, fontSize: 11 },
  detailValue: { color: colors.text, fontSize: 14, fontWeight: '600', fontVariant: ['tabular-nums'], marginTop: 2 },
  detailPct: { fontSize: 11, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 1 },
  modalOverlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.7)' },
  modalContent: { backgroundColor: colors.card, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 40 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { color: colors.text, fontSize: 20, fontWeight: '700' },
  input: { backgroundColor: colors.bg, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, color: colors.text, fontSize: 15, marginBottom: 12, borderWidth: 1, borderColor: colors.border },
  submitBtn: { backgroundColor: colors.primary, borderRadius: 30, paddingVertical: 16, alignItems: 'center', marginTop: 8 },
  submitBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
