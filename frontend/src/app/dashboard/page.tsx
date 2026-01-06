'use client';

import Link from 'next/link';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Layout>
        <div className="py-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Link
              href="/settings/accounts"
              className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Connected Accounts
              </h3>
              <p className="text-sm text-gray-600">
                Manage your OneDrive and Google Drive connections
              </p>
            </Link>
            <div className="bg-white shadow rounded-lg p-6 opacity-50 cursor-not-allowed">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Transfer Jobs
              </h3>
              <p className="text-sm text-gray-600">
                View and manage your file transfers (Coming soon)
              </p>
            </div>
            <Link
              href="/audit-logs"
              className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Activity Log
              </h3>
              <p className="text-sm text-gray-600">
                Review your account activity and audit logs
              </p>
            </Link>
          </div>
        </div>
      </Layout>
    </ProtectedRoute>
  );
}
