import type {
  Profile,
  ExchangeKey,
  PortfolioResponse,
  AggregatePortfolioResponse,
  ShareLink,
  ShareLinkCreate,
  SharedPortfolioView,
  GlobalMetrics,
  MarketCoin,
  CoinInfo,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

function getAuthHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...(options?.headers as Record<string, string> | undefined),
    },
  });

  // Handle expired token — try refresh once
  if (res.status === 401 && getToken()) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryRes = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${newToken}`,
          ...(options?.headers as Record<string, string> | undefined),
        },
      });
      if (retryRes.ok) return retryRes.json();
      if (retryRes.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        throw new Error("Session expired. Please log in again.");
      }
      const error = await retryRes.json().catch(() => ({ detail: retryRes.statusText }));
      throw new Error(error.detail ?? "Request failed");
    }
    // Refresh failed — clear tokens and redirect
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
    throw new Error("Session expired. Please log in again.");
  }

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
  fetch(`${BASE_URL}/api/v1/profiles/${id}`, { method: "DELETE", headers: getAuthHeader() });

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
    headers: getAuthHeader(),
  });

// Portfolio
export const getPortfolio = (profileId: number) =>
  request<PortfolioResponse>(`/api/v1/portfolio/profile/${profileId}`);

export const getAggregatePortfolio = () =>
  request<AggregatePortfolioResponse>("/api/v1/portfolio/aggregate");

// Share Links
export const getShareLinks = (profileId?: number) => {
  const q = profileId != null ? `?profile_id=${profileId}` : "";
  return request<ShareLink[]>(`/api/v1/share${q}`);
};

export const createShareLink = (payload: ShareLinkCreate) =>
  request<ShareLink>("/api/v1/share", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const revokeShareLink = (id: number) =>
  fetch(`${BASE_URL}/api/v1/share/${id}`, { method: "DELETE", headers: getAuthHeader() });

export const getPublicShare = (token: string) =>
  request<SharedPortfolioView>(`/api/v1/public/share/${token}`);

// Market Data (CoinMarketCap)
export const getGlobalMetrics = () =>
  request<GlobalMetrics>("/api/v1/market/global");

export const getMarketListings = (limit = 100) =>
  request<Record<string, MarketCoin>>(`/api/v1/market/listings?limit=${limit}`);

export const getCoinInfo = (symbol: string) =>
  request<CoinInfo>(`/api/v1/market/coin/${symbol}`);

export const getCoinsInfo = (symbols: string[]) =>
  request<Record<string, CoinInfo>>(`/api/v1/market/coins?symbols=${symbols.join(",")}`);
