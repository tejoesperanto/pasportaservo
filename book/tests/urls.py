from django.urls import include, path

urlpatterns = [
    path('', include('pasportaservo.urls')),
    path('', include('book.urls')),
]
