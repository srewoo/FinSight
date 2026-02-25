/**
 * News & Sentiment Screen
 * Displays market news with sentiment analysis.
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Linking,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../src/api';
import { useTheme } from '../src/theme';

interface NewsArticle {
  title: string;
  source: string;
  published: string;
  link: string;
  summary: string;
  sentiment_score: number;
  sentiment_label: string;
  relevance_symbols: string[];
}

interface SentimentSummary {
  overall_sentiment: string;
  overall_score: number;
  articles_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  latest_news: NewsArticle[];
}

export default function NewsScreen() {
  const theme = useTheme();
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadNews = async () => {
    try {
      const [newsData, sentimentData] = await Promise.all([
        api.getMarketNews(50),
        api.getSentimentSummary(),
      ]);
      setNews(newsData.news || []);
      setSentiment(sentimentData);
    } catch (err: any) {
      console.error('Failed to load news:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadNews();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadNews();
  };

  const openLink = (url: string) => {
    Linking.openURL(url);
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.2) return theme.success;
    if (score < -0.2) return theme.danger;
    return theme.warning;
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.2) return 'trending-up';
    if (score < -0.2) return 'trending-down';
    return 'remove';
  };

  const renderSentimentCard = () => {
    if (!sentiment) return null;

    return (
      <View style={[styles.sentimentCard, { backgroundColor: theme.cardBg, borderColor: theme.border }]}>
        <Text style={[styles.sentimentTitle, { color: theme.text }]}>Market Sentiment</Text>
        
        <View style={styles.sentimentBody}>
          <View style={[
            styles.sentimentBadge,
            { backgroundColor: getSentimentColor(sentiment.overall_score) },
          ]}>
            <Ionicons
              name={getSentimentIcon(sentiment.overall_score)}
              size={24}
              color="#fff"
            />
            <Text style={styles.sentimentBadgeText}>
              {sentiment.overall_sentiment.toUpperCase()}
            </Text>
          </View>

          <Text style={[styles.sentimentScore, { color: theme.text }]}>
            Score: {sentiment.overall_score.toFixed(2)}
          </Text>
        </View>

        <View style={styles.sentimentStats}>
          <View style={styles.statItem}>
            <View style={[styles.statDot, { backgroundColor: theme.success }]} />
            <Text style={[styles.statCount, { color: theme.text }]}>
              {sentiment.positive_count}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textMuted }]}>Positive</Text>
          </View>

          <View style={styles.statItem}>
            <View style={[styles.statDot, { backgroundColor: theme.warning }]} />
            <Text style={[styles.statCount, { color: theme.text }]}>
              {sentiment.neutral_count}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textMuted }]}>Neutral</Text>
          </View>

          <View style={styles.statItem}>
            <View style={[styles.statDot, { backgroundColor: theme.danger }]} />
            <Text style={[styles.statCount, { color: theme.text }]}>
              {sentiment.negative_count}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textMuted }]}>Negative</Text>
          </View>
        </View>
      </View>
    );
  };

  const renderNewsItem = ({ item }: { item: NewsArticle }) => (
    <TouchableOpacity
      style={[styles.newsCard, { backgroundColor: theme.cardBg, borderColor: theme.border }]}
      onPress={() => openLink(item.link)}
      activeOpacity={0.7}
    >
      <View style={styles.newsHeader}>
        <View style={styles.newsSource}>
          <Text style={[styles.sourceText, { color: theme.primary }]}>{item.source}</Text>
          <Text style={[styles.timeText, { color: theme.textMuted }]}>
            {new Date(item.published).toLocaleString()}
          </Text>
        </View>

        <View style={[
          styles.sentimentIndicator,
          { backgroundColor: getSentimentColor(item.sentiment_score) },
        ]}>
          <Ionicons
            name={getSentimentIcon(item.sentiment_score)}
            size={16}
            color="#fff"
          />
        </View>
      </View>

      <Text style={[styles.newsTitle, { color: theme.text }]} numberOfLines={3}>
        {item.title}
      </Text>

      {item.summary ? (
        <Text style={[styles.newsSummary, { color: theme.textMuted }]} numberOfLines={3}>
          {item.summary}
        </Text>
      ) : null}

      {item.relevance_symbols && item.relevance_symbols.length > 0 && (
        <View style={styles.symbolsRow}>
          {item.relevance_symbols.slice(0, 5).map((sym, index) => (
            <View key={index} style={[styles.symbolBadge, { backgroundColor: theme.badgeBg }]}>
              <Text style={[styles.symbolText, { color: theme.primary }]}>{sym}</Text>
            </View>
          ))}
        </View>
      )}

      <View style={styles.readMoreRow}>
        <Text style={[styles.readMore, { color: theme.primary }]}>Read more →</Text>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.bg }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textMuted }]}>Loading news...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.bg }]}>
      <View style={styles.header}>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Market News</Text>
        <TouchableOpacity onPress={onRefresh}>
          <Ionicons name="refresh" size={24} color={theme.text} />
        </TouchableOpacity>
      </View>

      <FlatList
        data={news}
        renderItem={renderNewsItem}
        keyExtractor={(item, index) => `${item.link}-${index}`}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
        }
        ListHeaderComponent={renderSentimentCard()}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="newspaper-outline" size={48} color={theme.textMuted} />
            <Text style={[styles.emptyText, { color: theme.textMuted }]}>No news available</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = {
  container: {
    flex: 1,
  } as any,
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  } as any,
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
  } as any,
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  } as any,
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  } as any,
  listContent: {
    padding: 16,
  } as any,
  sentimentCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    marginBottom: 20,
  } as any,
  sentimentTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  } as any,
  sentimentBody: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    marginBottom: 16,
  } as any,
  sentimentBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  } as any,
  sentimentBadgeText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  } as any,
  sentimentScore: {
    fontSize: 16,
    fontWeight: '500',
  } as any,
  sentimentStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 16,
    borderTopWidth: 1,
  } as any,
  statItem: {
    alignItems: 'center',
  } as any,
  statDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginBottom: 8,
  } as any,
  statCount: {
    fontSize: 20,
    fontWeight: 'bold',
  } as any,
  statLabel: {
    fontSize: 12,
    marginTop: 4,
  } as any,
  newsCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  } as any,
  newsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  } as any,
  newsSource: {
    flex: 1,
  } as any,
  sourceText: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  } as any,
  timeText: {
    fontSize: 12,
  } as any,
  sentimentIndicator: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  } as any,
  newsTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
    lineHeight: 22,
  } as any,
  newsSummary: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  } as any,
  symbolsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  } as any,
  symbolBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  } as any,
  symbolText: {
    fontSize: 12,
    fontWeight: '600',
  } as any,
  readMoreRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  } as any,
  readMore: {
    fontSize: 14,
    fontWeight: '600',
  } as any,
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
  } as any,
  emptyText: {
    fontSize: 16,
    marginTop: 16,
  } as any,
};
