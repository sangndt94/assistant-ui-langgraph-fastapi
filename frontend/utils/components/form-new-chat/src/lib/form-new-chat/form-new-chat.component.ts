import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzSelectModule } from 'ng-zorro-antd/select';

@Component({
  selector: 'lib-form-new-chat',
  imports: [
    CommonModule,
    NzFormModule,
    NzInputModule,
    NzButtonModule,
    ReactiveFormsModule,
    NzSelectModule
  ],
  templateUrl: './form-new-chat.component.html',
  styleUrl: './form-new-chat.component.css',
})
export class FormNewChatComponent {
  #fb = inject(FormBuilder);
  
  formGroup: FormGroup = this.#fb.group({
    link: [null, [Validators.required, Validators.pattern(
      /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([\/\w .-]*)*\/?$/
    )]],
    label: [],
    type: ['TIKTOK', [Validators.required]],
  });
}
