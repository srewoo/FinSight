import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  TextInput,
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
    keyPlaceholder: 'sk-...',
    models: [
      { id: 'gpt-5-mini', label: 'GPT-5 Mini', badge: 'Latest' },
    ],
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    icon: '✨',
    accent: '#4285F4',
    keyPlaceholder: 'AIza...',
    models: [
      { id: 'gemini-3.0', label: 'Gemini 3.0', badge: 'Latest' },
    ],
  },
  {
    id: 'claude',
    label: 'Anthropic Claude',
    icon: '🧠',
    accent: '#D97706',
    keyPlaceholder: 'sk-ant-...',
    models: [
      { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6', badge: 'Balanced' },
      { id: 'claude-opus-4-5', label: 'Claude Opus 4.5', badge: 'Most Capable' },
    ],
  },
];

interface ApiKeyState {
  openai: string;
  gemini: string;
  claude: string;
}

interface ApiKeyMasked {
  openai_key_masked: string;
  gemini_key_masked: string;
  claude_key_masked: string;
}

export default function SettingsScreen() {
  const [selectedProvider, setSelectedProvider] = useState<string>('openai');
  const [selectedModel, setSelectedModel] = useState<string>('gpt-5-mini');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const [apiKeys, setApiKeys] = useState<ApiKeyState>({ openai: '', gemini: '', claude: '' });
  const [maskedKeys, setMaskedKeys] = useState<ApiKeyMasked>({ openai_key_masked: '', gemini_key_masked: '', claude_key_masked: '' });
  const [showKey, setShowKey] = useState<{ openai: boolean; gemini: boolean; claude: boolean }>({ openai: false, gemini: false, claude: false });

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getSettings();
      if (data.preferred_provider) {
        setSelectedProvider(data.preferred_provider);
        const prov = PROVIDERS.find(p => p.id === data.preferred_provider);
        if (prov) {
          setSelectedModel(data.preferred_model || prov.models[0].id);
        }
      }
    } catch (_e) {
      // defaults are fine
    } finally {
      setLoading(false);
    }
  }, []);

  const loadApiKeys = useCallback(async () => {
    try {
      const data = await api.getApiKeys();
      setMaskedKeys(data);
    } catch (_e) {
      // ignore — keys section will show as unconfigured
    }
  }, []);

  useEffect(() => {
    loadSettings();
    loadApiKeys();
  }, [loadSettings, loadApiKeys]);

  const currentProvider = PROVIDERS.find(p => p.id === selectedProvider)!;
  const currentModels = currentProvider?.models ?? [];

  const handleProviderChange = (id: string) => {
    setSelectedProvider(id);
    const prov = PROVIDERS.find(p => p.id === id)!;
    setSelectedModel(prov.models[0].id);
  };

  const handleSaveAll = async () => {
    setSaving(true);
    try {
      const tasks: Promise<any>[] = [
        api.saveSettings({ preferred_provider: selectedProvider, preferred_model: selectedModel }),
      ];

      const keyPayload: { openai_key?: string; gemini_key?: string; claude_key?: string } = {};
      if (apiKeys.openai.trim()) keyPayload.openai_key = apiKeys.openai.trim();
      if (apiKeys.gemini.trim()) keyPayload.gemini_key = apiKeys.gemini.trim();
      if (apiKeys.claude.trim()) keyPayload.claude_key = apiKeys.claude.trim();
      if (Object.keys(keyPayload).length) {
        tasks.push(api.saveApiKeys(keyPayload));
      }

      await Promise.all(tasks);
      setApiKeys({ openai: '', gemini: '', claude: '' });
      await loadApiKeys();
      Alert.alert('Saved', 'Your settings have been saved successfully.');
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? 'Failed to save settings.');
    } finally {
      setSaving(false);
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
          <Text style={styles.headerTitle}>Settings</Text>
          <Text style={styles.headerSubtitle}>Configure your AI provider and API keys</Text>
        </View>

        {/* API Keys Section */}
        <Text style={styles.sectionLabel}>API Keys</Text>
        <View style={styles.apiKeysCard}>
          <View style={styles.apiKeysHeader}>
            <Ionicons name="key-outline" size={18} color={colors.primary} />
            <Text style={styles.apiKeysTitle}>Your Personal API Keys</Text>
          </View>
          <Text style={styles.apiKeysSubtitle}>
            Add your own API keys to use your quota. Keys are encrypted with AES-256 and never exposed in plaintext.
          </Text>

          {PROVIDERS.map(p => {
            const maskedField = `${p.id}_key_masked` as keyof ApiKeyMasked;
            const existingMasked = maskedKeys[maskedField];
            const inputKey = p.id as keyof ApiKeyState;
            const visible = showKey[inputKey];
            return (
              <View key={p.id} style={styles.apiKeyRow}>
                <View style={styles.apiKeyProviderRow}>
                  <Text style={styles.apiKeyProviderIcon}>{p.icon}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.apiKeyProviderLabel}>{p.label}</Text>
                    {existingMasked ? (
                      <Text style={styles.apiKeyExisting}>Current: {existingMasked}</Text>
                    ) : (
                      <Text style={styles.apiKeyNotSet}>Not configured</Text>
                    )}
                  </View>
                  {existingMasked ? (
                    <View style={styles.apiKeyBadgeSet}>
                      <Ionicons name="checkmark-circle" size={14} color={colors.profit} />
                      <Text style={styles.apiKeyBadgeSetText}>Set</Text>
                    </View>
                  ) : (
                    <View style={styles.apiKeyBadgeUnset}>
                      <Text style={styles.apiKeyBadgeUnsetText}>Missing</Text>
                    </View>
                  )}
                </View>
                <View style={styles.apiKeyInputRow}>
                  <TextInput
                    style={styles.apiKeyInput}
                    placeholder={`New ${p.label} key (${p.keyPlaceholder})`}
                    placeholderTextColor={colors.textMuted}
                    value={apiKeys[inputKey]}
                    onChangeText={val => setApiKeys(prev => ({ ...prev, [inputKey]: val }))}
                    secureTextEntry={!visible}
                    autoCapitalize="none"
                    autoCorrect={false}
                  />
                  <TouchableOpacity
                    style={styles.eyeBtn}
                    onPress={() => setShowKey(prev => ({ ...prev, [inputKey]: !visible }))}
                  >
                    <Ionicons name={visible ? 'eye-off-outline' : 'eye-outline'} size={18} color={colors.textMuted} />
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}

        </View>

        {/* Provider Selection */}
        <Text style={styles.sectionLabel}>LLM Provider</Text>
        <View style={styles.providerRow}>
          {PROVIDERS.map(p => {
            const active = selectedProvider === p.id;
            const maskedField = `${p.id}_key_masked` as keyof ApiKeyMasked;
            const hasKey = Boolean(maskedKeys[maskedField]);
            return (
              <TouchableOpacity
                key={p.id}
                style={[styles.providerCard, active && { borderColor: p.accent, backgroundColor: `${p.accent}18` }]}
                onPress={() => handleProviderChange(p.id)}
                activeOpacity={0.75}
              >
                <Text style={styles.providerIcon}>{p.icon}</Text>
                <Text style={[styles.providerLabel, active && { color: p.accent }]}>{p.label}</Text>
                {hasKey && <Ionicons name="checkmark-circle" size={12} color={colors.profit} style={{ marginTop: 2 }} />}
                {active && <Ionicons name="radio-button-on" size={14} color={p.accent} style={{ marginTop: 4 }} />}
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
                onPress={() => setSelectedModel(m.id)}
                activeOpacity={0.75}
              >
                <View style={{ flex: 1 }}>
                  <Text style={[styles.modelName, active && { color: colors.text }]}>{m.label}</Text>
                  <Text style={styles.modelId}>{m.id}</Text>
                </View>
                <View style={[styles.modelBadge, { backgroundColor: `${currentProvider.accent}22` }]}>
                  <Text style={[styles.modelBadgeText, { color: currentProvider.accent }]}>{m.badge}</Text>
                </View>
                {active
                  ? <Ionicons name="radio-button-on" size={20} color={currentProvider.accent} style={{ marginLeft: 10 }} />
                  : <Ionicons name="radio-button-off" size={20} color={colors.textMuted} style={{ marginLeft: 10 }} />
                }
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Single Save Button */}
        <View style={styles.actionRow}>
          <TouchableOpacity
            style={[styles.saveBtn, saving && { opacity: 0.6 }]}
            onPress={handleSaveAll}
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
            Your API keys take priority over server-side keys. If no user key is set, the server's configured key is used as fallback.
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

  sectionLabel: { fontSize: 12, fontWeight: '700', color: colors.textMuted, letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 10, marginTop: 4 },

  // API Keys
  apiKeysCard: { backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.border, marginBottom: 24 },
  apiKeysHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  apiKeysTitle: { fontSize: 15, fontWeight: '700', color: colors.text },
  apiKeysSubtitle: { fontSize: 12, color: colors.textSecondary, lineHeight: 18, marginBottom: 16 },

  apiKeyRow: { marginBottom: 16, borderBottomWidth: 1, borderBottomColor: colors.border, paddingBottom: 16 },
  apiKeyProviderRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  apiKeyProviderIcon: { fontSize: 20 },
  apiKeyProviderLabel: { fontSize: 14, fontWeight: '600', color: colors.text },
  apiKeyExisting: { fontSize: 11, color: colors.textMuted, marginTop: 2, fontFamily: 'monospace' },
  apiKeyNotSet: { fontSize: 11, color: colors.warning, marginTop: 2 },
  apiKeyBadgeSet: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${colors.profit}18`, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  apiKeyBadgeSetText: { fontSize: 11, fontWeight: '700', color: colors.profit },
  apiKeyBadgeUnset: { backgroundColor: `${colors.warning}18`, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  apiKeyBadgeUnsetText: { fontSize: 11, fontWeight: '700', color: colors.warning },

  apiKeyInputRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.cardHighlight, borderRadius: 10, borderWidth: 1, borderColor: colors.border },
  apiKeyInput: { flex: 1, color: colors.text, fontSize: 13, paddingHorizontal: 12, paddingVertical: 10, fontFamily: 'monospace' },
  eyeBtn: { paddingHorizontal: 12, paddingVertical: 10 },

  // Providers
  providerRow: { flexDirection: 'row', gap: 10, marginBottom: 24 },
  providerCard: { flex: 1, backgroundColor: colors.card, borderRadius: 14, padding: 14, alignItems: 'center', borderWidth: 1.5, borderColor: colors.border },
  providerIcon: { fontSize: 22, marginBottom: 6 },
  providerLabel: { fontSize: 11, fontWeight: '700', color: colors.textSecondary, textAlign: 'center' },

  // Models
  modelList: { gap: 8, marginBottom: 24 },
  modelRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.card, borderRadius: 14, padding: 14, borderWidth: 1.5, borderColor: colors.border },
  modelName: { fontSize: 15, fontWeight: '600', color: colors.textSecondary },
  modelId: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  modelBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  modelBadgeText: { fontSize: 11, fontWeight: '700' },

  // Actions
  actionRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  saveBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: colors.primary, borderRadius: 14, paddingVertical: 15 },
  saveBtnText: { fontSize: 15, fontWeight: '700', color: '#fff' },

  infoBox: { flexDirection: 'row', backgroundColor: `${colors.info}12`, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: `${colors.info}30`, marginBottom: 20 },
  infoText: { flex: 1, fontSize: 12, color: colors.textSecondary, lineHeight: 18 },
});
