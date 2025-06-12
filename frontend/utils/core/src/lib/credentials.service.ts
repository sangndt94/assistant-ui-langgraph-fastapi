import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

export interface Credentials {
  success: boolean;
  message: string;
  data: CredentialData;
}
export interface CredentialData {
  email: string;
  first_name: string;
  last_name: string;
  token: string;
  id: number;
  role: any[];
}
const credentialsKey = 'credentials';

/**
 * Provides storage for authentication credentials.
 * The Credentials interface should be replaced with proper implementation.
 */
@Injectable({
  providedIn: 'root',
})
export class CredentialsService {
  private _user: any | null = null;
  private _loginName: string | null = null;

  constructor() {
    try {
      const savedCredentials = (typeof window !== 'undefined' && window.localStorage)?
        (sessionStorage.getItem(credentialsKey) ||
        localStorage.getItem(credentialsKey)) : null;
      if (savedCredentials) {
        this._user = JSON.parse(savedCredentials);
      }
    } catch (e) {
      console.log(e)
    }
  }
  authoritiesConstantsAdmin(): boolean {
    if (this._user != null) {
      // Check if roles exist and if at least one of the roles has the name 'Admin'
      return this._user.data?.roles?.some((role: string) => role === 'Admin') ?? false;
    }
    return false;
  }

  getUserRoles(): Observable<string[]>  {
    return  of(this._user?.data?.roles || [])
  }

  getUserDepartments(): Observable<string[]>  {
    return of(this._user?.data?.departments || [])
  }



  authoritiesConstantsMkt(): boolean {
    if (this._user != null) {
      // Check if roles exist and if at least one of the roles has the name 'Admin'
      return this._user.data?.roles?.some((role: string) => role === 'Marketing') ?? false;
    }
    return false;
  }

  /**
   * Checks is the user is authenticated.
   * @return True if the user is authenticated.
   */
  isAuthenticated(): boolean {
    return !!this.credentials;
  }

  getNameLogged(): string | undefined {
    if (this._user != null) {
      return this._user.data?.name;
    }
    return undefined;
  }
  /**
   * Gets the user credentials.
   * @return The user credentials or null if the user is not authenticated.
   */
  get credentials(): unknown | null {
    return this._user;
  }

  get getLoginName(): string | null {
    return this._loginName;
  }

  logout(): Observable<boolean> {
    this.setCredentials();
    // this.authenticateFacade.logOutAction();
    return of(true);
  }
  /**
   * Sets the user credentials.
   * The credentials may be persisted across sessions by setting the `remember` parameter to true.
   * Otherwise, the credentials are only persisted for the current session.
   * @param user
   * @param remember True to remember credentials across sessions.
   */
  setCredentials(user?: unknown, remember?: boolean) {
    this._user = user || null;
    if (user) {
      const storage = remember ? localStorage : sessionStorage;
      storage.setItem(credentialsKey, JSON.stringify(user));
    } else {
      sessionStorage.removeItem(credentialsKey);
      localStorage.removeItem(credentialsKey);
    }
  }
}
