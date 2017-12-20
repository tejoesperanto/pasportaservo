import csv

from django.core.management.base import CommandError, LabelCommand

from hosting.models import Profile


class Command(LabelCommand):
    help = """
        Mark all emails from one or more CSV files as invalid.
        Usage: ./manage.py invalidate suppression_*.csv
        """

    def handle_label(self, file_name, **options):
        try:
            csvfile = open(file_name, 'r')
        except FileNotFoundError:
            raise CommandError("The file %s was not found" % file_name)
        with csvfile:
            reader = csv.DictReader(csvfile)
            try:
                emails = list(row['email'] for row in reader)
            except KeyError:
                raise CommandError("CSV file must have an 'email' column header.")
        self.action(file_name, emails)

    def action(self, file_name, emails):
        results = Profile.mark_invalid_emails(emails=emails)
        for model, updated in results.items():
            print(updated, model.__name__, "emails marked as invalid from", file_name)
