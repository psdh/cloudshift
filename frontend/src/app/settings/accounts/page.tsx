'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';
import { accountsService, ConnectedAccount } from '@/lib/accounts';

function ConnectedAccountsContent() {
  const searchParams = useSearchParams();
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [disconnecting, setDisconnecting] = useState<string | null>(null);

  useEffect(() => {
    loadAccounts();

    // Check for OAuth callback success/error
    const oauthStatus = searchParams.get('oauth_status');
    const oauthError = searchParams.get('oauth_error');

    if (oauthStatus === 'success') {
      setSuccessMessage('Account connected successfully!');
      setTimeout(() => setSuccessMessage(''), 5000);
    } else if (oauthError) {
      setError(decodeURIComponent(oauthError));
      setTimeout(() => setError(''), 5000);
    }
  }, [searchParams]);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const data = await accountsService.listAccounts();
      setAccounts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounts');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = (provider: 'onedrive' | 'google_drive') => {
    const url =
      provider === 'onedrive'
        ? accountsService.getOneDriveAuthUrl()
        : accountsService.getGoogleAuthUrl();
    window.location.href = url;
  };

  const handleDisconnect = async (provider: 'onedrive' | 'google_drive') => {
    if (
      !confirm(
        `Are you sure you want to disconnect your ${provider === 'onedrive' ? 'OneDrive' : 'Google Drive'} account?`
      )
    ) {
      return;
    }

    try {
      setDisconnecting(provider);
      await accountsService.disconnectAccount(provider);
      setSuccessMessage('Account disconnected successfully');
      setTimeout(() => setSuccessMessage(''), 5000);
      await loadAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect account');
      setTimeout(() => setError(''), 5000);
    } finally {
      setDisconnecting(null);
    }
  };

  const isConnected = (provider: 'onedrive' | 'google_drive') => {
    return accounts.some((acc) => acc.provider === provider);
  };

  const getAccount = (provider: 'onedrive' | 'google_drive') => {
    return accounts.find((acc) => acc.provider === provider);
  };

  return (
    <ProtectedRoute>
      <Layout>
        <div className="py-6 max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Connected Accounts</h1>

          {successMessage && (
            <div className="mb-4 bg-green-50 border border-green-400 text-green-700 px-4 py-3 rounded">
              {successMessage}
            </div>
          )}

          {error && (
            <div className="mb-4 bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <div className="text-gray-600">Loading accounts...</div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* OneDrive Account */}
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold">
                      OD
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">OneDrive</h3>
                      {isConnected('onedrive') ? (
                        <p className="text-sm text-gray-600">
                          Connected as: {getAccount('onedrive')?.account_email}
                        </p>
                      ) : (
                        <p className="text-sm text-gray-500">Not connected</p>
                      )}
                    </div>
                  </div>
                  <div>
                    {isConnected('onedrive') ? (
                      <button
                        onClick={() => handleDisconnect('onedrive')}
                        disabled={disconnecting === 'onedrive'}
                        className="px-4 py-2 border border-red-600 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {disconnecting === 'onedrive' ? 'Disconnecting...' : 'Disconnect'}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleConnect('onedrive')}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                      >
                        Connect OneDrive
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Google Drive Account */}
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center text-white font-bold">
                      GD
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Google Drive</h3>
                      {isConnected('google_drive') ? (
                        <p className="text-sm text-gray-600">
                          Connected as: {getAccount('google_drive')?.account_email}
                        </p>
                      ) : (
                        <p className="text-sm text-gray-500">Not connected</p>
                      )}
                    </div>
                  </div>
                  <div>
                    {isConnected('google_drive') ? (
                      <button
                        onClick={() => handleDisconnect('google_drive')}
                        disabled={disconnecting === 'google_drive'}
                        className="px-4 py-2 border border-red-600 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {disconnecting === 'google_drive' ? 'Disconnecting...' : 'Disconnect'}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleConnect('google_drive')}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                      >
                        Connect Google Drive
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-2">Why connect accounts?</h4>
            <p className="text-sm text-blue-800">
              Connect your OneDrive and Google Drive accounts to enable file transfers. You'll need
              both accounts connected to create a transfer job.
            </p>
          </div>
        </div>
      </Layout>
    </ProtectedRoute>
  );
}

export default function ConnectedAccountsPage() {
  return (
    <Suspense fallback={null}>
      <ConnectedAccountsContent />
    </Suspense>
  );
}
