'use client';

import React from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { authService } from "@/lib/auth";

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { logout } = useAuth();
  const isAuthenticated = typeof window !== 'undefined' && authService.getAccessToken();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-blue-600 text-white shadow-md">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <Link href={isAuthenticated ? "/dashboard" : "/"}>
              <h1 className="text-2xl font-bold cursor-pointer">CloudShift</h1>
            </Link>
            <p className="text-sm text-blue-100">Cloud File Migration Made Easy</p>
          </div>
          {isAuthenticated && (
            <button
              onClick={logout}
              className="bg-blue-700 hover:bg-blue-800 px-4 py-2 rounded transition-colors"
            >
              Logout
            </button>
          )}
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-8">{children}</main>

      <footer className="bg-gray-100 border-t border-gray-200">
        <div className="container mx-auto px-4 py-6 text-center text-gray-600 text-sm">
          &copy; 2026 CloudShift. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
