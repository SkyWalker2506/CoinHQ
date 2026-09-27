import useSWR from 'swr'
import type { TradeOrder, PortfolioSnapshot, PnlResponse, CostBasisResponse } from '@/lib/types'
import { getCostBasis } from '@/lib/api'
import { mergeCostBasis } from '@/lib/costBasis'

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

// Cost basis / average buy price. It can take seconds to compute on the
// backend, so it is fetched independently of the portfolio (never blocks the
// dashboard) and changes slowly — no focus/interval revalidation storms.
/**
 * Average buy price for one profile, or for several merged (the dashboard's
 * "All Profiles" view). One SWR entry either way; a profile whose cost basis
 * fails is dropped rather than failing the rest.
 */
export function useCostBasis(profileIds: number[]) {
  const key = profileIds.length > 0 ? `cost-basis:${profileIds.join(',')}` : null
  const { data, error, isLoading } = useSWR<CostBasisResponse | undefined>(
    key,
    async () => {
      const settled = await Promise.allSettled(profileIds.map((id) => getCostBasis(id)))
      return mergeCostBasis(
        settled.flatMap((r) => (r.status === 'fulfilled' ? [r.value] : []))
      )
    },
    { revalidateOnFocus: false, revalidateIfStale: false }
  )
  return { costBasis: data, error, isLoading }
}

export function useProfilePnl(profileId: number | null) {
  const { data, error, isLoading } = useSWR<PnlResponse>(
    profileId != null ? `${BASE_URL}/api/v1/profiles/${profileId}/pnl` : null,
    fetcher
  )
  return { pnl: data, error, isLoading }
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
