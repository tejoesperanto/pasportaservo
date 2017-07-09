from django.views import generic
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse_lazy

from core.mixins import LoginRequiredMixin

from .models import Product, Reservation
from .forms import ReservationForm


class ReserveRedirectView(LoginRequiredMixin, generic.RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        last_product = Product.objects.last()
        return reverse_lazy('reserve', kwargs={'product_code': last_product.code})


class ReserveView(LoginRequiredMixin, generic.UpdateView):
    model = Reservation
    form_class = ReservationForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_object(self):
        self.product = get_object_or_404(Product, code=self.kwargs['product_code'])
        self.profile = getattr(self.request.user, 'profile', None)
        try:
            return Reservation.objects.get(product=self.product, user=self.request.user)
        except Reservation.DoesNotExist:
            return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_in_book'] = self.profile.is_in_book
        kwargs['user'] = self.request.user
        kwargs['product'] = self.product
        return kwargs


class ReservationView(LoginRequiredMixin, generic.DetailView):
    model = Reservation

    def get_object(self):
        self.product = get_object_or_404(Product, code=self.kwargs['product_code'])
        self.profile = getattr(self.request.user, 'profile', None)
        return Reservation.objects.get(product=self.product, user=self.request.user)



