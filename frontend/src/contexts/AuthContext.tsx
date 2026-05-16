'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { authService, UserResponse } from '@/lib/auth';

interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (email: string, password: string, confirmPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Check for existing auth on mount
  useEffect(() => {
    const token = authService.getAccessToken();
    if (token) {
      // TODO: Validate token and fetch user data
      // For now, we'll just mark as not loading
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authService.clearTokens();
    setUser(null);
    router.push('/login');
  }, [router]);

  // Auto-refresh token before expiration
  useEffect(() => {
    const refreshInterval = setInterval(
      async () => {
        const refreshToken = authService.getRefreshToken();
        if (refreshToken) {
          try {
            const response = await authService.refreshToken(refreshToken);
            authService.storeTokens(response.access_token, response.refresh_token);
          } catch (error) {
            console.error('Token refresh failed:', error);
            logout();
          }
        }
      },
      14 * 60 * 1000
    ); // Refresh every 14 minutes (access token expires in 15)

    return () => clearInterval(refreshInterval);
  }, [logout]);

  const login = async (email: string, password: string) => {
    const response = await authService.login({ email, password });
    authService.storeTokens(response.access_token, response.refresh_token);
    // TODO: Fetch and set user data
    router.push('/dashboard');
  };

  const register = async (email: string, password: string, confirmPassword: string) => {
    const user = await authService.register({ email, password, confirm_password: confirmPassword });
    setUser(user);
    router.push('/login?registered=true');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
