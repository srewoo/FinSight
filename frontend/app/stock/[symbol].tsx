import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LineChart } from 'react-native-gifted-charts';
import { api } from '../../src/api';
import { colors, formatCurrency, formatLargeNumber } from '../../src/theme';
import SEBIDisclaimerBanner from '../../src/components/SEBIDisclaimerBanner';
import NewsCard from '../../src/components/NewsCard';
import OptionChainTable from '../../src/components/OptionChainTable';
import GreeksDisplay from '../../src/components/GreeksDisplay';

const SCREEN_WIDTH = Dimensions.get('window').width;

interface Quote {
  symbol: string; name: string; price: number; change: number; change_percent: number;
  open: number; high: number; low: number; volume: number; prev_close: number;
  day_high: number; day_low: number; fifty_two_week_high: number; fifty_two_week_low: number;
  market_cap: number; pe_ratio: number; sector: string; industry: string;
}

interface Technicals {
  rsi: number; rsi_signal: string;
  macd: { macd_line: number; signal_line: number; histogram: number; signal: string };
  moving_averages: { sma20: number; sma50: number; sma200: number; ema20: number };
  bollinger_bands: { upper: number; middle: number; lower: number; signal: string };
  price_vs_sma20: string;
}

interface AIResult {
  recommendation: string; confidence: number; target_price: number; stop_loss: number;
  summary: string; key_reasons: string[]; risks: string[];
  technical_outlook: string; sentiment: string;
}

