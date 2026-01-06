import { authService } from './auth';

export interface AuditLog {
  id: number;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditLogsResponse {
  logs: AuditLog[];
  total: number;
}

class AuditApiClient {
  private getHeaders(): Record<string, string> {
    const token = authService.getAccessToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  async getLogs(
    limit: number = 50,
    offset: number = 0,
    action?: string,
    startDate?: string,
    endDate?: string
  ): Promise<AuditLogsResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      ...(action && { action }),
      ...(startDate && { start_date: startDate }),
      ...(endDate && { end_date: endDate }),
    });

    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/audit-logs?${params}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch audit logs');
    }

    return response.json();
  }

  async exportLogs(
    action?: string,
    startDate?: string,
    endDate?: string
  ): Promise<Blob> {
    const params = new URLSearchParams({
      ...(action && { action }),
      ...(startDate && { start_date: startDate }),
      ...(endDate && { end_date: endDate }),
    });

    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/audit-logs/export?${params}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to export audit logs');
    }

    return response.blob();
  }
}

export const auditService = new AuditApiClient();
