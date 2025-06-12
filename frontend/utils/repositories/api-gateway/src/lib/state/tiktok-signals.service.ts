import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError,of, tap } from 'rxjs';
import { ApiStatus } from '../model/api-status.model';
import { ScraperResourceService } from '../api/scraperResource.service';
import { TikTokCommentRs } from '../model/tiktok/tiktokCommentRs';
import { TikTokScraperRq } from '../model/tiktok/tiktokScraperRq';

@Injectable({
    providedIn: 'root'
})
export class TiktokSignalsService {
  readonly #status = signal<ApiStatus>('idle');
  readonly isLoading = computed(() => this.#status() === 'loading');

  readonly #eventResourceService = inject(ScraperResourceService);
  readonly #allTiktokCommentsState = signal<TikTokCommentRs | undefined>(undefined);
  readonly allTiktokComments = computed(() => this.#allTiktokCommentsState());
  

  getAllTiktokComments(tiktokScraper: TikTokScraperRq) {
    this.#status.set('loading');
    return this.#eventResourceService.getAllTiktokComments(tiktokScraper).pipe(
      tap((scraperRs) => {
        this.#status.set('success');
        this.#allTiktokCommentsState.set(scraperRs);
        return scraperRs;
      }),
      catchError((err) => {
        this.#status.set('error');
        return of(err.error.data || err.error);
      })
    )
  }

}
