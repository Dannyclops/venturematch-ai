import type {
  BusinessModel, BusinessProfile, FundingStage, Industry, InvestmentRole,
  InvestorProfile, InvestorType, StageFlexibility, SupportedCurrency,
} from "./domain";
import type { MatchResponse } from "./matching";

export interface ProfilePage<T extends BusinessProfile | InvestorProfile> {
  items: T[];
  total: number;
  next_offset: number | null;
  notice: string;
}

export interface HealthResponse {
  status: "ok";
  execution_mode: "engine_only";
  live_agent_enabled: false;
}

export interface MetadataResponse {
  execution_mode: "engine_only";
  industries: Industry[];
  funding_stages: FundingStage[];
  currencies: SupportedCurrency[];
  business_models: BusinessModel[];
  investor_types: InvestorType[];
  investment_roles: InvestmentRole[];
  stage_flexibility: StageFlexibility[];
  fx_snapshot: {
    base_currency: SupportedCurrency;
    as_of: string;
    source: string;
    is_live: boolean;
    rates: { currency: SupportedCurrency; rate_to_base: string }[];
    notice: string;
  };
  notice: string;
}

export interface EngineMatchResponse {
  execution_mode: "engine_only";
  response: MatchResponse;
  considered_count: number;
  display_currency: SupportedCurrency;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    issues: { location: (string | number)[]; code: string }[];
  };
}
