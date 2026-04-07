import useSWR from 'swr'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const fetcher = (url: string) =>
  fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
    .then(r => r.json())

export function usePortfolio(profileId: number) {
  const { data, error, isLoading, mutate } = useSWR(
    profileId ? `${BASE_URL}/api/v1/portfolio/${profileId}` : null,
    fetcher,
    { refreshInterval: 60000 }
  )
  return { portfolio: data, error, isLoading, refresh: mutate }
}

export function useProfiles() {
  const { data, error, isLoading } = useSWR(`${BASE_URL}/api/v1/profiles/`, fetcher)
  return { profiles: data, error, isLoading }
}
