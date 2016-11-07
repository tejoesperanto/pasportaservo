from django.core.management.base import LabelCommand

from .base import LatexCommand


class Command(LatexCommand, LabelCommand):
    help = """Usage: ./manage.py makelatexfor FR DE HU"""
    address_only = True
