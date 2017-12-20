from hosting.models import Profile

from .invalidate import Command as InvalidateCommand


class Command(InvalidateCommand):
    help = """
        Mark all emails from one or more CSV files as valid.
        Usage: ./manage.py validate suppression_*.csv
        """

    def action(self, file_name, emails):
        results = Profile.mark_valid_emails(emails=emails)
        for model, updated in results.items():
            print(updated, model.__name__, "emails marked as valid from", file_name)
