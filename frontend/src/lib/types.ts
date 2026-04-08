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
  allow_follow: boolean;
}

export interface ShareLinkCreate {
  profile_id: number;
  show_total_value: boolean;
  show_coin_amounts: boolean;
  show_exchange_names: boolean;
  show_allocation_pct: boolean;
  expires_at: string | null;
  label: string | null;
  allow_follow?: boolean;
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
  token: string;
  profile_name: string;
  total_usd: number | null;
  exchanges: SharedExchange[];
  show_total_value: boolean;
  show_coin_amounts: boolean;
  show_exchange_names: boolean;
  show_allocation_pct: boolean;
  allow_follow: boolean;
}

// Market data (CoinMarketCap)
export interface GlobalMetrics {
  total_market_cap: number | null;
  total_volume_24h: number | null;
  btc_dominance: number | null;
  eth_dominance: number | null;
  active_cryptocurrencies: number | null;
  total_market_cap_change_24h: number | null;
}

export interface MarketCoin {
  name: string;
  symbol: string;
  rank: number;
  price: number | null;
  change_1h: number | null;
  change_24h: number | null;
  change_7d: number | null;
  market_cap: number | null;
  volume_24h: number | null;
}

export interface CoinInfo {
  name: string;
  symbol: string;
  slug: string;
  description: string | null;
  logo: string | null;
  website: string | null;
  explorer: string | null;
  twitter: string | null;
  tags: string[];
  date_added: string | null;
  category: string | null;
}
