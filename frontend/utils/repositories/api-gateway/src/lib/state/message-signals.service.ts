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
  readonly #isStreaming = signal(false);
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

  private addUserMessage(message: ChatMessage) {
    this.#history.set([...this.#history(), message]);
  }

  private updateLastAssistantMessage(text: string) {
    const history = this.#history();
    const last = history[history.length - 1];
    if (last?.role === 'assistant') {
      const updated: ChatMessage = {
        ...last,
        content: [{ type: 'text', text }] as MessageContent[]
      };
      this.#history.set([...history.slice(0, -1), updated]);
    }
  }

  private ensureEmptyAssistantMessage(): void {
    const history = this.#history();
    const last = history[history.length - 1];
    if (!last || last.role !== 'assistant') {
      this.#history.set([
        ...history,
        {
          role: 'assistant',
          content: [{ type: 'text', text: '' }] as MessageContent[]
        }
      ]);
    }
  }

  sendMessageStream(sendMessageRs: SendMessageRequest): Observable<SendMessageResponse> {
    if (this.#isStreaming()) return of({} as SendMessageResponse);
    this.#isStreaming.set(true);
    this.#status.set('loading');

    const userMessage = sendMessageRs.messages[sendMessageRs.messages.length - 1];
    this.addUserMessage(userMessage);
    this.ensureEmptyAssistantMessage();

    return this.#eventMessageResourceService.sendMessageStream(sendMessageRs).pipe(
      tap({
        next: (response: SendMessageResponse) => {
          const contents = response.answer?.content ?? [];

          for (const content of contents) {
            if (content.type === 'tool-call') {
              this.handleToolCall(content, sendMessageRs);

            } else if (content.type === 'tool-result') {
              // Chỉ lưu tool-result vào history, KHÔNG updateLastAssistantMessage nữa
              const toolMessage: ChatMessage = { role: 'tool', content: [content] };
              this.#history.set([...this.#history(), toolMessage]);

            } else if (content.type === 'text') {
              // ⚠️ Để tránh đúp nếu BE đã format lại tool-result → hãy kiểm tra text này khác với tool-result
              const last = this.#history()[this.#history().length - 1];
              if (!(last?.role === 'assistant' && last.content[0]?.type === 'text' && last.content[0].text === content.text)) {
                this.updateLastAssistantMessage(content.text!);
              }
            }
          }

          this.#status.set('success');
          this.#messageRs.set(response);
        },
        error: (err) => {
          this.#history.set([
            ...this.#history(),
            {
              role: 'assistant',
              content: [{ type: 'text', text: '⚠️ Gửi tin nhắn thất bại.' }]
            } as ChatMessage
          ]);
          this.#status.set('error');
        },
        finalize: () => {
          this.#isStreaming.set(false);
        }
      }),
      // Hoặc đảm bảo chỉ lấy 1 giá trị duy nhất
      // take(1)
    );
  }

  private prettifyKey(key: string): string {
    return key
      .replace(/_/g, ' ')
      .replace(/(?:^|\s)\S/g, (c) => c.toUpperCase()); // Viết hoa chữ cái đầu
  }

  private isIsoDate(value: string): boolean {
    return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$/.test(value);
  }

  private convertToolResultToText(result: any, toolName: string): string {
    if (!result || typeof result !== 'object') return '[Không có dữ liệu từ tool]';

    const entries = Object.entries(result);
    return entries.map(([key, value]) => {
      let label = this.prettifyKey(key);
      let formattedValue = typeof value === 'number' && key.toLowerCase().includes('time')
        ? new Date(value).toLocaleString()
        : typeof value === 'string' && this.isIsoDate(value)
          ? new Date(value).toISOString().replace('T', ' ').replace('Z', ' UTC')
          : value;

      return `${label}: ${formattedValue}`;
    }).join('\n');
  }

  private handleToolCall(toolCall: MessageContent, sendMessageRs: SendMessageRequest): void {
    const { toolName, toolCallId, args } = toolCall;

    if (toolName === 'get_stock_price') {
      // Trường hợp là tool backend → chờ backend trả về result (không xử lý ở đây)
      return;
    }

    // Kiểm tra có phải tool frontend không
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

      // ✅ Tạo luôn tin nhắn assistant dạng text để hiển thị
      const formattedText = this.convertToolResultToText(result, toolName!);
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: [{ type: 'text', text: formattedText }] as MessageContent[]
      };

      // ✅ Cập nhật history luôn (tool + assistant text)
      this.#history.set([...this.#history(), toolResultMessage, assistantMessage]);

      // Nếu cần tiếp tục xử lý với tool-result → gửi tiếp cho backend
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

    return this.#eventMessageResourceService.fetchHistory({
      session_id: sessionId,
      user_id: userId,
      agent: 'core_agent',
    }).pipe(
      tap((res) => {
        const allMessages: ChatMessage[] = [];

        (res.results || []).forEach((entry: any) => {
          try {
            const parsed = JSON.parse(entry.text);
            if (Array.isArray(parsed)) {
              parsed.forEach((msg: any) => {
                const converted: ChatMessage = {
                  role: msg.role,
                  content: msg.text // Gán trực tiếp vì đã đúng định dạng [{ type: 'text', text: '...' }]
                };
                allMessages.push(converted);
              });
            }
          } catch (e) {
            console.warn('Lỗi parse message:', e);
          }
        });

        this.#history.set(allMessages);
        this.#activeSessionId.set(sessionId);
        this.#status.set('success');
      }),
      catchError((err) => {
        console.log(err);
        this.#status.set('error');
        this.resetHistory();
        return of(err.error?.data || err.error);
      })
    );
  }


  resetHistory() {
    this.#history.set([]);
  }
}
