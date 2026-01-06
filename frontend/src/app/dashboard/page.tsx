'use client';

import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Layout>
        <div className="py-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>
          <div className="bg-white shadow rounded-lg p-6">
            <p className="text-gray-600 mb-4">
              Welcome to CloudShift! Your dashboard is ready.
            </p>
            <p className="text-sm text-gray-500">
              More features coming soon...
            </p>
          </div>
        </div>
      </Layout>
    </ProtectedRoute>
  );
}
