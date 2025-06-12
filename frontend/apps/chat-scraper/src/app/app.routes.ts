import { Route } from '@angular/router';

export const appRoutes: Route[] = [
    {
        path: '',
        loadComponent: () =>
            import('../pages/home/home.component').then(
            (c) => c.HomeComponent
        ),
    },
    {
        path: 'c/:session_id',
        loadComponent: () =>
            import('../pages/home/home.component').then(
            (c) => c.HomeComponent
            ),
        data: { renderMode: 'client' }
    }
];
