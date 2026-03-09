import { Routes } from '@angular/router';
import { ChatPageComponent } from './pages/chat/chat-page.component';
import { DashboardPageComponent } from './pages/dashboard/dashboard-page.component';

export const routes: Routes = [
  { path: '', component: ChatPageComponent },
  { path: 'dashboard', component: DashboardPageComponent },
  { path: '**', redirectTo: '' }
];
