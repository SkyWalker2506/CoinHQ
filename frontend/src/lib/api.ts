import type {
  Profile,
  ExchangeKey,
  PortfolioResponse,
  AggregatePortfolioResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }
  return res.json();
}

// Profiles
export const getProfiles = () => request<Profile[]>("/api/v1/profiles/");

export const createProfile = (name: string) =>
  request<Profile>("/api/v1/profiles/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });

export const deleteProfile = (id: number) =>
  fetch(`${BASE_URL}/api/v1/profiles/${id}`, { method: "DELETE" });

// Exchange Keys
export const getKeys = (profileId: number) =>
  request<ExchangeKey[]>(`/api/v1/profiles/${profileId}/keys/`);

export const addKey = (
  profileId: number,
  exchange: string,
  api_key: string,
  api_secret: string
) =>
  request<ExchangeKey>(`/api/v1/profiles/${profileId}/keys/`, {
    method: "POST",
    body: JSON.stringify({ exchange, api_key, api_secret }),
  });

export const deleteKey = (profileId: number, keyId: number) =>
  fetch(`${BASE_URL}/api/v1/profiles/${profileId}/keys/${keyId}`, {
    method: "DELETE",
  });

// Portfolio
export const getPortfolio = (profileId: number) =>
  request<PortfolioResponse>(`/api/v1/portfolio/profile/${profileId}`);

export const getAggregatePortfolio = () =>
  request<AggregatePortfolioResponse>("/api/v1/portfolio/aggregate");
