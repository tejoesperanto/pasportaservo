from django.http import Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic

from core.auth import AuthMixin, AuthRole

from ..forms import FamilyMemberCreateForm, FamilyMemberForm
from .mixins import (
    CreateMixin, DeleteMixin, FamilyMemberAuthMixin,
    FamilyMemberMixin, UpdateMixin,
)


class FamilyMemberCreateView(
        CreateMixin, AuthMixin, FamilyMemberMixin,
        generic.CreateView):
    template_name = 'hosting/profile_form.html'
    form_class = FamilyMemberCreateForm

    def verify_anonymous_family(self):
        # Allow creation of only one completely anonymous family member.
        if self.place.family_is_anonymous:
            return HttpResponseRedirect(reverse_lazy(
                'family_member_update',
                kwargs={'pk': self.place.family_members_cache()[0].pk,
                        'place_pk': self.kwargs['place_pk']}
            ))
        else:
            return None

    def get(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs


class FamilyMemberUpdateView(
        UpdateMixin, AuthMixin, FamilyMemberAuthMixin, FamilyMemberMixin,
        generic.UpdateView):
    template_name = 'hosting/profile_form.html'
    form_class = FamilyMemberForm
    display_fair_usage_condition = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs


class FamilyMemberRemoveView(
        AuthMixin, FamilyMemberMixin,
        generic.DeleteView):
    """
    Removes the family member for the Place.
    """
    template_name = 'hosting/family_member_confirm_delete.html'
    display_fair_usage_condition = True
    minimum_role = AuthRole.OWNER

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.place.family_members.remove(self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['place'] = self.place
        return context


class FamilyMemberDeleteView(
        DeleteMixin, AuthMixin, FamilyMemberAuthMixin, FamilyMemberMixin,
        generic.DeleteView):
    """
    Removes the family member for the Place and deletes the profile.
    """
    template_name = 'hosting/profile_confirm_delete.html'
    display_fair_usage_condition = True

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.other_places.count() > 0:
            raise Http404("This family member is listed at other places as well; cannot delete the profile.")
        return self.object

    def delete(self, request, *args, **kwargs):
        redirect = super().delete(request, *args, **kwargs)
        self.place.family_members.remove(self.object)
        return redirect
