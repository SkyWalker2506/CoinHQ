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

// Trading Analysis (TradingView MCP)
export interface TradingSummary {
  recommendation: string;
  buy: number;
  sell: number;
  neutral: number;
}

export interface TradingPrice {
  close: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  change: number | null;
}

export interface TradingIndicators {
  rsi: number | null;
  macd: { macd: number | null; signal: number | null };
  bollinger: { upper: number | null; lower: number | null; basis: number | null };
  ema: Record<string, number | null>;
  sma: Record<string, number | null>;
  adx: number | null;
  atr: number | null;
  stoch_k: number | null;
  stoch_d: number | null;
  cci: number | null;
}

export interface CoinAnalysis {
  symbol: string;
  exchange: string;
  interval: string;
  summary: TradingSummary;
  price: TradingPrice;
  indicators: TradingIndicators;
  metrics: Record<string, unknown>;
  momentum: Record<string, unknown>;
  bb_signal: Record<string, unknown>;
}

export interface MultiTimeframeAnalysis {
  symbol: string;
  exchange: string;
  timeframes: Record<string, CoinAnalysis & { error?: string }>;
  alignment: string;
}

export interface BacktestResult {
  symbol: string;
  strategy: string;
  period: string;
  total_return_pct: number;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate: number | null;
  total_trades: number;
  final_equity: number;
  buy_hold_return_pct: number | null;
  trade_log?: Array<Record<string, unknown>>;
  error?: string;
}

export interface StrategyComparison {
  symbol: string;
  results: Record<string, BacktestResult>;
  best_strategy: string;
}
