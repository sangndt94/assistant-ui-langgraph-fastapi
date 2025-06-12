import { Injectable } from '@angular/core';
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Credentials } from './credentials.service';
import {environment} from '@chat-scraper/environment';

const credentialsKey = 'credentials';

@Injectable()
export class BasicAuthInterceptor implements HttpInterceptor {
  #credentials?: Credentials;

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    const savedCredentials =
      sessionStorage.getItem(credentialsKey) ||
      localStorage.getItem(credentialsKey);
    
    // Tạo object headers cơ bản
    let headers: { [key: string]: string } = {
      'X-Merchant-ID': environment.merchantId.toString()  // Thêm header X-Merchant-ID với value = 1
    };

    // Nếu có credentials thì thêm Authorization header
    if (savedCredentials) {
      this.#credentials = JSON.parse(savedCredentials);
      headers['Authorization'] = `Bearer ${this.#credentials?.data?.token}`;
    }

    // Clone request với headers đã cập nhật
    request = request.clone({
      setHeaders: headers
    });

    return next.handle(request);
  }
}
