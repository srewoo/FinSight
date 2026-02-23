import React, { useState, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, ScrollView, Image, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { api } from '../../src/api';
import { colors } from '../../src/theme';

interface ChartAnalysis {
  prediction: string; confidence: number; trend: string; patterns_identified: string[];
  support_levels: string[]; resistance_levels: string[];
  summary: string; recommendation: string; key_observations: string[];
}

export default function ScanScreen() {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<ChartAnalysis | null>(null);

  const pickImage = async (useCamera: boolean) => {
    try {
      let permResult;
      if (useCamera) {
        permResult = await ImagePicker.requestCameraPermissionsAsync();
      } else {
        permResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
      }

      if (!permResult.granted) {
        return;
      }

      const pickerResult = useCamera
        ? await ImagePicker.launchCameraAsync({
            base64: true,
            quality: 0.7,
            allowsEditing: true,
          })
        : await ImagePicker.launchImageLibraryAsync({
            base64: true,
            quality: 0.7,
            allowsEditing: true,
            mediaTypes: ['images'],
          });

      if (!pickerResult.canceled && pickerResult.assets[0]) {
        const asset = pickerResult.assets[0];
        setImageUri(asset.uri);
        setImageBase64(asset.base64 || null);
        setResult(null);
      }
    } catch (e) {
      console.error('Image pick error:', e);
    }
  };

  const analyzeChart = async () => {
    if (!imageBase64) return;
    setAnalyzing(true);
    setResult(null);
    try {
      const data = await api.analyzeChartImage(imageBase64);
      setResult(data.analysis);
    } catch (e) {
      console.error('Analysis error:', e);
    } finally {
      setAnalyzing(false);
    }
  };

  const predColor = result?.prediction === 'UP' ? colors.profit
    : result?.prediction === 'DOWN' ? colors.loss : colors.warning;
  const recColor = result?.recommendation === 'BUY' ? colors.profit
    : result?.recommendation === 'SELL' ? colors.loss : colors.warning;

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>Chart Scanner</Text>
          <View style={styles.aiBadge}>
            <Ionicons name="sparkles" size={13} color={colors.primary} />
            <Text style={styles.aiBadgeText}>Vision AI</Text>
          </View>
        </View>
        <Text style={styles.subtitle}>
          Capture or upload a candlestick chart. AI will analyze patterns and predict stock movement.
        </Text>

        {/* Image Preview or Placeholder */}
        {imageUri ? (
          <View style={styles.imageContainer}>
            <Image source={{ uri: imageUri }} style={styles.chartImage} resizeMode="contain" />
            <TouchableOpacity style={styles.removeImageBtn} onPress={() => { setImageUri(null); setImageBase64(null); setResult(null); }} testID="remove-image-btn">
              <Ionicons name="close-circle" size={28} color={colors.loss} />
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.placeholder}>
            <Ionicons name="bar-chart-outline" size={56} color={colors.textMuted} />
            <Text style={styles.placeholderTitle}>No Chart Selected</Text>
            <Text style={styles.placeholderDesc}>Take a photo of any candlestick chart or pick from gallery</Text>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actionsRow}>
          <TouchableOpacity style={styles.cameraBtn} onPress={() => pickImage(true)} testID="camera-capture-btn">
            <Ionicons name="camera" size={22} color="#FFF" />
            <Text style={styles.actionBtnText}>Camera</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.galleryBtn} onPress={() => pickImage(false)} testID="gallery-pick-btn">
            <Ionicons name="images" size={22} color="#FFF" />
            <Text style={styles.actionBtnText}>Gallery</Text>
          </TouchableOpacity>
        </View>

        {/* Analyze Button */}
        {imageBase64 && (
          <TouchableOpacity style={styles.analyzeBtn} onPress={analyzeChart} disabled={analyzing} testID="analyze-chart-btn" activeOpacity={0.8}>
            {analyzing ? (
              <View style={styles.analyzeBtnInner}>
                <ActivityIndicator color="#FFF" size="small" />
                <Text style={styles.analyzeBtnText}>Analyzing Chart Patterns...</Text>
              </View>
            ) : (
              <View style={styles.analyzeBtnInner}>
                <Ionicons name="sparkles" size={20} color="#FFF" />
                <Text style={styles.analyzeBtnText}>Analyze with AI</Text>
              </View>
            )}
          </TouchableOpacity>
        )}

        {/* AI Result */}
        {result && (
          <View style={styles.resultCard}>
            {/* Prediction */}
            <View style={[styles.predictionBadge, { backgroundColor: predColor + '18', borderColor: predColor + '40' }]}>
              <Ionicons
                name={result.prediction === 'UP' ? 'arrow-up-circle' : result.prediction === 'DOWN' ? 'arrow-down-circle' : 'swap-horizontal'}
                size={32} color={predColor}
              />
              <View style={{ marginLeft: 14, flex: 1 }}>
                <Text style={styles.predLabel}>Prediction</Text>
                <Text style={[styles.predValue, { color: predColor }]}>Stock will go {result.prediction}</Text>
              </View>
              <View style={[styles.confBadge, { backgroundColor: predColor + '18' }]}>
                <Text style={[styles.confBadgeText, { color: predColor }]}>{result.confidence}%</Text>
              </View>
            </View>

            {/* Recommendation + Trend */}
            <View style={styles.metaRow}>
              <View style={[styles.metaCard, { borderColor: recColor + '30' }]}>
                <Text style={styles.metaLabel}>Recommendation</Text>
                <Text style={[styles.metaValue, { color: recColor }]}>{result.recommendation}</Text>
              </View>
              <View style={styles.metaCard}>
                <Text style={styles.metaLabel}>Trend</Text>
                <Text style={styles.metaValue}>{result.trend}</Text>
              </View>
            </View>

            {/* Summary */}
            <Text style={styles.resultSummary}>{result.summary}</Text>

            {/* Patterns */}
            {result.patterns_identified && result.patterns_identified.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Patterns Identified</Text>
                <View style={styles.patternRow}>
                  {result.patterns_identified.map((p, i) => (
                    <View key={i} style={styles.patternChip}>
                      <Text style={styles.patternText}>{p}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Support / Resistance */}
            <View style={styles.srSection}>
              {result.support_levels && result.support_levels.length > 0 && (
                <View style={styles.srCol}>
                  <Text style={[styles.srTitle, { color: colors.profit }]}>Support Levels</Text>
                  {result.support_levels.map((l, i) => (
                    <Text key={i} style={styles.srLevel}>{l}</Text>
                  ))}
                </View>
              )}
              {result.resistance_levels && result.resistance_levels.length > 0 && (
                <View style={styles.srCol}>
                  <Text style={[styles.srTitle, { color: colors.loss }]}>Resistance Levels</Text>
                  {result.resistance_levels.map((l, i) => (
                    <Text key={i} style={styles.srLevel}>{l}</Text>
                  ))}
                </View>
              )}
            </View>

            {/* Key Observations */}
            {result.key_observations && result.key_observations.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Key Observations</Text>
                {result.key_observations.map((obs, i) => (
                  <View key={i} style={styles.obsRow}>
                    <Ionicons name="eye" size={14} color={colors.accent} />
                    <Text style={styles.obsText}>{obs}</Text>
                  </View>
                ))}
              </View>
            )}

            <View style={styles.disclaimer}>
              <Ionicons name="information-circle" size={14} color={colors.textMuted} />
              <Text style={styles.disclaimerText}>
                Chart analysis is based on visual pattern recognition. Results may vary. Not financial advice.
              </Text>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 100 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 4 },
  title: { color: colors.text, fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
  aiBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(124,58,237,0.12)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(124,58,237,0.2)', gap: 5 },
  aiBadgeText: { color: colors.accent, fontSize: 12, fontWeight: '600' },
  subtitle: { color: colors.textMuted, fontSize: 14, lineHeight: 20, marginBottom: 20 },
  imageContainer: { borderRadius: 20, overflow: 'hidden', backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, marginBottom: 16 },
  chartImage: { width: '100%', height: 250 },
  removeImageBtn: { position: 'absolute', top: 10, right: 10 },
  placeholder: { backgroundColor: colors.card, borderRadius: 20, borderWidth: 1, borderColor: colors.border, borderStyle: 'dashed', padding: 40, alignItems: 'center', marginBottom: 16 },
  placeholderTitle: { color: colors.text, fontSize: 16, fontWeight: '700', marginTop: 12 },
  placeholderDesc: { color: colors.textMuted, fontSize: 13, textAlign: 'center', marginTop: 6, lineHeight: 19 },
  actionsRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  cameraBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: colors.card, borderRadius: 14, paddingVertical: 16, gap: 8, borderWidth: 1, borderColor: colors.border },
  galleryBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: colors.card, borderRadius: 14, paddingVertical: 16, gap: 8, borderWidth: 1, borderColor: colors.border },
  actionBtnText: { color: colors.text, fontSize: 15, fontWeight: '600' },
  analyzeBtn: { backgroundColor: colors.primary, borderRadius: 30, paddingVertical: 16, alignItems: 'center', marginBottom: 16 },
  analyzeBtnInner: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  analyzeBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  resultCard: { backgroundColor: colors.card, borderRadius: 20, padding: 20, borderWidth: 1, borderColor: 'rgba(124,58,237,0.15)' },
  predictionBadge: { flexDirection: 'row', alignItems: 'center', padding: 16, borderRadius: 16, borderWidth: 1, marginBottom: 16 },
  predLabel: { color: colors.textMuted, fontSize: 12 },
  predValue: { fontSize: 20, fontWeight: '800', marginTop: 2 },
  confBadge: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 14 },
  confBadgeText: { fontSize: 18, fontWeight: '800' },
  metaRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  metaCard: { flex: 1, backgroundColor: 'rgba(39,39,42,0.3)', borderRadius: 14, padding: 14, borderWidth: 1, borderColor: 'rgba(39,39,42,0.3)' },
  metaLabel: { color: colors.textMuted, fontSize: 12 },
  metaValue: { color: colors.text, fontSize: 16, fontWeight: '700', marginTop: 4 },
  resultSummary: { color: colors.textSecondary, fontSize: 14, lineHeight: 22, marginBottom: 16 },
  section: { marginBottom: 16 },
  sectionTitle: { color: colors.text, fontSize: 15, fontWeight: '700', marginBottom: 10 },
  patternRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  patternChip: { backgroundColor: 'rgba(124,58,237,0.12)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(124,58,237,0.2)' },
  patternText: { color: colors.accent, fontSize: 12, fontWeight: '600' },
  srSection: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  srCol: { flex: 1 },
  srTitle: { fontSize: 13, fontWeight: '700', marginBottom: 6 },
  srLevel: { color: colors.textSecondary, fontSize: 13, fontVariant: ['tabular-nums'], marginBottom: 3 },
  obsRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 8 },
  obsText: { color: colors.textSecondary, fontSize: 13, lineHeight: 20, flex: 1 },
  disclaimer: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: 8, padding: 12, backgroundColor: 'rgba(39,39,42,0.2)', borderRadius: 10 },
  disclaimerText: { color: colors.textMuted, fontSize: 11, lineHeight: 16, flex: 1 },
});
