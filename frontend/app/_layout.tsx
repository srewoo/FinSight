import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import { useEffect } from 'react';
import { AuthProvider, useAuth } from '../src/auth-context';
import { BrokerProvider } from '../src/broker-context';
import { ErrorBoundary } from '../src/components/ErrorBoundary';

function AuthGuard() {
  const { user, loading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;

    const inAuthGroup = segments[0] === '(auth)';

    if (!user && !inAuthGroup) {
      // Redirect to login if user is not authenticated
      router.replace('/(auth)/login');
    } else if (user && inAuthGroup) {
      // Redirect to app if user is already authenticated
      router.replace('/(tabs)');
    }
  }, [user, loading, segments]);

  if (loading) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color="#7C3AED" />
      </View>
    );
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#09090B' },
        animation: 'slide_from_right',
      }}
    />
  );
}

export default function RootLayout() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrokerProvider>
          <View style={styles.container}>
            <StatusBar style="light" />
            <AuthGuard />
          </View>
        </BrokerProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#09090B',
  },
});
