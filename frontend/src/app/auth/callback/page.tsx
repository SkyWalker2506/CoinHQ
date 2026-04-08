'use client'
import { Suspense, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

function AuthCallbackInner() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const token = searchParams.get('token')
    const refreshToken = searchParams.get('refresh_token')
    if (token) {
      localStorage.setItem('token', token)
      if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken)
      }
      router.replace('/dashboard')
    } else {
      router.replace('/login?error=auth_failed')
    }
  }, [searchParams, router])

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-gray-400">Logging you in...</div>
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400">Logging you in...</div>
      </div>
    }>
      <AuthCallbackInner />
    </Suspense>
  )
}
