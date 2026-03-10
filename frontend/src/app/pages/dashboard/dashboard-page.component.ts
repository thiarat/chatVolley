import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { Stats, HistoryItem } from '../../models/api.model';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
  <div class="dash-shell">
    <!-- Top nav -->
    <header class="dash-header">
      <a routerLink="/" class="back-btn">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 3L5 8L10 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        กลับหน้าแชท
      </a>
      <div class="header-title">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <rect x="1" y="1" width="7" height="7" rx="1.5" fill="#2563EB" opacity="0.15" stroke="#2563EB" stroke-width="1.5"/>
          <rect x="12" y="1" width="7" height="7" rx="1.5" fill="#2563EB" opacity="0.15" stroke="#2563EB" stroke-width="1.5"/>
          <rect x="1" y="12" width="7" height="7" rx="1.5" fill="#2563EB" opacity="0.15" stroke="#2563EB" stroke-width="1.5"/>
          <rect x="12" y="12" width="7" height="7" rx="1.5" fill="#2563EB" opacity="0.15" stroke="#2563EB" stroke-width="1.5"/>
        </svg>
        Dashboard
      </div>
      <button class="refresh-btn" (click)="loadData()">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M12 7A5 5 0 1 1 7 2M7 2L10 5M7 2L4 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        รีเฟรช
      </button>
    </header>

    <div class="dash-body">
      <!-- Stat Cards -->
      <section class="stats-grid">
        <div class="stat-card" *ngFor="let s of statCards">
          <div class="stat-icon" [style.background]="s.iconBg">
            <span>{{ s.icon }}</span>
          </div>
          <div class="stat-info">
            <p class="stat-label">{{ s.label }}</p>
            <p class="stat-value">{{ s.value }}</p>
          </div>
          <div class="stat-trend" [class.up]="s.trendUp" [class.neutral]="!s.trendUp">
            {{ s.sub }}
          </div>
        </div>
      </section>

      <!-- Confidence Bar -->
      <section class="conf-section" *ngIf="stats">
        <div class="section-title">ระดับความมั่นใจเฉลี่ย</div>
        <div class="conf-bar-wrap">
          <div class="conf-bar">
            <div class="conf-fill"
              [style.width.%]="(stats.avg_confidence * 100)"
              [class.good]="stats.avg_confidence >= 0.7"
              [class.medium]="stats.avg_confidence >= 0.5 && stats.avg_confidence < 0.7"
              [class.low]="stats.avg_confidence < 0.5">
            </div>
          </div>
          <span class="conf-pct">{{ (stats.avg_confidence * 100).toFixed(1) }}%</span>
        </div>
        <div class="conf-labels">
          <span>ต่ำ</span><span>กลาง</span><span>สูง</span>
        </div>
      </section>

      <!-- History Table -->
      <section class="table-section">
        <div class="section-header">
          <div class="section-title">ประวัติการถาม-ตอบ</div>
          <span class="total-badge">{{ history.length }} รายการ</span>
        </div>

        <div class="loading-state" *ngIf="loading">
          <div class="spinner"></div>
          <p>กำลังโหลด...</p>
        </div>

        <div class="table-wrap" *ngIf="!loading && history.length > 0">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>คำถาม</th>
                <th>คำตอบ</th>
                <th>เวลา</th>
                <th>ความมั่นใจ</th>
                <th>Feedback</th>
                <th>เวลาที่ถาม</th>
              </tr>
            </thead>
            <tbody>
              <ng-container *ngFor="let item of history; let i = index">
              <tr
                (click)="toggleDetail(item)"
                [class.expanded]="expandedId === item.id">
                <td class="num">{{ i + 1 }}</td>
                <td class="q-cell">{{ item.question | slice:0:60 }}{{ item.question.length > 60 ? '…' : '' }}</td>
                <td class="a-cell">{{ item.answer | slice:0:80 }}{{ item.answer.length > 80 ? '…' : '' }}</td>
                <td>
                  <span class="time-badge" [class.fast]="item.response_time_ms < 1000" [class.slow]="item.response_time_ms >= 2000">
                    {{ item.response_time_ms }}ms
                  </span>
                </td>
                <td>
                  <div class="mini-bar" *ngIf="item.confidence !== null">
                    <div class="mini-fill"
                      [style.width.%]="(item.confidence || 0) * 100"
                      [class.good]="(item.confidence || 0) >= 0.7"
                      [class.medium]="(item.confidence || 0) >= 0.5 && (item.confidence || 0) < 0.7"
                      [class.low]="(item.confidence || 0) < 0.5">
                    </div>
                    <span>{{ ((item.confidence || 0) * 100).toFixed(0) }}%</span>
                  </div>
                  <span *ngIf="item.confidence === null" class="na">—</span>
                </td>
                <td>
                  <span class="fb-badge like" *ngIf="item.feedback === 'like'">👍 ถูกใจ</span>
                  <span class="fb-badge dislike" *ngIf="item.feedback === 'dislike'">👎 ไม่ถูกใจ</span>
                  <span class="na" *ngIf="!item.feedback">—</span>
                </td>
                <td class="ts-cell">{{ item.timestamp | slice:0:16 }}</td>
              </tr>
              <!-- Expanded detail row -->
              <tr class="detail-row" *ngIf="expandedId === item.id">
                <td colspan="7">
                  <div class="detail-content">
                    <div class="detail-q"><strong>คำถาม:</strong> {{ item.question }}</div>
                    <div class="detail-a"><strong>คำตอบ:</strong> {{ item.answer }}</div>
                    <div class="detail-src" *ngIf="item.source_chunk">
                      <strong>แหล่งอ้างอิง:</strong> {{ item.source_chunk }}
                    </div>
                  </div>
                </td>
              </tr>
              </ng-container>
            </tbody>
          </table>
        </div>

        <div class="empty-state" *ngIf="!loading && history.length === 0">
          <span>📭</span>
          <p>ยังไม่มีข้อมูล</p>
        </div>
      </section>
    </div>
  </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; background: #F8FAFC; }

    .dash-shell {
      font-family: 'Sarabun', 'Noto Sans Thai', sans-serif;
      min-height: 100vh;
    }

    /* Header */
    .dash-header {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 0 28px;
      height: 56px;
      background: #fff;
      border-bottom: 1px solid #E2E8F0;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .back-btn {
      display: flex; align-items: center; gap: 6px;
      color: #64748B; text-decoration: none;
      font-size: 13px;
      padding: 6px 10px;
      border-radius: 8px;
      transition: background 0.12s;
    }
    .back-btn:hover { background: #F1F5F9; color: #1E293B; }
    .header-title {
      display: flex; align-items: center; gap: 8px;
      font-size: 16px; font-weight: 700; color: #1E293B;
      flex: 1;
    }
    .refresh-btn {
      display: flex; align-items: center; gap: 6px;
      padding: 7px 12px;
      background: #F1F5F9;
      border: 1px solid #E2E8F0;
      border-radius: 8px;
      font-size: 12px; color: #475569;
      cursor: pointer; font-family: inherit;
      transition: background 0.12s;
    }
    .refresh-btn:hover { background: #E2E8F0; }

    .dash-body { padding: 28px; max-width: 1200px; margin: 0 auto; }

    /* Stat cards */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: #fff;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .stat-icon {
      width: 44px; height: 44px;
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 20px;
      flex-shrink: 0;
    }
    .stat-info { flex: 1; }
    .stat-label { font-size: 12px; color: #64748B; margin: 0 0 2px; }
    .stat-value { font-size: 22px; font-weight: 700; color: #1E293B; margin: 0; }
    .stat-trend {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 10px;
      font-weight: 500;
      align-self: flex-start;
    }
    .stat-trend.up { background: #F0FDF4; color: #15803D; }
    .stat-trend.neutral { background: #F1F5F9; color: #64748B; }

    /* Confidence section */
    .conf-section {
      background: #fff;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 24px;
    }
    .section-title {
      font-size: 14px; font-weight: 600; color: #374151; margin-bottom: 12px;
    }
    .conf-bar-wrap {
      display: flex; align-items: center; gap: 12px;
    }
    .conf-bar {
      flex: 1; height: 10px;
      background: #F1F5F9;
      border-radius: 10px;
      overflow: hidden;
    }
    .conf-fill {
      height: 100%; border-radius: 10px;
      transition: width 0.6s ease;
    }
    .conf-fill.good { background: linear-gradient(90deg, #4ADE80, #22C55E); }
    .conf-fill.medium { background: linear-gradient(90deg, #FCD34D, #F59E0B); }
    .conf-fill.low { background: linear-gradient(90deg, #FCA5A5, #EF4444); }
    .conf-pct { font-size: 15px; font-weight: 700; color: #1E293B; min-width: 48px; }
    .conf-labels {
      display: flex; justify-content: space-between;
      font-size: 11px; color: #94A3B8; margin-top: 6px;
    }

    /* Table section */
    .table-section {
      background: #fff;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      overflow: hidden;
    }
    .section-header {
      display: flex; align-items: center; gap: 10px;
      padding: 16px 20px;
      border-bottom: 1px solid #F1F5F9;
    }
    .total-badge {
      font-size: 11px;
      background: #EFF6FF;
      color: #2563EB;
      padding: 2px 8px;
      border-radius: 10px;
      font-weight: 500;
    }

    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    thead tr { background: #F8FAFC; }
    th {
      text-align: left;
      padding: 10px 14px;
      font-size: 11.5px;
      font-weight: 600;
      color: #64748B;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      border-bottom: 1px solid #E2E8F0;
    }
    td {
      padding: 12px 14px;
      font-size: 13px;
      color: #374151;
      border-bottom: 1px solid #F1F5F9;
      vertical-align: middle;
    }
    tr:last-child td { border-bottom: none; }
    tbody tr:hover { background: #F8FAFC; cursor: pointer; }
    tbody tr.expanded { background: #EFF6FF; }

    .num { color: #94A3B8; font-size: 12px; width: 32px; }
    .q-cell { font-weight: 500; max-width: 200px; }
    .a-cell { color: #64748B; max-width: 240px; }
    .ts-cell { color: #94A3B8; font-size: 11.5px; white-space: nowrap; }
    .na { color: #CBD5E1; }

    .time-badge {
      padding: 2px 8px; border-radius: 10px;
      font-size: 11.5px; font-weight: 500;
    }
    .time-badge.fast { background: #F0FDF4; color: #15803D; }
    .time-badge.slow { background: #FEF2F2; color: #DC2626; }
    .time-badge:not(.fast):not(.slow) { background: #F1F5F9; color: #64748B; }

    .mini-bar { display: flex; align-items: center; gap: 6px; }
    .mini-fill {
      width: 60px; height: 5px;
      border-radius: 4px;
    }
    .mini-fill.good { background: #22C55E; }
    .mini-fill.medium { background: #F59E0B; }
    .mini-fill.low { background: #EF4444; }
    .mini-bar span { font-size: 11px; color: #64748B; }

    .fb-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 500;
      padding: 3px 9px;
      border-radius: 10px;
      white-space: nowrap;
    }
    .fb-badge.like    { background: #DCFCE7; color: #15803D; }
    .fb-badge.dislike { background: #FEE2E2; color: #DC2626; }

    .detail-row td { background: #F8FAFC; padding: 0; }
    .detail-content {
      padding: 14px 20px;
      border-left: 3px solid #2563EB;
      margin: 4px 14px;
      border-radius: 0 6px 6px 0;
    }
    .detail-q, .detail-a, .detail-src {
      font-size: 13px; line-height: 1.6; color: #374151;
      margin-bottom: 6px;
    }
    .detail-src { color: #64748B; font-size: 12px; }

    .loading-state {
      display: flex; flex-direction: column;
      align-items: center; gap: 12px;
      padding: 40px;
      color: #64748B; font-size: 14px;
    }
    .spinner {
      width: 28px; height: 28px;
      border: 3px solid #E2E8F0;
      border-top-color: #2563EB;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .empty-state {
      display: flex; flex-direction: column;
      align-items: center; padding: 48px;
      color: #94A3B8;
    }
    .empty-state span { font-size: 32px; margin-bottom: 8px; }
    .empty-state p { font-size: 14px; margin: 0; }
  `]
})
export class DashboardPageComponent implements OnInit {
  stats: Stats | null = null;
  history: HistoryItem[] = [];
  loading = true;
  expandedId: number | null = null;
  statCards: any[] = [];

  constructor(private api: ApiService) { }

  ngOnInit() { this.loadData(); }

  loadData() {
    this.loading = true;
    this.api.getStats().subscribe(s => {
      this.stats = s;
      this.buildStatCards(s);
    });
    this.api.getHistory(100).subscribe({
      next: res => { this.history = res.data; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  buildStatCards(s: Stats) {
    this.statCards = [
      { icon: '💬', label: 'คำถามทั้งหมด', value: s.total_questions, sub: 'รายการ', iconBg: '#EFF6FF', trendUp: true },
      { icon: '⚡', label: 'เวลาตอบเฉลี่ย', value: s.avg_response_time_ms + 'ms', sub: 'ต่อคำถาม', iconBg: '#F0FDF4', trendUp: true },
      { icon: '👍', label: 'Satisfaction', value: s.satisfaction_rate + '%', sub: `${s.total_likes} likes`, iconBg: '#FFF7ED', trendUp: s.satisfaction_rate >= 70 },
      { icon: '🎯', label: 'ความมั่นใจเฉลี่ย', value: (s.avg_confidence * 100).toFixed(1) + '%', sub: 'จาก RAG', iconBg: '#F5F3FF', trendUp: s.avg_confidence >= 0.6 },
    ];
  }

  toggleDetail(item: HistoryItem) {
    this.expandedId = this.expandedId === item.id ? null : item.id;
  }
}
