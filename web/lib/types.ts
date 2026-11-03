export interface ProblemType {
  type: string;
  confidence: number;
  reason: string;
  mode: string;
}

export interface UserIntent {
  problem: string;
  goal: string;
  metric: string;
  group: string;
  constraints: Record<string, string>;
  audience: string;
  mode: string;
}

export interface Option {
  name: string;
  summary: string;
  est_effect: string;
  impact: number;
  cost: number;
  risk: number;
  speed: number;
  score: number;
  idea?: string;
  how_it_works?: string[];
  evidence_ids?: string[];
  expected_effect?: string;
  main_risk?: string;
  failure_condition?: string;
}

export interface Confidence {
  label: "High" | "Medium" | "Low";
  wins: number;
  total: number;
  alternative: string | null;
  evidence_strength: number;
}

export interface Source {
  id: string;
  title: string;
  url: string;
  retrieved_date: string;
}

export interface Finding {
  id: string;
  claim: string;
  source_url: string;
  title: string;
  retrieved_date: string;
  supporting_snippet: string;
}

export interface ResearchResult {
  status: string;
  themes: Record<string, string[]>;
  findings: Finding[];
  sources: Source[];
  coverage: number;
  message?: string;
}

export interface Decision {
  status: string;
  problem_type: ProblemType;
  user_intent: UserIntent;
  options: Option[];
  best: number;
  reason: string;
  confidence: Confidence;
  why_not: Record<string, string>;
  tie: boolean;
  evidence_strength: number;
  findings: unknown[];
}

export interface Question {
  id: string;
  field: string;
  text: string;
  kind: "choice" | "text";
  options: string[] | null;
  required: boolean;
}
