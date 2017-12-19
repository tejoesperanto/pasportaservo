from django.core.management.base import BaseCommand

from .base import LatexCommand


class Command(LatexCommand, BaseCommand):
    make_pdf = True

    def handle(self, *args, **options):
        self.activate_translation()
        self.make()
