from hosting.models import Place

for place in Place.objects.all():
    family_members = place.profile_set.all()
    place.family_members.add(*family_members)
    place.profile_set.remove(*family_members)
