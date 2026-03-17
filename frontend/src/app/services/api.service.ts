import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AskResponse, FeedbackRequest, HistoryItem, Stats, DocumentStatus, ChatSession, SessionMessage } from '../models/api.model';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  ask(question: string, sessionId: string): Observable<AskResponse> {
    return this.http.post<AskResponse>(`${this.base}/ask`, { question, session_id: sessionId });
  }

  sendFeedback(qa_id: number, rating: 'like' | 'dislike'): Observable<any> {
    return this.http.post(`${this.base}/feedback`, { qa_id, rating } as FeedbackRequest);
  }

  getHistory(limit = 100): Observable<{ data: HistoryItem[]; total: number }> {
    return this.http.get<{ data: HistoryItem[]; total: number }>(`${this.base}/history?limit=${limit}`);
  }

  // ── Session endpoints ────────────────────────────────────────────────────
  getSessions(limit = 60): Observable<{ sessions: ChatSession[] }> {
    return this.http.get<{ sessions: ChatSession[] }>(`${this.base}/sessions?limit=${limit}`);
  }

  getSessionMessages(sessionId: string): Observable<{ session_id: string; messages: SessionMessage[] }> {
    return this.http.get<{ session_id: string; messages: SessionMessage[] }>(`${this.base}/sessions/${sessionId}`);
  }

  deleteSession(sessionId: string): Observable<any> {
    return this.http.delete(`${this.base}/sessions/${sessionId}`);
  }
  // ────────────────────────────────────────────────────────────────────────

  getStats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.base}/stats`);
  }

  getDocumentStatus(): Observable<DocumentStatus> {
    return this.http.get<DocumentStatus>(`${this.base}/document-status`);
  }

  uploadRules(file: File): Observable<any> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post(`${this.base}/upload-rules`, form);
  }
}
