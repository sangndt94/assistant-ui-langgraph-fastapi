import { Component, inject } from '@angular/core';
import { NzLayoutModule } from 'ng-zorro-antd/layout';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzAffixModule } from 'ng-zorro-antd/affix';
import { BoxChatComponent } from '@chat-scraper/box-chat';
// import { BoxCommentsComponent } from '@chat-scraper/box-comments';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MessageSignalsService } from '@chat-scraper/api-gateway';
import { Router } from '@angular/router';
import { ChatMessage, MessageContent, SendMessageRequest } from 'utils/repositories/api-gateway/src/lib/model/message/sendMessageRq';
@Component({
  selector: 'app-home',
  imports: [
    NzLayoutModule,
    NzIconModule,
    NzButtonModule,
    NzFormModule,
    NzInputModule,
    NzAffixModule,
    BoxChatComponent,
    // BoxCommentsComponent,
    FormsModule,
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent {
  isCollapsed = false;
  message = '';
  // history: [string, string][] = [];

  constructor(private http: HttpClient) { }
  readonly messageSignalsService = inject(MessageSignalsService);
  readonly #router = inject(Router);

  onInputChange(value: string): void {
    this.message = value;
  }

  onEnter(event: Event): void {
    const keyboardEvent = event as KeyboardEvent;
    keyboardEvent.preventDefault();
    this.sendMessage();
  }
  onMessageSent(): void {
    const scrollContainer = document.querySelector('.chat-history');
    if (scrollContainer) {
      setTimeout(() => {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }, 50);
    }
  }

  sendMessage(): void {
    const content = this.message.trim();
    if (!content) return;

    const userId = this.messageSignalsService.getCookie('mammy_user_id');
    let sessionId = this.messageSignalsService.activeSessionId();
    const currentHistory = this.messageSignalsService.history(); // Lịch sử hiện tại: ChatMessage[]

    // Tạo tin nhắn người dùng mới
    const newUserMessage: ChatMessage = {
      role: 'user' as const,
      content: [{ type: 'text' as const, text: content } as MessageContent]
    };

    // // Cập nhật lịch sử lạc quan (optimistic update)
    // const optimisticHistory: ChatMessage[] = [
    //   ...currentHistory,
    //   newUserMessage,
    //   { role: 'assistant' as const, content: [{ type: 'text' as const, text: '🤖 Đang trả lời...' } as MessageContent] }
    // ];
    // this.messageSignalsService.updateHistory(optimisticHistory);

    // Xử lý sessionId
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      this.messageSignalsService.setSessionCookie(sessionId, content, 7);
      this.messageSignalsService.setActiveSession(sessionId);

      const updatedGroups = this.messageSignalsService.getSessionGroupsFromRaw(
        this.messageSignalsService.getAllSessionCookies()
      );
      this.messageSignalsService.setGroup(updatedGroups);
      this.#router.navigate(['/c', sessionId]);
    } else {
      const cookieName = `session_${sessionId}`;
      if (this.messageSignalsService.getCookie(cookieName)) {
        this.messageSignalsService.setSessionCookie(sessionId, content, 7);
        const updatedGroups = this.messageSignalsService.getSessionGroupsFromRaw(
          this.messageSignalsService.getAllSessionCookies()
        );
        this.messageSignalsService.setGroup(updatedGroups);
      }
    }

    // Tạo payload gửi lên BE
    const payload: SendMessageRequest = {
      system: 'Bạn là trợ lý thông minh, trả lời ngắn gọn và chính xác.',
      // tools: [
      //   {
      //     name: 'get_stock_price',
      //     description: 'Lấy giá cổ phiếu hiện tại',
      //     parameters: { stock_symbol: 'string' }
      //   }
      // ],
      tools: [],
      messages: [newUserMessage],
      user_id: userId as string,
      session_id: sessionId as string,
      agent: 'core_agent'
    };

    // Gửi tin nhắn
    this.messageSignalsService
      .sendMessageStream(payload)
      .subscribe({
        next: () => {
          this.onMessageSent();
          setTimeout(() => {
            this.message = '';
          }, 300);
        }
      });

  }
}
