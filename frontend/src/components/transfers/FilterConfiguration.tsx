'use client';

import { useState, useEffect } from 'react';

export interface TransferFilters {
  fileTypes: string[];
  dateRange: {
    startDate: string;
    endDate: string;
  };
  folderInclude: string[];
  folderExclude: string[];
}

interface FilterConfigurationProps {
  onFiltersChange: (filters: TransferFilters) => void;
  initialFilters?: TransferFilters;
}

const COMMON_FILE_TYPES = [
  { label: 'Documents', extensions: ['.pdf', '.doc', '.docx', '.txt', '.rtf'], color: 'blue' },
  { label: 'Spreadsheets', extensions: ['.xls', '.xlsx', '.csv'], color: 'green' },
  { label: 'Presentations', extensions: ['.ppt', '.pptx'], color: 'orange' },
  { label: 'Images', extensions: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'], color: 'purple' },
  { label: 'Videos', extensions: ['.mp4', '.avi', '.mov', '.wmv', '.flv'], color: 'red' },
  { label: 'Audio', extensions: ['.mp3', '.wav', '.flac', '.aac', '.ogg'], color: 'pink' },
  { label: 'Archives', extensions: ['.zip', '.rar', '.7z', '.tar', '.gz'], color: 'yellow' },
];

export default function FilterConfiguration({
  onFiltersChange,
  initialFilters
}: FilterConfigurationProps) {
  const [selectedFileTypes, setSelectedFileTypes] = useState<Set<string>>(
    new Set(initialFilters?.fileTypes || [])
  );
  const [startDate, setStartDate] = useState(initialFilters?.dateRange.startDate || '');
  const [endDate, setEndDate] = useState(initialFilters?.dateRange.endDate || '');
  const [includeFolders, setIncludeFolders] = useState<string>(
    initialFilters?.folderInclude?.join(', ') || ''
  );
  const [excludeFolders, setExcludeFolders] = useState<string>(
    initialFilters?.folderExclude?.join(', ') || ''
  );
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Notify parent of filter changes
  useEffect(() => {
    const filters: TransferFilters = {
      fileTypes: Array.from(selectedFileTypes),
      dateRange: {
        startDate,
        endDate
      },
      folderInclude: includeFolders
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
      folderExclude: excludeFolders
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
    };
    onFiltersChange(filters);
  }, [selectedFileTypes, startDate, endDate, includeFolders, excludeFolders]);

  const toggleFileType = (extension: string) => {
    const newSelected = new Set(selectedFileTypes);
    if (newSelected.has(extension)) {
      newSelected.delete(extension);
    } else {
      newSelected.add(extension);
    }
    setSelectedFileTypes(newSelected);
  };

  const toggleCategory = (extensions: string[]) => {
    const allSelected = extensions.every((ext) => selectedFileTypes.has(ext));
    const newSelected = new Set(selectedFileTypes);

    if (allSelected) {
      // Deselect all in category
      extensions.forEach((ext) => newSelected.delete(ext));
    } else {
      // Select all in category
      extensions.forEach((ext) => newSelected.add(ext));
    }

    setSelectedFileTypes(newSelected);
  };

  const clearAllFilters = () => {
    setSelectedFileTypes(new Set());
    setStartDate('');
    setEndDate('');
    setIncludeFolders('');
    setExcludeFolders('');
  };

  const hasActiveFilters = selectedFileTypes.size > 0 || startDate || endDate || includeFolders || excludeFolders;

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Filter Configuration</h3>
            <p className="text-sm text-gray-600 mt-1">
              Optionally filter which files to transfer
            </p>
          </div>
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
            >
              Clear All Filters
            </button>
          )}
        </div>
      </div>

      <div className="px-6 py-4 space-y-6">
        {/* File Type Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-3">
            File Types
            {selectedFileTypes.size > 0 && (
              <span className="ml-2 text-xs text-blue-600">({selectedFileTypes.size} selected)</span>
            )}
          </label>
          <div className="space-y-2">
            {COMMON_FILE_TYPES.map((category) => {
              const allSelected = category.extensions.every((ext) =>
                selectedFileTypes.has(ext)
              );
              const someSelected = category.extensions.some((ext) =>
                selectedFileTypes.has(ext)
              );

              return (
                <div key={category.label} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <button
                      onClick={() => toggleCategory(category.extensions)}
                      className="flex items-center hover:text-blue-600 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={() => toggleCategory(category.extensions)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-2"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="text-sm font-medium text-gray-900">
                        {category.label}
                      </span>
                      {someSelected && !allSelected && (
                        <span className="ml-2 text-xs text-gray-500">(partial)</span>
                      )}
                    </button>
                    <div className="flex flex-wrap gap-1">
                      {category.extensions.slice(0, 3).map((ext) => (
                        <span
                          key={ext}
                          className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded"
                        >
                          {ext}
                        </span>
                      ))}
                      {category.extensions.length > 3 && (
                        <span className="text-xs px-2 py-0.5 text-gray-500">
                          +{category.extensions.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Date Range Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-3">
            Date Range (Modified Date)
          </label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-600 mb-1">From</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">To</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          {startDate && endDate && new Date(startDate) > new Date(endDate) && (
            <p className="text-xs text-red-600 mt-1">Start date must be before end date</p>
          )}
        </div>

        {/* Advanced Filters */}
        <div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
          >
            <svg
              className={`w-4 h-4 mr-1 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
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
            Advanced Folder Filters
          </button>

          {showAdvanced && (
            <div className="mt-3 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Include Only These Folders
                </label>
                <input
                  type="text"
                  value={includeFolders}
                  onChange={(e) => setIncludeFolders(e.target.value)}
                  placeholder="e.g., Work, Personal, Projects (comma-separated)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Only files within these folders will be transferred
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Exclude These Folders
                </label>
                <input
                  type="text"
                  value={excludeFolders}
                  onChange={(e) => setExcludeFolders(e.target.value)}
                  placeholder="e.g., Temp, Cache, Archive (comma-separated)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Files within these folders will be skipped
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Filter Summary */}
        {hasActiveFilters && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Active Filters:</h4>
            <ul className="space-y-1 text-sm text-blue-800">
              {selectedFileTypes.size > 0 && (
                <li>
                  • File types: {Array.from(selectedFileTypes).slice(0, 5).join(', ')}
                  {selectedFileTypes.size > 5 && ` (+${selectedFileTypes.size - 5} more)`}
                </li>
              )}
              {startDate && <li>• Modified after: {new Date(startDate).toLocaleDateString()}</li>}
              {endDate && <li>• Modified before: {new Date(endDate).toLocaleDateString()}</li>}
              {includeFolders && <li>• Include folders: {includeFolders}</li>}
              {excludeFolders && <li>• Exclude folders: {excludeFolders}</li>}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
