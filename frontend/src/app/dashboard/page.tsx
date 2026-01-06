'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/lib/auth';
import Layout from '@/components/Layout';

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated
    const token = authService.getAccessToken();
    if (!token) {
      router.push('/login');
    } else {
      setLoading(false);
    }
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
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
  );
}
