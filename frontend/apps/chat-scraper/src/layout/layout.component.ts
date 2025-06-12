import { Component, HostListener, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NzLayoutModule } from 'ng-zorro-antd/layout';
import { NzMenuModule } from 'ng-zorro-antd/menu';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { ReactiveFormsModule } from '@angular/forms';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { Router, RouterModule } from '@angular/router';
import { NzDrawerModule, NzDrawerPlacement, NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { FormNewChatComponent } from '@chat-scraper/form-new-chat';
import { MessageSignalsService } from '@chat-scraper/api-gateway';
@Component({
  selector: 'app-layout',
  imports: [
    CommonModule,
    NzLayoutModule,
    NzMenuModule,
    NzIconModule,
    NzButtonModule,
    NzFormModule,
    ReactiveFormsModule,
    NzInputModule,
    NzAvatarModule,
    RouterModule,
    NzDrawerModule
  ],
  templateUrl: './layout.component.html',
  styleUrl: './layout.component.css',
})
export class LayoutComponent {
  isCollapsed = false;
  #nzDrawerService = inject(NzDrawerService);
  #nzPlacementDraw: NzDrawerPlacement = 'left';
  readonly messageSignalsService = inject(MessageSignalsService);
  readonly #router = inject(Router);
  @HostListener('window:resize', ['$event'])
  onResize(event: any): void {
    this.checkWindowSize(event.target.innerWidth);
  }

  checkWindowSize(width: number): void {
    this.#nzPlacementDraw = width < 768 ? 'bottom' : 'right';
  }

  setCookie(name: string, value: string, days: number): void {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
  }
  
  getCookie(name: string): string | null {
    const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match[2]) : null;
  }

  ngOnInit() {
    this.messageSignalsService.getSessionGroups();
    if (!this.getCookie("mammy_user_id")) {
      const randomId = crypto.randomUUID();
      this.setCookie("mammy_user_id", randomId, 7); // 7 ngày
    }
  }

  newChat(): void {
    const sessionId = crypto.randomUUID();
    const createdAt = new Date().toISOString();
  
    const sessionData = {
      sessionId,
      label: sessionId,
      createdAt
    };
  
    // Set cookie riêng cho từng sessionId, TTL 7 ngày
    this.messageSignalsService.setSessionCookie(sessionId, sessionId, 7);
  
    console.log('Tạo session mới:', sessionId);
    this.messageSignalsService.getSessionGroups();  // nếu cần đọc lại toàn bộ cookies
    this.messageSignalsService.setActiveSession(sessionId);
    this.#router.navigate(['/c', sessionId]);
  }

  selectChat(): void {

  }
  // activeSessionId: string | null = null;

  // // setActiveSession(sessionId: string) {
  // //   this.activeSessionId = sessionId;
  // // }
}
