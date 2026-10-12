import type {
  BusinessProfile,
  FundingStage,
  Industry,
  InvestorProfile,
  MoneyRange,
  SupportedCurrency,
} from "./domain";

export type UserMode = "founder" | "investor";
export type MatchDirection = "founder_to_investor" | "investor_to_business";
export type ConfidenceLevel = "low" | "medium" | "high";
export type ConcernSeverity = "info" | "warning" | "blocking";
export type AgentActivityStatus = "pending" | "running" | "completed" | "failed";

export type MatchFactor =
  | "industry_alignment"
  | "funding_stage_alignment"
  | "ticket_size_compatibility"
  | "semantic_thesis_similarity"
  | "geographic_alignment"
  | "portfolio_compatibility";

export interface ScoreBreakdown {
  industry_alignment: number;
  funding_stage_alignment: number;
  ticket_size_compatibility: number;
  semantic_thesis_similarity: number;
  geographic_alignment: number;
  portfolio_compatibility: number;
}

export interface MatchEvidence {
  factor: MatchFactor;
  source_entity_id: string;
  source_field: string;
  statement: string;
}

export interface MatchConcern {
  code: string;
  severity: ConcernSeverity;
  message: string;
}

export interface MatchResult {
  direction: MatchDirection;
  query_entity_id: string;
  candidate_entity_id: string;
  candidate_name: string;
  rank: number;
  overall_score: number;
  score_breakdown: ScoreBreakdown;
  evidence: MatchEvidence[];
  concerns: MatchConcern[];
  explanation: string;
  confidence: ConfidenceLevel;
}

export interface MatchConstraints {
  industries: Industry[] | null;
  stages: FundingStage[] | null;
  geographies: string[] | null;
  ticket_size: MoneyRange | null;
  excluded_entity_ids: string[];
  include_exploration_matches: boolean;
  display_currency: SupportedCurrency;
}

export interface MatchRequest {
  mode: UserMode;
  objective: string;
  business_profile: BusinessProfile | null;
  investor_profile: InvestorProfile | null;
  constraints: MatchConstraints;
  top_k: number;
  conversation_id: string | null;
}

export interface RefinementRequest {
  run_id: string;
  instruction: string;
  constraints: MatchConstraints | null;
  top_k: number | null;
}

export interface AgentActivity {
  step: string;
  status: AgentActivityStatus;
  message: string;
}

export interface MatchResponse {
  run_id: string;
  mode: UserMode;
  query_entity_id: string;
  normalized_objective: string;
  matches: MatchResult[];
  activity: AgentActivity[];
  missing_information: string[];
  warnings: string[];
  suggested_refinements: string[];
}

