export interface ProgressEvent {
  step: string;
  message: string;
  timestamp: number;
  done: boolean;
}

export interface Source {
  url: string;
  title: string;
  domain: string;
  quality_score: number;
  quality_tier: string;
  snippet: string;
}

export interface Citation {
  id: string;
  title: string;
  url: string;
  domain: string;
}

export interface ResearchResponse {
  thread_id: string;
  question: string;
  status: string;
  message: string;
}

export interface ResearchResult {
  thread_id: string;
  question: string;
  status: string;
  final_report: string;
  sources: Source[];
  citations: Citation[];
  iterations: number;
  duration_seconds: number;
}

export interface Session {
  thread_id: string;
  question: string;
  status: string;
  source_count: number;
  created_at: string;
}

export interface ChatResponse {
  thread_id: string;
  message: string;
  response: string;
}

export type ResearchStatus =
  | "idle"
  | "starting"
  | "streaming"
  | "loading-result"
  | "done"
  | "error";
