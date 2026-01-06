import { apiClient } from './api';

export interface RegisterData {
  email: string;
  password: string;
  confirm_password: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const authService = {
  async register(data: RegisterData): Promise<UserResponse> {
    return apiClient.post<UserResponse>('/api/auth/register', data);
  },

  async login(data: LoginData): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/api/auth/login', data);
  },

  storeTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },

  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  },

  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  },

  clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};
