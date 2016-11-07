from django.core.management.base import LabelCommand

from .base import LatexCommand


class Command(LatexCommand, LabelCommand):
    help = """Usage: ./manage.py makepdffor FR DE HU"""
    make_pdf = True
    address_only = True
