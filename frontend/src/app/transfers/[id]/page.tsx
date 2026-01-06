'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';

interface TransferJob {
  id: number;
  status: string;
  source_provider: string;
  dest_provider: string;
  source_folder_id: string | null;
  dest_folder_id: string | null;
  config: Record<string, any> | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  scheduled_for: string | null;
}

interface TransferItem {
  id: number;
  source_path: string;
  dest_path: string;
  status: string;
  size: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export default function TransferDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [job, setJob] = useState<TransferJob | null>(null);
  const [items, setItems] = useState<TransferItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [retrying, setRetrying] = useState(false);
  const [showRescheduleModal, setShowRescheduleModal] = useState(false);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleTime, setRescheduleTime] = useState('');
  const [rescheduling, setRescheduling] = useState(false);

  // Format date
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Get status badge
  const getStatusBadge = (status: string): JSX.Element => {
    const colors: Record<string, string> = {
      'draft': 'bg-gray-100 text-gray-800',
      'pending': 'bg-yellow-100 text-yellow-800',
      'running': 'bg-blue-100 text-blue-800',
      'completed': 'bg-green-100 text-green-800',
      'failed': 'bg-red-100 text-red-800',
      'cancelled': 'bg-gray-100 text-gray-800',
      'scheduled': 'bg-purple-100 text-purple-800'
    };

    const colorClass = colors[status] || 'bg-gray-100 text-gray-800';

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${colorClass}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  // Fetch job details
  const fetchJobDetails = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch transfer details');
      }

      const data = await response.json();
      setJob(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch transfer details');
    } finally {
      setLoading(false);
    }
  };

  // Handle retry failed files
  const handleRetryFailed = async () => {
    if (!confirm('Retry all failed files?')) {
      return;
    }

    setRetrying(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/resume`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to retry transfer');
      }

      // Redirect to progress page
      router.push(`/transfers/${jobId}/progress`);
    } catch (err: any) {
      alert(`Failed to retry: ${err.message}`);
    } finally {
      setRetrying(false);
    }
  };

  // Handle reschedule
  const handleReschedule = async () => {
    if (!rescheduleDate || !rescheduleTime) {
      alert('Please select both date and time');
      return;
    }

    setRescheduling(true);
    try {
      const token = localStorage.getItem('access_token');
      const scheduledDateTime = new Date(`${rescheduleDate}T${rescheduleTime}`);

      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/schedule`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          scheduled_for: scheduledDateTime.toISOString()
        })
      });

      if (!response.ok) {
        throw new Error('Failed to reschedule transfer');
      }

      // Refresh job details
      await fetchJobDetails();
      setShowRescheduleModal(false);
      setRescheduleDate('');
      setRescheduleTime('');
    } catch (err: any) {
      alert(`Failed to reschedule: ${err.message}`);
    } finally {
      setRescheduling(false);
    }
  };

  // Cancel scheduled transfer
  const handleCancelScheduled = async () => {
    if (!confirm('Cancel this scheduled transfer?')) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to cancel transfer');
      }

      router.push('/dashboard?message=Transfer cancelled');
    } catch (err: any) {
      alert(`Failed to cancel: ${err.message}`);
    }
  };

  // Download job report (CSV format)
  const handleDownloadReport = () => {
    if (!job) return;

    const csvContent = [
      ['Transfer Report'],
      ['Job ID', job.id],
      ['Status', job.status],
      ['Source', job.source_provider],
      ['Destination', job.dest_provider],
      ['Created', formatDate(job.created_at)],
      ['Started', job.started_at ? formatDate(job.started_at) : 'N/A'],
      ['Completed', job.completed_at ? formatDate(job.completed_at) : 'N/A'],
      ['Duration', calculateDuration(job.started_at, job.completed_at)],
      [],
      ['Configuration'],
      ...(job.config ? Object.entries(job.config).map(([key, value]) => [key, JSON.stringify(value)]) : []),
      [],
      ['Files'],
      ['Source Path', 'Destination Path', 'Status', 'Size', 'Error']
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transfer-${jobId}-report.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  useEffect(() => {
    fetchJobDetails();
  }, [jobId]);

  // Filter items
  const filteredItems = items.filter(item => {
    if (statusFilter !== 'all' && item.status !== statusFilter) {
      return false;
    }
    if (searchTerm && !item.source_path.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    return true;
  });

  const completedCount = items.filter(i => i.status === 'completed').length;
  const failedCount = items.filter(i => i.status === 'failed').length;
  const totalSize = items.reduce((sum, i) => sum + i.size, 0);

  if (loading) {
    return (
      <ProtectedRoute>
        <Layout>
          <div className="py-6 max-w-7xl mx-auto">
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading transfer details...</p>
            </div>
          </div>
        </Layout>
      </ProtectedRoute>
    );
  }

  if (error || !job) {
    return (
      <ProtectedRoute>
        <Layout>
          <div className="py-6 max-w-7xl mx-auto">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h3 className="text-red-800 font-semibold mb-2">Error Loading Transfer</h3>
              <p className="text-red-600">{error || 'Transfer not found'}</p>
              <button
                onClick={() => router.push('/transfers/history')}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Back to History
              </button>
            </div>
          </div>
        </Layout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <Layout>
        <div className="py-6 max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <button
                  onClick={() => router.push('/transfers/history')}
                  className="text-gray-600 hover:text-gray-900"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                </button>
                <h1 className="text-3xl font-bold text-gray-900">Transfer Details</h1>
                {getStatusBadge(job.status)}
              </div>
              <p className="text-gray-600 ml-8">Transfer ID: {job.id}</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleDownloadReport}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
              >
                Download Report
              </button>
              {job.status === 'scheduled' && (
                <>
                  <button
                    onClick={() => setShowRescheduleModal(true)}
                    className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 font-medium transition-colors"
                  >
                    Reschedule
                  </button>
                  <button
                    onClick={handleCancelScheduled}
                    className="px-4 py-2 border border-red-600 text-red-600 rounded-lg hover:bg-red-50 font-medium transition-colors"
                  >
                    Cancel Schedule
                  </button>
                </>
              )}
              {job.status === 'running' && (
                <button
                  onClick={() => router.push(`/transfers/${jobId}/progress`)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors"
                >
                  View Progress
                </button>
              )}
              {(job.status === 'failed' || job.status === 'paused') && failedCount > 0 && (
                <button
                  onClick={handleRetryFailed}
                  disabled={retrying}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors disabled:opacity-50"
                >
                  {retrying ? 'Retrying...' : 'Retry Failed Files'}
                </button>
              )}
            </div>
          </div>

          <div className="space-y-6">
            {/* Job Metadata */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Job Information</h3>
              </div>
              <div className="px-6 py-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Source</p>
                    <p className="font-medium text-gray-900">
                      {job.source_provider === 'onedrive' ? 'OneDrive' : 'Google Drive'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Destination</p>
                    <p className="font-medium text-gray-900">
                      {job.dest_provider === 'google' ? 'Google Drive' : 'OneDrive'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Created</p>
                    <p className="font-medium text-gray-900">{formatDate(job.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Started</p>
                    <p className="font-medium text-gray-900">
                      {job.started_at ? formatDate(job.started_at) : 'Not started'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Completed</p>
                    <p className="font-medium text-gray-900">
                      {job.completed_at ? formatDate(job.completed_at) : 'Not completed'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Duration</p>
                    <p className="font-medium text-gray-900">
                      {calculateDuration(job.started_at, job.completed_at)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Files</p>
                    <p className="font-medium text-gray-900">
                      {items.length} total
                      <span className="text-sm text-gray-500 ml-2">
                        ({completedCount} done, {failedCount} failed)
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Total Size</p>
                    <p className="font-medium text-gray-900">{formatSize(totalSize)}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Configuration */}
            {job.config && Object.keys(job.config).length > 0 && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Configuration</h3>
                </div>
                <div className="px-6 py-4">
                  <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {job.config.file_types && job.config.file_types.length > 0 && (
                      <div>
                        <dt className="text-sm text-gray-600 mb-1">File Types Filter</dt>
                        <dd className="font-medium text-gray-900">
                          {job.config.file_types.join(', ')}
                        </dd>
                      </div>
                    )}
                    {job.config.conflict_strategy && (
                      <div>
                        <dt className="text-sm text-gray-600 mb-1">Conflict Strategy</dt>
                        <dd className="font-medium text-gray-900">
                          {job.config.conflict_strategy.replace('_', ' ').toUpperCase()}
                        </dd>
                      </div>
                    )}
                    {job.config.date_range && (
                      <div>
                        <dt className="text-sm text-gray-600 mb-1">Date Range</dt>
                        <dd className="font-medium text-gray-900">
                          {job.config.date_range.start_date && `From: ${job.config.date_range.start_date}`}
                          {job.config.date_range.start_date && job.config.date_range.end_date && ' | '}
                          {job.config.date_range.end_date && `To: ${job.config.date_range.end_date}`}
                        </dd>
                      </div>
                    )}
                    {job.config.folder_include && job.config.folder_include.length > 0 && (
                      <div>
                        <dt className="text-sm text-gray-600 mb-1">Include Folders</dt>
                        <dd className="font-medium text-gray-900">
                          {job.config.folder_include.join(', ')}
                        </dd>
                      </div>
                    )}
                    {job.config.folder_exclude && job.config.folder_exclude.length > 0 && (
                      <div>
                        <dt className="text-sm text-gray-600 mb-1">Exclude Folders</dt>
                        <dd className="font-medium text-gray-900">
                          {job.config.folder_exclude.join(', ')}
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>
              </div>
            )}

            {/* File List */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">Files ({filteredItems.length})</h3>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      placeholder="Search files..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">All Status</option>
                      <option value="completed">Completed</option>
                      <option value="failed">Failed</option>
                      <option value="pending">Pending</option>
                      <option value="running">Running</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="px-6 py-4">
                {filteredItems.length === 0 ? (
                  <p className="text-center text-gray-600 py-8">
                    {items.length === 0 ? 'No files in this transfer' : 'No files match your filters'}
                  </p>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {filteredItems.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center">
                            <svg className="w-5 h-5 text-gray-400 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                            </svg>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {item.source_path}
                              </p>
                              {item.error_message && (
                                <p className="text-xs text-red-600 mt-1">Error: {item.error_message}</p>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="ml-4 flex items-center gap-4">
                          <span className="text-sm text-gray-500">{formatSize(item.size)}</span>
                          {getStatusBadge(item.status)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Reschedule Modal */}
          {showRescheduleModal && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                <div className="px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900">Reschedule Transfer</h3>
                    <button
                      onClick={() => setShowRescheduleModal(false)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div className="px-6 py-4">
                  <p className="text-sm text-gray-600 mb-4">
                    Choose a new date and time for this transfer
                  </p>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
                      <input
                        type="date"
                        value={rescheduleDate}
                        onChange={(e) => setRescheduleDate(e.target.value)}
                        min={new Date().toISOString().split('T')[0]}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Time</label>
                      <input
                        type="time"
                        value={rescheduleTime}
                        onChange={(e) => setRescheduleTime(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    {job.scheduled_for && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <p className="text-sm text-blue-800">
                          <span className="font-medium">Currently scheduled for:</span><br />
                          {new Date(job.scheduled_for).toLocaleString()}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
                  <button
                    onClick={() => setShowRescheduleModal(false)}
                    disabled={rescheduling}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleReschedule}
                    disabled={rescheduling || !rescheduleDate || !rescheduleTime}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors disabled:opacity-50"
                  >
                    {rescheduling ? 'Rescheduling...' : 'Reschedule'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </Layout>
    </ProtectedRoute>
  );
}
