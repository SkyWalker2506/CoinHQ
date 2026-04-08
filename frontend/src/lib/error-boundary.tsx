'use client'
import { Component, ReactNode } from 'react'
import { captureError } from './sentry'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  componentDidCatch(error: Error) {
    console.error('[ErrorBoundary]', error)
    captureError(error, { source: 'ErrorBoundary' })
  }
  render() {
    if (this.state.hasError) return this.props.fallback ?? <div className="text-red-400 p-4">Something went wrong</div>
    return this.props.children
  }
}
