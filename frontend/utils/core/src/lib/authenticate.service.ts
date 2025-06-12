import { inject, Injectable } from '@angular/core';
import { CredentialsService } from './credentials.service';
import { BehaviorSubject, Observable, of } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthenticateService {
  readonly #credentialsService = inject(CredentialsService);
  authenticationAsOb = new BehaviorSubject<boolean>(
    this.#credentialsService.isAuthenticated()
  );
  getAuthenticationAsOb = this.authenticationAsOb.asObservable();


  getToken(): string | null {
    return localStorage.getItem('credentials') || null;
  }

  getUser(): any {
    const credentials = localStorage.getItem('credentials');
    return credentials? JSON.parse(credentials): null;
  }

  isLoggedIn() {
    const token = this.getToken();
    return token != null;
  }
  isAuthenticated() {
    return this.#credentialsService.isAuthenticated();
  }

  getLoginName() {
    return this.#credentialsService.getNameLogged();
  }

  authoritiesConstantsAdmin() {
    return this.#credentialsService.authoritiesConstantsAdmin();
  }

  storeAuthenticationToken(data: any, remember: boolean): Observable<boolean> {
    this.#credentialsService.setCredentials(data, remember);
    this.authenticationAsOb.next(true);
    return of(true);
  }

  /**
   * Logs out the user and clear credentials.
   * @return True if the user was logged out successfully.
   */
  logout(): Observable<boolean> {
    this.#credentialsService.setCredentials();
    this.authenticationAsOb.next(false);
    return of(true);
  }
}