export default function StockDetailScreen() {
  const { symbol } = useLocalSearchParams<{ symbol: string }>();
  const router = useRouter();
  const decodedSymbol = decodeURIComponent(symbol || '');

  const [quote, setQuote] = useState<Quote | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [technicals, setTechnicals] = useState<Technicals | null>(null);
  const [supportResistance, setSupportResistance] = useState<any>(null);
  const [fibLevels, setFibLevels] = useState<any>(null);
  const [poc, setPoc] = useState<number | null>(null);
  const [aiResult, setAiResult] = useState<AIResult | null>(null);
  const [fundamentals, setFundamentals] = useState<any>(null);
  const [stockNews, setStockNews] = useState<any[]>([]);
  const [earnings, setEarnings] = useState<any>(null);
  const [optionChain, setOptionChain] = useState<any>(null);
  const [selectedExpiry, setSelectedExpiry] = useState<string | null>(null);
  const [greeks, setGreeks] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'fundamentals' | 'news' | 'fno'>('overview');
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState('1mo');
  const [aiTimeframe, setAiTimeframe] = useState('short');
  const [inWatchlist, setInWatchlist] = useState(false);

  useEffect(() => {
    if (decodedSymbol) loadData();
  }, [decodedSymbol]);

  useEffect(() => {
    if (decodedSymbol) loadChart(selectedPeriod);
  }, [selectedPeriod, decodedSymbol]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [quoteData, techData, wlData] = await Promise.all([
        api.getQuote(decodedSymbol),
        api.getTechnicals(decodedSymbol),
        api.getWatchlist(),
      ]);
      setQuote(quoteData);
      setTechnicals(techData.technicals);
      setSupportResistance(techData.support_resistance || quoteData.support_resistance || null);
      setFibLevels(techData.fib_levels || null);
      setPoc(techData.poc || null);
      const isInWl = (wlData.watchlist || []).some((w: any) => w.symbol === decodedSymbol);
      setInWatchlist(isInWl);
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
    // Lazy-load non-critical data
    api.getFundamentals(decodedSymbol).then(res => setFundamentals(res.fundamentals)).catch(() => { });
    api.getStockNews(decodedSymbol, 8).then(res => setStockNews(res.articles || [])).catch(() => { });
    api.getEarnings(decodedSymbol).then(res => setEarnings(res)).catch(() => { });
    api.getOptionChain(decodedSymbol).then(res => {
      setOptionChain(res);
      if (res.expiry_dates?.[0]) setSelectedExpiry(res.expiry_dates[0]);
    }).catch(() => { });
  };

  const loadChart = async (period: string) => {
    try {
      const interval = period === '1d' ? '15m' : period === '5d' ? '1h' : '1d';
      const data = await api.getHistory(decodedSymbol, period, interval);
      const pts = (data.data || []).map((d: any, i: number) => ({
        value: d.close,
        label: i % Math.max(1, Math.floor((data.data || []).length / 5)) === 0
          ? (period === '1d' ? d.date.slice(11, 16) : d.date.slice(5, 10))
          : '',
        dataPointText: '',
      }));
      setChartData(pts);
    } catch (e) {
      console.error('Chart error:', e);
    }
  };

  const runAI = async () => {
    setAiLoading(true);
    setAiResult(null);
    try {
      const data = await api.getAIAnalysis(decodedSymbol, aiTimeframe);
      setAiResult(data.analysis);
    } catch (e: any) {
      const msg: string = e?.message ?? 'Failed to get AI analysis.';
      const isNoKey = msg.toLowerCase().includes('api key') || msg.toLowerCase().includes('no ai');
      Alert.alert(
        isNoKey ? 'API Key Required' : 'AI Analysis Failed',
        isNoKey
          ? 'No AI API key is configured. Go to Settings → add your OpenAI, Gemini, or Claude key → Save Settings.'
          : msg,
        isNoKey ? [{ text: 'Go to Settings', onPress: () => router.push('/(tabs)/settings') }, { text: 'Cancel', style: 'cancel' }] : undefined,
      );
    } finally {
      setAiLoading(false);
    }
  };

  const toggleWatchlist = async () => {
    try {
      if (inWatchlist) {
        await api.removeFromWatchlist(decodedSymbol);
        setInWatchlist(false);
      } else {
        const exchange = decodedSymbol.endsWith('.BO') ? 'BSE' : 'NSE';
        await api.addToWatchlist(decodedSymbol, quote?.name || decodedSymbol, exchange);
        setInWatchlist(true);
      }
    } catch (e) { console.error(e); }
  };

  const periods = [
    { label: '1D', value: '1d' },
    { label: '5D', value: '5d' },
    { label: '1M', value: '1mo' },
    { label: '3M', value: '3mo' },
    { label: '6M', value: '6mo' },
    { label: '1Y', value: '1y' },
  ];

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading stock data...</Text>
        </View>
      </SafeAreaView>
    );
  }

  const recColor = aiResult?.recommendation === 'BUY' ? colors.profit
    : aiResult?.recommendation === 'SELL' ? colors.loss : colors.warning;

  const TABS: Array<{ key: 'overview' | 'fundamentals' | 'news' | 'fno'; label: string }> = [
    { key: 'overview', label: 'Overview' },
    { key: 'fundamentals', label: 'Fundamentals' },
    { key: 'news', label: 'News' },
    { key: 'fno', label: 'F&O' },
  ];

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} testID="stock-back-btn">
            <Ionicons name="arrow-back" size={22} color={colors.text} />
          </TouchableOpacity>
          <View style={{ flex: 1 }}>
            <Text style={styles.stockSymbol} testID="stock-symbol">
              {decodedSymbol.replace('.NS', '').replace('.BO', '')}
            </Text>
            <Text style={styles.stockName} numberOfLines={1}>{quote?.name}</Text>
          </View>
          <TouchableOpacity onPress={toggleWatchlist} style={styles.watchlistBtn} testID="toggle-watchlist-btn">
            <Ionicons name={inWatchlist ? 'heart' : 'heart-outline'} size={24} color={inWatchlist ? colors.loss : colors.textMuted} />
          </TouchableOpacity>
        </View>

        {/* Price */}
        <View style={styles.priceSection}>
          <Text style={styles.price} testID="stock-price">{formatCurrency(quote?.price)}</Text>
          <View style={[styles.changeBadge, { backgroundColor: (quote?.change || 0) >= 0 ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
            <Ionicons
              name={(quote?.change || 0) >= 0 ? 'trending-up' : 'trending-down'}
              size={16}
              color={(quote?.change || 0) >= 0 ? colors.profit : colors.loss}
            />
            <Text style={[styles.changeText, { color: (quote?.change || 0) >= 0 ? colors.profit : colors.loss }]}>
              {(quote?.change || 0) >= 0 ? '+' : ''}{quote?.change} ({quote?.change_percent}%)
            </Text>
          </View>
        </View>

        {/* Tab bar */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabRow}>
          {TABS.map(tab => (
            <TouchableOpacity
              key={tab.key}
              style={[styles.tab, activeTab === tab.key && styles.tabActive]}
              onPress={() => setActiveTab(tab.key)}
            >
              <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}>{tab.label}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Chart (always shown) */}
        <View style={styles.chartCard}>
          <View style={styles.periodRow}>
            {periods.map((p) => (
              <TouchableOpacity
                key={p.value}
                style={[styles.periodBtn, selectedPeriod === p.value && styles.periodBtnActive]}
                onPress={() => setSelectedPeriod(p.value)}
                testID={`period-${p.value}`}
              >
                <Text style={[styles.periodText, selectedPeriod === p.value && styles.periodTextActive]}>{p.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          {chartData.length > 0 ? (
            <View style={styles.chartWrap}>
              <LineChart
                data={chartData}
                width={SCREEN_WIDTH - 80}
                height={180}
                color={colors.primary}
                thickness={2}
                hideDataPoints
                startFillColor="rgba(124,58,237,0.15)"
                endFillColor="rgba(124,58,237,0.01)"
                areaChart
                curved
                hideRules
                yAxisTextStyle={{ color: colors.textMuted, fontSize: 10 }}
                xAxisLabelTextStyle={{ color: colors.textMuted, fontSize: 9 }}
                noOfSections={4}
                yAxisColor="transparent"
                xAxisColor="transparent"
                backgroundColor="transparent"
              />
            </View>
          ) : (
            <View style={styles.noChart}>
              <Text style={styles.noChartText}>No chart data</Text>
            </View>
          )}
        </View>

        {/* --- OVERVIEW TAB --- */}
        {activeTab === 'overview' && (
          <>
            {/* Key Stats */}
            <View style={styles.statsCard}>
              <Text style={styles.cardTitle}>Key Statistics</Text>
              <View style={styles.statsGrid}>
                <StatItem label="Open" value={formatCurrency(quote?.open)} />
                <StatItem label="High" value={formatCurrency(quote?.high)} />
                <StatItem label="Low" value={formatCurrency(quote?.low)} />
                <StatItem label="Prev Close" value={formatCurrency(quote?.prev_close)} />
                <StatItem label="Volume" value={quote?.volume?.toLocaleString('en-IN') || '—'} />
                <StatItem label="P/E Ratio" value={quote?.pe_ratio ? String(quote.pe_ratio) : '—'} />
                <StatItem label="52W High" value={formatCurrency(quote?.fifty_two_week_high)} />
                <StatItem label="52W Low" value={formatCurrency(quote?.fifty_two_week_low)} />
                <StatItem label="Market Cap" value={formatLargeNumber(quote?.market_cap)} />
                <StatItem label="Sector" value={quote?.sector || '—'} />
              </View>
            </View>

            {/* Support & Resistance Levels */}
            {supportResistance && (
              <View style={styles.srCard}>
                <Text style={styles.cardTitle}>Support & Resistance</Text>
                <View style={styles.srGrid}>
                  <View style={styles.srSection}>
                    <Text style={[styles.srSectionTitle, { color: colors.loss }]}>Resistance</Text>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>R3</Text><Text style={styles.srLevelValue}>{formatCurrency(supportResistance.resistance?.r3)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>R2</Text><Text style={styles.srLevelValue}>{formatCurrency(supportResistance.resistance?.r2)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>R1</Text><Text style={styles.srLevelValue}>{formatCurrency(supportResistance.resistance?.r1)}</Text></View>
                  </View>
                  <View style={styles.srPivotCol}>
                    <Text style={styles.srPivotLabel}>Pivot</Text>
                    <Text style={styles.srPivotValue}>{formatCurrency(supportResistance.pivot)}</Text>
                  </View>
                  <View style={styles.srSection}>
                    <Text style={[styles.srSectionTitle, { color: colors.profit }]}>Support</Text>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>S1</Text><Text style={styles.srLevelValue}>{formatCurrency(supportResistance.support?.s1)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>S2</Text><Text style={styles.srLevelValue}>{formatCurrency(supportResistance.support?.s2)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>S3</Text><Text style={styles.srLevelValue}>{formatCurrency(supportResistance.support?.s3)}</Text></View>
                  </View>
                </View>
              </View>
            )}

            {/* Advanced Technicals (Fibonacci & Volume Profile) */}
            {fibLevels?.levels && (
              <View style={styles.srCard}>
                <Text style={styles.cardTitle}>Advanced Technicals</Text>
                {poc !== null && (
                  <View style={{ marginBottom: 16 }}>
                    <Text style={{ color: colors.textMuted, fontSize: 13, marginBottom: 4 }}>Volume Profile (POC)</Text>
                    <Text style={{ color: colors.accent, fontSize: 18, fontWeight: '700' }}>{formatCurrency(poc)}</Text>
                  </View>
                )}
                <View style={styles.srGrid}>
                  <View style={styles.srSection}>
                    <Text style={[styles.srSectionTitle, { color: colors.textSecondary }]}>Fibonacci Retracement</Text>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>0.0% (High)</Text><Text style={styles.srLevelValue}>{formatCurrency(fibLevels.levels.level_0)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>23.6%</Text><Text style={styles.srLevelValue}>{formatCurrency(fibLevels.levels.level_23_6)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>38.2%</Text><Text style={styles.srLevelValue}>{formatCurrency(fibLevels.levels.level_38_2)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>50.0%</Text><Text style={styles.srLevelValue}>{formatCurrency(fibLevels.levels.level_50_0)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>61.8%</Text><Text style={styles.srLevelValue}>{formatCurrency(fibLevels.levels.level_61_8)}</Text></View>
                    <View style={styles.srLevel}><Text style={styles.srLevelLabel}>100% (Low)</Text><Text style={styles.srLevelValue}>{formatCurrency(fibLevels.levels.level_100)}</Text></View>
                  </View>
                </View>
              </View>
            )}

            {/* Technical Indicators */}
            {technicals && (
              <View style={styles.techCard}>
                <Text style={styles.cardTitle}>Technical Indicators</Text>
                <View style={styles.techRow}>
                  <View style={styles.techLabel}><Text style={styles.techName}>RSI (14)</Text><Text style={styles.techValue}>{technicals.rsi}</Text></View>
                  <View style={[styles.techSignal, { backgroundColor: technicals.rsi_signal === 'Overbought' ? 'rgba(239,68,68,0.12)' : technicals.rsi_signal === 'Oversold' ? 'rgba(16,185,129,0.12)' : 'rgba(113,113,122,0.12)' }]}>
                    <Text style={[styles.techSignalText, { color: technicals.rsi_signal === 'Overbought' ? colors.loss : technicals.rsi_signal === 'Oversold' ? colors.profit : colors.neutral }]}>{technicals.rsi_signal}</Text>
                  </View>
                </View>
                <View style={styles.techRow}>
                  <View style={styles.techLabel}><Text style={styles.techName}>MACD</Text><Text style={styles.techValue}>H: {technicals.macd.histogram}</Text></View>
                  <View style={[styles.techSignal, { backgroundColor: technicals.macd.signal === 'Bullish' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
                    <Text style={[styles.techSignalText, { color: technicals.macd.signal === 'Bullish' ? colors.profit : colors.loss }]}>{technicals.macd.signal}</Text>
                  </View>
                </View>
                <View style={styles.techRow}>
                  <View style={styles.techLabel}><Text style={styles.techName}>SMA 20</Text><Text style={styles.techValue}>{formatCurrency(technicals.moving_averages.sma20)}</Text></View>
                  <View style={[styles.techSignal, { backgroundColor: technicals.price_vs_sma20 === 'Above' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
                    <Text style={[styles.techSignalText, { color: technicals.price_vs_sma20 === 'Above' ? colors.profit : colors.loss }]}>Price {technicals.price_vs_sma20}</Text>
                  </View>
                </View>
                <View style={styles.techRow}>
                  <View style={styles.techLabel}><Text style={styles.techName}>Bollinger</Text><Text style={styles.techValue}>{formatCurrency(technicals.bollinger_bands.lower)} – {formatCurrency(technicals.bollinger_bands.upper)}</Text></View>
                  <View style={[styles.techSignal, { backgroundColor: technicals.bollinger_bands.signal === 'Overbought' ? 'rgba(239,68,68,0.12)' : technicals.bollinger_bands.signal === 'Oversold' ? 'rgba(16,185,129,0.12)' : 'rgba(113,113,122,0.12)' }]}>
                    <Text style={[styles.techSignalText, { color: technicals.bollinger_bands.signal === 'Overbought' ? colors.loss : technicals.bollinger_bands.signal === 'Oversold' ? colors.profit : colors.neutral }]}>{technicals.bollinger_bands.signal}</Text>
                  </View>
                </View>
              </View>
            )}

            {/* AI Analysis Section */}
            <View style={styles.aiCard}>
              <View style={styles.aiHeader}>
                <View style={styles.aiTitleRow}>
                  <Ionicons name="sparkles" size={20} color={colors.aiGlow} />
                  <Text style={styles.aiTitle}>AI Analysis</Text>
                </View>
              </View>
              <View style={styles.aiTimeframeRow}>
                <TouchableOpacity style={[styles.tfBtn, aiTimeframe === 'short' && styles.tfBtnActive]} onPress={() => setAiTimeframe('short')} testID="ai-timeframe-short">
                  <Text style={[styles.tfBtnText, aiTimeframe === 'short' && styles.tfBtnTextActive]}>Short Term</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.tfBtn, aiTimeframe === 'long' && styles.tfBtnActive]} onPress={() => setAiTimeframe('long')} testID="ai-timeframe-long">
                  <Text style={[styles.tfBtnText, aiTimeframe === 'long' && styles.tfBtnTextActive]}>Long Term</Text>
                </TouchableOpacity>
              </View>
              <TouchableOpacity style={styles.analyzeBtn} onPress={runAI} disabled={aiLoading} testID="run-ai-analysis-btn" activeOpacity={0.8}>
                {aiLoading ? (
                  <View style={styles.aiLoadingRow}><ActivityIndicator color="#FFF" size="small" /><Text style={styles.analyzeBtnText}>Analyzing...</Text></View>
                ) : (
                  <View style={styles.aiLoadingRow}><Ionicons name="sparkles" size={18} color="#FFF" /><Text style={styles.analyzeBtnText}>Get AI Prediction</Text></View>
                )}
              </TouchableOpacity>
              {aiResult && (
                <View style={styles.aiResult}>
                  <View style={[styles.recBadge, { backgroundColor: recColor + '18', borderColor: recColor + '40' }]}>
                    <Ionicons name={aiResult.recommendation === 'BUY' ? 'arrow-up-circle' : aiResult.recommendation === 'SELL' ? 'arrow-down-circle' : 'pause-circle'} size={28} color={recColor} />
                    <View style={{ marginLeft: 12 }}>
                      <Text style={[styles.recText, { color: recColor }]}>{aiResult.recommendation}</Text>
                      <Text style={styles.recConfidence}>Confidence: {aiResult.confidence}%</Text>
                    </View>
                  </View>
                  {(aiResult as any).multi_timeframe_sentiment && (
                    <View style={{ marginBottom: 16 }}>
                      <Text style={styles.aiSectionTitle}>Timeframe Confluence</Text>
                      <View style={[styles.reasonRow, { alignItems: 'center' }]}>
                        <Ionicons name="shuffle" size={16} color={colors.accent} />
                        <Text style={[styles.reasonText, { fontWeight: '600' }]}>{(aiResult as any).multi_timeframe_sentiment}</Text>
                      </View>
                    </View>
                  )}
                  <View style={styles.targetRow}>
                    <View style={styles.targetCol}><Text style={styles.targetLabel}>Target Price</Text><Text style={[styles.targetValue, { color: colors.profit }]}>{formatCurrency(aiResult.target_price)}</Text></View>
                    <View style={styles.targetCol}><Text style={styles.targetLabel}>Stop Loss</Text><Text style={[styles.targetValue, { color: colors.loss }]}>{formatCurrency(aiResult.stop_loss)}</Text></View>
                  </View>
                  <Text style={styles.aiSummary}>{aiResult.summary}</Text>
                  <Text style={styles.aiSectionTitle}>Key Reasons</Text>
                  {(aiResult.key_reasons || []).map((r, i) => (
                    <View key={i} style={styles.reasonRow}><Ionicons name="checkmark-circle" size={16} color={colors.profit} /><Text style={styles.reasonText}>{r}</Text></View>
                  ))}
                  <Text style={styles.aiSectionTitle}>Risks</Text>
                  {(aiResult.risks || []).map((r, i) => (
                    <View key={i} style={styles.reasonRow}><Ionicons name="warning" size={16} color={colors.warning} /><Text style={styles.reasonText}>{r}</Text></View>
                  ))}
                </View>
              )}
            </View>
          </>
        )}

        {/* --- FUNDAMENTALS TAB --- */}
        {activeTab === 'fundamentals' && fundamentals && (
          <View>
            {[
              {
                label: 'Valuation', data: [
                  { k: 'PE Ratio', v: fundamentals.valuation?.pe_ratio },
                  { k: 'Forward PE', v: fundamentals.valuation?.forward_pe },
                  { k: 'PB Ratio', v: fundamentals.valuation?.pb_ratio },
                  { k: 'EV/EBITDA', v: fundamentals.valuation?.ev_ebitda },
                ]
              },
              {
                label: 'Profitability', data: [
                  { k: 'ROE', v: fundamentals.profitability?.roe != null ? `${fundamentals.profitability.roe}%` : null },
                  { k: 'ROA', v: fundamentals.profitability?.roa != null ? `${fundamentals.profitability.roa}%` : null },
                  { k: 'Net Margin', v: fundamentals.profitability?.profit_margin != null ? `${fundamentals.profitability.profit_margin}%` : null },
                  { k: 'Gross Margin', v: fundamentals.profitability?.gross_margin != null ? `${fundamentals.profitability.gross_margin}%` : null },
                ]
              },
              {
                label: 'Growth', data: [
                  { k: 'Revenue Growth', v: fundamentals.growth?.revenue_growth != null ? `${fundamentals.growth.revenue_growth}%` : null },
                  { k: 'Earnings Growth', v: fundamentals.growth?.earnings_growth != null ? `${fundamentals.growth.earnings_growth}%` : null },
                  { k: 'EPS (TTM)', v: fundamentals.growth?.eps },
                  { k: 'Forward EPS', v: fundamentals.growth?.forward_eps },
                ]
              },
              {
                label: 'Financial Health', data: [
                  { k: 'Debt/Equity', v: fundamentals.financial_health?.debt_to_equity },
                  { k: 'Current Ratio', v: fundamentals.financial_health?.current_ratio },
                  { k: 'Free Cash Flow', v: formatLargeNumber(fundamentals.financial_health?.free_cash_flow) },
                ]
              },
              {
                label: 'Dividends', data: [
                  { k: 'Dividend Yield', v: fundamentals.dividends?.dividend_yield != null ? `${fundamentals.dividends.dividend_yield}%` : null },
                  { k: 'Payout Ratio', v: fundamentals.dividends?.payout_ratio != null ? `${fundamentals.dividends.payout_ratio}%` : null },
                ]
              },
            ].map(section => (
              <View key={section.label} style={styles.fundCard}>
                <Text style={styles.cardTitle}>{section.label}</Text>
                <View style={styles.statsGrid}>
                  {section.data.map(item => item.v != null && (
                    <StatItem key={item.k} label={item.k} value={String(item.v)} />
                  ))}
                </View>
              </View>
            ))}
            
            {/* Earnings Calendar Section */}
            {earnings && (earnings.upcoming?.length > 0 || earnings.historical?.length > 0) && (
              <View style={styles.fundCard}>
                <Text style={styles.cardTitle}>Earnings Calendar</Text>
                
                {earnings.upcoming?.length > 0 && (
                  <View style={{ marginBottom: 16 }}>
                    <Text style={[styles.aiSectionTitle, { color: colors.accent, marginTop: 0 }]}>Upcoming Date</Text>
                    {earnings.upcoming.slice(0, 1).map((e: any, i: number) => (
                      <View key={i} style={styles.reasonRow}>
                        <Ionicons name="calendar-outline" size={16} color={colors.accent} />
                        <Text style={[styles.reasonText, { fontWeight: '700', color: colors.text }]}>{e.date?.split(' ')[0] || 'TBD'}</Text>
                      </View>
                    ))}
                  </View>
                )}
                
                {earnings.historical?.length > 0 && (
                  <View>
                    <Text style={[styles.aiSectionTitle, { marginTop: 0 }]}>Recent Earnings</Text>
                    {earnings.historical.slice(0, 3).map((e: any, i: number) => (
                      <View key={i} style={[styles.techRow, { borderBottomWidth: i === 2 ? 0 : 1 }]}>
                        <View>
                          <Text style={[styles.techName, { fontWeight: '600' }]}>{e.date?.split(' ')[0] || 'N/A'}</Text>
                          <Text style={{ fontSize: 11, color: colors.textMuted, marginTop: 2 }}>Est: {e.eps_estimate || '-'} | Act: {e.eps_actual || '-'}</Text>
                        </View>
                        {e.surprise_pct != null && (
                          <View style={[styles.techSignal, { backgroundColor: e.surprise_pct >= 0 ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
                            <Text style={[styles.techSignalText, { color: e.surprise_pct >= 0 ? colors.profit : colors.loss }]}>
                              {e.surprise_pct >= 0 ? '+' : ''}{e.surprise_pct}%
                            </Text>
                          </View>
                        )}
                      </View>
                    ))}
                  </View>
                )}
              </View>
            )}
            
          </View>
        )}
        {activeTab === 'fundamentals' && !fundamentals && (
          <View style={styles.emptyTab}><ActivityIndicator color={colors.primary} /><Text style={styles.emptyTabText}>Loading fundamentals...</Text></View>
        )}

        {/* --- NEWS TAB --- */}
        {activeTab === 'news' && (
          <View>
            {stockNews.length === 0 ? (
              <View style={styles.emptyTab}><Ionicons name="newspaper-outline" size={36} color={colors.textMuted} /><Text style={styles.emptyTabText}>No news found</Text></View>
            ) : (
              stockNews.map((article, i) => <NewsCard key={i} article={article} />)
            )}
          </View>
        )}

        {/* --- F&O TAB --- */}
        {activeTab === 'fno' && (
          <View style={styles.fundCard}>
            <Text style={styles.cardTitle}>Options Chain</Text>
            {optionChain ? (
              <OptionChainTable
                symbol={decodedSymbol}
                chain={optionChain.chain || []}
                underlying_price={optionChain.underlying_price || 0}
                max_pain={optionChain.max_pain}
                oi_analysis={optionChain.oi_analysis}
                expiry_dates={optionChain.expiry_dates || []}
                selected_expiry={selectedExpiry}
                onSelectExpiry={(exp) => {
                  setSelectedExpiry(exp);
                  api.getOptionChain(decodedSymbol, exp)
                    .then(res => setOptionChain(res)).catch(() => { });
                }}
                loading={false}
              />
            ) : (
              <View style={styles.emptyTab}>
                <ActivityIndicator color={colors.primary} />
                <Text style={styles.emptyTabText}>Loading option chain...</Text>
              </View>
            )}
          </View>
        )}

        <SEBIDisclaimerBanner />
      </ScrollView>
    </SafeAreaView>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.statItem}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: colors.textMuted, marginTop: 12, fontSize: 14 },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 100 },
  header: { flexDirection: 'row', alignItems: 'center', marginTop: 8, marginBottom: 16, gap: 12 },
  backBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: colors.card, alignItems: 'center', justifyContent: 'center' },
  stockSymbol: { color: colors.text, fontSize: 22, fontWeight: '800' },
  stockName: { color: colors.textMuted, fontSize: 13 },
  watchlistBtn: { width: 44, height: 44, borderRadius: 12, backgroundColor: colors.card, alignItems: 'center', justifyContent: 'center' },
  priceSection: { marginBottom: 20 },
  price: { color: colors.text, fontSize: 36, fontWeight: '800', fontVariant: ['tabular-nums'] },
  changeBadge: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, marginTop: 8, gap: 6 },
  changeText: { fontSize: 14, fontWeight: '700', fontVariant: ['tabular-nums'] },
  chartCard: { backgroundColor: colors.card, borderRadius: 20, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  periodRow: { flexDirection: 'row', gap: 6, marginBottom: 16 },
  periodBtn: { flex: 1, paddingVertical: 8, borderRadius: 10, alignItems: 'center', backgroundColor: 'rgba(39,39,42,0.3)' },
  periodBtnActive: { backgroundColor: colors.primary },
  periodText: { color: colors.textMuted, fontSize: 12, fontWeight: '600' },
  periodTextActive: { color: '#FFF' },
  chartWrap: { alignItems: 'center', overflow: 'hidden' },
  noChart: { height: 180, alignItems: 'center', justifyContent: 'center' },
  noChartText: { color: colors.textMuted },
  statsCard: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  cardTitle: { color: colors.text, fontSize: 17, fontWeight: '700', marginBottom: 16 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  statItem: { width: '50%', marginBottom: 14 },
  statLabel: { color: colors.textMuted, fontSize: 12 },
  statValue: { color: colors.text, fontSize: 14, fontWeight: '600', fontVariant: ['tabular-nums'], marginTop: 2 },
  techCard: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  techRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.3)' },
  techLabel: {},
  techName: { color: colors.textSecondary, fontSize: 13 },
  techValue: { color: colors.text, fontSize: 15, fontWeight: '600', fontVariant: ['tabular-nums'], marginTop: 2 },
  techSignal: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 12 },
  techSignalText: { fontSize: 12, fontWeight: '700' },
  aiCard: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(124,58,237,0.15)' },
  aiHeader: { marginBottom: 16 },
  aiTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  aiTitle: { color: colors.text, fontSize: 18, fontWeight: '700' },
  aiSubtitle: { color: colors.textMuted, fontSize: 12, marginTop: 4 },
  aiTimeframeRow: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  tfBtn: { flex: 1, paddingVertical: 12, borderRadius: 12, alignItems: 'center', backgroundColor: 'rgba(39,39,42,0.3)', borderWidth: 1, borderColor: 'transparent' },
  tfBtnActive: { backgroundColor: 'rgba(124,58,237,0.12)', borderColor: 'rgba(124,58,237,0.3)' },
  tfBtnText: { color: colors.textMuted, fontSize: 14, fontWeight: '600' },
  tfBtnTextActive: { color: colors.accent },
  analyzeBtn: { backgroundColor: colors.primary, borderRadius: 30, paddingVertical: 16, alignItems: 'center', shadowColor: colors.primary, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 8 },
  analyzeBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  aiLoadingRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  aiResult: { marginTop: 20 },
  recBadge: { flexDirection: 'row', alignItems: 'center', padding: 16, borderRadius: 16, borderWidth: 1, marginBottom: 16 },
  recText: { fontSize: 22, fontWeight: '800' },
  recConfidence: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  sentimentBadge: { marginLeft: 'auto', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 12 },
  sentimentText: { fontSize: 12, fontWeight: '700' },
  targetRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  targetCol: { flex: 1, backgroundColor: 'rgba(39,39,42,0.3)', borderRadius: 14, padding: 14 },
  targetLabel: { color: colors.textMuted, fontSize: 12 },
  targetValue: { fontSize: 18, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 4 },
  aiSummary: { color: colors.textSecondary, fontSize: 14, lineHeight: 22, marginBottom: 16 },
  aiSectionTitle: { color: colors.text, fontSize: 15, fontWeight: '700', marginBottom: 10, marginTop: 8 },
  reasonRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 8 },
  reasonText: { color: colors.textSecondary, fontSize: 13, lineHeight: 20, flex: 1 },
  techOutlook: { backgroundColor: 'rgba(39,39,42,0.3)', borderRadius: 14, padding: 14, marginTop: 12 },
  techOutlookLabel: { color: colors.textMuted, fontSize: 12, marginBottom: 4 },
  techOutlookText: { color: colors.textSecondary, fontSize: 13, lineHeight: 20 },
  disclaimer: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: 16, padding: 12, backgroundColor: 'rgba(39,39,42,0.2)', borderRadius: 10 },
  disclaimerText: { color: colors.textMuted, fontSize: 11, lineHeight: 16, flex: 1 },
  srCard: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  srGrid: { flexDirection: 'row', gap: 12 },
  srSection: { flex: 1 },
  srSectionTitle: { fontSize: 14, fontWeight: '700', marginBottom: 10 },
  srLevel: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.3)' },
  srLevelLabel: { color: colors.textMuted, fontSize: 12, fontWeight: '600' },
  srLevelValue: { color: colors.text, fontSize: 13, fontWeight: '600', fontVariant: ['tabular-nums'] },
  srPivotCol: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 },
  srPivotLabel: { color: colors.textMuted, fontSize: 11 },
  srPivotValue: { color: colors.accent, fontSize: 16, fontWeight: '800', fontVariant: ['tabular-nums'], marginTop: 4 },
  periodHLGrid: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 16, gap: 8 },
  periodHLItem: { width: '30%', backgroundColor: 'rgba(39,39,42,0.3)', borderRadius: 10, padding: 10 },
  periodHLLabel: { color: colors.textMuted, fontSize: 11 },
  periodHLValue: { fontSize: 13, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 3 },
  fundCard: { backgroundColor: colors.card, borderRadius: 20, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
  emptyTab: { alignItems: 'center', paddingVertical: 40 },
  emptyTabText: { color: colors.textMuted, marginTop: 12, fontSize: 14 },
  tabRow: { marginBottom: 16 },
  tab: { paddingHorizontal: 16, paddingVertical: 8, marginRight: 8, borderRadius: 20, backgroundColor: 'rgba(39,39,42,0.4)', borderWidth: 1, borderColor: 'transparent' },
  tabActive: { backgroundColor: 'rgba(124,58,237,0.12)', borderColor: 'rgba(124,58,237,0.4)' },
  tabText: { color: colors.textMuted, fontSize: 13, fontWeight: '600' },
  tabTextActive: { color: colors.accent, fontWeight: '700' },
});
