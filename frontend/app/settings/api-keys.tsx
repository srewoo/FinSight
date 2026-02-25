/**
 * Extended API Keys Settings Screen
 * Let users configure their own API keys for FMP, Zerodha, Groww, etc.
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api';
import { useTheme } from '../../src/theme';

interface APIKeyStatus {
  fmp_configured: boolean;
  zerodha_configured: boolean;
  groww_configured: boolean;
  firebase_token_configured: boolean;
}

interface APIKeyConfig {
  name: string;
  key: string;
  description: string;
  getUrl: string;
  icon: string;
  placeholder: string;
}

const API_SERVICES: APIKeyConfig[] = [
  {
    name: 'Financial Modeling Prep',
    key: 'fmp',
    description: 'Reliable stock data, fundamentals, and screener. Fallback to Yahoo Finance.',
    getUrl: 'https://site.financialmodelingprep.com/developer/docs',
    icon: 'bar-chart',
    placeholder: 'Enter FMP API key',
  },
  {
    name: 'Zerodha Kite',
    key: 'zerodha',
    description: 'Indian discount broker. Place orders, view holdings and positions.',
    getUrl: 'https://kite.trade/',
    icon: 'briefcase',
    placeholder: 'Enter Zerodha API key',
  },
  {
    name: 'Groww',
    key: 'groww',
    description: 'Alternative broker integration for order execution.',
    getUrl: 'https://groww.in/',
    icon: 'trending-up',
    placeholder: 'Enter Groww API key',
  },
];

export default function ApiKeysSettingsScreen() {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<APIKeyStatus | null>(null);
  const [keys, setKeys] = useState({
    fmp: '',
    zerodha: '',
    zerodha_token: '',
    groww: '',
  });
  const [validating, setValidating] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const data = await api.getExtendedApiKeys();
      setStatus(data);
    } catch (err: any) {
      console.error('Failed to load API key status:', err);
      Alert.alert('Error', 'Failed to load API key status');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.saveExtendedApiKeys({
        fmp_key: keys.fmp || undefined,
        zerodha_api_key: keys.zerodha || undefined,
        zerodha_access_token: keys.zerodha_token || undefined,
        groww_api_key: keys.groww || undefined,
      });
      
      Alert.alert('Success', 'API keys saved successfully');
      loadStatus();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to save API keys');
    } finally {
      setSaving(false);
    }
  };

  const handleValidate = async (service: string, apiKey: string) => {
    if (!apiKey.trim()) {
      Alert.alert('Error', 'Please enter an API key first');
      return;
    }

    setValidating(service);
    try {
      const result = await api.validateApiKey(service, apiKey);
      
      if (result.valid) {
        Alert.alert('Success', result.message);
      } else {
        Alert.alert('Validation Failed', result.message);
      }
    } catch (err: any) {
      Alert.alert('Error', `Validation failed: ${err.message}`);
    } finally {
      setValidating(null);
    }
  };

  const openUrl = (url: string) => {
    Linking.openURL(url);
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.bg }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textMuted }]}>
            Loading API keys...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.bg }]}>
      <View style={styles.header}>
        <Text style={[styles.headerTitle, { color: theme.text }]}>API Keys</Text>
      </View>

      <ScrollView style={styles.content} contentContainerStyle={styles.scrollContent}>
        {/* Info Card */}
        <View style={[styles.infoCard, { backgroundColor: theme.cardBg, borderColor: theme.border }]}>
          <Ionicons name="information-circle" size={24} color={theme.primary} />
          <Text style={[styles.infoText, { color: theme.text }]}>
            Add your own API keys for enhanced features. Keys are encrypted and stored securely.
          </Text>
        </View>

        {/* LLM API Keys Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>AI Provider Keys</Text>
          <Text style={[styles.sectionDescription, { color: theme.textMuted }]}>
            Already configured in Settings → AI Preferences
          </Text>
          <TouchableOpacity
            style={[styles.existingButton, { backgroundColor: theme.cardBg, borderColor: theme.border }]}
            onPress={() => {}}
          >
            <Ionicons name="key" size={20} color={theme.primary} />
            <Text style={[styles.existingText, { color: theme.text }]}>
              Manage AI Keys (OpenAI, Gemini, Claude)
            </Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textMuted} />
          </TouchableOpacity>
        </View>

        {/* Extended API Keys Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Data & Broker APIs</Text>

          {API_SERVICES.map((service) => {
            const isConfigured = status?.[`${service.key}_configured` as keyof APIKeyStatus];
            
            return (
              <View
                key={service.key}
                style={[styles.serviceCard, { backgroundColor: theme.cardBg, borderColor: theme.border }]}
              >
                <View style={styles.serviceHeader}>
                  <View style={styles.serviceIcon}>
                    <Ionicons name={service.icon as any} size={24} color={theme.primary} />
                    <Text style={[styles.serviceName, { color: theme.text }]}>{service.name}</Text>
                  </View>
                  
                  {isConfigured && (
                    <View style={styles.configuredBadge}>
                      <Ionicons name="checkmark-circle" size={16} color={theme.success} />
                      <Text style={styles.configuredText}>Configured</Text>
                    </View>
                  )}
                </View>

                <Text style={[styles.serviceDescription, { color: theme.textMuted }]}>
                  {service.description}
                </Text>

                <TouchableOpacity
                  onPress={() => openUrl(service.getUrl)}
                  style={styles.getUrlButton}
                >
                  <Ionicons name="link" size={16} color={theme.primary} />
                  <Text style={styles.getUrlText}>Get API Key</Text>
                </TouchableOpacity>

                {/* API Key Input */}
                <View style={styles.inputGroup}>
                  <TextInput
                    style={[
                      styles.input,
                      { backgroundColor: theme.inputBg, color: theme.text, borderColor: theme.border },
                    ]}
                    placeholder={service.placeholder}
                    placeholderTextColor={theme.textMuted}
                    value={service.key === 'zerodha' ? keys.zerodha : 
                           service.key === 'fmp' ? keys.fmp : 
                           service.key === 'groww' ? keys.groww : ''}
                    onChangeText={(text) => setKeys(prev => ({
                      ...prev,
                      [service.key]: text,
                    }))}
                    autoCapitalize="none"
                    autoCorrect={false}
                  />

                  <View style={styles.inputActions}>
                    <TouchableOpacity
                      style={[styles.validateButton, { backgroundColor: theme.secondary }]}
                      onPress={() => handleValidate(service.key, 
                        service.key === 'zerodha' ? keys.zerodha :
                        service.key === 'fmp' ? keys.fmp :
                        service.key === 'groww' ? keys.groww : ''
                      )}
                      disabled={validating !== null}
                    >
                      {validating === service.key ? (
                        <ActivityIndicator size="small" color={theme.text} />
                      ) : (
                        <>
                          <Ionicons name="shield-checkmark" size={18} color={theme.text} />
                          <Text style={[styles.validateText, { color: theme.text }]}>Validate</Text>
                        </>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Zerodha additional token field */}
                {service.key === 'zerodha' && (
                  <View style={styles.inputGroup}>
                    <TextInput
                      style={[
                        styles.input,
                        { backgroundColor: theme.inputBg, color: theme.text, borderColor: theme.border },
                      ]}
                      placeholder="Zerodha Access Token (optional)"
                      placeholderTextColor={theme.textMuted}
                      value={keys.zerodha_token}
                      onChangeText={(text) => setKeys(prev => ({ ...prev, zerodha_token: text }))}
                      autoCapitalize="none"
                    />
                    <Text style={[styles.hintText, { color: theme.textMuted }]}>
                      Access token generated after OAuth login
                    </Text>
                  </View>
                )}
              </View>
            );
          })}
        </View>

        {/* Firebase Device Token */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Push Notifications</Text>
          <View style={[styles.serviceCard, { backgroundColor: theme.cardBg, borderColor: theme.border }]}>
            <View style={styles.serviceHeader}>
              <View style={styles.serviceIcon}>
                <Ionicons name="notifications" size={24} color={theme.primary} />
                <Text style={[styles.serviceName, { color: theme.text }]}>Firebase Cloud Messaging</Text>
              </View>
              
              {status?.firebase_token_configured && (
                <View style={styles.configuredBadge}>
                  <Ionicons name="checkmark-circle" size={16} color={theme.success} />
                  <Text style={styles.configuredText}>Registered</Text>
                </View>
              )}
            </View>

            <Text style={[styles.serviceDescription, { color: theme.textMuted }]}>
              Device token is automatically registered for push notifications.
            </Text>

            {status?.firebase_token_configured ? (
              <View style={styles.successRow}>
                <Ionicons name="checkmark-circle" size={20} color={theme.success} />
                <Text style={[styles.successText, { color: theme.text }]}>
                  Push notifications enabled
                </Text>
              </View>
            ) : (
              <View style={styles.warningRow}>
                <Ionicons name="warning" size={20} color={theme.warning} />
                <Text style={[styles.warningText, { color: theme.text }]}>
                  Device token not registered. Restart the app.
                </Text>
              </View>
            )}
          </View>
        </View>

        {/* Save Button */}
        <TouchableOpacity
          style={[
            styles.saveButton,
            { backgroundColor: saving ? theme.textMuted : theme.primary },
          ]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Ionicons name="save" size={20} color="#fff" />
              <Text style={styles.saveButtonText}>Save API Keys</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Security Notice */}
        <View style={styles.securityNotice}>
          <Ionicons name="lock-closed" size={16} color={theme.textMuted} />
          <Text style={[styles.securityText, { color: theme.textMuted }]}>
            All API keys are encrypted with Fernet encryption before storage.
          </Text>
        </View>
      </ScrollView>
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
  content: {
    flex: 1,
  } as any,
  scrollContent: {
    padding: 16,
  } as any,
  infoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    marginBottom: 20,
  } as any,
  infoText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  } as any,
  section: {
    marginBottom: 24,
  } as any,
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  } as any,
  sectionDescription: {
    fontSize: 14,
    marginBottom: 12,
  } as any,
  existingButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
  } as any,
  existingText: {
    flex: 1,
    fontSize: 15,
    fontWeight: '500',
  } as any,
  serviceCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  } as any,
  serviceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  } as any,
  serviceIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  } as any,
  serviceName: {
    fontSize: 16,
    fontWeight: '600',
  } as any,
  configuredBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  } as any,
  configuredText: {
    color: '#10B981',
    fontSize: 12,
    fontWeight: '600',
  } as any,
  serviceDescription: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  } as any,
  getUrlButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 12,
  } as any,
  getUrlText: {
    color: '#7C3AED',
    fontSize: 14,
    fontWeight: '500',
  } as any,
  inputGroup: {
    marginBottom: 12,
  } as any,
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    marginBottom: 8,
  } as any,
  inputActions: {
    flexDirection: 'row',
    gap: 8,
  } as any,
  validateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    alignSelf: 'flex-start',
  } as any,
  validateText: {
    fontSize: 14,
    fontWeight: '500',
  } as any,
  hintText: {
    fontSize: 12,
    marginTop: 4,
  } as any,
  successRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
  } as any,
  successText: {
    fontSize: 14,
    color: '#10B981',
  } as any,
  warningRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
  } as any,
  warningText: {
    fontSize: 14,
    color: '#F59E0B',
  } as any,
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderRadius: 12,
    paddingVertical: 16,
    marginTop: 8,
  } as any,
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  } as any,
  securityNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    justifyContent: 'center',
    marginTop: 20,
    marginBottom: 8,
  } as any,
  securityText: {
    fontSize: 12,
  } as any,
};
