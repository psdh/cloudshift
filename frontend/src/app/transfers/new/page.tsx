'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';
import OneDriveFileBrowser from '@/components/transfers/OneDriveFileBrowser';
import GoogleDriveFileBrowser from '@/components/transfers/GoogleDriveFileBrowser';

interface OneDriveItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  size?: number;
  modifiedAt?: string;
  path: string;
}

export default function NewTransferPage() {
  const router = useRouter();
  const [step, setStep] = useState(1); // 1: source, 2: destination, 3: filters, 4: review
  const [selectedSource, setSelectedSource] = useState<OneDriveItem[]>([]);
  const [destinationFolderId, setDestinationFolderId] = useState<string>('');
  const [destinationFolderName, setDestinationFolderName] = useState<string>('');

  const handleNext = () => {
    if (step === 1 && selectedSource.length === 0) {
      alert('Please select at least one file or folder');
      return;
    }
    if (step === 2 && !destinationFolderId) {
      alert('Please select a destination folder');
      return;
    }
    setStep(step + 1);
  };

  const handleDestinationSelect = (folderId: string, folderName: string) => {
    setDestinationFolderId(folderId);
    setDestinationFolderName(folderName);
  };

  const handleBack = () => {
    if (step === 1) {
      router.push('/dashboard');
    } else {
      setStep(step - 1);
    }
  };

  return (
    <ProtectedRoute>
      <Layout>
        <div className="py-6 max-w-6xl mx-auto">
          {/* Progress Indicator */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center">
                  {[
                    { num: 1, label: 'Source' },
                    { num: 2, label: 'Destination' },
                    { num: 3, label: 'Filters' },
                    { num: 4, label: 'Review' },
                  ].map((item, index) => (
                    <div key={item.num} className="flex items-center flex-1">
                      <div
                        className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                          step >= item.num
                            ? 'border-blue-600 bg-blue-600 text-white'
                            : 'border-gray-300 bg-white text-gray-500'
                        }`}
                      >
                        {item.num}
                      </div>
                      <div className="ml-3">
                        <p
                          className={`text-sm font-medium ${
                            step >= item.num ? 'text-blue-600' : 'text-gray-500'
                          }`}
                        >
                          {item.label}
                        </p>
                      </div>
                      {index < 3 && (
                        <div
                          className={`flex-1 h-0.5 mx-4 ${
                            step > item.num ? 'bg-blue-600' : 'bg-gray-300'
                          }`}
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Step 1: Source Selection */}
          {step === 1 && (
            <div>
              <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">Select Source Files</h1>
                <p className="mt-2 text-gray-600">
                  Choose the files and folders you want to transfer from OneDrive
                </p>
              </div>

              <OneDriveFileBrowser onSelectionChange={setSelectedSource} />

              <div className="mt-6 flex justify-between">
                <button
                  onClick={handleBack}
                  className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleNext}
                  disabled={selectedSource.length === 0}
                  className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                    selectedSource.length === 0
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
                >
                  Next: Choose Destination
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Destination Selection */}
          {step === 2 && (
            <div>
              <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">Select Destination Folder</h1>
                <p className="mt-2 text-gray-600">
                  Choose the Google Drive folder where you want to transfer your files
                </p>
              </div>

              <GoogleDriveFileBrowser
                onFolderSelect={handleDestinationSelect}
                selectedFolderId={destinationFolderId}
              />

              <div className="mt-6 flex justify-between">
                <button
                  onClick={handleBack}
                  className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={handleNext}
                  disabled={!destinationFolderId}
                  className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                    !destinationFolderId
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
                >
                  Next: Configure Filters
                </button>
              </div>
            </div>
          )}

          {/* Steps 3-4 will be implemented in subsequent tasks (11.4-11.5) */}
          {step > 2 && (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Step {step} - Coming Soon
              </h2>
              <p className="text-gray-600 mb-6">
                This step will be implemented in Tasks 11.4-11.5
              </p>
              <button
                onClick={handleBack}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Go Back
              </button>
            </div>
          )}
        </div>
      </Layout>
    </ProtectedRoute>
  );
}
