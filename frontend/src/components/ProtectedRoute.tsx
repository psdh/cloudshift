'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/lib/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  // Derive the initial auth state synchronously from the stored token so we
  // don't call setState inside the effect (which causes cascading renders).
  const [isAuthenticated] = useState<boolean | null>(() =>
    typeof window === 'undefined' ? null : Boolean(authService.getAccessToken())
  );

  useEffect(() => {
    if (isAuthenticated === false) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  if (isAuthenticated === null || isAuthenticated === false) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return <>{children}</>;
}
