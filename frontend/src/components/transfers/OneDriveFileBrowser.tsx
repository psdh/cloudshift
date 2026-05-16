'use client';

import { useState, useEffect, useCallback } from 'react';

interface OneDriveItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  size?: number;
  modifiedAt?: string;
  path: string;
}

interface OneDriveFileBrowserProps {
  onSelectionChange: (selectedItems: OneDriveItem[]) => void;
}

export default function OneDriveFileBrowser({ onSelectionChange }: OneDriveFileBrowserProps) {
  const [items, setItems] = useState<OneDriveItem[]>([]);
  const [currentPath, setCurrentPath] = useState<string[]>(['root']);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [selectAll, setSelectAll] = useState(false);

  const fetchFolderContents = useCallback(async (folderId: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      // Mock data for now - in real implementation, this would call the backend API
      // which would fetch from OneDrive Microsoft Graph API
      await new Promise((resolve) => setTimeout(resolve, 500)); // Simulate network delay

      const mockItems: OneDriveItem[] = [
        {
          id: '1',
          name: 'Documents',
          type: 'folder',
          path: `/root/${folderId}/Documents`,
        },
        {
          id: '2',
          name: 'Photos',
          type: 'folder',
          path: `/root/${folderId}/Photos`,
        },
        {
          id: '3',
          name: 'Work Files',
          type: 'folder',
          path: `/root/${folderId}/Work Files`,
        },
        {
          id: '4',
          name: 'presentation.pptx',
          type: 'file',
          size: 2457600,
          modifiedAt: '2026-01-05T10:30:00Z',
          path: `/root/${folderId}/presentation.pptx`,
        },
        {
          id: '5',
          name: 'report.pdf',
          type: 'file',
          size: 524288,
          modifiedAt: '2026-01-04T15:20:00Z',
          path: `/root/${folderId}/report.pdf`,
        },
        {
          id: '6',
          name: 'budget.xlsx',
          type: 'file',
          size: 102400,
          modifiedAt: '2026-01-03T09:15:00Z',
          path: `/root/${folderId}/budget.xlsx`,
        },
      ];

      setItems(mockItems);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching OneDrive contents:', error);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFolderContents(currentPath[currentPath.length - 1]);
  }, [currentPath, fetchFolderContents]);

  useEffect(() => {
    // Notify parent of selection changes
    const selected = items.filter((item) => selectedItems.has(item.id));
    onSelectionChange(selected);
    // onSelectionChange is intentionally omitted: parents may pass an
    // unstable callback and including it would cause an update loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedItems, items]);

  const handleItemClick = (item: OneDriveItem) => {
    if (item.type === 'folder') {
      setCurrentPath([...currentPath, item.id]);
      setSelectedItems(new Set()); // Clear selection when navigating
      setSelectAll(false);
    }
  };

  const handleItemSelect = (itemId: string, event: React.ChangeEvent<HTMLInputElement>) => {
    const newSelected = new Set(selectedItems);
    if (event.target.checked) {
      newSelected.add(itemId);
    } else {
      newSelected.delete(itemId);
      setSelectAll(false);
    }
    setSelectedItems(newSelected);
  };

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    const checked = event.target.checked;
    setSelectAll(checked);
    if (checked) {
      setSelectedItems(new Set(items.map((item) => item.id)));
    } else {
      setSelectedItems(new Set());
    }
  };

  const handleBreadcrumbClick = (index: number) => {
    setCurrentPath(currentPath.slice(0, index + 1));
    setSelectedItems(new Set());
    setSelectAll(false);
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const getSelectedStats = () => {
    const selected = items.filter((item) => selectedItems.has(item.id));
    const fileCount = selected.filter((item) => item.type === 'file').length;
    const folderCount = selected.filter((item) => item.type === 'folder').length;
    const totalSize = selected.reduce((sum, item) => sum + (item.size || 0), 0);
    return { fileCount, folderCount, totalSize };
  };

  const stats = getSelectedStats();

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Breadcrumb Navigation */}
      <div className="px-4 py-3 border-b border-gray-200">
        <nav className="flex items-center space-x-2 text-sm">
          {currentPath.map((path, index) => (
            <div key={index} className="flex items-center">
              {index > 0 && (
                <svg
                  className="w-4 h-4 text-gray-400 mx-2"
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
              )}
              <button
                onClick={() => handleBreadcrumbClick(index)}
                className={`font-medium ${
                  index === currentPath.length - 1
                    ? 'text-gray-900'
                    : 'text-blue-600 hover:text-blue-700'
                }`}
              >
                {path === 'root' ? 'OneDrive' : path}
              </button>
            </div>
          ))}
        </nav>
      </div>

      {/* Selection Stats */}
      {selectedItems.size > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 text-sm text-blue-900">
          Selected: {stats.fileCount} file{stats.fileCount !== 1 ? 's' : ''}
          {stats.folderCount > 0 &&
            `, ${stats.folderCount} folder${stats.folderCount !== 1 ? 's' : ''}`}
          {stats.totalSize > 0 && ` (${formatBytes(stats.totalSize)})`}
        </div>
      )}

      {/* File List */}
      <div className="overflow-auto" style={{ maxHeight: '500px' }}>
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-600">Loading files...</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-4 py-3 text-left w-12">
                  <input
                    type="checkbox"
                    checked={selectAll}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Modified
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className={`hover:bg-gray-50 ${
                    selectedItems.has(item.id) ? 'bg-blue-50' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedItems.has(item.id)}
                      onChange={(e) => handleItemSelect(item.id, e)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleItemClick(item)}
                      className="flex items-center text-left w-full"
                    >
                      {item.type === 'folder' ? (
                        <svg
                          className="w-5 h-5 text-blue-500 mr-2"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                        </svg>
                      ) : (
                        <svg
                          className="w-5 h-5 text-gray-400 mr-2"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                      <span className="text-sm font-medium text-gray-900">
                        {item.name}
                      </span>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {item.size ? formatBytes(item.size) : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {item.modifiedAt
                      ? new Date(item.modifiedAt).toLocaleDateString()
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
