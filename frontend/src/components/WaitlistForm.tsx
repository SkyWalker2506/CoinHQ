'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { events } from '@/lib/analytics'

const STORAGE_KEY = 'coinhq_waitlist_emails'
// Conservative RFC-5322-ish check; intentionally simple — backend will do strict
// validation when the real signup endpoint lands.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

type SubmissionState = 'idle' | 'submitting' | 'success' | 'error'

interface Props {
  /**
   * Anchor id so existing in-page links (#waitlist) jump here. The pricing
   * card "Join waitlist" CTA scrolls users down to this form.
   */
  anchorId?: string
  /** Plan name for analytics breakdown ("Cloud Premium" by default). */
  planName?: string
}

/**
 * Read the existing waitlist queue from localStorage, returning an empty array
 * if storage is unavailable or contains malformed JSON.
 */
function loadQueue(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((v): v is string => typeof v === 'string')
  } catch {
    return []
  }
}

function saveQueue(queue: string[]): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(queue))
  } catch {
    // Storage may be disabled (private mode, quota); the analytics event
    // still fires so we have a record.
  }
}

export default function WaitlistForm({
  anchorId = 'waitlist',
  planName = 'Cloud Premium',
}: Props) {
  const [email, setEmail] = useState('')
  const [state, setState] = useState<SubmissionState>('idle')
  const [message, setMessage] = useState<string>('')
  const [alreadySubscribed, setAlreadySubscribed] = useState(false)
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)

  // On first paint, surface "already on the list" if this device is in the queue.
  useEffect(() => {
    const queue = loadQueue()
    if (queue.length > 0) {
      setAlreadySubscribed(true)
    }
  }, [])

  function handleSubmit(e: React.FormEvent<HTMLFormElement>): void {
    e.preventDefault()
    const trimmed = email.trim().toLowerCase()
    if (!EMAIL_RE.test(trimmed)) {
      setState('error')
      setMessage('Please enter a valid email address.')
      inputRef.current?.focus()
      return
    }
    setState('submitting')

    const queue = loadQueue()
    const isDuplicate = queue.includes(trimmed)
    if (!isDuplicate) {
      queue.push(trimmed)
      saveQueue(queue)
    }

    // Fire analytics — this is the durable signal even if storage is blocked.
    events.waitlistSubmitted(planName, isDuplicate)

    setState('success')
    setAlreadySubscribed(true)
    setMessage(
      isDuplicate
        ? "You're already on the list — we'll be in touch."
        : "You're on the list. We'll email you when premium opens.",
    )
    setEmail('')
  }

  return (
    <section
      id={anchorId}
      aria-labelledby={`${inputId}-heading`}
      className="mt-16 max-w-xl mx-auto rounded-2xl border border-gray-800 bg-gray-900 p-6 sm:p-8 scroll-mt-16"
    >
      <h2
        id={`${inputId}-heading`}
        className="text-xl font-bold text-white mb-2 text-center"
      >
        Join the Cloud Premium waitlist
      </h2>
      <p className="text-gray-400 text-sm text-center mb-6">
        Get notified when premium hosting opens. No spam, unsubscribe anytime.
      </p>
      <form onSubmit={handleSubmit} noValidate className="flex flex-col sm:flex-row gap-3">
        <label htmlFor={inputId} className="sr-only">
          Email address
        </label>
        <input
          id={inputId}
          ref={inputRef}
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          aria-invalid={state === 'error'}
          aria-describedby={message ? `${inputId}-msg` : undefined}
          placeholder="you@example.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value)
            if (state === 'error') {
              setState('idle')
              setMessage('')
            }
          }}
          className="flex-1 min-w-0 rounded-xl bg-gray-800 border border-gray-700 px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          disabled={state === 'submitting'}
        />
        <button
          type="submit"
          disabled={state === 'submitting' || !email.trim()}
          className="rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium px-5 py-2.5 transition-colors"
        >
          {state === 'submitting' ? 'Adding…' : alreadySubscribed && state !== 'success' ? 'Update email' : 'Notify me'}
        </button>
      </form>
      {message && (
        <p
          id={`${inputId}-msg`}
          role={state === 'error' ? 'alert' : 'status'}
          className={`mt-3 text-sm text-center ${
            state === 'error' ? 'text-red-400' : 'text-green-400'
          }`}
        >
          {message}
        </p>
      )}
    </section>
  )
}
