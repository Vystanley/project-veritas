import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, Keyboard,
  ScrollView, Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../components/AuthContext';
import ConsentContent from '../components/ConsentContent';
import { colors, fonts, radius, spacing } from '../constants/theme';

export default function AuthScreen() {
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [showConsent, setShowConsent] = useState(false);
  const { user, loading, login, register } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      if (user.email_verified) {
        router.replace('/home');
      } else {
        router.replace('/verify-email');
      }
    }
  }, [user, loading]);

  if (loading) {
    return <View style={s.loadingContainer}><ActivityIndicator size="large" color={colors.accent} /></View>;
  }
  if (user) return null;

  async function handleSubmit() {
    Keyboard.dismiss();
    setError('');
    if (!email.trim() || !password.trim()) { setError('Please fill in all fields'); return; }
    if (!isLogin && !name.trim()) { setError('Please enter your name'); return; }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    if (!emailRegex.test(email.trim())) { setError('Please enter a valid email address'); return; }
    if (password.length < 6) { setError('Password must be at least 6 characters'); return; }
    if (!isLogin && !consentAccepted) { setError('You must accept the Terms & Conditions to create an account'); return; }

    setSubmitting(true);
    try {
      if (isLogin) {
        await login(email.trim(), password);
      } else {
        await register(name.trim(), email.trim(), password, consentAccepted);
      }
    } catch (e: any) {
      setError(e.message || 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={s.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.flex}>
        <ScrollView contentContainerStyle={s.scrollContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          {/* Logo */}
          <View style={s.logoSection}>
            <Text style={s.appName}>VERITAS</Text>
            <Text style={s.tagline}>AI-Powered Video Fact Checker</Text>
          </View>

          {/* Form */}
          <View style={s.formSection}>
            <Text style={s.formTitle}>{isLogin ? 'Welcome back' : 'Create account'}</Text>
            <Text style={s.formSubtitle}>{isLogin ? 'Sign in to verify video content' : 'Join to start fact-checking videos'}</Text>

            {!isLogin && (
              <View style={s.inputWrapper}>
                <Ionicons name="person-outline" size={18} color={colors.textMuted} style={s.inputIcon} />
                <TextInput testID="register-name-input" style={s.input} placeholder="Full name" placeholderTextColor={colors.textMuted} value={name} onChangeText={setName} autoCapitalize="words" />
              </View>
            )}

            <View style={s.inputWrapper}>
              <Ionicons name="mail-outline" size={18} color={colors.textMuted} style={s.inputIcon} />
              <TextInput testID="auth-email-input" style={s.input} placeholder="Email address" placeholderTextColor={colors.textMuted} value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoCorrect={false} />
            </View>

            <View style={s.inputWrapper}>
              <Ionicons name="lock-closed-outline" size={18} color={colors.textMuted} style={s.inputIcon} />
              <TextInput testID="auth-password-input" style={[s.input, s.passwordInput]} placeholder="Password" placeholderTextColor={colors.textMuted} value={password} onChangeText={setPassword} secureTextEntry={!showPassword} />
              <TouchableOpacity testID="toggle-password-btn" onPress={() => setShowPassword(!showPassword)} style={s.eyeBtn}>
                <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={18} color={colors.textMuted} />
              </TouchableOpacity>
            </View>

            {/* Consent Checkbox (Register only) */}
            {!isLogin && (
              <View style={s.consentRow}>
                <TouchableOpacity
                  testID="consent-checkbox"
                  style={[s.checkbox, consentAccepted && s.checkboxChecked]}
                  onPress={() => setConsentAccepted(!consentAccepted)}
                  activeOpacity={0.7}
                >
                  {consentAccepted && <Ionicons name="checkmark" size={14} color={colors.bg} />}
                </TouchableOpacity>
                <View style={s.consentTextWrap}>
                  <Text style={s.consentText}>
                    I have read and agree to the{' '}
                  </Text>
                  <TouchableOpacity testID="open-terms-btn" onPress={() => setShowConsent(true)}>
                    <Text style={s.consentLink}>Terms of Service, Privacy Policy & Legal Disclosures</Text>
                  </TouchableOpacity>
                  <Text style={s.consentText}>
                    {' '}including the AI disclaimer, GDPR data processing, and third-party data sharing.
                  </Text>
                </View>
              </View>
            )}

            {error ? (
              <View style={s.errorBox}>
                <Ionicons name="alert-circle" size={16} color={colors.error} />
                <Text style={s.errorText}>{error}</Text>
              </View>
            ) : null}

            <TouchableOpacity testID="auth-submit-btn" style={[s.submitBtn, submitting && s.submitBtnDisabled]} onPress={handleSubmit} disabled={submitting} activeOpacity={0.8}>
              {submitting ? <ActivityIndicator color={colors.bg} size="small" /> : <Text style={s.submitBtnText}>{isLogin ? 'Sign In' : 'Create Account'}</Text>}
            </TouchableOpacity>

            <TouchableOpacity testID="auth-toggle-btn" style={s.toggleBtn} onPress={() => { setIsLogin(!isLogin); setError(''); setConsentAccepted(false); }}>
              <Text style={s.toggleText}>
                {isLogin ? "Don't have an account? " : 'Already have an account? '}
                <Text style={s.toggleTextBold}>{isLogin ? 'Sign Up' : 'Sign In'}</Text>
              </Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Consent Modal */}
      <Modal visible={showConsent} animationType="slide" transparent>
        <View style={cm.overlay}>
          <View style={cm.sheet}>
            <View style={cm.header}>
              <View style={cm.handle} />
              <TouchableOpacity testID="close-consent-modal" style={cm.closeBtn} onPress={() => setShowConsent(false)}>
                <Ionicons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
            <View style={cm.content}>
              <ConsentContent />
            </View>
            <View style={cm.footer}>
              <TouchableOpacity
                testID="accept-terms-btn"
                style={cm.acceptBtn}
                onPress={() => { setConsentAccepted(true); setShowConsent(false); }}
                activeOpacity={0.8}
              >
                <Ionicons name="checkmark-circle" size={20} color={colors.bg} />
                <Text style={cm.acceptBtnText}>I Accept All Terms</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const cm = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.85)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: '92%', flex: 1 },
  header: { paddingTop: 12, paddingBottom: 8, paddingHorizontal: 20, flexDirection: 'row', justifyContent: 'center' },
  handle: { width: 36, height: 4, borderRadius: 2, backgroundColor: colors.borderLight },
  closeBtn: { position: 'absolute', top: 12, right: 20, width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  content: { flex: 1, paddingHorizontal: 20 },
  footer: { padding: 20, paddingBottom: 36, borderTopWidth: 1, borderTopColor: colors.border },
  acceptBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: colors.accent, borderRadius: radius.lg, height: 54 },
  acceptBtnText: { color: colors.bg, fontSize: 16, fontFamily: fonts.semiBold },
});

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  loadingContainer: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
  scrollContent: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },
  logoSection: { alignItems: 'center', marginBottom: 48 },
  appName: { fontSize: 36, fontFamily: fonts.semiBold, color: colors.text, letterSpacing: 8 },
  tagline: { fontSize: 14, fontFamily: fonts.regular, color: colors.textMuted, marginTop: 8 },
  formSection: { width: '100%' },
  formTitle: { fontSize: 24, fontFamily: fonts.semiBold, color: colors.text, marginBottom: 6 },
  formSubtitle: { fontSize: 15, fontFamily: fonts.regular, color: colors.textSecondary, marginBottom: 28 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, marginBottom: 14, paddingHorizontal: 16, height: 54 },
  inputIcon: { marginRight: 12 },
  input: { flex: 1, color: colors.text, fontSize: 15, fontFamily: fonts.regular, height: '100%' },
  passwordInput: { paddingRight: 40 },
  eyeBtn: { position: 'absolute', right: 16, height: 54, justifyContent: 'center' },
  consentRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 14, gap: 12, paddingHorizontal: 4 },
  checkbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: colors.textMuted, alignItems: 'center', justifyContent: 'center', marginTop: 2 },
  checkboxChecked: { backgroundColor: colors.accent, borderColor: colors.accent },
  consentTextWrap: { flex: 1, flexDirection: 'row', flexWrap: 'wrap' },
  consentText: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 20 },
  consentLink: { fontSize: 13, fontFamily: fonts.semiBold, color: colors.accent, lineHeight: 20, textDecorationLine: 'underline' },
  errorBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.errorBg, borderRadius: radius.sm, padding: 12, marginBottom: 14, gap: 8 },
  errorText: { color: colors.error, fontSize: 14, fontFamily: fonts.regular, flex: 1 },
  submitBtn: { backgroundColor: colors.accent, borderRadius: radius.md, height: 54, alignItems: 'center', justifyContent: 'center', marginTop: 8 },
  submitBtnDisabled: { opacity: 0.6 },
  submitBtnText: { color: colors.bg, fontSize: 16, fontFamily: fonts.semiBold },
  toggleBtn: { alignItems: 'center', marginTop: 24, paddingVertical: 8 },
  toggleText: { color: colors.textSecondary, fontSize: 15, fontFamily: fonts.regular },
  toggleTextBold: { color: colors.accent, fontFamily: fonts.semiBold },
});
