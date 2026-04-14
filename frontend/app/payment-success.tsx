import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../components/AuthContext';
import { colors, fonts } from '../constants/theme';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function PaymentSuccessScreen() {
  const router = useRouter();
  const { session_id } = useLocalSearchParams<{ session_id: string }>();
  const { token } = useAuth();
  const [status, setStatus] = useState<'polling' | 'success' | 'failed'>('polling');
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (session_id && token) {
      pollStatus();
    }
  }, [session_id, token]);

  async function pollStatus() {
    const maxAttempts = 8;
    const pollInterval = 2500;

    for (let i = 0; i < maxAttempts; i++) {
      try {
        const res = await fetch(`${BACKEND_URL}/api/payments/status/${session_id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setAttempts(i + 1);
          if (data.payment_status === 'paid') {
            setStatus('success');
            setTimeout(() => router.replace('/home'), 2500);
            return;
          }
          if (data.status === 'expired') {
            setStatus('failed');
            setTimeout(() => router.replace('/home'), 3000);
            return;
          }
        }
      } catch {}
      await new Promise(r => setTimeout(r, pollInterval));
    }
    setStatus('failed');
    setTimeout(() => router.replace('/home'), 3000);
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.center}>
        {status === 'polling' && (
          <>
            <ActivityIndicator size="large" color={colors.accent} />
            <Text style={styles.title}>Processing Payment...</Text>
            <Text style={styles.subtitle}>Please wait while we confirm your payment</Text>
          </>
        )}
        {status === 'success' && (
          <>
            <View style={styles.iconWrap}>
              <Ionicons name="checkmark-circle" size={56} color={colors.success} />
            </View>
            <Text style={styles.title}>Payment Successful!</Text>
            <Text style={styles.subtitle}>Welcome to Veritas Premium. Redirecting...</Text>
          </>
        )}
        {status === 'failed' && (
          <>
            <View style={styles.iconWrap}>
              <Ionicons name="alert-circle" size={56} color={colors.warning} />
            </View>
            <Text style={styles.title}>Payment Pending</Text>
            <Text style={styles.subtitle}>We couldn't confirm your payment yet. Please check your account. Redirecting...</Text>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 },
  iconWrap: { marginBottom: 8 },
  title: { fontSize: 22, fontFamily: fonts.semiBold, color: colors.text, marginTop: 16, textAlign: 'center' },
  subtitle: { fontSize: 15, fontFamily: fonts.regular, color: colors.textSecondary, marginTop: 8, textAlign: 'center', lineHeight: 22 },
});
