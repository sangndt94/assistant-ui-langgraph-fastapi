import {NgModule,} from '@angular/core';
import {BASE_PATH} from './variables';
import {environment} from '@env/environment';

@NgModule({
  imports: [],
  declarations: [],
  exports: [],
  providers: [
    { provide: BASE_PATH, useValue: environment.apiClient },
  ],
})
export class ApiGatewayModule {

}
