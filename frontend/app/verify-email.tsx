import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, Keyboard,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../components/AuthContext';
import { colors, fonts, radius } from '../constants/theme';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function VerifyEmailScreen() {
  const { token, user, setUser, loading: authLoading } = useAuth();
  const router = useRouter();
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const inputs = useRef<(TextInput | null)[]>([]);

  useEffect(() => {
    if (!authLoading && !user) router.replace('/');
    if (!authLoading && user && user.email_verified) router.replace('/home');
  }, [user, authLoading]);

  useEffect(() => {
    if (countdown > 0) {
      const t = setTimeout(() => setCountdown(c => c - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [countdown]);

  function handleChange(text: string, index: number) {
    const newCode = [...code];
    if (text.length > 1) {
      const digits = text.replace(/\D/g, '').slice(0, 6).split('');
      for (let i = 0; i < 6; i++) newCode[i] = digits[i] || '';
      setCode(newCode);
      const lastFilled = Math.min(digits.length, 5);
      inputs.current[lastFilled]?.focus();
      if (digits.length === 6) handleVerify(newCode.join(''));
      return;
    }
    newCode[index] = text.replace(/\D/g, '');
    setCode(newCode);
    if (text && index < 5) inputs.current[index + 1]?.focus();
    if (newCode.every(d => d) && newCode.join('').length === 6) handleVerify(newCode.join(''));
  }

  function handleKeyPress(e: any, index: number) {
    if (e.nativeEvent.key === 'Backspace' && !code[index] && index > 0) {
      const newCode = [...code];
      newCode[index - 1] = '';
      setCode(newCode);
      inputs.current[index - 1]?.focus();
    }
  }

  async function handleVerify(fullCode?: string) {
    Keyboard.dismiss();
    const codeStr = fullCode || code.join('');
    if (codeStr.length !== 6) { Alert.alert('Error', 'Please enter the 6-digit code'); return; }
    setSubmitting(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ code: codeStr }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Verification failed');
      Alert.alert('Success', 'Email verified successfully!');
      if (user) setUser({ ...user, email_verified: true });
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Verification failed');
      setCode(['', '', '', '', '', '']);
      inputs.current[0]?.focus();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResend() {
    setResending(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/resend-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to resend');
      setCountdown(60);
      if (data.verification_code) {
        Alert.alert('Verification Code (Dev Mode)', `Your code: ${data.verification_code}`);
      } else {
        Alert.alert('Code Sent', 'A new verification code has been sent to your email');
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setResending(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.iconWrap}>
          <Ionicons name="mail-outline" size={40} color={colors.accent} />
        </View>

        <Text style={styles.title}>Verify Your Email</Text>
        <Text style={styles.subtitle}>
          We sent a 6-digit verification code to{'\n'}
          <Text style={styles.emailText}>{user?.email || 'your email'}</Text>
        </Text>

        <View style={styles.codeRow} data-testid="otp-input-row">
          {code.map((digit, i) => (
            <TextInput
              key={i}
              ref={el => inputs.current[i] = el}
              style={[styles.codeInput, digit ? styles.codeInputFilled : null]}
              value={digit}
              onChangeText={t => handleChange(t, i)}
              onKeyPress={e => handleKeyPress(e, i)}
              keyboardType="number-pad"
              maxLength={i === 0 ? 6 : 1}
              selectTextOnFocus
              data-testid={`otp-digit-${i}`}
            />
          ))}
        </View>

        <TouchableOpacity
          data-testid="verify-btn"
          style={[styles.verifyBtn, submitting && styles.btnDisabled]}
          onPress={() => handleVerify()}
          disabled={submitting}
          activeOpacity={0.8}
        >
          {submitting ? (
            <ActivityIndicator color={colors.bg} size={20} />
          ) : (
            <Text style={styles.verifyBtnText}>Verify Email</Text>
          )}
        </TouchableOpacity>

        <View style={styles.resendRow}>
          <Text style={styles.resendLabel}>Didn't receive the code?</Text>
          <TouchableOpacity
            data-testid="resend-code-btn"
            onPress={handleResend}
            disabled={resending || countdown > 0}
          >
            <Text style={[styles.resendLink, (resending || countdown > 0) && styles.resendDisabled]}>
              {countdown > 0 ? `Resend in ${countdown}s` : resending ? 'Sending...' : 'Resend Code'}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.noteCard}>
          <Ionicons name="information-circle-outline" size={16} color={colors.textMuted} />
          <Text style={styles.noteText}>
            Check your spam folder if you don't see the email. The code expires in 10 minutes.
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { flex: 1, paddingHorizontal: 28, justifyContent: 'center', alignItems: 'center' },
  iconWrap: { width: 80, height: 80, borderRadius: 20, backgroundColor: colors.accentMuted, alignItems: 'center', justifyContent: 'center', marginBottom: 28 },
  title: { fontSize: 24, fontFamily: fonts.semiBold, color: colors.text, marginBottom: 10 },
  subtitle: { fontSize: 15, fontFamily: fonts.regular, color: colors.textSecondary, textAlign: 'center', lineHeight: 22, marginBottom: 32 },
  emailText: { color: colors.accent, fontFamily: fonts.semiBold },
  codeRow: { flexDirection: 'row', gap: 10, marginBottom: 28 },
  codeInput: { width: 46, height: 56, borderRadius: radius.md, backgroundColor: colors.surface, borderWidth: 1.5, borderColor: colors.border, textAlign: 'center', fontSize: 22, fontFamily: fonts.semiBold, color: colors.text },
  codeInputFilled: { borderColor: colors.accent, backgroundColor: colors.accentMuted },
  verifyBtn: { width: '100%', height: 54, backgroundColor: colors.accent, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', marginBottom: 20 },
  btnDisabled: { opacity: 0.6 },
  verifyBtnText: { color: colors.bg, fontSize: 16, fontFamily: fonts.semiBold },
  resendRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 28 },
  resendLabel: { color: colors.textMuted, fontSize: 14, fontFamily: fonts.regular },
  resendLink: { color: colors.accent, fontSize: 14, fontFamily: fonts.semiBold },
  resendDisabled: { color: colors.textMuted },
  noteCard: { flexDirection: 'row', gap: 8, backgroundColor: colors.surface, borderRadius: radius.md, padding: 14, borderWidth: 1, borderColor: colors.border },
  noteText: { color: colors.textMuted, fontSize: 13, fontFamily: fonts.regular, lineHeight: 19, flex: 1 },
});
