from shop.models import Product, Reservation


def reservation_check(request):
    if getattr(request, 'skip_hosting_checks', False):
        return {}  # Exclude django-admin pages.
    # Slicing the queryset does not execute it and keeps it lazy.
    latest_offer = Product.objects.exclude(code='Donation').order_by('-pk')[0:1]
    flag = 'flag_book_reservation'
    if request.user.is_anonymous:
        return {'BOOK_RESERVED': False}
    elif flag in request.session:
        return {'BOOK_RESERVED': request.session[flag]}
    else:
        reserved = Reservation.objects.filter(user=request.user, product=latest_offer).exists()
        request.session[flag] = reserved
        return {'BOOK_RESERVED': reserved}
