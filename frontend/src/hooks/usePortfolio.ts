import useSWR from 'swr'
import type { TradeOrder, PortfolioSnapshot } from '@/lib/types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const fetcher = (url: string) =>
  fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
    .then(r => r.json())

export function usePortfolio(profileId: number) {
  const { data, error, isLoading, mutate } = useSWR(
    profileId ? `${BASE_URL}/api/v1/portfolio/profile/${profileId}` : null,
    fetcher,
    { refreshInterval: 60000 }
  )
  return { portfolio: data, error, isLoading, refresh: mutate }
}

export function useProfiles() {
  const { data, error, isLoading } = useSWR(`${BASE_URL}/api/v1/profiles/`, fetcher)
  return { profiles: data, error, isLoading }
}

export function usePortfolioHistory(profileId: number | null, days: number = 30) {
  const { data, error, isLoading } = useSWR<PortfolioSnapshot[]>(
    profileId != null
      ? `${BASE_URL}/api/v1/profiles/${profileId}/history?days=${days}`
      : null,
    fetcher
  )
  return { history: data, error, isLoading }
}

export function useTradeHistory(profileId: number | null) {
  const { data, error, isLoading } = useSWR<TradeOrder[]>(
    profileId != null ? `${BASE_URL}/api/v1/profiles/${profileId}/trade` : null,
    fetcher
  )
  const sorted = data
    ? [...data].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    : data
  return { trades: sorted, error, isLoading }
}
