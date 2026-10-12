/** Shared JSON contracts returned by the VentureMatch backend. */

export type FundingStage =
  | "bootstrapped"
  | "pre_seed"
  | "seed"
  | "series_a"
  | "series_b"
  | "series_c_plus"
  | "growth";

export type Industry =
  | "agritech"
  | "climate_tech"
  | "consumer"
  | "cybersecurity"
  | "e_commerce"
  | "edtech"
  | "enterprise_software"
  | "fintech"
  | "healthtech"
  | "logistics_mobility";

export type BusinessModel =
  | "b2b"
  | "b2c"
  | "b2b2c"
  | "d2c"
  | "marketplace"
  | "saas"
  | "other";

export interface Location {
  country_code: string;
  city: string | null;
  region: string | null;
}

export interface MoneyAmount {
  amount: number;
  currency: string;
}

export interface MoneyRange {
  minimum: number;
  maximum: number;
  currency: string;
}

export interface TractionMetrics {
  is_revenue_generating: boolean;
  annual_revenue: MoneyAmount | null;
  monthly_recurring_revenue: MoneyAmount | null;
  active_users: number | null;
  customers: number | null;
  year_over_year_growth_percent: number | null;
}

export interface BusinessProfile {
  id: string;
  name: string;
  one_liner: string;
  description: string;
  primary_industry: Industry;
  industry_tags: string[];
  headquarters: Location;
  operating_markets: string[];
  funding_stage: FundingStage;
  amount_raising: MoneyAmount;
  business_model: BusinessModel;
  founded_year: number | null;
  team_size: number | null;
  traction: TractionMetrics | null;
  keywords: string[];
}

export type InvestorType =
  | "angel"
  | "corporate_vc"
  | "family_office"
  | "micro_vc"
  | "venture_capital";

export type InvestmentRole = "lead" | "follow" | "flexible";

export interface PortfolioCompany {
  id: string;
  name: string;
  one_liner: string;
  primary_industry: Industry;
  headquarters: Location;
  funding_stage_at_investment: FundingStage;
  business_model: BusinessModel;
  keywords: string[];
}

export interface InvestorProfile {
  id: string;
  name: string;
  investor_type: InvestorType;
  thesis: string;
  preferred_industries: Industry[];
  excluded_industries: Industry[];
  preferred_stages: FundingStage[];
  ticket_size: MoneyRange;
  preferred_geographies: string[];
  investment_role: InvestmentRole;
  actively_investing: boolean;
  requires_revenue: boolean;
  portfolio_company_ids: string[];
  keywords: string[];
}

