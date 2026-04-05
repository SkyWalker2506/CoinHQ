import useSWR from 'swr'

const fetcher = (url: string) =>
  fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
    .then(r => r.json())

export function usePortfolio(profileId: number) {
  const { data, error, isLoading, mutate } = useSWR(
    profileId ? `/api/v1/portfolio/${profileId}` : null,
    fetcher,
    { refreshInterval: 60000 } // 60s auto-refresh
  )
  return { portfolio: data, error, isLoading, refresh: mutate }
}

export function useProfiles() {
  const { data, error, isLoading } = useSWR('/api/v1/profiles/', fetcher)
  return { profiles: data, error, isLoading }
}
