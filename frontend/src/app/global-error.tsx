'use client'
import { useEffect } from 'react'
import { captureError } from '@/lib/sentry'

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    captureError(error, { source: 'GlobalError' })
  }, [error])

  return (
    <html>
      <body className="bg-gray-950 flex items-center justify-center min-h-screen">
        <div className="text-center p-8">
          <h2 className="text-xl font-bold text-white mb-4">Something went wrong</h2>
          <button onClick={reset} className="px-4 py-2 bg-blue-600 text-white rounded-lg">
            Try again
          </button>
        </div>
      </body>
    </html>
  )
}
