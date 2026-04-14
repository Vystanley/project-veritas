import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert, Platform } from 'react-native';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface User {
  id: string;
  name: string;
  email: string;
  email_verified: boolean;
}

interface AuthContextType {
  user: User | null;
  setUser: (user: User) => void;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, consentAccepted: boolean) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

function extractErrorMessage(err: any): string {
  if (!err) return '';
  if (typeof err.detail === 'string') return err.detail;
  if (Array.isArray(err.detail)) {
    const msgs = err.detail.map((e: any) => {
      const field = e.loc ? e.loc[e.loc.length - 1] : '';
      const msg = e.msg || 'Invalid value';
      return field ? `${field}: ${msg}` : msg;
    });
    return msgs.join('. ');
  }
  if (typeof err.message === 'string') return err.message;
  return JSON.stringify(err);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStoredAuth();
  }, []);

  async function loadStoredAuth() {
    try {
      const storedToken = await AsyncStorage.getItem('auth_token');
      if (storedToken) {
        const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
        });
        if (res.ok) {
          const userData = await res.json();
          setUser(userData);
          setToken(storedToken);
        } else {
          await AsyncStorage.removeItem('auth_token');
        }
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function login(email: string, password: string) {
    const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      const msg = extractErrorMessage(err) || 'Login failed';
      throw new Error(msg);
    }
    const data = await res.json();
    await AsyncStorage.setItem('auth_token', data.token);
    setToken(data.token);
    setUser(data.user);
    // Show mock verification code if not verified
    if (data.verification_code && !data.user.email_verified) {
      setTimeout(() => {
        Alert.alert('Verification Code (Dev Mode)', `Your code: ${data.verification_code}`);
      }, 500);
    }
  }

  async function register(name: string, email: string, password: string, consentAccepted: boolean) {
    const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, consent_accepted: consentAccepted }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      const msg = extractErrorMessage(err) || 'Registration failed';
      throw new Error(msg);
    }
    const data = await res.json();
    await AsyncStorage.setItem('auth_token', data.token);
    setToken(data.token);
    setUser(data.user);
    // Show mock verification code
    if (data.verification_code) {
      setTimeout(() => {
        Alert.alert('Verification Code (Dev Mode)', `Your code: ${data.verification_code}`);
      }, 500);
    }
  }

  async function logout() {
    await AsyncStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, setUser, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
