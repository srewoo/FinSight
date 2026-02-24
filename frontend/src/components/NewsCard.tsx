import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Linking } from 'react-native';
import { colors } from '../theme';

interface NewsArticle {
    title: string;
    link: string;
    source: string;
    published: string;
    summary?: string;
}

interface Props {
    article: NewsArticle;
}

const NewsCard: React.FC<Props> = ({ article }) => {
    const openLink = async () => {
        try {
            // expo-web-browser preferred if available, fallback to Linking
            try {
                const { openBrowserAsync } = await import('expo-web-browser');
                await openBrowserAsync(article.link);
            } catch {
                Linking.openURL(article.link);
            }
        } catch { /* ignore */ }
    };

    return (
        <TouchableOpacity style={styles.card} onPress={openLink} activeOpacity={0.7}>
            <Text style={styles.title} numberOfLines={2}>{article.title}</Text>
            <View style={styles.meta}>
                <Text style={styles.source}>{article.source}</Text>
                {article.published ? (
                    <>
                        <Text style={styles.dot}>·</Text>
                        <Text style={styles.time}>{article.published}</Text>
                    </>
                ) : null}
            </View>
            {article.summary ? (
                <Text style={styles.summary} numberOfLines={1}>{article.summary}</Text>
            ) : null}
        </TouchableOpacity>
    );
};

const styles = StyleSheet.create({
    card: {
        backgroundColor: colors.card,
        borderRadius: 14,
        padding: 14,
        marginBottom: 10,
        borderWidth: 1,
        borderColor: 'rgba(39,39,42,0.4)',
    },
    title: {
        color: colors.text,
        fontSize: 14,
        fontWeight: '600',
        lineHeight: 20,
    },
    meta: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 6,
        gap: 4,
    },
    source: {
        color: colors.primary,
        fontSize: 11,
        fontWeight: '600',
    },
    dot: {
        color: colors.textMuted,
        fontSize: 11,
    },
    time: {
        color: colors.textMuted,
        fontSize: 11,
    },
    summary: {
        color: colors.textMuted,
        fontSize: 12,
        marginTop: 6,
        lineHeight: 18,
    },
});

export default NewsCard;
