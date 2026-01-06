'use client';

import { useState, useEffect } from 'react';

interface GoogleDriveItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  size?: number;
  modifiedAt?: string;
  path: string;
}

interface GoogleDriveFileBrowserProps {
  onFolderSelect: (folderId: string, folderName: string) => void;
  selectedFolderId?: string;
}

export default function GoogleDriveFileBrowser({
  onFolderSelect,
  selectedFolderId
}: GoogleDriveFileBrowserProps) {
  const [items, setItems] = useState<GoogleDriveItem[]>([]);
  const [currentPath, setCurrentPath] = useState<Array<{ id: string; name: string }>>([
    { id: 'root', name: 'My Drive' }
  ]);
  const [loading, setLoading] = useState(true);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchFolderContents(currentPath[currentPath.length - 1].id);
  }, [currentPath]);

  const fetchFolderContents = async (folderId: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(
        `http://localhost:8000/api/transfers/browse/google/${folderId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch Google Drive contents');
      }

      const data = await response.json();
      setItems(data.items || []);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching Google Drive contents:', error);
      setLoading(false);
    }
  };

  const handleFolderClick = (item: GoogleDriveItem) => {
    if (item.type === 'folder') {
      setCurrentPath([...currentPath, { id: item.id, name: item.name }]);
    }
  };

  const handleBreadcrumbClick = (index: number) => {
    setCurrentPath(currentPath.slice(0, index + 1));
  };

  const handleSelectFolder = () => {
    const current = currentPath[currentPath.length - 1];
    onFolderSelect(current.id, current.name);
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;

    setCreating(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const currentFolderId = currentPath[currentPath.length - 1].id;

      const response = await fetch(
        'http://localhost:8000/api/transfers/browse/google/create-folder',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            folder_name: newFolderName,
            parent_folder_id: currentFolderId
          })
        }
      );

      if (!response.ok) {
        throw new Error('Failed to create folder');
      }

      // Refresh the current folder
      await fetchFolderContents(currentFolderId);
      setNewFolderName('');
      setShowCreateFolder(false);
    } catch (error) {
      console.error('Error creating folder:', error);
      alert('Failed to create folder');
    } finally {
      setCreating(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const currentFolderId = currentPath[currentPath.length - 1].id;
  const isCurrentSelected = selectedFolderId === currentFolderId;

  // Filter to show only folders
  const folders = items.filter((item) => item.type === 'folder');

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Breadcrumb Navigation */}
      <div className="px-4 py-3 border-b border-gray-200">
        <nav className="flex items-center space-x-2 text-sm">
          {currentPath.map((pathItem, index) => (
            <div key={pathItem.id} className="flex items-center">
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
                {pathItem.name}
              </button>
            </div>
          ))}
        </nav>
      </div>

      {/* Current folder selection */}
      <div className="px-4 py-3 bg-blue-50 border-b border-blue-100 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-900">
            Current folder: <span className="text-blue-600">{currentPath[currentPath.length - 1].name}</span>
          </p>
          {isCurrentSelected && (
            <p className="text-xs text-green-600 mt-1">✓ Selected as destination</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCreateFolder(!showCreateFolder)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
          >
            + New Folder
          </button>
          <button
            onClick={handleSelectFolder}
            className={`px-4 py-1.5 text-sm rounded-lg font-medium transition-colors ${
              isCurrentSelected
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isCurrentSelected ? 'Selected' : 'Select This Folder'}
          </button>
        </div>
      </div>

      {/* Create folder form */}
      {showCreateFolder && (
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="New folder name"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleCreateFolder();
                }
              }}
            />
            <button
              onClick={handleCreateFolder}
              disabled={creating || !newFolderName.trim()}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                creating || !newFolderName.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => {
                setShowCreateFolder(false);
                setNewFolderName('');
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Folder List */}
      <div className="overflow-auto" style={{ maxHeight: '400px' }}>
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-600">Loading folders...</p>
          </div>
        ) : folders.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="w-12 h-12 text-gray-400 mx-auto mb-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
              />
            </svg>
            <p className="text-sm text-gray-600">No folders in this directory</p>
            <p className="text-xs text-gray-500 mt-1">Create a new folder to get started</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Folder Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Modified
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {folders.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 cursor-pointer">
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleFolderClick(item)}
                      className="flex items-center text-left w-full"
                    >
                      <svg
                        className="w-5 h-5 text-blue-500 mr-2"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-900">{item.name}</span>
                    </button>
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
