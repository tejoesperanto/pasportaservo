from django.contrib import admin

from .models import Product, Reservation


class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created')
    list_filter = ()
    search_fields = ()
    date_hierarchy = 'created'


class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'discount', 'support', 'product', 'created')
    list_display_links = ('user', 'amount')
    list_filter = ()
    search_fields = ()
    date_hierarchy = 'created'
    raw_id_fields = ('user',)


admin.site.register(Product, ProductAdmin)
admin.site.register(Reservation, ReservationAdmin)
