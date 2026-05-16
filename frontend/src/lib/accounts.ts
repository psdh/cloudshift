import { authService } from './auth';

export type CloudProvider = 'onedrive' | 'google_drive';

export interface ConnectedAccount {
  id: number;
  provider: CloudProvider;
  account_email: string;
  created_at: string;
}

class AuthenticatedApiClient {
  private getHeaders(): Record<string, string> {
    const token = authService.getAccessToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  async get<T>(endpoint: string): Promise<T> {
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Request failed');
    }

    return response.json();
  }

  async delete<T>(endpoint: string): Promise<T> {
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`;
    const response = await fetch(url, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Request failed');
    }

    return response.json();
  }
}

const authenticatedClient = new AuthenticatedApiClient();

export const accountsService = {
  async listAccounts(): Promise<ConnectedAccount[]> {
    return authenticatedClient.get<ConnectedAccount[]>('/api/accounts');
  },

  async disconnectAccount(provider: CloudProvider): Promise<{ message: string }> {
    return authenticatedClient.delete<{ message: string }>(`/api/accounts/${provider}`);
  },

  getOneDriveAuthUrl(): string {
    const token = authService.getAccessToken();
    return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/oauth/onedrive/authorize?token=${token}`;
  },

  getGoogleAuthUrl(): string {
    const token = authService.getAccessToken();
    return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/oauth/google/authorize?token=${token}`;
  },
};
