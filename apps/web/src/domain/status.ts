export type ValidationStatus =
  | "UNVALIDATABLE"
  | "PENDING_VALIDATION"
  | "VALIDATED"
  | "UNVALIDATED - DO NOT USE WITH REAL CAPITAL";

export type AnalyzeRequest = {
  S0: number;
  sigma_base: number;
  r: number;
  Target: number;
  Bias: "bullish" | "bearish";
  Capital: number;
  Total_Portfolio_Value: number;
  allow_short: boolean;
  ATR_14: number;
  ticker?: string;
  sigma_is_historical_approx?: boolean;
};

export type AnalyzeResponse = {
  status: ValidationStatus | string;
  warnings: string[];
  dte_days: number | null;
  expiry: string | null;
  probabilities: Record<string, number>;
  kc: number | null;
  kp: number | null;
  strike_note: string;
  composition: {
    stock_factor: number;
    nc: number;
    np: number;
    justification: string;
  } | null;
  greeks: {
    delta_net: number;
    gamma_net: number;
    vega_net: number;
    theta_net: number;
  } | null;
  efficiency_net: number | null;
  rebalance_cost: number | null;
  premium_total: number | null;
  capital_at_risk: number | null;
  gap_iv_scenarios: Array<{
    gap: number;
    iv_scenario: string;
    pnl: number;
    accepted: boolean;
    reason?: string | null;
  }>;
  simulation_grid: Array<{
    price: number;
    tau: number;
    delta_net: number;
    value: number;
  }>;
  rejections: string[];
  uncalibrated_placeholders: Record<string, number>;
  disclaimer: string;
  extras?: Record<string, number>;
};

export type ValidationJobRequest = {
  tickers: string[];
  min_trades: number;
  hold_days?: number;
  sample_every_n_days?: number;
};

export type ValidationJob = {
  id: string;
  type: string;
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED" | string;
  payload: ValidationJobRequest;
  result: {
    status: string;
    reason?: string | null;
    phase_a_ok: boolean;
    phase_b?: Record<string, number | string> | null;
    phase_c?: Record<string, number | string | boolean> | null;
    phase_d?: Record<string, number | string> | null;
    ci95?: Record<string, number> | null;
    sensitivity_ok?: boolean;
    disclaimer?: string;
  } | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};
