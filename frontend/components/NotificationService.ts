import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// Configure how notifications are shown when app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

/**
 * Request notification permissions and get push token.
 * Returns the push token string or null if denied.
 */
export async function requestNotificationPermission(): Promise<string | null> {
  // Notifications only work on real devices
  if (!Device.isDevice && Platform.OS !== 'web') {
    console.log('Notifications require a physical device');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    return null;
  }

  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    return tokenData.data;
  } catch {
    return null;
  }
}

/**
 * Register push token with backend for server-side notifications.
 */
export async function registerPushToken(token: string, authToken: string): Promise<void> {
  try {
    await fetch(`${BACKEND_URL}/api/notifications/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({ push_token: token }),
    });
  } catch {}
}

/**
 * Schedule a local notification for when weekly free scans reset (every Monday).
 */
export async function scheduleWeeklyResetNotification(): Promise<void> {
  // Cancel any existing scheduled notifications to avoid duplicates
  await Notifications.cancelAllScheduledNotificationsAsync();

  try {
    // Schedule for next Monday at 9:00 AM local time
    await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Your free scans have reset!',
        body: 'You have 3 new free video fact-checks this week. Open Veritas to verify a video now.',
        sound: true,
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.WEEKLY,
        weekday: 2, // Monday (1=Sunday, 2=Monday, ...)
        hour: 9,
        minute: 0,
      },
    });
  } catch (e) {
    console.warn('Failed to schedule notification:', e);
  }
}

/**
 * Schedule a reminder if user is close to scan limit.
 */
export async function scheduleScansLowNotification(scansRemaining: number): Promise<void> {
  if (scansRemaining === 1) {
    try {
      // Notify after 1 hour that they have 1 scan left
      await Notifications.scheduleNotificationAsync({
        content: {
          title: 'Last free scan this week',
          body: 'You have 1 scan left. Upgrade to Premium for unlimited fact-checks!',
          sound: true,
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
          seconds: 3600,
        },
      });
    } catch {}
  }
}

/**
 * Initialize notifications: request permission, register token, schedule reset.
 */
export async function initializeNotifications(authToken: string | null): Promise<void> {
  const pushToken = await requestNotificationPermission();

  if (pushToken && authToken) {
    await registerPushToken(pushToken, authToken);
  }

  await scheduleWeeklyResetNotification();
}
