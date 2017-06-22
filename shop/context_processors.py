from django.urls import reverse
from shop.models import Product, Reservation


def reservation_check(request):
    if request.path.startswith(reverse('admin:index')):
        return {} # Exclude django-admin pages.
    # Slicing the queryset does not execute it and keeps it lazy.
    latest_offer = Product.objects.order_by('-pk')[0:1]
    if request.user.is_anonymous:
        return {'BOOK_RESERVED': False}
    else:
        return {'BOOK_RESERVED': Reservation.objects.filter(user=request.user, product=latest_offer).exists()}
