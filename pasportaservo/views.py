from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.functional import SimpleLazyObject, cached_property
from django.views.defaults import ERROR_403_TEMPLATE_NAME, permission_denied

from postman.views import WriteView

from hosting.models import Phone, Place, Profile

User = get_user_model()


def custom_permission_denied_view(request, exception, template_name=ERROR_403_TEMPLATE_NAME):
    """
    The Permission Denied view normally lacks information about the view that triggered the
    exception, unless this information was provided in the exception object manually (as the
    second parameter).  This custom view attempts to include the relevant information if it
    is available.
    It is used, among others, by the Auth mixin to provide data about the offending view to
    the Debug toolbar.
    """
    response = permission_denied(request, exception.args[0] if exception.args else exception, template_name)
    try:
        response.context_data = getattr(response, 'context_data', {})
        response.context_data['view'] = exception.args[1]
    except IndexError:
        pass
    return response


class ExtendedWriteView(WriteView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recipients = context['form'].initial.get('recipients')
        if recipients:
            to = recipients.split(', ')[0]
            self.to_user = User.objects.get(username=to)
            context['target_user'] = self.to_user
            context['target_public_phones'] = SimpleLazyObject(lambda: self.target_user_public_phones)
        else:
            context['target_user'] = None
        return context

    @cached_property
    def author_is_authorized(self):
        try:
            auth_users = Place.objects.filter(owner=self.to_user.profile).values_list('authorized_users', flat=True)
        except (AttributeError, Profile.DoesNotExist):
            return False
        is_authorized = (self.request.user.pk in auth_users)
        return is_authorized

    @cached_property
    def target_user_public_phones(self):
        try:
            if self.author_is_authorized:
                by_visibility = Q(visibility__visible_online_authed=True)
            else:
                by_visibility = Q(visibility__visible_online_public=True)
            phones = (
                Phone.objects
                .filter(profile=self.to_user.profile)
                .filter(by_visibility)
                .select_related(None)
                .only('number', 'type', 'country')
            )
        except (AttributeError, Profile.DoesNotExist):
            phones = None
        return phones
