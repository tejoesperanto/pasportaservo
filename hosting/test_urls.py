import pytest

pytestmark = pytest.mark.django_db


def test_root(client):
    response = client.get('/')
    assert response.status_code == 200

def test_profile(client):
    response = client.get('/profilo/', follow=True)
    assert response.redirect_chain[0] == ('/ensaluti/?next=/profilo/', 302)
    assert response.status_code == 200
