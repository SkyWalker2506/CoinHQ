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

export type SupportedExchange = "binance" | "bybit" | "okx" | "coinbase" | "kraken" | "binancetr";

export interface ShareLink {
  id: number;
  token: string;
  profile_id: number;
  show_total_value: boolean;
  show_coin_amounts: boolean;
  show_exchange_names: boolean;
  show_allocation_pct: boolean;
  expires_at: string | null;
  is_active: boolean;
  label: string | null;
  created_at: string;
  share_url: string;
}

export interface ShareLinkCreate {
  profile_id: number;
  show_total_value: boolean;
  show_coin_amounts: boolean;
  show_exchange_names: boolean;
  show_allocation_pct: boolean;
  expires_at: string | null;
  label: string | null;
}

export interface SharedAsset {
  asset: string;
  amount: number | null;
  usd_value: number | null;
  allocation_pct: number | null;
}

export interface SharedExchange {
  exchange_name: string;
  assets: SharedAsset[];
  total_usd: number | null;
}

export interface SharedPortfolioView {
  total_usd: number | null;
  exchanges: SharedExchange[];
  show_total_value: boolean;
  show_coin_amounts: boolean;
  show_exchange_names: boolean;
  show_allocation_pct: boolean;
}
