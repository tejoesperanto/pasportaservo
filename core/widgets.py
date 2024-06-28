from django.forms import widgets as form_widgets


class PasswordWithToggleInput(form_widgets.PasswordInput):
    template_name = 'ui/widget-password+toggle.html'
