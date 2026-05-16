'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface OneDriveItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  size?: number;
  modifiedAt?: string;
  path: string;
}

interface TransferFilters {
  fileTypes: string[];
  dateRange: {
    startDate: string;
    endDate: string;
  };
  folderInclude: string[];
  folderExclude: string[];
}

interface DryRunFileInfo {
  source_name: string;
  source_path: string;
  dest_path: string;
  size: number;
  has_conflict: boolean;
  conflict_resolution?: string;
}

interface DryRunResult {
  files_to_transfer: DryRunFileInfo[];
  folders_to_create: string[];
  total_files: number;
  total_size: number;
  conflicts: number;
  estimated_time_minutes: number;
}

interface ReviewConfirmProps {
  selectedSource: OneDriveItem[];
  destinationFolderId: string;
  destinationFolderName: string;
  filters: TransferFilters;
  onBack: () => void;
}

export default function ReviewConfirm({
  selectedSource,
  destinationFolderId,
  destinationFolderName,
  filters,
  onBack
}: ReviewConfirmProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [dryRunning, setDryRunning] = useState(false);
  const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null);
  const [conflictStrategy, setConflictStrategy] = useState<string>('ask');
  const [scheduleOption, setScheduleOption] = useState<'now' | 'later'>('now');
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [jobId, setJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Calculate total size of selected files
  const totalSize = selectedSource.reduce((sum, item) => sum + (item.size || 0), 0);

  // Run dry run
  const handleDryRun = async () => {
    if (!jobId) {
      setError('Job not created yet. Please wait...');
      return;
    }

    setDryRunning(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/dry-run`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to run dry run');
      }

      const result = await response.json();
      setDryRunResult(result);
    } catch (err: any) {
      setError(err.message || 'Failed to run dry run');
    } finally {
      setDryRunning(false);
    }
  };

  // Create transfer job and analyze on mount
  useEffect(() => {
    const createAndAnalyze = async () => {
      setLoading(true);
      setError(null);

      try {
        const token = localStorage.getItem('access_token');

        // Step 1: Create transfer job
        const createResponse = await fetch('http://localhost:8000/api/transfers', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            source_provider: 'onedrive',
            dest_provider: 'google_drive',
            source_folder_id: selectedSource[0]?.id || 'root',
            dest_folder_id: destinationFolderId,
            config: {
              file_types: filters.fileTypes,
              date_range: filters.dateRange.startDate || filters.dateRange.endDate ? {
                start_date: filters.dateRange.startDate || null,
                end_date: filters.dateRange.endDate || null
              } : null,
              folder_include: filters.folderInclude,
              folder_exclude: filters.folderExclude,
              conflict_strategy: conflictStrategy
            }
          })
        });

        if (!createResponse.ok) {
          const errorData = await createResponse.json();
          throw new Error(errorData.detail || 'Failed to create transfer');
        }

        const jobData = await createResponse.json();
        setJobId(jobData.id);

        // Step 2: Analyze transfer
        const analyzeResponse = await fetch(`http://localhost:8000/api/transfers/${jobData.id}/analyze`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!analyzeResponse.ok) {
          const errorData = await analyzeResponse.json();
          throw new Error(errorData.detail || 'Failed to analyze transfer');
        }

        // Analysis successful, automatically run dry run
        await new Promise(resolve => setTimeout(resolve, 500)); // Brief delay

      } catch (err: any) {
        setError(err.message || 'Failed to create transfer');
      } finally {
        setLoading(false);
      }
    };

    createAndAnalyze();
  }, []);

  // Auto-run dry run after job is created
  useEffect(() => {
    if (jobId && !dryRunResult && !dryRunning && !error) {
      handleDryRun();
    }
  }, [jobId]);

  // Handle start/schedule transfer
  const handleStartTransfer = async () => {
    if (!jobId) return;

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');

      if (scheduleOption === 'later') {
        // Schedule transfer
        if (!scheduledDate || !scheduledTime) {
          throw new Error('Please select a date and time for scheduling');
        }

        const scheduledDateTime = new Date(`${scheduledDate}T${scheduledTime}`);

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
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to schedule transfer');
        }

        // Redirect to dashboard
        router.push('/dashboard?message=Transfer scheduled successfully');
      } else {
        // Start immediately (we'll use resume endpoint since there's no start endpoint)
        const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/resume`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to start transfer');
        }

        // Redirect to progress page
        router.push(`/transfers/${jobId}/progress`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to start transfer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Review & Confirm Transfer</h1>
        <p className="mt-2 text-gray-600">
          Review your transfer settings and start when ready
        </p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-red-800 font-medium">{error}</span>
          </div>
        </div>
      )}

      {loading && !dryRunResult && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Analyzing transfer...</p>
        </div>
      )}

      {!loading && dryRunResult && (
        <div className="space-y-6">
          {/* Summary Card */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Transfer Summary</h3>
            </div>
            <div className="px-6 py-4">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Source</p>
                  <p className="font-medium text-gray-900">OneDrive</p>
                  <p className="text-sm text-gray-500">{selectedSource.length} item(s) selected</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Destination</p>
                  <p className="font-medium text-gray-900">Google Drive</p>
                  <p className="text-sm text-gray-500">{destinationFolderName || 'Root folder'}</p>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-blue-600 font-medium">Total Files</p>
                  <p className="text-2xl font-bold text-blue-900 mt-1">{dryRunResult.total_files}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-600 font-medium">Total Size</p>
                  <p className="text-2xl font-bold text-green-900 mt-1">{formatSize(dryRunResult.total_size)}</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <p className="text-sm text-purple-600 font-medium">Est. Time</p>
                  <p className="text-2xl font-bold text-purple-900 mt-1">{dryRunResult.estimated_time_minutes}m</p>
                </div>
              </div>
            </div>
          </div>

          {/* Conflicts */}
          {dryRunResult.conflicts > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <div className="flex items-start">
                <svg className="w-6 h-6 text-yellow-600 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <h4 className="text-lg font-semibold text-yellow-900 mb-2">
                    {dryRunResult.conflicts} Conflict(s) Detected
                  </h4>
                  <p className="text-yellow-800 mb-4">
                    Some files already exist at the destination. Choose how to handle conflicts:
                  </p>
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="conflict"
                        value="ask"
                        checked={conflictStrategy === 'ask'}
                        onChange={(e) => setConflictStrategy(e.target.value)}
                        className="text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-900">Ask me for each conflict</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="conflict"
                        value="skip_all"
                        checked={conflictStrategy === 'skip_all'}
                        onChange={(e) => setConflictStrategy(e.target.value)}
                        className="text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-900">Skip all conflicting files</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="conflict"
                        value="rename_all"
                        checked={conflictStrategy === 'rename_all'}
                        onChange={(e) => setConflictStrategy(e.target.value)}
                        className="text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-900">Rename all conflicting files</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="conflict"
                        value="overwrite_all"
                        checked={conflictStrategy === 'overwrite_all'}
                        onChange={(e) => setConflictStrategy(e.target.value)}
                        className="text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-900">Overwrite all existing files</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Scheduling */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">When to Transfer</h3>
            </div>
            <div className="px-6 py-4">
              <div className="space-y-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="schedule"
                    value="now"
                    checked={scheduleOption === 'now'}
                    onChange={(e) => setScheduleOption(e.target.value as 'now')}
                    className="text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-3 text-gray-900 font-medium">Start immediately</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="schedule"
                    value="later"
                    checked={scheduleOption === 'later'}
                    onChange={(e) => setScheduleOption(e.target.value as 'later')}
                    className="text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-3 text-gray-900 font-medium">Schedule for later</span>
                </label>

                {scheduleOption === 'later' && (
                  <div className="ml-7 mt-3 grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Date</label>
                      <input
                        type="date"
                        value={scheduledDate}
                        onChange={(e) => setScheduledDate(e.target.value)}
                        min={new Date().toISOString().split('T')[0]}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Time</label>
                      <input
                        type="time"
                        value={scheduledTime}
                        onChange={(e) => setScheduledTime(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* File Preview (first 10 files) */}
          {dryRunResult.files_to_transfer.length > 0 && (
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Files to Transfer</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Showing {Math.min(10, dryRunResult.files_to_transfer.length)} of {dryRunResult.total_files} file(s)
                </p>
              </div>
              <div className="px-6 py-4">
                <div className="space-y-2">
                  {dryRunResult.files_to_transfer.slice(0, 10).map((file, index) => (
                    <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <div className="flex items-center flex-1 min-w-0">
                        <svg className="w-5 h-5 text-gray-400 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                        </svg>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-gray-900 truncate">{file.source_name}</p>
                          <p className="text-xs text-gray-500">{formatSize(file.size)}</p>
                        </div>
                      </div>
                      {file.has_conflict && (
                        <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded">
                          Conflict
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between">
            <button
              onClick={onBack}
              disabled={loading}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Back
            </button>
            <div className="flex gap-3">
              <button
                onClick={handleDryRun}
                disabled={loading || dryRunning || !jobId}
                className="px-6 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {dryRunning ? 'Running...' : 'Re-run Preview'}
              </button>
              <button
                onClick={handleStartTransfer}
                disabled={loading || !jobId}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Starting...' : scheduleOption === 'now' ? 'Start Transfer' : 'Schedule Transfer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
