import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AskResponse, FeedbackRequest, HistoryItem, Stats, DocumentStatus } from '../models/api.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  ask(question: string): Observable<AskResponse> {
    return this.http.post<AskResponse>(`${this.base}/ask`, { question });
  }

  sendFeedback(qa_id: number, rating: 'like' | 'dislike'): Observable<any> {
    return this.http.post(`${this.base}/feedback`, { qa_id, rating } as FeedbackRequest);
  }

  getHistory(limit = 100): Observable<{ data: HistoryItem[]; total: number }> {
    return this.http.get<{ data: HistoryItem[]; total: number }>(`${this.base}/history?limit=${limit}`);
  }

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
