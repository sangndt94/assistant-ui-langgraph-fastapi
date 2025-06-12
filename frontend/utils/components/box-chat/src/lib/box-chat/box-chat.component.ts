import { Component, ElementRef, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MessageSignalsService } from '@chat-scraper/api-gateway';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ChatMessage, MessageContent } from 'utils/repositories/api-gateway/src/lib/model/message/sendMessageRq';

@Component({
  selector: 'lib-box-chat',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './box-chat.component.html',
  styleUrls: ['./box-chat.component.css']
})
export class BoxChatComponent {
  readonly messageSignalsService = inject(MessageSignalsService);
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;
  readonly history = this.messageSignalsService.history; // Use signal from service
  notFound = false;

  constructor(private route: ActivatedRoute, private http: HttpClient) {}

  parseSimpleMarkdown(text: string | undefined | null): string {
    if (!text) {
      console.warn('parseSimpleMarkdown received undefined or null text');
      return '';
    }
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\[([^\]]*)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  }

  getMessageText(content: MessageContent[]): string {
    const textContent = content.find(item => item.type === 'text');
    return textContent?.text || '';
  }

  ngAfterViewInit(): void {
    this.scrollToBottom();
  }

  onMessageSent(): void {
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    try {
      setTimeout(() => {
        this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
      }, 100);
    } catch (err) {
      console.error('Scroll failed', err);
    }
  }

  ngOnInit(): void {
    const sessionId = this.route.snapshot.paramMap.get('session_id');
    const userId = this.messageSignalsService.getCookie('mammy_user_id');

    if (sessionId && userId) {
      this.messageSignalsService.loadHistory(sessionId, userId).subscribe({
        next: () => this.scrollToBottom(),
        error: () => (this.notFound = true)
      });
    } else {
      this.notFound = true;
    }
  }
}