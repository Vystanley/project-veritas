import React, { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator } from 'react-native';
import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
// NOTE: expo-share-intent is temporarily stubbed out — its API shape doesn't
// match the installed version in Expo Go and it requires a dev-client build
// to work properly anyway. Re-enable when you build a dev client.
// import useShareIntent from 'expo-share-intent';
const useShareIntent = (_opts?: any) => ({
  hasShareIntent: false,
  shareIntent: null as null | { webUrl?: string; text?: string },
  resetShareIntent: () => {},
});
import { AuthProvider, useAuth } from '../components/AuthContext';
import { ShareIntentProvider, useSharedUrl, extractUrlFromShareData } from '../components/ShareIntentContext';
import { colors } from '../constants/theme';

SplashScreen.preventAutoHideAsync();

/**
 * Inner layout that handles share intent detection.
 * useShareIntent is web-safe (disabled on web automatically).
 */
function InnerLayout() {
  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntent({
    debug: __DEV__,
    resetOnBackground: true,
  });
  const { setSharedUrl } = useSharedUrl();
  const { user } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  // When a share intent is received, extract URL and navigate
  useEffect(() => {
    if (hasShareIntent && shareIntent) {
      const url = extractUrlFromShareData({
        webUrl: shareIntent.webUrl ?? undefined,
        text: shareIntent.text ?? undefined,
      });

      if (url) {
        setSharedUrl(url);

        // If user is logged in, go to home; otherwise go to login
        // (after login, the auth flow will redirect to home)
        if (user && user.email_verified) {
          router.replace('/home');
        }
        // If not logged in, the URL is stored in context
        // and will be picked up when they reach home after login

        resetShareIntent();
      }
    }
  }, [hasShareIntent, shareIntent]);

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.bg },
        animation: 'slide_from_right',
      }}
    />
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    'Inter-Regular': require('@expo-google-fonts/inter/400Regular/Inter_400Regular.ttf'),
    'Inter-SemiBold': require('@expo-google-fonts/inter/600SemiBold/Inter_600SemiBold.ttf'),
  });

  useEffect(() => {
    if (fontsLoaded || fontError) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <ShareIntentProvider>
      <AuthProvider>
        <StatusBar style="light" />
        <InnerLayout />
      </AuthProvider>
    </ShareIntentProvider>
  );
}
