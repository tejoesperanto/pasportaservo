
def domain(request):
    """ Returns the domain with the protocol, without trailing slash.
        E.g.: "https://pasportaservo.org" or "http://localhost:8000"
    """
    return {'DOMAIN': request.build_absolute_uri('/')[:-1]}
