import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { TiktokSignalsService } from '@chat-scraper/api-gateway';

@Component({
  selector: 'lib-box-comments',
  imports: [
    CommonModule,
    NzEmptyModule,
    NzAvatarModule
  ],
  templateUrl: './box-comments.component.html',
  styleUrl: './box-comments.component.css',
})
export class BoxCommentsComponent {
  readonly scraperSignalService = inject(TiktokSignalsService);

  convertTime(time: number): Date {
    let dateTime: Date = new Date(time);
    return dateTime;
  }
}
