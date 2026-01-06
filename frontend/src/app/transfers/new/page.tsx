'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';
import OneDriveFileBrowser from '@/components/transfers/OneDriveFileBrowser';

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

  const handleNext = () => {
    if (step === 1 && selectedSource.length === 0) {
      alert('Please select at least one file or folder');
      return;
    }
    // For now, just show an alert - full flow will be implemented in subsequent tasks
    alert(`Source selection complete! Selected ${selectedSource.length} items.\n\nNext steps (Task 11.3-11.5):\n- Destination selection (Google Drive)\n- Filter configuration\n- Review and confirm`);
    // setStep(step + 1);
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

          {/* Steps 2-4 will be implemented in subsequent tasks (11.3-11.5) */}
          {step > 1 && (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Step {step} - Coming Soon
              </h2>
              <p className="text-gray-600 mb-6">
                This step will be implemented in Tasks 11.3-11.5
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
