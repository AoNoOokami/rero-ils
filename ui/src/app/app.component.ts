import { Component, OnInit, Injector } from '@angular/core';
import { User } from './users';
import { UserService } from './user.service';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { ApiService } from './core';
import { createCustomElement } from '@angular/elements';
import { AutocompleteComponent } from './autocomplete/autocomplete.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {

  loggedUser: User;

  constructor(
    private userService: UserService,
    private translate: TranslateService,
    private apiService: ApiService,
    private injector: Injector
    ) {
      const autoElement = createCustomElement(
        AutocompleteComponent,
        { injector: this.injector }
      );
      customElements.define('search-autocomplete', autoElement);
    }

  ngOnInit() {
    this.userService.userSettings.subscribe(settings => {
      if (settings) {
        moment.locale(settings.language);
        this.translate.use(settings.language);
        this.apiService.setBaseUrl(settings.baseUrl);
      }
    });
  }
}