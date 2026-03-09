export interface AskResponse {
  id: number;
  question: string;
  answer: string;
  source_chunk: string | null;
  confidence: number | null;
  response_time_ms: number;
  warning: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  id?: number;
  confidence?: number | null;
  source_chunk?: string | null;
  response_time_ms?: number;
  warning?: string | null;
  timestamp: Date;
  loading?: boolean;
}

export interface FeedbackRequest {
  qa_id: number;
  rating: 'like' | 'dislike';
}

export interface HistoryItem {
  id: number;
  question: string;
  answer: string;
  source_chunk: string | null;
  confidence: number | null;
  response_time_ms: number;
  timestamp: string;
  feedback: 'like' | 'dislike' | null;
}

export interface Stats {
  total_questions: number;
  avg_response_time_ms: number;
  total_likes: number;
  total_dislikes: number;
  avg_confidence: number;
  satisfaction_rate: number;
}

export interface DocumentStatus {
  has_documents: boolean;
  chunk_count: number;
}
