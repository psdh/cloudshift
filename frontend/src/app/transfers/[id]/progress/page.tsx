'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';

interface ProgressData {
  job_id: number;
  total_files: number;
  total_size: number;
  files_completed: number;
  files_failed: number;
  bytes_transferred: number;
  current_file: string | null;
  current_file_bytes: number;
  current_file_total: number;
  percent_complete: number;
  started_at: string;
  last_update: string;
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

export default function TransferProgressPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [items, setItems] = useState<TransferItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCompleted, setShowCompleted] = useState(false);
  const [showFailed, setShowFailed] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Calculate transfer speed
  const calculateSpeed = (): string => {
    if (!progress || !progress.started_at) return '0 MB/s';

    const startTime = new Date(progress.started_at).getTime();
    const now = new Date().getTime();
    const elapsedSeconds = (now - startTime) / 1000;

    if (elapsedSeconds <= 0) return '0 MB/s';

    const bytesPerSecond = progress.bytes_transferred / elapsedSeconds;
    const mbPerSecond = bytesPerSecond / (1024 * 1024);

    return `${mbPerSecond.toFixed(2)} MB/s`;
  };

  // Calculate estimated time remaining
  const calculateETA = (): string => {
    if (!progress || progress.bytes_transferred === 0) return 'Calculating...';

    const startTime = new Date(progress.started_at).getTime();
    const now = new Date().getTime();
    const elapsedSeconds = (now - startTime) / 1000;

    const bytesPerSecond = progress.bytes_transferred / elapsedSeconds;
    const remainingBytes = progress.total_size - progress.bytes_transferred;
    const remainingSeconds = remainingBytes / bytesPerSecond;

    if (!isFinite(remainingSeconds) || remainingSeconds < 0) return 'Calculating...';

    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = Math.floor(remainingSeconds % 60);

    if (minutes > 60) {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours}h ${mins}m`;
    }

    return `${minutes}m ${seconds}s`;
  };

  // Fetch progress
  const fetchProgress = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/progress`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        if (response.status === 404) {
          // Progress not available yet, check job status
          const jobResponse = await fetch(`http://localhost:8000/api/transfers/${jobId}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (jobResponse.ok) {
            const jobData = await jobResponse.json();
            if (jobData.status === 'completed' || jobData.status === 'failed') {
              setIsComplete(true);
            }
          }
          throw new Error('Progress data not available yet');
        }
        throw new Error('Failed to fetch progress');
      }

      const data = await response.json();
      setProgress(data);
      setLoading(false);

      // Check if transfer is complete
      if (data.files_completed + data.files_failed >= data.total_files) {
        setIsComplete(true);
      }
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  }, [jobId]);

  // Fetch transfer items
  const fetchItems = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch transfer items');
      }

      const data = await response.json();
      // Note: The API might not return items in the detail endpoint
      // In a real implementation, you'd have a separate endpoint for items
      // For now, we'll leave this as a placeholder
    } catch (err: any) {
      console.error('Failed to fetch items:', err);
    }
  }, [jobId]);

  // Cancel transfer
  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this transfer?')) {
      return;
    }

    setCancelling(true);
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
      alert(`Failed to cancel transfer: ${err.message}`);
    } finally {
      setCancelling(false);
    }
  };

  // Poll for progress updates every 2 seconds
  useEffect(() => {
    fetchProgress();
    const interval = setInterval(() => {
      if (!isComplete) {
        fetchProgress();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchProgress, isComplete]);

  if (loading && !progress) {
    return (
      <ProtectedRoute>
        <Layout>
          <div className="py-6 max-w-6xl mx-auto">
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading transfer progress...</p>
            </div>
          </div>
        </Layout>
      </ProtectedRoute>
    );
  }

  if (error && !progress) {
    return (
      <ProtectedRoute>
        <Layout>
          <div className="py-6 max-w-6xl mx-auto">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h3 className="text-red-800 font-semibold mb-2">Error Loading Progress</h3>
              <p className="text-red-600">{error}</p>
              <p className="text-sm text-red-500 mt-2">
                The transfer may not have started yet, or there was an error fetching progress data.
              </p>
              <button
                onClick={() => router.push('/dashboard')}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Return to Dashboard
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
        <div className="py-6 max-w-6xl mx-auto">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Transfer Progress</h1>
              <p className="text-gray-600 mt-1">Transfer ID: {jobId}</p>
            </div>
            {!isComplete && (
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="px-4 py-2 border border-red-600 text-red-600 rounded-lg hover:bg-red-50 font-medium transition-colors disabled:opacity-50"
              >
                {cancelling ? 'Cancelling...' : 'Cancel Transfer'}
              </button>
            )}
          </div>

          {progress && (
            <div className="space-y-6">
              {/* Overall Progress */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Progress</h3>

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">
                      {progress.files_completed} of {progress.total_files} files completed
                    </span>
                    <span className="text-sm font-medium text-blue-600">
                      {progress.percent_complete.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className="bg-blue-600 h-4 rounded-full transition-all duration-500"
                      style={{ width: `${progress.percent_complete}%` }}
                    ></div>
                  </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-blue-600 font-medium">Transferred</p>
                    <p className="text-xl font-bold text-blue-900 mt-1">
                      {formatSize(progress.bytes_transferred)}
                    </p>
                    <p className="text-xs text-blue-600 mt-1">of {formatSize(progress.total_size)}</p>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4">
                    <p className="text-sm text-green-600 font-medium">Completed</p>
                    <p className="text-xl font-bold text-green-900 mt-1">
                      {progress.files_completed}
                    </p>
                    <p className="text-xs text-green-600 mt-1">files</p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4">
                    <p className="text-sm text-purple-600 font-medium">Speed</p>
                    <p className="text-xl font-bold text-purple-900 mt-1">
                      {calculateSpeed()}
                    </p>
                    <p className="text-xs text-purple-600 mt-1">average</p>
                  </div>
                  <div className="bg-orange-50 rounded-lg p-4">
                    <p className="text-sm text-orange-600 font-medium">ETA</p>
                    <p className="text-xl font-bold text-orange-900 mt-1">
                      {isComplete ? 'Complete' : calculateETA()}
                    </p>
                    <p className="text-xs text-orange-600 mt-1">remaining</p>
                  </div>
                </div>
              </div>

              {/* Current File */}
              {progress.current_file && !isComplete && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Current File</h3>
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <div className="animate-pulse w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-4 flex-1">
                      <p className="font-medium text-gray-900">{progress.current_file}</p>
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-gray-600">
                            {formatSize(progress.current_file_bytes)} of {formatSize(progress.current_file_total)}
                          </span>
                          <span className="text-gray-600">
                            {progress.current_file_total > 0
                              ? ((progress.current_file_bytes / progress.current_file_total) * 100).toFixed(1)
                              : 0}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{
                              width: `${progress.current_file_total > 0
                                ? (progress.current_file_bytes / progress.current_file_total) * 100
                                : 0}%`
                            }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Failed Files */}
              {progress.files_failed > 0 && (
                <div className="bg-white rounded-lg shadow">
                  <button
                    onClick={() => setShowFailed(!showFailed)}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center">
                      <svg className="w-5 h-5 text-red-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <span className="font-semibold text-gray-900">
                        Failed Files ({progress.files_failed})
                      </span>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-400 transition-transform ${showFailed ? 'rotate-180' : ''}`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                  {showFailed && (
                    <div className="px-6 pb-4 border-t border-gray-200">
                      <p className="text-sm text-gray-600 py-4">
                        Failed files will appear here as the transfer progresses.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Completed Files */}
              {progress.files_completed > 0 && (
                <div className="bg-white rounded-lg shadow">
                  <button
                    onClick={() => setShowCompleted(!showCompleted)}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center">
                      <svg className="w-5 h-5 text-green-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="font-semibold text-gray-900">
                        Completed Files ({progress.files_completed})
                      </span>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-400 transition-transform ${showCompleted ? 'rotate-180' : ''}`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                  {showCompleted && (
                    <div className="px-6 pb-4 border-t border-gray-200">
                      <p className="text-sm text-gray-600 py-4">
                        Completed files will appear here as the transfer progresses.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Completion Message */}
              {isComplete && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                  <div className="flex items-center">
                    <svg className="w-8 h-8 text-green-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <div>
                      <h3 className="text-lg font-semibold text-green-900">Transfer Complete!</h3>
                      <p className="text-green-700 mt-1">
                        {progress.files_completed} file(s) transferred successfully
                        {progress.files_failed > 0 && `, ${progress.files_failed} file(s) failed`}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 flex gap-3">
                    <button
                      onClick={() => router.push(`/transfers/${jobId}`)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors"
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => router.push('/dashboard')}
                      className="px-4 py-2 border border-green-600 text-green-700 rounded-lg hover:bg-green-50 font-medium transition-colors"
                    >
                      Return to Dashboard
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Layout>
    </ProtectedRoute>
  );
}
