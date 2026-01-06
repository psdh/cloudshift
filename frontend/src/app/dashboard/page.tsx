'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';
import { apiClient } from '@/lib/api';

interface TransferJob {
  id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'scheduled';
  source_provider: string;
  dest_provider: string;
  started_at: string | null;
  completed_at: string | null;
  scheduled_for: string | null;
  created_at: string;
}

interface TransferStats {
  total_files: number;
  total_bytes: number;
  total_transfers: number;
}

export default function DashboardPage() {
  const [activeTransfers, setActiveTransfers] = useState<TransferJob[]>([]);
  const [scheduledTransfers, setScheduledTransfers] = useState<TransferJob[]>([]);
  const [recentTransfers, setRecentTransfers] = useState<TransferJob[]>([]);
  const [stats, setStats] = useState<TransferStats>({
    total_files: 0,
    total_bytes: 0,
    total_transfers: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    // Poll for updates every 5 seconds for active transfers
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      // Fetch all transfers
      const response = await fetch('http://localhost:8000/api/transfers', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch transfers');

      const transfers: TransferJob[] = await response.json();

      // Categorize transfers
      setActiveTransfers(
        transfers.filter((t) => t.status === 'running' || t.status === 'paused')
      );
      setScheduledTransfers(
        transfers.filter((t) => t.status === 'scheduled')
      );
      setRecentTransfers(
        transfers
          .filter((t) => t.status === 'completed' || t.status === 'failed')
          .slice(0, 5)
      );

      // Calculate stats (would come from backend API in real implementation)
      setStats({
        total_files: transfers.length * 100, // Placeholder
        total_bytes: transfers.length * 1024 * 1024 * 1024, // Placeholder
        total_transfers: transfers.length,
      });

      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const formatTimeRemaining = (scheduledFor: string): string => {
    const now = new Date();
    const scheduled = new Date(scheduledFor);
    const diff = scheduled.getTime() - now.getTime();

    if (diff < 0) return 'Overdue';

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h`;
    }
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const hasAnyData = activeTransfers.length > 0 || scheduledTransfers.length > 0 || recentTransfers.length > 0;

  return (
    <ProtectedRoute>
      <Layout>
        <div className="py-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <Link
              href="/transfers/new"
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
            >
              New Transfer
            </Link>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading dashboard...</p>
            </div>
          ) : !hasAnyData ? (
            // Empty state for new users
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <svg
                className="mx-auto h-24 w-24 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <h3 className="mt-4 text-xl font-semibold text-gray-900">
                Welcome to CloudShift!
              </h3>
              <p className="mt-2 text-gray-600 max-w-md mx-auto">
                Get started by creating your first file transfer from OneDrive to Google Drive.
              </p>
              <Link
                href="/transfers/new"
                className="mt-6 inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
              >
                Create Your First Transfer
              </Link>
              <div className="mt-6 pt-6 border-t border-gray-200">
                <p className="text-sm text-gray-600 mb-4">First, connect your cloud accounts:</p>
                <Link
                  href="/settings/accounts"
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  Manage Connected Accounts →
                </Link>
              </div>
            </div>
          ) : (
            <>
              {/* Quick Stats */}
              <div className="grid gap-4 md:grid-cols-3 mb-8">
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-sm font-medium text-gray-600 mb-1">Total Files Migrated</h3>
                  <p className="text-3xl font-bold text-gray-900">
                    {stats.total_files.toLocaleString()}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-sm font-medium text-gray-600 mb-1">Data Transferred</h3>
                  <p className="text-3xl font-bold text-gray-900">
                    {formatBytes(stats.total_bytes)}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-sm font-medium text-gray-600 mb-1">Total Transfers</h3>
                  <p className="text-3xl font-bold text-gray-900">{stats.total_transfers}</p>
                </div>
              </div>

              {/* Active Transfers */}
              {activeTransfers.length > 0 && (
                <div className="mb-8">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">Active Transfers</h2>
                  <div className="bg-white rounded-lg shadow divide-y divide-gray-200">
                    {activeTransfers.map((transfer) => (
                      <Link
                        key={transfer.id}
                        href={`/transfers/${transfer.id}`}
                        className="block p-4 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-sm font-medium text-gray-900">
                                {transfer.source_provider} → {transfer.dest_provider}
                              </span>
                              <span className={`px-2 py-1 text-xs font-medium rounded ${
                                transfer.status === 'running'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {transfer.status}
                              </span>
                            </div>
                            {/* Progress bar placeholder */}
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full animate-pulse"
                                style={{ width: '45%' }}
                              ></div>
                            </div>
                            <p className="text-xs text-gray-600 mt-1">
                              Processing... Real-time updates via SSE
                            </p>
                          </div>
                          <svg
                            className="w-5 h-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Scheduled Transfers */}
              {scheduledTransfers.length > 0 && (
                <div className="mb-8">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">Scheduled Transfers</h2>
                  <div className="bg-white rounded-lg shadow divide-y divide-gray-200">
                    {scheduledTransfers.map((transfer) => (
                      <Link
                        key={transfer.id}
                        href={`/transfers/${transfer.id}`}
                        className="block p-4 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm font-medium text-gray-900">
                                {transfer.source_provider} → {transfer.dest_provider}
                              </span>
                              <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
                                Scheduled
                              </span>
                            </div>
                            <p className="text-sm text-gray-600">
                              Starts in:{' '}
                              <span className="font-medium">
                                {transfer.scheduled_for &&
                                  formatTimeRemaining(transfer.scheduled_for)}
                              </span>
                            </p>
                          </div>
                          <svg
                            className="w-5 h-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Completed Transfers */}
              {recentTransfers.length > 0 && (
                <div className="mb-8">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">Recent Transfers</h2>
                    <Link
                      href="/transfers/history"
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      View All →
                    </Link>
                  </div>
                  <div className="bg-white rounded-lg shadow divide-y divide-gray-200">
                    {recentTransfers.map((transfer) => (
                      <Link
                        key={transfer.id}
                        href={`/transfers/${transfer.id}`}
                        className="block p-4 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm font-medium text-gray-900">
                                {transfer.source_provider} → {transfer.dest_provider}
                              </span>
                              <span className={`px-2 py-1 text-xs font-medium rounded ${
                                transfer.status === 'completed'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {transfer.status}
                              </span>
                            </div>
                            <p className="text-xs text-gray-600">
                              {transfer.completed_at &&
                                new Date(transfer.completed_at).toLocaleString()}
                            </p>
                          </div>
                          <svg
                            className="w-5 h-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Quick Links */}
          <div className="grid gap-4 md:grid-cols-3 mt-8">
            <Link
              href="/settings/accounts"
              className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Connected Accounts
              </h3>
              <p className="text-sm text-gray-600">
                Manage your OneDrive and Google Drive connections
              </p>
            </Link>
            <Link
              href="/transfers/history"
              className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Transfer History</h3>
              <p className="text-sm text-gray-600">View all past transfer jobs</p>
            </Link>
            <Link
              href="/audit-logs"
              className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Activity Log</h3>
              <p className="text-sm text-gray-600">
                Review your account activity and audit logs
              </p>
            </Link>
          </div>
        </div>
      </Layout>
    </ProtectedRoute>
  );
}
