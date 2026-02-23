import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, shared } from '../../src/theme';
import { api } from '../../src/api';

const PROVIDERS = [
  {
    id: 'openai',
    label: 'OpenAI',
    icon: '🔮',
    accent: '#10A37F',
    models: [
      { id: 'gpt-5.2', label: 'GPT-5.2', badge: 'Latest' },
    ],
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    icon: '✨',
    accent: '#4285F4',
    models: [
      { id: 'gemini-3.0', label: 'Gemini 3.0', badge: 'Latest' },
    ],
  },
  {
    id: 'claude',
    label: 'Anthropic Claude',
    icon: '🧠',
    accent: '#D97706',
    models: [
      { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6', badge: 'Balanced' },
      { id: 'claude-opus-4-5', label: 'Claude Opus 4.5', badge: 'Most Capable' },
    ],
  },
];

export default function SettingsScreen() {
  const [selectedProvider, setSelectedProvider] = useState<string>('openai');
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4o');
  const [apiKey, setApiKey] = useState<string>('');
  const [showKey, setShowKey] = useState(false);
  const [apiKeySet, setApiKeySet] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getSettings();
      if (data.provider) {
        setSelectedProvider(data.provider);
        setSelectedModel(data.model);
        setApiKeySet(data.api_key_set);
      }
    } catch (e) {
      // no settings yet, defaults are fine
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const currentProvider = PROVIDERS.find(p => p.id === selectedProvider)!;
  const currentModels = currentProvider?.models ?? [];

  const handleProviderChange = (id: string) => {
    setSelectedProvider(id);
    const prov = PROVIDERS.find(p => p.id === id)!;
    setSelectedModel(prov.models[0].id);
    setTestResult(null);
  };

  const handleSave = async () => {
    if (!apiKey.trim() && !apiKeySet) {
      Alert.alert('Missing API Key', 'Please enter your API key to save settings.');
      return;
    }
    setSaving(true);
    setTestResult(null);
    try {
      await api.saveSettings({ provider: selectedProvider, model: selectedModel, api_key: apiKey.trim() || '***keep***' });
      setApiKeySet(true);
      setApiKey('');
      Alert.alert('✅ Saved', `${currentProvider.label} · ${selectedModel} is now active.`);
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!apiKeySet && !apiKey.trim()) {
      Alert.alert('No API Key', 'Save your settings first.');
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testConnection();
      setTestResult({ success: true, message: `✅ Connected to ${res.provider} · ${res.model}` });
    } catch (e: any) {
      const msg = e?.message ?? 'Connection failed.';
      setTestResult({ success: false, message: `❌ ${msg}` });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={shared.screen}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={shared.screen}>
      <ScrollView contentContainerStyle={shared.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <LinearGradient colors={['#7C3AED22', '#00000000']} style={styles.headerGlow} />
          <Text style={styles.headerTitle}>AI Settings</Text>
          <Text style={styles.headerSubtitle}>Configure your LLM provider for AI-powered analysis</Text>
          {apiKeySet && (
            <View style={styles.activeBadge}>
              <Ionicons name="checkmark-circle" size={14} color={colors.profit} />
              <Text style={styles.activeBadgeText}>{currentProvider.label} · {selectedModel} active</Text>
            </View>
          )}
        </View>

        {/* Provider Selection */}
        <Text style={styles.sectionLabel}>LLM Provider</Text>
        <View style={styles.providerRow}>
          {PROVIDERS.map(p => {
            const active = selectedProvider === p.id;
            return (
              <TouchableOpacity
                key={p.id}
                style={[styles.providerCard, active && { borderColor: p.accent, backgroundColor: `${p.accent}18` }]}
                onPress={() => handleProviderChange(p.id)}
                activeOpacity={0.75}
              >
                <Text style={styles.providerIcon}>{p.icon}</Text>
                <Text style={[styles.providerLabel, active && { color: p.accent }]}>{p.label}</Text>
                {active && <Ionicons name="checkmark-circle" size={14} color={p.accent} style={{ marginTop: 4 }} />}
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Model Selection */}
        <Text style={styles.sectionLabel}>Model</Text>
        <View style={styles.modelList}>
          {currentModels.map(m => {
            const active = selectedModel === m.id;
            return (
              <TouchableOpacity
                key={m.id}
                style={[styles.modelRow, active && { borderColor: currentProvider.accent, backgroundColor: `${currentProvider.accent}12` }]}
                onPress={() => { setSelectedModel(m.id); setTestResult(null); }}
                activeOpacity={0.75}
              >
                <View style={{ flex: 1 }}>
                  <Text style={[styles.modelName, active && { color: colors.text }]}>{m.label}</Text>
                  <Text style={styles.modelId}>{m.id}</Text>
                </View>
                <View style={[styles.modelBadge, { backgroundColor: `${currentProvider.accent}22` }]}>
                  <Text style={[styles.modelBadgeText, { color: currentProvider.accent }]}>{m.badge}</Text>
                </View>
                {active && <Ionicons name="radio-button-on" size={20} color={currentProvider.accent} style={{ marginLeft: 10 }} />}
                {!active && <Ionicons name="radio-button-off" size={20} color={colors.textMuted} style={{ marginLeft: 10 }} />}
              </TouchableOpacity>
            );
          })}
        </View>

        {/* API Key */}
        <Text style={styles.sectionLabel}>API Key</Text>
        <View style={styles.keyCard}>
          {apiKeySet && (
            <View style={styles.keySetBanner}>
              <Ionicons name="lock-closed" size={14} color={colors.profit} />
              <Text style={styles.keySetText}>API key is saved securely. Enter a new key below to replace it.</Text>
            </View>
          )}
          <View style={styles.keyInputRow}>
            <TextInput
              style={styles.keyInput}
              placeholder={apiKeySet ? '••••••••••••••••••••' : `Enter your ${currentProvider.label} API key`}
              placeholderTextColor={colors.textMuted}
              value={apiKey}
              onChangeText={setApiKey}
              secureTextEntry={!showKey}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <TouchableOpacity onPress={() => setShowKey(v => !v)} style={styles.eyeBtn}>
              <Ionicons name={showKey ? 'eye-off' : 'eye'} size={20} color={colors.textMuted} />
            </TouchableOpacity>
          </View>
          <Text style={styles.keyHint}>
            {selectedProvider === 'openai' && '🔗 Get your key at platform.openai.com'}
            {selectedProvider === 'gemini' && '🔗 Get your key at aistudio.google.com'}
            {selectedProvider === 'claude' && '🔗 Get your key at console.anthropic.com'}
          </Text>
        </View>

        {/* Test Result */}
        {testResult && (
          <View style={[styles.testResultBanner, { borderColor: testResult.success ? colors.profit : colors.loss }]}>
            <Text style={[styles.testResultText, { color: testResult.success ? colors.profit : colors.loss }]}>
              {testResult.message}
            </Text>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actionRow}>
          <TouchableOpacity
            style={[styles.testBtn, testing && { opacity: 0.6 }]}
            onPress={handleTest}
            disabled={testing}
            activeOpacity={0.8}
          >
            {testing
              ? <ActivityIndicator size="small" color={colors.primary} />
              : <><Ionicons name="wifi" size={16} color={colors.primary} /><Text style={styles.testBtnText}>Test</Text></>
            }
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.saveBtn, saving && { opacity: 0.6 }]}
            onPress={handleSave}
            disabled={saving}
            activeOpacity={0.8}
          >
            {saving
              ? <ActivityIndicator size="small" color="#fff" />
              : <><Ionicons name="save" size={16} color="#fff" /><Text style={styles.saveBtnText}>Save Settings</Text></>
            }
          </TouchableOpacity>
        </View>

        {/* Info box */}
        <View style={styles.infoBox}>
          <Ionicons name="information-circle" size={16} color={colors.info} style={{ marginRight: 8 }} />
          <Text style={styles.infoText}>
            Your API key is stored securely on the server and is never sent back to this app. All AI analysis, deep scans, and chart recognition use your configured provider.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  header: { marginTop: 16, marginBottom: 28, position: 'relative', overflow: 'hidden' },
  headerGlow: { position: 'absolute', top: -20, left: -20, right: -20, height: 120, borderRadius: 60 },
  headerTitle: { fontSize: 28, fontWeight: '800', color: colors.text, letterSpacing: -0.5 },
  headerSubtitle: { fontSize: 14, color: colors.textSecondary, marginTop: 4, lineHeight: 20 },
  activeBadge: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 6, backgroundColor: `${colors.profit}18`, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, alignSelf: 'flex-start' },
  activeBadgeText: { fontSize: 12, color: colors.profit, fontWeight: '600' },

  sectionLabel: { fontSize: 12, fontWeight: '700', color: colors.textMuted, letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 10, marginTop: 4 },

  providerRow: { flexDirection: 'row', gap: 10, marginBottom: 24 },
  providerCard: { flex: 1, backgroundColor: colors.card, borderRadius: 14, padding: 14, alignItems: 'center', borderWidth: 1.5, borderColor: colors.border },
  providerIcon: { fontSize: 22, marginBottom: 6 },
  providerLabel: { fontSize: 11, fontWeight: '700', color: colors.textSecondary, textAlign: 'center' },

  modelList: { gap: 8, marginBottom: 24 },
  modelRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.card, borderRadius: 14, padding: 14, borderWidth: 1.5, borderColor: colors.border },
  modelName: { fontSize: 15, fontWeight: '600', color: colors.textSecondary },
  modelId: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  modelBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  modelBadgeText: { fontSize: 11, fontWeight: '700' },

  keyCard: { backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.border, marginBottom: 16 },
  keySetBanner: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: `${colors.profit}15`, borderRadius: 8, padding: 10, marginBottom: 12 },
  keySetText: { fontSize: 12, color: colors.profit, flex: 1, lineHeight: 16 },
  keyInputRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.cardHighlight, borderRadius: 12, borderWidth: 1, borderColor: colors.borderActive },
  keyInput: { flex: 1, color: colors.text, fontSize: 14, paddingHorizontal: 14, paddingVertical: Platform.OS === 'ios' ? 14 : 10 },
  eyeBtn: { padding: 12 },
  keyHint: { fontSize: 11, color: colors.textMuted, marginTop: 10 },

  testResultBanner: { borderRadius: 12, borderWidth: 1, padding: 12, marginBottom: 12 },
  testResultText: { fontSize: 13, fontWeight: '600' },

  actionRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  testBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: colors.card, borderRadius: 14, paddingVertical: 15, borderWidth: 1.5, borderColor: colors.primary },
  testBtnText: { fontSize: 15, fontWeight: '700', color: colors.primary },
  saveBtn: { flex: 2, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: colors.primary, borderRadius: 14, paddingVertical: 15 },
  saveBtnText: { fontSize: 15, fontWeight: '700', color: '#fff' },

  infoBox: { flexDirection: 'row', backgroundColor: `${colors.info}12`, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: `${colors.info}30`, marginBottom: 20 },
  infoText: { flex: 1, fontSize: 12, color: colors.textSecondary, lineHeight: 18 },
});
