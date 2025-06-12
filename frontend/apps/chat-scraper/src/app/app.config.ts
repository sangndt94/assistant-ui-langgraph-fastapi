import { ApplicationConfig, importProvidersFrom, LOCALE_ID, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { appRoutes } from './app.routes';
import {
  provideClientHydration,
  withEventReplay,
} from '@angular/platform-browser';

import { NgOptimizedImage, registerLocaleData } from '@angular/common';
import en from '@angular/common/locales/en';
import vi from '@angular/common/locales/vi';
registerLocaleData(en);
registerLocaleData(vi);
import { en_US, vi_VN, NZ_I18N } from 'ng-zorro-antd/i18n';
import { provideNzIcons } from './icons-provider';
import { provideAnimations } from '@angular/platform-browser/animations';
import { HTTP_INTERCEPTORS, HttpClient, provideHttpClient, withFetch, withInterceptorsFromDi } from '@angular/common/http';
import { AuthGuard, AuthGuardAdmin, AuthGuardNotLoggedIn, BasicAuthInterceptor, ListAuthGuard } from '@chat-scraper/core';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';

export function createTranslateLoader(http: HttpClient) {
  return new TranslateHttpLoader(http, 'i18n/', '.json');
}
const language = (typeof window !== 'undefined' && window.localStorage)
  ? localStorage.getItem('lang')
  : 'vi';

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(withEventReplay()),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(
      appRoutes, withInMemoryScrolling({
      scrollPositionRestoration: 'enabled'
    })),
    provideAnimations(),
    provideNzIcons(),
    {
      provide: NZ_I18N,
      useFactory: (localId: string) => {
        switch (localId) {
          case 'en_US':
            return en_US;
          case 'vi_VN':
            return vi_VN;
          default:
            return en_US;
        }
      },
      deps: [LOCALE_ID]
    },
    importProvidersFrom(
      NgOptimizedImage,
      TranslateModule.forRoot({
        defaultLanguage: language ?? 'vi',
        loader: {
          provide: TranslateLoader,
          useFactory: (createTranslateLoader),
          deps: [HttpClient]
        },
        isolate: true
      })
    ),
    AuthGuardNotLoggedIn,
    AuthGuard,
    AuthGuardAdmin,
    ListAuthGuard,
    provideHttpClient(
      withFetch(),
      withInterceptorsFromDi(),
    ),
    {
      provide: HTTP_INTERCEPTORS,
      useClass: BasicAuthInterceptor,
      multi: true,
    }
  ],
};
