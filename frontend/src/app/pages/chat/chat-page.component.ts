import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { ChatMessage, ChatSession, SessionGroup } from '../../models/api.model';

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
  <div class="app-shell">
    <!-- SIDEBAR -->
    <aside class="sidebar" [class.collapsed]="sidebarCollapsed">
      <div class="sidebar-header">
        <div class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="13" stroke="#2563EB" stroke-width="2"/>
            <path d="M8 14 Q14 6 20 14 Q14 22 8 14Z" fill="#2563EB" opacity="0.15"/>
            <circle cx="14" cy="14" r="4" fill="#2563EB"/>
          </svg>
        </div>
        <span class="logo-text" *ngIf="!sidebarCollapsed">Smart PDF <b>Q&A</b></span>
        <button class="collapse-btn" (click)="sidebarCollapsed = !sidebarCollapsed">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path *ngIf="!sidebarCollapsed" d="M10 3L5 8L10 13" stroke="#64748B" stroke-width="1.5" stroke-linecap="round"/>
            <path *ngIf="sidebarCollapsed" d="M6 3L11 8L6 13" stroke="#64748B" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <button class="new-chat-btn" (click)="newChat()" *ngIf="!sidebarCollapsed">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1V13M1 7H13" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
        แชทใหม่
      </button>
      <button class="new-chat-btn icon-only" (click)="newChat()" *ngIf="sidebarCollapsed">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1V13M1 7H13" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </button>

      <nav class="history-nav" *ngIf="!sidebarCollapsed">
        <p class="history-label">ประวัติแชท</p>
        <div class="loading-skeleton" *ngIf="historyLoading">
          <div class="skeleton-line" *ngFor="let i of [1,2,3,4]"></div>
        </div>
        <div class="history-empty" *ngIf="!historyLoading && sessionGroups.today.length === 0 && sessionGroups.yesterday.length === 0 && sessionGroups.older.length === 0">
          <p>ยังไม่มีประวัติ</p>
        </div>

        <!-- วันนี้ -->
        <div *ngIf="sessionGroups.today.length > 0">
          <p class="group-label">วันนี้</p>
          <div class="session-wrap" *ngFor="let s of sessionGroups.today">
            <button class="history-item" (click)="loadSession(s)"
              [class.active]="activeSessionId === s.session_id">
              <span class="history-icon">💬</span>
              <span class="history-text">{{ s.title | slice:0:32 }}{{ s.title.length > 32 ? '…' : '' }}</span>
              <span class="msg-badge" *ngIf="s.message_count > 1">{{ s.message_count }}</span>
            </button>
            <button class="delete-session-btn" (click)="deleteSession(s, $event)" title="ลบแชทนี้">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M9 3L3 9M3 3L9 9" stroke="#94A3B8" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- เมื่อวาน -->
        <div *ngIf="sessionGroups.yesterday.length > 0">
          <p class="group-label">เมื่อวาน</p>
          <div class="session-wrap" *ngFor="let s of sessionGroups.yesterday">
            <button class="history-item" (click)="loadSession(s)"
              [class.active]="activeSessionId === s.session_id">
              <span class="history-icon">💬</span>
              <span class="history-text">{{ s.title | slice:0:32 }}{{ s.title.length > 32 ? '…' : '' }}</span>
              <span class="msg-badge" *ngIf="s.message_count > 1">{{ s.message_count }}</span>
            </button>
            <button class="delete-session-btn" (click)="deleteSession(s, $event)" title="ลบแชทนี้">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M9 3L3 9M3 3L9 9" stroke="#94A3B8" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- ก่อนหน้า -->
        <div *ngIf="sessionGroups.older.length > 0">
          <p class="group-label">ก่อนหน้า</p>
          <div class="session-wrap" *ngFor="let s of sessionGroups.older">
            <button class="history-item" (click)="loadSession(s)"
              [class.active]="activeSessionId === s.session_id">
              <span class="history-icon">💬</span>
              <span class="history-text">{{ s.title | slice:0:32 }}{{ s.title.length > 32 ? '…' : '' }}</span>
              <span class="msg-badge" *ngIf="s.message_count > 1">{{ s.message_count }}</span>
            </button>
            <button class="delete-session-btn" (click)="deleteSession(s, $event)" title="ลบแชทนี้">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M9 3L3 9M3 3L9 9" stroke="#94A3B8" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>
      </nav>

      <div class="sidebar-footer" *ngIf="!sidebarCollapsed">
        <a routerLink="/dashboard" class="dash-link">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="1" y="1" width="6" height="6" rx="1" stroke="#64748B" stroke-width="1.5"/>
            <rect x="9" y="1" width="6" height="6" rx="1" stroke="#64748B" stroke-width="1.5"/>
            <rect x="1" y="9" width="6" height="6" rx="1" stroke="#64748B" stroke-width="1.5"/>
            <rect x="9" y="9" width="6" height="6" rx="1" stroke="#64748B" stroke-width="1.5"/>
          </svg>
          Dashboard
        </a>
      </div>
    </aside>

    <!-- MAIN CHAT -->
    <main class="chat-main">
      <div class="chat-topbar">
        <div class="topbar-title">
          <span class="sport-badge">🏐</span>
          <span>กติกาวอลเลย์บอล AI</span>
        </div>
        <div class="topbar-status" [class.ready]="docReady" [class.notready]="!docReady">
          <span class="status-dot"></span>
          {{ docReady ? 'พร้อมใช้งาน' : 'ยังไม่มีเอกสาร' }}
        </div>
      </div>

      <!-- MESSAGES -->
      <div class="messages-wrap" #messagesContainer>
        <!-- Welcome screen -->
        <div class="welcome" *ngIf="messages.length === 0">
          <div class="welcome-icon">🏐</div>
          <h1>ถามเรื่องกติกาวอลเลย์บอล</h1>
          <p>ระบบ AI ตอบคำถามจากเอกสารกติกาจริง</p>
          <div class="suggestions">
            <button class="suggestion-chip" *ngFor="let q of suggestions" (click)="sendSuggestion(q)">
              {{ q }}
            </button>
          </div>
        </div>

        <!-- Chat messages -->
        <div class="messages" *ngIf="messages.length > 0">
          <div class="message-row" *ngFor="let msg of messages" [class.user]="msg.role === 'user'" [class.assistant]="msg.role === 'assistant'">
            <div class="msg-avatar" *ngIf="msg.role === 'assistant'">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="9" fill="#EFF6FF" stroke="#2563EB" stroke-width="1.5"/>
                <circle cx="10" cy="10" r="3" fill="#2563EB"/>
              </svg>
            </div>
            <div class="msg-bubble">
              <!-- Loading -->
              <div class="typing-dots" *ngIf="msg.loading">
                <span></span><span></span><span></span>
              </div>
              <!-- Content -->
              <div *ngIf="!msg.loading">
                <p class="msg-text">{{ msg.content }}</p>
                <!-- Warning -->
                <div class="msg-warning" *ngIf="msg.warning">
                  {{ msg.warning }}
                </div>
                <!-- Meta -->
                <div class="msg-meta" *ngIf="msg.role === 'assistant' && msg.id">
                  <span class="meta-conf" *ngIf="msg.confidence !== null && msg.confidence !== undefined">
                    ความมั่นใจ {{ (msg.confidence * 100).toFixed(0) }}%
                  </span>
                  <span class="meta-time">{{ msg.response_time_ms }}ms</span>
                  <div class="feedback-btns">
                    <button class="fb-btn like"
                      [class.active]="msg.feedback === 'like'"
                      (click)="sendFeedback(msg, 'like')"
                      title="ถูกต้อง">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M4 6V12M1 7H4L6 2C6.5 2 8 2.5 8 4V6H11.5C12 6 12.5 6.5 12.5 7L11.5 11.5C11.3 12 11 12 10.5 12H4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
                      </svg>
                    </button>
                    <button class="fb-btn dislike"
                      [class.active]="msg.feedback === 'dislike'"
                      (click)="sendFeedback(msg, 'dislike')"
                      title="ไม่ถูกต้อง">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M10 8V2M13 7H10L8 12C7.5 12 6 11.5 6 10V8H2.5C2 8 1.5 7.5 1.5 7L2.5 2.5C2.7 2 3 2 3.5 2H10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
                      </svg>
                    </button>
                  </div>
                </div>
                <!-- Source -->
                <details class="source-details" *ngIf="msg.role === 'assistant' && msg.source_chunk">
                  <summary>ดูแหล่งอ้างอิง</summary>
                  <p class="source-text">{{ msg.source_chunk }}</p>
                </details>
              </div>
            </div>
            <div class="msg-avatar user-avatar" *ngIf="msg.role === 'user'">
              <span>U</span>
            </div>
          </div>
        </div>
      </div>

      <!-- INPUT BAR -->
      <div class="input-bar">
        <div class="input-wrap">
          <textarea
            #inputArea
            [(ngModel)]="question"
            (keydown)="onKeyDown($event)"
            placeholder="ถามเกี่ยวกับกติกาวอลเลย์บอล... (Enter เพื่อส่ง)"
            rows="1"
            [disabled]="isLoading"
            (input)="autoResize($event)"
          ></textarea>
          <button class="send-btn" (click)="sendQuestion()" [disabled]="!question.trim() || isLoading">
            <svg *ngIf="!isLoading" width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M16 9L2 2L5.5 9L2 16L16 9Z" fill="white"/>
            </svg>
            <div *ngIf="isLoading" class="send-spinner"></div>
          </button>
        </div>
        <p class="input-hint">Enter เพื่อส่ง • Shift+Enter ขึ้นบรรทัดใหม่</p>
      </div>
    </main>
  </div>
  `,
  styles: [`
    :host { display: block; height: 100vh; }

    .app-shell {
      display: flex;
      height: 100vh;
      background: #F8FAFC;
      font-family: 'Sarabun', 'Noto Sans Thai', sans-serif;
    }

    /* ===== SIDEBAR ===== */
    .sidebar {
      width: 260px;
      min-width: 260px;
      background: #fff;
      border-right: 1px solid #E2E8F0;
      display: flex;
      flex-direction: column;
      transition: width 0.2s ease, min-width 0.2s ease;
      overflow: hidden;
    }
    .sidebar.collapsed {
      width: 64px;
      min-width: 64px;
    }

    .sidebar-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 16px 14px;
      border-bottom: 1px solid #F1F5F9;
      min-height: 64px;
    }
    .logo-mark { flex-shrink: 0; }
    .logo-text {
      font-size: 15px;
      color: #1E293B;
      font-weight: 400;
      white-space: nowrap;
      flex: 1;
    }
    .logo-text b { color: #2563EB; font-weight: 700; }
    .collapse-btn {
      background: none; border: none; cursor: pointer;
      padding: 4px; border-radius: 6px; display: flex;
      margin-left: auto;
    }
    .collapse-btn:hover { background: #F1F5F9; }

    .new-chat-btn {
      margin: 12px;
      padding: 9px 14px;
      background: #2563EB;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 13.5px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background 0.15s;
      font-family: inherit;
    }
    .new-chat-btn:hover { background: #1D4ED8; }
    .new-chat-btn.icon-only { padding: 9px; justify-content: center; }

    .history-nav {
      flex: 1;
      overflow-y: auto;
      padding: 4px 8px 12px;
    }
    .history-label {
      font-size: 11px;
      font-weight: 600;
      color: #94A3B8;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 10px 6px 6px;
      margin: 0;
    }
    .group-label {
      font-size: 11px;
      color: #94A3B8;
      padding: 8px 6px 4px;
      margin: 0;
    }
    /* ── Session item ── */
    .session-wrap {
      position: relative;
      display: flex;
      align-items: center;
    }
    .session-wrap:hover .delete-session-btn { opacity: 1; }

    .delete-session-btn {
      position: absolute;
      right: 4px;
      opacity: 0;
      padding: 4px 5px;
      background: none;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      display: flex;
      align-items: center;
      transition: opacity 0.15s, background 0.12s;
      flex-shrink: 0;
      z-index: 1;
    }
    .delete-session-btn:hover { background: #FEE2E2; }
    .delete-session-btn:hover svg path { stroke: #EF4444; }

    .msg-badge {
      font-size: 10px;
      background: #E2E8F0;
      color: #64748B;
      padding: 1px 6px;
      border-radius: 8px;
      margin-left: auto;
      flex-shrink: 0;
      line-height: 1.6;
    }

    .history-item {
      flex: 1;
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 8px;
      padding-right: 28px;
      background: none;
      border: none;
      border-radius: 7px;
      cursor: pointer;
      text-align: left;
      transition: background 0.12s;
      font-family: inherit;
    }
    .history-item:hover { background: #F1F5F9; }
    .history-item.active { background: #EFF6FF; }
    .history-icon { font-size: 12px; flex-shrink: 0; }
    .history-text { font-size: 12.5px; color: #374151; line-height: 1.4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; }
    .history-empty p { font-size: 12px; color: #94A3B8; text-align: center; padding: 16px 0; margin: 0; }
    .loading-skeleton { padding: 4px 0; }
    .skeleton-line {
      height: 32px; border-radius: 7px;
      background: linear-gradient(90deg, #F1F5F9 25%, #E2E8F0 50%, #F1F5F9 75%);
      background-size: 200% 100%;
      animation: shimmer 1.2s infinite;
      margin-bottom: 4px;
    }
    @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

    .sidebar-footer {
      padding: 12px;
      border-top: 1px solid #F1F5F9;
    }
    .dash-link {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 8px;
      color: #475569;
      text-decoration: none;
      font-size: 13px;
      transition: background 0.12s;
    }
    .dash-link:hover { background: #F1F5F9; color: #1E293B; }

    /* ===== MAIN CHAT ===== */
    .chat-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .chat-topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      height: 56px;
      background: #fff;
      border-bottom: 1px solid #E2E8F0;
      flex-shrink: 0;
    }
    .topbar-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 600;
      color: #1E293B;
    }
    .sport-badge { font-size: 18px; }
    .topbar-status {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 20px;
      font-weight: 500;
    }
    .topbar-status.ready { background: #F0FDF4; color: #15803D; }
    .topbar-status.notready { background: #FEF9C3; color: #92400E; }
    .status-dot {
      width: 7px; height: 7px; border-radius: 50%;
    }
    .ready .status-dot { background: #22C55E; }
    .notready .status-dot { background: #EAB308; }

    /* ===== MESSAGES ===== */
    .messages-wrap {
      flex: 1;
      overflow-y: auto;
      padding: 24px 0;
    }

    .welcome {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      min-height: 400px;
      text-align: center;
      padding: 40px 24px;
    }
    .welcome-icon { font-size: 56px; margin-bottom: 16px; }
    .welcome h1 {
      font-size: 22px;
      font-weight: 700;
      color: #1E293B;
      margin: 0 0 8px;
    }
    .welcome p {
      font-size: 14px;
      color: #64748B;
      margin: 0 0 28px;
    }
    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
      max-width: 600px;
    }
    .suggestion-chip {
      padding: 8px 16px;
      background: #fff;
      border: 1px solid #CBD5E1;
      border-radius: 20px;
      font-size: 13px;
      color: #374151;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.15s;
    }
    .suggestion-chip:hover {
      background: #EFF6FF;
      border-color: #93C5FD;
      color: #1D4ED8;
    }

    .messages { max-width: 760px; margin: 0 auto; padding: 0 20px; }
    .message-row {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      align-items: flex-start;
    }
    .message-row.user { flex-direction: row-reverse; }

    .msg-avatar {
      width: 32px; height: 32px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .user-avatar {
      background: #2563EB;
      color: white;
      font-size: 13px;
      font-weight: 600;
    }

    .msg-bubble {
      max-width: 72%;
      padding: 12px 16px;
      border-radius: 14px;
      line-height: 1.6;
    }
    .user .msg-bubble {
      background: #2563EB;
      color: white;
      border-bottom-right-radius: 4px;
    }
    .assistant .msg-bubble {
      background: #fff;
      border: 1px solid #E2E8F0;
      color: #1E293B;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    .msg-text { margin: 0; font-size: 14px; white-space: pre-wrap; }
    .msg-warning {
      margin-top: 8px;
      padding: 6px 10px;
      background: #FEF9C3;
      border: 1px solid #FDE047;
      border-radius: 6px;
      font-size: 12px;
      color: #92400E;
    }
    .msg-meta {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 8px;
      flex-wrap: wrap;
    }
    .meta-conf {
      font-size: 11px;
      color: #64748B;
      background: #F1F5F9;
      padding: 2px 7px;
      border-radius: 10px;
    }
    .meta-time { font-size: 11px; color: #94A3B8; }
    .feedback-btns { display: flex; gap: 4px; margin-left: auto; }
    .fb-btn {
      padding: 4px 6px;
      background: none;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      color: #94A3B8;
      transition: all 0.15s;
    }
    .fb-btn.like:hover { background: #F0FDF4; color: #16A34A; border-color: #86EFAC; }
    .fb-btn.dislike:hover { background: #FEF2F2; color: #DC2626; border-color: #FCA5A5; }
    .fb-btn.like.active { background: #DCFCE7; color: #16A34A; border-color: #4ADE80; }
    .fb-btn.dislike.active { background: #FEE2E2; color: #DC2626; border-color: #F87171; }

    .source-details {
      margin-top: 8px;
      font-size: 12px;
    }
    .source-details summary {
      cursor: pointer;
      color: #64748B;
      font-size: 11.5px;
    }
    .source-text {
      margin: 6px 0 0;
      padding: 8px;
      background: #F8FAFC;
      border-left: 2px solid #93C5FD;
      font-size: 11.5px;
      color: #475569;
      line-height: 1.5;
      border-radius: 0 4px 4px 0;
    }

    .typing-dots {
      display: flex;
      gap: 4px;
      align-items: center;
      height: 20px;
    }
    .typing-dots span {
      width: 7px; height: 7px;
      background: #94A3B8;
      border-radius: 50%;
      animation: bounce 1.2s infinite;
    }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    /* ===== INPUT ===== */
    .input-bar {
      padding: 16px 24px 20px;
      background: #fff;
      border-top: 1px solid #E2E8F0;
      flex-shrink: 0;
    }
    .input-wrap {
      max-width: 760px;
      margin: 0 auto;
      position: relative;
    }
    textarea {
      width: 100%;
      padding: 12px 52px 12px 16px;
      border: 1.5px solid #CBD5E1;
      border-radius: 12px;
      font-size: 14px;
      font-family: inherit;
      color: #1E293B;
      resize: none;
      outline: none;
      transition: border-color 0.15s;
      max-height: 160px;
      box-sizing: border-box;
      line-height: 1.5;
      background: #F8FAFC;
    }
    textarea:focus { border-color: #2563EB; background: #fff; }
    textarea:disabled { opacity: 0.6; }

    .send-btn {
      position: absolute;
      right: 10px;
      bottom: 10px;
      width: 34px; height: 34px;
      background: #2563EB;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
    }
    .send-btn:hover:not(:disabled) { background: #1D4ED8; }
    .send-btn:disabled { background: #CBD5E1; cursor: not-allowed; }
    .send-spinner {
      width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,0.4);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .input-hint {
      font-size: 11px;
      color: #94A3B8;
      text-align: center;
      margin: 6px 0 0;
    }
  `]
})
export class ChatPageComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('inputArea') inputArea!: ElementRef;

  question = '';
  messages: ChatMessage[] = [];
  isLoading = false;
  docReady = false;
  sidebarCollapsed = false;
  historyLoading = false;

  // Session management
  currentSessionId: string = this.generateSessionId();
  activeSessionId: string | null = null;   // session ที่เลือกใน sidebar

  sessionGroups: SessionGroup = { today: [], yesterday: [], older: [] };

  suggestions = [
    'ลูกเสิร์ฟต้องทำอย่างไร?',
    'ผู้เล่นแต่ละทีมมีกี่คน?',
    'การหมุนตำแหน่งทำอย่างไร?',
    'ลิเบโร คือใคร?',
    'เซตหนึ่งต้องแต้มเท่าไหร่?'
  ];

  private shouldScroll = false;

  constructor(private api: ApiService) { }

  ngOnInit() {
    this.api.getDocumentStatus().subscribe(s => this.docReady = s.has_documents);
    this.loadHistory();
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private generateSessionId(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  loadHistory() {
    this.historyLoading = true;
    this.api.getSessions(60).subscribe({
      next: res => {
        const now = new Date();
        const todayStr = now.toDateString();
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toDateString();

        this.sessionGroups = { today: [], yesterday: [], older: [] };
        res.sessions.forEach(s => {
          const d = new Date(s.last_message_at).toDateString();
          if (d === todayStr)           this.sessionGroups.today.push(s);
          else if (d === yesterdayStr)  this.sessionGroups.yesterday.push(s);
          else                          this.sessionGroups.older.push(s);
        });
        this.historyLoading = false;
      },
      error: () => { this.historyLoading = false; }
    });
  }

  loadSession(session: ChatSession) {
    this.activeSessionId = session.session_id;
    this.messages = [];
    this.api.getSessionMessages(session.session_id).subscribe({
      next: res => {
        const msgs: ChatMessage[] = [];
        res.messages.forEach(m => {
          msgs.push({ role: 'user',      content: m.question, timestamp: new Date(m.timestamp) });
          msgs.push({ role: 'assistant', content: m.answer,   timestamp: new Date(m.timestamp),
            id: m.id, confidence: m.confidence, source_chunk: m.source_chunk,
            response_time_ms: m.response_time_ms, feedback: m.feedback });
        });
        this.messages = msgs;
        this.shouldScroll = true;
      }
    });
  }

  deleteSession(session: ChatSession, event: Event) {
    event.stopPropagation();   // ไม่ให้ trigger loadSession
    this.api.deleteSession(session.session_id).subscribe({
      next: () => {
        // ถ้าลบ session ที่กำลังดูอยู่ → ล้างหน้าจอ
        if (this.activeSessionId === session.session_id) {
          this.messages = [];
          this.activeSessionId = null;
        }
        // ถ้าเป็น session ปัจจุบัน (กำลังคุยอยู่) → สร้าง session ใหม่
        if (this.currentSessionId === session.session_id) {
          this.currentSessionId = this.generateSessionId();
        }
        // อัปเดต sidebar
        this.loadHistory();
      }
    });
  }

  newChat() {
    this.messages = [];
    this.activeSessionId = null;
    this.currentSessionId = this.generateSessionId();
    this.question = '';
  }

  onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.sendQuestion();
    }
  }

  autoResize(e: Event) {
    const el = e.target as HTMLTextAreaElement;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  sendSuggestion(q: string) {
    this.question = q;
    this.sendQuestion();
  }

  sendQuestion() {
    if (!this.question.trim() || this.isLoading) return;
    const q = this.question.trim();
    this.question = '';

    this.messages.push({ role: 'user', content: q, timestamp: new Date() });

    const loadingMsg: ChatMessage = { role: 'assistant', content: '', timestamp: new Date(), loading: true };
    this.messages.push(loadingMsg);
    this.shouldScroll = true;

    this.isLoading = true;
    this.api.ask(q, this.currentSessionId).subscribe({
      next: res => {
        const idx = this.messages.indexOf(loadingMsg);
        if (idx !== -1) {
          this.messages[idx] = {
            role: 'assistant',
            content: res.answer,
            id: res.id,
            confidence: res.confidence,
            source_chunk: res.source_chunk,
            response_time_ms: res.response_time_ms,
            warning: res.warning,
            timestamp: new Date(),
            loading: false
          };
        }
        this.isLoading = false;
        this.shouldScroll = true;
        // ไฮไลต์ session ปัจจุบันใน sidebar
        this.activeSessionId = this.currentSessionId;
        this.loadHistory();
      },
      error: () => {
        const idx = this.messages.indexOf(loadingMsg);
        if (idx !== -1) {
          this.messages[idx] = {
            role: 'assistant',
            content: 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง',
            timestamp: new Date(),
            loading: false
          };
        }
        this.isLoading = false;
        this.shouldScroll = true;
      }
    });
  }

  sendFeedback(msg: ChatMessage, rating: 'like' | 'dislike') {
    if (msg.id && msg.feedback !== rating) {
      msg.feedback = rating;   // update UI ทันที — ปุ่มเปลี่ยนสีค้าง
      this.api.sendFeedback(msg.id, rating).subscribe();
    }
  }

  private scrollToBottom() {
    try {
      const el = this.messagesContainer?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    } catch { }
  }
}
