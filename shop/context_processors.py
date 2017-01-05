from shop.models import Reservation


def reservation(request):
    if request.user.is_anonymous:
        return {'BOOK_RESERVED': False}
    else:
        return {'BOOK_RESERVED': Reservation.objects.filter(user=request.user).exists}
