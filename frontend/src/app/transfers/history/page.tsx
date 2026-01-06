'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';

interface TransferJob {
  id: number;
  status: string;
  source_provider: string;
  dest_provider: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  scheduled_for: string | null;
  total_items: number;
  completed_items: number;
  failed_items: number;
}

interface PaginatedResponse {
  items: TransferJob[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export default function TransferHistoryPage() {
  const router = useRouter();
  const [transfers, setTransfers] = useState<TransferJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [deleting, setDeleting] = useState<number | null>(null);

  // Format date
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Calculate duration
  const calculateDuration = (startedAt: string | null, completedAt: string | null): string => {
    if (!startedAt || !completedAt) return 'N/A';

    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const durationMs = end - start;

    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      const mins = minutes % 60;
      return `${hours}h ${mins}m`;
    }
    if (minutes > 0) {
      const secs = seconds % 60;
      return `${minutes}m ${secs}s`;
    }
    return `${seconds}s`;
  };

  // Format file size (rough calculation)
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Get status badge color
  const getStatusBadge = (status: string): JSX.Element => {
    const colors: Record<string, string> = {
      'draft': 'bg-gray-100 text-gray-800',
      'pending': 'bg-yellow-100 text-yellow-800',
      'running': 'bg-blue-100 text-blue-800',
      'completed': 'bg-green-100 text-green-800',
      'failed': 'bg-red-100 text-red-800',
      'cancelled': 'bg-gray-100 text-gray-800',
      'scheduled': 'bg-purple-100 text-purple-800',
      'paused': 'bg-orange-100 text-orange-800'
    };

    const colorClass = colors[status] || 'bg-gray-100 text-gray-800';

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${colorClass}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  // Fetch transfers
  const fetchTransfers = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers?page=${page}&page_size=20`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch transfers');
      }

      const data: PaginatedResponse = await response.json();

      // Apply client-side filtering
      let filteredItems = data.items;

      // Status filter
      if (statusFilter !== 'all') {
        filteredItems = filteredItems.filter(t => t.status === statusFilter);
      }

      // Date range filter
      if (startDate) {
        const startDateTime = new Date(startDate).getTime();
        filteredItems = filteredItems.filter(t => new Date(t.created_at).getTime() >= startDateTime);
      }

      if (endDate) {
        const endDateTime = new Date(endDate).getTime() + (24 * 60 * 60 * 1000); // End of day
        filteredItems = filteredItems.filter(t => new Date(t.created_at).getTime() <= endDateTime);
      }

      setTransfers(filteredItems);
      setTotalPages(data.total_pages);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch transfers');
    } finally {
      setLoading(false);
    }
  };

  // Delete transfer
  const handleDelete = async (jobId: number) => {
    if (!confirm('Are you sure you want to delete this transfer? This action cannot be undone.')) {
      return;
    }

    setDeleting(jobId);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to delete transfer');
      }

      // Refresh the list
      await fetchTransfers();
    } catch (err: any) {
      alert(`Failed to delete transfer: ${err.message}`);
    } finally {
      setDeleting(null);
    }
  };

  // Load transfers on mount and when filters change
  useEffect(() => {
    fetchTransfers();
  }, [page]);

  // Apply filters
  const applyFilters = () => {
    setPage(1);
    fetchTransfers();
  };

  return (
    <ProtectedRoute>
      <Layout>
        <div className="py-6 max-w-7xl mx-auto">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Transfer History</h1>
              <p className="text-gray-600 mt-1">View and manage your past transfers</p>
            </div>
            <button
              onClick={() => router.push('/transfers/new')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              New Transfer
            </button>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-lg shadow mb-6 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Filters</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Status Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="running">Running</option>
                  <option value="pending">Pending</option>
                  <option value="scheduled">Scheduled</option>
                </select>
              </div>

              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="mt-4 flex gap-3">
              <button
                onClick={applyFilters}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Apply Filters
              </button>
              <button
                onClick={() => {
                  setStatusFilter('all');
                  setStartDate('');
                  setEndDate('');
                  setPage(1);
                  fetchTransfers();
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg font-medium transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading transfers...</p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {/* Transfer List */}
          {!loading && !error && (
            <>
              {transfers.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-12 text-center">
                  <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">No Transfers Found</h3>
                  <p className="text-gray-600 mb-6">
                    {statusFilter !== 'all' || startDate || endDate
                      ? 'No transfers match your filter criteria'
                      : "You haven't created any transfers yet"}
                  </p>
                  {statusFilter === 'all' && !startDate && !endDate && (
                    <button
                      onClick={() => router.push('/transfers/new')}
                      className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                    >
                      Create Your First Transfer
                    </button>
                  )}
                </div>
              ) : (
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Date
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Source → Destination
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Files
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Duration
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {transfers.map((transfer) => (
                          <tr
                            key={transfer.id}
                            className="hover:bg-gray-50 cursor-pointer"
                            onClick={() => router.push(`/transfers/${transfer.id}`)}
                          >
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {formatDate(transfer.created_at)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                              <div className="flex items-center">
                                <span className="font-medium text-gray-900">
                                  {transfer.source_provider === 'onedrive' ? 'OneDrive' : 'Google Drive'}
                                </span>
                                <svg className="w-4 h-4 text-gray-400 mx-2" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10.293 15.707a1 1 0 010-1.414L14.586 10l-4.293-4.293a1 1 0 111.414-1.414l5 5a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0z" clipRule="evenodd" />
                                </svg>
                                <span className="font-medium text-gray-900">
                                  {transfer.dest_provider === 'google' ? 'Google Drive' : 'OneDrive'}
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              <div>
                                <span className="font-medium">{transfer.total_items}</span> total
                                {transfer.completed_items > 0 && (
                                  <span className="text-green-600 ml-2">• {transfer.completed_items} done</span>
                                )}
                                {transfer.failed_items > 0 && (
                                  <span className="text-red-600 ml-2">• {transfer.failed_items} failed</span>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {getStatusBadge(transfer.status)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {calculateDuration(transfer.started_at, transfer.completed_at)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  router.push(`/transfers/${transfer.id}`);
                                }}
                                className="text-blue-600 hover:text-blue-900 mr-4"
                              >
                                View
                              </button>
                              {(transfer.status === 'completed' || transfer.status === 'failed' || transfer.status === 'cancelled') && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDelete(transfer.id);
                                  }}
                                  disabled={deleting === transfer.id}
                                  className="text-red-600 hover:text-red-900 disabled:opacity-50"
                                >
                                  {deleting === transfer.id ? 'Deleting...' : 'Delete'}
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                      <div className="text-sm text-gray-700">
                        Page {page} of {totalPages}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPage(Math.max(1, page - 1))}
                          disabled={page === 1}
                          className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          Previous
                        </button>
                        <button
                          onClick={() => setPage(Math.min(totalPages, page + 1))}
                          disabled={page === totalPages}
                          className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </Layout>
    </ProtectedRoute>
  );
}
