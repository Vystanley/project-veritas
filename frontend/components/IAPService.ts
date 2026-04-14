import { Platform, Alert } from 'react-native';

const REVENUECAT_IOS_KEY = process.env.EXPO_PUBLIC_REVENUECAT_IOS_KEY || '';
const REVENUECAT_ANDROID_KEY = process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_KEY || '';

export const IAP_PRODUCTS = {
  premium_monthly: {
    ios: 'com.veritas.premium.monthly',
    android: 'com.veritas.premium.monthly',
    price: '$13.99/month',
  },
  premium_annual: {
    ios: 'com.veritas.premium.annual',
    android: 'com.veritas.premium.annual',
    price: '$119/year',
  },
};

export type PaymentMethod = 'stripe' | 'iap';

/**
 * Detect which payment method to use.
 * Web => Stripe. Native with RevenueCat keys => IAP. Else => Stripe fallback.
 */
export function getPaymentMethod(): PaymentMethod {
  if (Platform.OS === 'web') return 'stripe';
  const key = Platform.OS === 'ios' ? REVENUECAT_IOS_KEY : REVENUECAT_ANDROID_KEY;
  return key ? 'iap' : 'stripe';
}

export function isIAPConfigured(): boolean {
  if (Platform.OS === 'web') return false;
  const key = Platform.OS === 'ios' ? REVENUECAT_IOS_KEY : REVENUECAT_ANDROID_KEY;
  return !!key;
}

let revenueCatInitialized = false;

/**
 * Initialize RevenueCat on app startup for native platforms.
 * Call this once in _layout.tsx or on login.
 */
export async function initializeIAP(userId?: string): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  if (revenueCatInitialized) return true;

  const key = Platform.OS === 'ios' ? REVENUECAT_IOS_KEY : REVENUECAT_ANDROID_KEY;
  if (!key) return false;

  try {
    const Purchases = require('react-native-purchases').default;
    await Purchases.configure({ apiKey: key });
    if (userId) {
      await Purchases.logIn(userId);
    }
    revenueCatInitialized = true;
    return true;
  } catch (e) {
    console.warn('RevenueCat initialization failed:', e);
    return false;
  }
}

/**
 * Purchase a subscription via RevenueCat (App Store / Google Play).
 */
export async function purchaseIAP(planKey: 'premium_monthly' | 'premium_annual'): Promise<{
  success: boolean;
  transactionId?: string;
  error?: string;
}> {
  try {
    const Purchases = require('react-native-purchases').default;
    const productId = Platform.OS === 'ios'
      ? IAP_PRODUCTS[planKey].ios
      : IAP_PRODUCTS[planKey].android;

    const offerings = await Purchases.getOfferings();
    const currentOffering = offerings.current;

    if (!currentOffering) {
      return { success: false, error: 'No offerings available. Please try again later.' };
    }

    const pkg = currentOffering.availablePackages.find(
      (p: any) => p.product.identifier === productId
    );

    if (!pkg) {
      return { success: false, error: 'Selected plan not available on this platform.' };
    }

    const result = await Purchases.purchasePackage(pkg);
    return {
      success: true,
      transactionId: result.customerInfo?.originalAppUserId,
    };
  } catch (e: any) {
    if (e.userCancelled) {
      return { success: false, error: 'Purchase cancelled' };
    }
    return { success: false, error: e.message || 'Purchase failed' };
  }
}

/**
 * Restore purchases (required by Apple App Store Review guidelines).
 */
export async function restorePurchases(): Promise<{
  success: boolean;
  hasActive: boolean;
  error?: string;
}> {
  try {
    const Purchases = require('react-native-purchases').default;
    const customerInfo = await Purchases.restorePurchases();
    const hasActive = Object.keys(customerInfo.entitlements.active).length > 0;
    return { success: true, hasActive };
  } catch (e: any) {
    return { success: false, hasActive: false, error: e.message };
  }
}

/**
 * Production Setup Instructions:
 *
 * 1. Create a RevenueCat account at https://app.revenuecat.com
 * 2. Create a new project for Veritas
 * 3. Configure App Store Connect (iOS):
 *    - Create subscription products: com.veritas.premium.monthly ($13.99)
 *      and com.veritas.premium.annual ($119.00)
 *    - Add shared secret to RevenueCat
 * 4. Configure Google Play Console (Android):
 *    - Create subscription products with same IDs
 *    - Upload service account JSON to RevenueCat
 * 5. In RevenueCat:
 *    - Create entitlement "premium"
 *    - Create offering "default" with monthly and annual packages
 *    - Get API keys from Settings > API Keys
 * 6. Add keys to /app/frontend/.env:
 *    EXPO_PUBLIC_REVENUECAT_IOS_KEY=appl_xxxxxxxxxxxx
 *    EXPO_PUBLIC_REVENUECAT_ANDROID_KEY=goog_xxxxxxxxxxxx
 * 7. The app will automatically detect native platform and use IAP
 *    instead of Stripe.
 *
 * Webhook: Configure RevenueCat webhook to POST to:
 *   https://your-domain.com/api/webhook/revenuecat
 *   to sync subscription status with your backend.
 */
