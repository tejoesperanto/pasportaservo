from django.contrib.admin import widgets as admin_widgets

from ..widgets import ClearableWithPreviewImageInput


class AdminImageWithPreviewWidget(ClearableWithPreviewImageInput, admin_widgets.AdminFileWidget):
    preview_template_name = 'ui/widget-image_file_preview_admin.html'

    def format_value(self, value, **kwargs):
        substitutions = {'initial_raw_value': value}
        substitutions.update(**kwargs)
        return super().format_value(value, **substitutions)
