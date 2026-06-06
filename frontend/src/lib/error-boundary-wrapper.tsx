"use client";

import { ErrorBoundary } from "./error-boundary";

export function ErrorBoundaryWrapper({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-950">
          <div className="text-center px-4">
            <h1 className="text-2xl font-bold text-white mb-2">Something went wrong</h1>
            <p className="text-gray-400 mb-4">An unexpected error occurred. Please try refreshing the page.</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Refresh Page
            </button>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
