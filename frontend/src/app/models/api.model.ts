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
  feedback?: 'like' | 'dislike' | null;
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

export interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
}

export interface SessionMessage {
  id: number;
  question: string;
  answer: string;
  source_chunk: string | null;
  confidence: number | null;
  response_time_ms: number;
  timestamp: string;
  feedback: 'like' | 'dislike' | null;
}

export interface SessionGroup {
  today: ChatSession[];
  yesterday: ChatSession[];
  older: ChatSession[];
}
