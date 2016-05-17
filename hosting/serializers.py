from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Place, Profile


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email')


class PlaceSerializer(serializers.HyperlinkedModelSerializer):
    link = serializers.URLField(source='get_absolute_url')

    class Meta:
        model = Place
        fields = (
            'owner',
            'city',
            'latitude',
            'longitude',
            'link',
        )


class ProfileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Profile
        fields = (
            'user',
            'title',
            'first_name',
            'last_name',
        )
