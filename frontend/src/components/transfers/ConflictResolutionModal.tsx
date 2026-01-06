'use client';

import { useState, useEffect } from 'react';

interface ConflictInfo {
  id: number;
  item_id: number;
  source_path: string;
  dest_path: string;
  source_size: number;
  dest_file_exists: boolean;
  resolution: string | null;
  resolved_at: string | null;
}

interface ConflictResolutionModalProps {
  jobId: number;
  isOpen: boolean;
  onClose: () => void;
  onResolved: () => void;
}

export default function ConflictResolutionModal({
  jobId,
  isOpen,
  onClose,
  onResolved
}: ConflictResolutionModalProps) {
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyToAll, setApplyToAll] = useState(false);
  const [previewName, setPreviewName] = useState<string>('');

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Generate renamed filename
  const generateRenamedFilename = (filename: string): string => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const parts = filename.split('.');
    if (parts.length > 1) {
      const extension = parts.pop();
      return `${parts.join('.')}_${timestamp}.${extension}`;
    }
    return `${filename}_${timestamp}`;
  };

  // Fetch conflicts
  const fetchConflicts = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/conflicts`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch conflicts');
      }

      const data = await response.json();

      // Filter only pending conflicts
      const pendingConflicts = data.conflicts.filter((c: ConflictInfo) => !c.resolution);
      setConflicts(pendingConflicts);

      if (pendingConflicts.length === 0) {
        // No conflicts to resolve, close modal
        onResolved();
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch conflicts');
    } finally {
      setLoading(false);
    }
  };

  // Resolve current conflict
  const handleResolve = async (resolution: 'skip' | 'rename' | 'overwrite') => {
    if (conflicts.length === 0) return;

    setResolving(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');

      if (applyToAll) {
        // Resolve all remaining conflicts
        const response = await fetch(`http://localhost:8000/api/transfers/${jobId}/conflicts/resolve-all`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ resolution })
        });

        if (!response.ok) {
          throw new Error('Failed to resolve all conflicts');
        }

        // All conflicts resolved
        onResolved();
        onClose();
      } else {
        // Resolve single conflict
        const currentConflict = conflicts[currentIndex];
        const response = await fetch(
          `http://localhost:8000/api/transfers/${jobId}/conflicts/${currentConflict.id}/resolve`,
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resolution })
          }
        );

        if (!response.ok) {
          throw new Error('Failed to resolve conflict');
        }

        // Move to next conflict or finish
        if (currentIndex + 1 < conflicts.length) {
          setCurrentIndex(currentIndex + 1);
        } else {
          // All conflicts resolved
          onResolved();
          onClose();
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to resolve conflict');
    } finally {
      setResolving(false);
    }
  };

  // Update preview name when rename is hovered
  useEffect(() => {
    if (conflicts.length > 0) {
      const currentConflict = conflicts[currentIndex];
      setPreviewName(generateRenamedFilename(currentConflict.source_path));
    }
  }, [currentIndex, conflicts]);

  // Fetch conflicts when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchConflicts();
      setCurrentIndex(0);
      setApplyToAll(false);
    }
  }, [isOpen, jobId]);

  if (!isOpen) return null;

  const currentConflict = conflicts[currentIndex];
  const progress = conflicts.length > 0 ? ((currentIndex + 1) / conflicts.length) * 100 : 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Resolve File Conflicts</h2>
              <p className="text-sm text-gray-600 mt-1">
                {conflicts.length > 0
                  ? `Conflict ${currentIndex + 1} of ${conflicts.length}`
                  : 'Loading conflicts...'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Progress Bar */}
          {conflicts.length > 0 && (
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {loading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading conflicts...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span className="text-red-800">{error}</span>
              </div>
            </div>
          )}

          {!loading && conflicts.length > 0 && currentConflict && (
            <div className="space-y-6">
              {/* Conflict Details */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                <div className="flex items-start">
                  <svg className="w-8 h-8 text-yellow-600 mr-3 flex-shrink-0 mt-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-yellow-900 mb-2">File Already Exists</h3>
                    <div className="space-y-3">
                      <div>
                        <p className="text-sm font-medium text-yellow-800 mb-1">Filename:</p>
                        <p className="text-sm text-yellow-900 font-mono bg-yellow-100 px-3 py-2 rounded break-all">
                          {currentConflict.source_path}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm font-medium text-yellow-800 mb-1">Source File Size:</p>
                          <p className="text-sm text-yellow-900">{formatSize(currentConflict.source_size)}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-yellow-800 mb-1">Destination:</p>
                          <p className="text-sm text-yellow-900">File exists at destination</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Rename Preview */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-blue-900 mb-2">Rename Preview:</h4>
                <p className="text-sm text-blue-800 font-mono bg-blue-100 px-3 py-2 rounded break-all">
                  {previewName}
                </p>
                <p className="text-xs text-blue-600 mt-2">
                  If you choose "Rename", the file will be saved with a timestamp suffix
                </p>
              </div>

              {/* Resolution Options */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-gray-900">Choose an action:</h4>
                <div className="grid grid-cols-1 gap-3">
                  <button
                    onClick={() => handleResolve('skip')}
                    disabled={resolving}
                    className="flex items-start p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left"
                  >
                    <svg className="w-6 h-6 text-gray-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    <div>
                      <p className="font-semibold text-gray-900">Skip This File</p>
                      <p className="text-sm text-gray-600 mt-1">
                        Don't transfer this file, keep the existing destination file
                      </p>
                    </div>
                  </button>

                  <button
                    onClick={() => handleResolve('rename')}
                    disabled={resolving}
                    className="flex items-start p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left"
                  >
                    <svg className="w-6 h-6 text-gray-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <div>
                      <p className="font-semibold text-gray-900">Rename & Keep Both</p>
                      <p className="text-sm text-gray-600 mt-1">
                        Add a timestamp to the filename and transfer it
                      </p>
                    </div>
                  </button>

                  <button
                    onClick={() => handleResolve('overwrite')}
                    disabled={resolving}
                    className="flex items-start p-4 border-2 border-red-300 rounded-lg hover:border-red-500 hover:bg-red-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left"
                  >
                    <svg className="w-6 h-6 text-red-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                      <p className="font-semibold text-red-900">Overwrite Destination File</p>
                      <p className="text-sm text-red-600 mt-1">
                        Replace the existing file at the destination (cannot be undone)
                      </p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Apply to All Checkbox */}
              {conflicts.length > 1 && (
                <div className="border-t border-gray-200 pt-4">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={applyToAll}
                      onChange={(e) => setApplyToAll(e.target.checked)}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-900">
                      Apply this choice to all remaining {conflicts.length - currentIndex} conflict(s)
                    </span>
                  </label>
                  <p className="text-xs text-gray-500 ml-6 mt-1">
                    This will automatically resolve all conflicts with the same action
                  </p>
                </div>
              )}

              {resolving && (
                <div className="flex items-center justify-center py-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
                  <span className="text-gray-600">Resolving conflict...</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
