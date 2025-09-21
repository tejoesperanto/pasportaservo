import logging
from typing import Optional

from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest

admin_log = logging.getLogger('PasportaServo.config')


class AdminSite(admin.AdminSite):
    index_template = 'admin/custom_index.html'

    def __init__(self, name='admin'):
        super().__init__(name)
        self.disable_action('delete_selected')

    def _get_model_path(self, app_label: str, model_name: str) -> str:
        if '.' not in model_name:
            model_name = f'{app_label}.{model_name}'
        return model_name

    def get_app_list(self, request: HttpRequest, app_label: Optional[str] = None):
        # Logic inspired by django-modeladmin-reorder (no longer maintained since 2018).
        apps_dict = self._build_app_dict(request, app_label)
        models_dict = {}
        for app in apps_dict.values():
            for model in app['models']:
                model['model_full_path'] = (
                    self._get_model_path(app['app_label'], model['object_name'])
                )
                models_dict[model['model_full_path']] = model
        apps_list = []

        if not apps_dict:
            return apps_list

        for this_app_config in getattr(settings, 'ADMIN_APP_ORDERING', tuple()):
            if not isinstance(this_app_config, (dict, str)):
                admin_log.warning(
                    'ADMIN_APP_ORDERING item must be dict or string.'
                    f' Got {type(this_app_config).__name__} ({this_app_config!r}).'
                )
                continue

            if isinstance(this_app_config, str):
                # Keep the original app label and models.
                this_app_label = this_app_config
                this_app_config = {}
            else:
                this_app_label = this_app_config.get('app')

            if this_app_label and (app := apps_dict.get(this_app_label)):
                # Optionally set a new label for the app.
                if 'label' in this_app_config:
                    app['name'] = this_app_config['label']

                this_app_models = []
                # First place all explicitly named models.
                for model_name in this_app_config.get('models', []):
                    if not isinstance(model_name, str):
                        admin_log.warning(
                            'ADMIN_APP_ORDERING models item must be a string:'
                            ' name of the model or path of the model (`app_label.ModelName`).'
                            f' Got {type(model_name).__name__} ({model_name!r}).'
                        )
                        continue
                    model_path = self._get_model_path(app['app_label'], model_name)
                    if model := models_dict.get(model_path):
                        this_app_models.append(model)
                        try:
                            app['models'].remove(model)
                        except ValueError:
                            pass  # Might be a model from a different app.
                # Then place the remaining models, sorted alphabetically.
                app['models'].sort(key=lambda model: model['name'])
                this_app_models.extend(app['models'])
                app['models'] = this_app_models

                del apps_dict[this_app_label]
                apps_list.append(app)

        # Sort alphabetically the apps not explicitly listed in ADMIN_APP_ORDERING
        # and the models within each such app.
        remaining_apps_list = sorted(apps_dict.values(), key=lambda app: app['name'].lower())
        for app in remaining_apps_list:
            app['models'].sort(key=lambda model: model['name'])
        apps_list.extend(remaining_apps_list)

        return apps_list
