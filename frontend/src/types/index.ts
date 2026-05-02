export interface User {
  id: number;
  email: string;
  display_name: string;
  avatar_url?: string | null;
}

export interface Channel {
  id: number;
  name: string;
  workspace_id: number;
}

export interface Message {
  id: number;
  channel_id: number;
  user_id: number;
  content: string;
  created_at: string;
}

export interface WsEvent<T = unknown> {
  type: string;
  payload: T;
}

export interface AnalysisSummary {
  channel_id: number;
  total_messages: number;
  top_keywords: string[];
  positive_count: number;
  negative_count: number;
  question_count: number;
  active_users: number;
  summary_text: string;
  insights: string[];
  suggested_actions: string[];
  analyzed_at: string;
}

export interface AnalysisQueued {
  status: string;
}

export interface AnalysisCompletedPayload {
  channel_id: number;
  result: AnalysisSummary;
}

export interface UserRankingEntry {
  user_id: number;
  display_name: string;
  points: number;
  level: 'Platinum' | 'Gold' | 'Silver' | 'Bronze';
  rank: number;
  enthusiasm_score: number;
  // Semantic quality scores (0.0–1.0 each, from LLM analysis)
  insight_quality_score: number;
  discussion_impact_score: number;
  decision_contribution_score: number;
  // Normalized total quality contribution (0–100)
  impact_score: number;
}
