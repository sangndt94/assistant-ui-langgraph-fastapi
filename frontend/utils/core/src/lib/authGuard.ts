import { ActivatedRouteSnapshot, CanActivate, Router } from '@angular/router';
import { combineLatest, Observable } from 'rxjs';
import { inject, Injectable } from '@angular/core';
import { CredentialsService } from './credentials.service';
import { map } from 'rxjs/operators';
import { NzModalService } from 'ng-zorro-antd/modal';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {
  constructor(
    private credentialsService: CredentialsService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> | boolean {
    if (this.credentialsService.isAuthenticated()) {
      return true;
    }
    console.log('access denied!');
    this.router.navigateByUrl('/auth/login').then(r => console.log(r));
    return false;
  }
}

@Injectable()
export class AuthGuardNotLoggedIn implements CanActivate {
  constructor(
    private credentialsService: CredentialsService,
    private router: Router
  ) {}
  canActivate(): Observable<boolean> | boolean {
    if (!this.credentialsService.isAuthenticated()) {
      return true;
    }
    console.log('access denied!');
    this.router.navigate(['/']).then(r => console.log(r));
    return false;
  }
}
@Injectable()
export class AuthGuardAdmin implements CanActivate {
  constructor(
    private credentialsService: CredentialsService,
    private router: Router
  ) {}
  canActivate(): Observable<boolean> | boolean {
    if (this.credentialsService.authoritiesConstantsAdmin()) {
      // This is the injected auth service which depends on what you are using
      return true;
    }
    console.log('access denied!');
    this.router.navigate(['']).then();
    return false;
  }
}


@Injectable({
  providedIn: 'root',
})
export class ListAuthGuard implements CanActivate {
  readonly #credentialsService = inject(CredentialsService);
  #modalService = inject(NzModalService);

  canActivate(
    route: ActivatedRouteSnapshot
  ): Observable<boolean> {
    const allowedRoles = route.data['roles'] as Array<string>; // Allowed roles
    const allowedDepartments = route.data['departments'] as Array<string>; // Allowed departments

    // Get both roles and departments from the credentials service
    return combineLatest([
      this.#credentialsService.getUserRoles(),      // Observable of user roles
      this.#credentialsService.getUserDepartments() // Observable of user departments
    ]).pipe(
      map(([userRoles, userDepartments]: [string[], string[]]) => {
        // Check if user has at least one allowed role
        const hasRoleAccess = userRoles.some(role => allowedRoles.includes(role));
        // Check if user belongs to at least one allowed department
        const hasDepartmentAccess = allowedDepartments? userDepartments.some(department => allowedDepartments.includes(department)): false;

        const hasAccess = hasRoleAccess || hasDepartmentAccess;

        if (!hasAccess) {
          
        }

        return hasAccess;
      })
    );
  }
}
