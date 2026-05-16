'use client';

import { useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

function OAuthCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    // The backend handles the OAuth flow and redirects here
    // We just need to redirect back to the accounts page with status
    const success = searchParams.get('success');
    const error = searchParams.get('error');

    if (success === 'true') {
      router.push('/settings/accounts?oauth_status=success');
    } else if (error) {
      router.push(`/settings/accounts?oauth_error=${encodeURIComponent(error)}`);
    } else {
      // No clear status, just redirect to accounts
      router.push('/settings/accounts');
    }
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="text-gray-600 mb-4">Processing OAuth callback...</div>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="text-gray-600 mb-4">Processing OAuth callback...</div>
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          </div>
        </div>
      }
    >
      <OAuthCallback />
    </Suspense>
  );
}
