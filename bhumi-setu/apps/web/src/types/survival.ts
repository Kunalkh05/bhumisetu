/**
 * Survival Risk, Calibration & Explainability Types (LOOP 11 & LOOP 12)
 *
 * Reflects backend schemas from `app.schemas.survival_risk` and ensures
 * strict role-based field separation, non-causal explanation phrasing,
 * and prominent statistical uncertainty indicators.
 */

export type StatutoryTransition =
  | 'SECTION_11_TO_SECTION_19'
  | 'SECTION_19_TO_AWARD'
  | 'CASE_INITIATION_TO_MILESTONE';

export type SurvivalHorizon = 30 | 90 | 180 | 365 | 730;

export interface ExtrapolationFlags {
  '30d'?: boolean;
  '90d'?: boolean;
  '180d'?: boolean;
  '365d'?: boolean;
  '730d'?: boolean;
  [key: string]: boolean | undefined;
}

export interface OfficerSurvivalRisk {
  case_id: string;
  snapshot_date: string;
  transition: StatutoryTransition | string;
  model_version: string;
  linear_predictor: number;
  relative_hazard: number;
  survival_probability_30d: number;
  survival_probability_90d: number;
  survival_probability_180d: number;
  survival_probability_365d: number;
  survival_probability_730d: number;
  event_probability_30d: number;
  event_probability_90d: number;
  event_probability_180d: number;
  event_probability_365d: number;
  event_probability_730d: number;
  risk_band_90d: string;
  calibration_status: string;
  uncertainty_status: string;
  extrapolation_status: ExtrapolationFlags;
  data_quality_warning: string;
  governance_disclaimer: string;
  is_degraded_simulation?: boolean;
  mode_label?: 'LIVE_MODEL_INFERENCE' | 'DEGRADED_SIMULATION_BASELINE';
}

export interface HazardFactorContribution {
  feature?: string;
  feature_name?: string;
  label?: string;
  human_name?: string;
  value?: string | number | boolean | null;
  feature_value?: string | number | boolean | null;
  contribution: number;
  hazard_multiplier: number;
  direction?: 'INCREASED_HAZARD' | 'DECREASED_HAZARD' | string;
  narrative: string;
}

export interface MissingFeatureAudit {
  feature?: string;
  feature_name?: string;
  label?: string;
  human_name?: string;
  imputation?: string;
  status?: string;
}

export interface OfficerSurvivalExplanation extends OfficerSurvivalRisk {
  summary_narrative: string;
  why_hazard_is_higher: HazardFactorContribution[];
  why_hazard_is_lower: HazardFactorContribution[];
  missing_features: MissingFeatureAudit[];
}

export interface SurvivalMLHealth {
  status: string;
  model_version: string;
  feature_version: string;
  available_transitions: string[];
  model_checksums?: Record<string, string>;
  calibration_status?: Record<string, string>;
  explainability_available?: boolean;
  governance_disclaimer: string;
}

export interface CitizenMilestoneTimeline {
  case_id: string;
  current_stage: string;
  milestone_name: string;
  statutory_time_limit_days: number;
  days_in_current_stage: number;
  proceedings_status: string;
  statutory_rights_summary: string;
  citizen_procedural_explanation: string;
}

export interface SurvivalPredictPayload {
  case_id: string | number;
  snapshot_date: string;
  transition: StatutoryTransition | string;
  features: Record<string, any>;
  horizon?: number;
  require_features?: boolean;
}
