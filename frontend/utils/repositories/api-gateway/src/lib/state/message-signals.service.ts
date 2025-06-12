import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, Observable, of, tap } from 'rxjs';
import { ApiStatus } from '../model/api-status.model';
import { TikTokCommentRs } from '../model/tiktok/tiktokCommentRs';
import { TikTokScraperRq } from '../model/tiktok/tiktokScraperRq';
import { MessageResourceService } from '../api/MessageResource.service';
import { ChatMessage, MessageContent, SendMessageRequest, SendMessageResponse } from '../model/message/sendMessageRq';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root',
})
export class MessageSignalsService {
  readonly #status = signal<ApiStatus>('idle');
  readonly isLoading = computed(() => this.#status() === 'loading');

  readonly #eventMessageResourceService = inject(MessageResourceService);
  readonly #messageRs = signal<any | undefined>(undefined);
  readonly message = computed(() => this.#messageRs());
  readonly #router = inject(Router);
  readonly #activeSessionId = signal<string | null>(null);
  readonly activeSessionId = computed(() => this.#activeSessionId());
  readonly #history = signal<ChatMessage[]>([]);
  readonly history = computed(() => this.#history());

  readonly #sessionGroups = signal<{
    today: any[];
    past7Days: any[];
    older: any[];
  }>({
    today: [],
    past7Days: [],
    older: [],
  });
  readonly sessionGroups = computed(() => this.#sessionGroups());

  updateHistory(newHistory: ChatMessage[]): void {
    this.#history.set(newHistory);
  }

  setSessionCookie(sessionId: string, label: string, ttlDays: number) {
    const value = JSON.stringify({
      sessionId,
      label,
      createdAt: new Date().toISOString(),
    });

    const expires = new Date(Date.now() + ttlDays * 864e5).toUTCString();
    document.cookie = `session_${sessionId}=${encodeURIComponent(
      value
    )}; expires=${expires}; path=/`;
  }

  getAllSessionCookies(): any[] {
    const allCookies = document.cookie.split(';').map((c) => c.trim());
    const sessions = [];

    for (const c of allCookies) {
      if (c.startsWith('session_')) {
        const [, value] = c.split('=');
        try {
          sessions.push(JSON.parse(decodeURIComponent(value)));
        } catch (_) { }
      }
    }

    return sessions;
  }

  setCookie(name: string, value: string, days: number): void {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(
      value
    )}; expires=${expires}; path=/`;
  }

  getCookie(name: string): string | null {
    const match = document.cookie.match(
      '(^|;)\\s*' + name + '\\s*=\\s*([^;]+)'
    );
    return match ? decodeURIComponent(match[2]) : null;
  }

  setGroup(updatedGroups: {
    today: any[];
    past7Days: any[];
    older: any[];
  }): void {
    this.#sessionGroups.set(updatedGroups);
  }

  sendMessage(sendMessageRs: SendMessageRequest) {
    this.#status.set('loading');

    return this.#eventMessageResourceService.sendMessage(sendMessageRs).pipe(
      tap((response) => {
        console.log("response", response)
        // Giả sử BE trả về { answer: { role: string, content: MessageContent[] } }
        const answer = response.answer || {
          role: 'assistant' as const,
          content: [{ type: 'text' as const, text: '' } as MessageContent]
        };

        // Kiểm tra nếu có tool-call
        const toolCall = answer.content.find((item: MessageContent) => item.type === 'tool-call');
        if (toolCall) {
          this.handleToolCall(toolCall, sendMessageRs);
        } else {
          // Cập nhật lịch sử
          const updatedHistory: ChatMessage[] = [
            ...sendMessageRs.messages,
            answer
          ];
          this.#history.set(updatedHistory);
        }

        this.#status.set('success');
        this.#messageRs.set(response);
        return response;
      }),
      catchError((err) => {
        // Thêm tin nhắn lỗi vào lịch sử
        const failedHistory: ChatMessage[] = [
          ...sendMessageRs.messages,
          {
            role: 'assistant' as const,
            content: [{ type: 'text' as const, text: '⚠️ Gửi tin nhắn thất bại.' } as MessageContent]
          }
        ];
        this.#history.set(failedHistory);
        this.#status.set('error');
        return of(err.error?.data || err.error);
      })
    );
  }

  sendMessageStream(sendMessageRs: SendMessageRequest): Observable<SendMessageResponse> {
    this.#status.set('loading');

    return this.#eventMessageResourceService.sendMessageStream(sendMessageRs).pipe(
      tap((response: SendMessageResponse) => {
        console.log("response", response);

        const answer = response.answer || {
          role: 'assistant' as const,
          content: [{ type: 'text' as const, text: '' }]
        };

        const toolCall = answer.content.find(item => item.type === 'tool-call');
        if (toolCall) {
          this.handleToolCall(toolCall, sendMessageRs);
        } else {
          const updatedHistory: ChatMessage[] = [
            ...sendMessageRs.messages,
            answer
          ];
          this.#history.set(updatedHistory);
        }

        this.#status.set('success');
        this.#messageRs.set(response);
      }),
      catchError((err) => {
        const failedHistory: ChatMessage[] = [
          ...sendMessageRs.messages,
          {
            role: 'assistant',
            content: [{ type: 'text', text: '⚠️ Gửi tin nhắn thất bại.' }]
          }
        ];
        this.#history.set(failedHistory);
        this.#status.set('error');

        return of(err.error?.data || err.error || { error: true });
      })
    );
  }

  private handleToolCall(toolCall: MessageContent, sendMessageRs: SendMessageRequest): void {
    const { toolName, toolCallId, args } = toolCall;

    if (toolName === 'get_stock_price') {
      // Công cụ backend, chờ BE trả về kết quả
      return;
    }

    // Xử lý công cụ frontend (nếu có)
    const frontendTools = sendMessageRs.tools?.map(t => t.name) || [];
    if (frontendTools.includes(toolName!)) {
      const result = this.executeFrontendTool(toolName!, args);
      const toolResultMessage: ChatMessage = {
        role: 'tool' as const,
        content: [
          {
            type: 'tool-result' as const,
            toolCallId,
            toolName,
            result,
            isError: false
          } as MessageContent
        ]
      };

      const payload: SendMessageRequest = {
        system: sendMessageRs.system,
        tools: sendMessageRs.tools,
        messages: [...sendMessageRs.messages, toolResultMessage],
        user_id: sendMessageRs.user_id,
        session_id: sendMessageRs.session_id,
        agent: sendMessageRs.agent
      };

      this.sendMessage(payload).subscribe();
    }
  }

  private executeFrontendTool(toolName: string, args: any): any {
    console.log(`Executing frontend tool: ${toolName} with args:`, args);
    return { mockResult: 'Frontend tool result' }; // Thay bằng logic thực tế
  }


  setActiveSession(sessionId: string) {
    this.#activeSessionId.set(sessionId);
    this.#router.navigate(['/c', sessionId]);
    const userId = this.getCookie('mammy_user_id');
    this.loadHistory(sessionId, userId as string).subscribe({
      error: (s) => {
        console.log("s", s)
      }
    });
    return sessionId;
  }

  getSessionGroups() {
    const sessions = this.getAllSessionCookies(); // Lấy tất cả session_<id> còn hạn
    console.log(sessions);

    const now = new Date();
    const today: any[] = [];
    const past7Days: any[] = [];
    const older: any[] = [];

    sessions.forEach((s: any) => {
      const created = new Date(s.createdAt);
      const diff = (now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24);

      if (diff < 1) today.unshift(s);
      else if (diff < 7) past7Days.unshift(s);
      else older.unshift(s);
    });

    this.#sessionGroups.set({ today, past7Days, older });
    return { today, past7Days, older };
  }

  getSessionGroupsFromRaw(rawList: any[]) {
    const now = new Date();
    const today: any[] = [];
    const past7Days: any[] = [];
    const older: any[] = [];

    rawList.forEach((s: any) => {
      const created = new Date(s.createdAt);
      const diff = (now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24);

      if (diff < 1) today.unshift(s);
      else if (diff < 7) past7Days.unshift(s);
      else older.unshift(s);
    });

    return { today, past7Days, older };
  }

  deleteSession(sessionId: string, event: Event): void {
    event.stopPropagation(); // tránh trigger setActiveSession

    // Xóa cookie
    document.cookie = `session_${sessionId}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;

    // Nếu session bị xoá là session hiện tại
    if (this.activeSessionId() === sessionId) {
      this.setActiveSession('');
      this.#router.navigate(['/']); // hoặc về trang mặc định
    }

    // Cập nhật lại danh sách
    const updatedGroups = this.getSessionGroupsFromRaw(
      this.getAllSessionCookies()
    );
    this.setGroup(updatedGroups);
  }

  loadHistory(sessionId: string, userId: string) {
    this.#status.set('loading');

    return this.#eventMessageResourceService.fetchHistory({ session_id: sessionId, user_id: userId, "agent": "mammy_assistant" }).pipe(
      tap((res) => {
        this.#history.set(res.history || []);
        this.#activeSessionId.set(sessionId);
        this.#status.set('success');
      }),
      catchError((err) => {
        console.log(err)
        this.#status.set('error');
        this.resetHistory()
        return of(err.error?.data || err.error);
      })
    );
  }

  resetHistory() {
    this.#history.set([]);
  }
}
