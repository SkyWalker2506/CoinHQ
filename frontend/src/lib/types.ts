export interface Profile {
  id: number;
  name: string;
  created_at: string;
}

export interface ExchangeKey {
  id: number;
  profile_id: number;
  exchange: string;
  created_at: string;
}

export interface Balance {
  asset: string;
  free: number;
  locked: number;
  total: number;
  usd_value?: number;
}

export interface ExchangeBalance {
  exchange: string;
  balances: Balance[];
  total_usd: number;
}

export interface PortfolioResponse {
  profile_id: number;
  profile_name: string;
  exchanges: ExchangeBalance[];
  total_usd: number;
  cached: boolean;
}

export interface ProfilePortfolio {
  profile_id: number;
  profile_name: string;
  total_usd: number;
  exchanges: ExchangeBalance[];
}

export interface AggregatePortfolioResponse {
  profiles: ProfilePortfolio[];
  grand_total_usd: number;
  asset_totals: Record<string, number>;
}

export type SupportedExchange = "binance" | "bybit" | "okx";
