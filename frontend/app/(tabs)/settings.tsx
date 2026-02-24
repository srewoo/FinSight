import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, shared } from '../../src/theme';
import { api } from '../../src/api';
import { useAuth } from '../../src/auth-context';

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

interface Quota {
  used: number;
  limit: number;
  remaining: number;
}

export default function SettingsScreen() {
  const { user, signOut } = useAuth();

  const [selectedProvider, setSelectedProvider] = useState<string>('openai');
  const [selectedModel, setSelectedModel] = useState<string>('gpt-5.2');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [quotaLoading, setQuotaLoading] = useState(true);

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getSettings();
      if (data.preferred_provider) {
        setSelectedProvider(data.preferred_provider);
        const prov = PROVIDERS.find(p => p.id === data.preferred_provider);
        if (prov) {
          setSelectedModel(prov.models[0].id);
        }
      }
    } catch (_e) {
      // no settings yet, defaults are fine
    } finally {
      setLoading(false);
    }
  }, []);

  const loadQuota = useCallback(async () => {
    try {
      setQuotaLoading(true);
      const data = await api.getQuota();
      setQuota(data);
    } catch (_e) {
      setQuota(null);
    } finally {
      setQuotaLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
    loadQuota();
  }, [loadSettings, loadQuota]);

  const currentProvider = PROVIDERS.find(p => p.id === selectedProvider)!;
  const currentModels = currentProvider?.models ?? [];

  const handleProviderChange = (id: string) => {
    setSelectedProvider(id);
    const prov = PROVIDERS.find(p => p.id === id)!;
    setSelectedModel(prov.models[0].id);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.saveSettings({ preferred_provider: selectedProvider });
      Alert.alert('Saved', `${currentProvider.label} is now your preferred provider.`);
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleSignOut = async () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          try {
            await signOut();
          } catch (e: any) {
            Alert.alert('Error', e?.message ?? 'Failed to sign out.');
          }
        },
      },
    ]);
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

  const quotaPercent = quota && quota.limit > 0 ? Math.min((quota.used / quota.limit) * 100, 100) : 0;
  const quotaBarColor = quotaPercent >= 90 ? colors.loss : quotaPercent >= 70 ? colors.warning : colors.profit;

  return (
    <SafeAreaView style={shared.screen}>
      <ScrollView contentContainerStyle={shared.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <LinearGradient colors={['#7C3AED22', '#00000000']} style={styles.headerGlow} />
          <Text style={styles.headerTitle}>Settings</Text>
          <Text style={styles.headerSubtitle}>Manage your profile and AI preferences</Text>
        </View>

        {/* User Profile Section */}
        <Text style={styles.sectionLabel}>Profile</Text>
        <View style={styles.profileCard}>
          <View style={styles.profileAvatar}>
            <Ionicons name="person-circle" size={44} color={colors.primary} />
          </View>
          <View style={styles.profileInfo}>
            <Text style={styles.profileEmail}>{user?.email ?? 'Not signed in'}</Text>
            <Text style={styles.profileHint}>Signed in with Firebase</Text>
          </View>
          <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut} activeOpacity={0.8}>
            <Ionicons name="log-out-outline" size={18} color={colors.loss} />
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>

        {/* Usage Quota Section */}
        <Text style={styles.sectionLabel}>Usage Quota</Text>
        <View style={styles.quotaCard}>
          {quotaLoading ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : quota ? (
            <>
              <View style={styles.quotaHeader}>
                <Text style={styles.quotaLabel}>AI Requests</Text>
                <Text style={styles.quotaCount}>
                  {quota.used}
                  <Text style={styles.quotaLimit}> / {quota.limit}</Text>
                </Text>
              </View>
              <View style={styles.progressBarBg}>
                <View style={[styles.progressBarFill, { width: `${quotaPercent}%`, backgroundColor: quotaBarColor }]} />
              </View>
              <Text style={styles.quotaRemaining}>
                {quota.remaining} requests remaining
              </Text>
            </>
          ) : (
            <Text style={styles.quotaError}>Unable to load quota information</Text>
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
                {active && <Ionicons name="radio-button-on" size={20} color={currentProvider.accent} style={{ marginLeft: 10 }} />}
                {!active && <Ionicons name="radio-button-off" size={20} color={colors.textMuted} style={{ marginLeft: 10 }} />}
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Save Button */}
        <View style={styles.actionRow}>
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
            Your preferred provider is used for all AI analysis, deep scans, and chart recognition. API keys are managed server-side by your administrator.
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

  // Profile
  profileCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.border, marginBottom: 24 },
  profileAvatar: { marginRight: 12 },
  profileInfo: { flex: 1 },
  profileEmail: { fontSize: 15, fontWeight: '600', color: colors.text },
  profileHint: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  signOutBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: `${colors.loss}18`, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10 },
  signOutText: { fontSize: 13, fontWeight: '600', color: colors.loss },

  // Quota
  quotaCard: { backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.border, marginBottom: 24 },
  quotaHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  quotaLabel: { fontSize: 14, fontWeight: '600', color: colors.textSecondary },
  quotaCount: { fontSize: 16, fontWeight: '700', color: colors.text },
  quotaLimit: { fontSize: 14, fontWeight: '500', color: colors.textMuted },
  progressBarBg: { height: 8, backgroundColor: colors.cardHighlight, borderRadius: 4, overflow: 'hidden' },
  progressBarFill: { height: 8, borderRadius: 4 },
  quotaRemaining: { fontSize: 12, color: colors.textMuted, marginTop: 8 },
  quotaError: { fontSize: 13, color: colors.textMuted },

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

  // Info
  infoBox: { flexDirection: 'row', backgroundColor: `${colors.info}12`, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: `${colors.info}30`, marginBottom: 20 },
  infoText: { flex: 1, fontSize: 12, color: colors.textSecondary, lineHeight: 18 },
});
