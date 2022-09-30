import json
import operator
import os
import re
import time
import unicodedata
from collections import OrderedDict, defaultdict
from datetime import date
from functools import partial as partial_func, reduce
from itertools import chain
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string as random_hash

import rstr
from faker import Faker
from faker.providers import BaseProvider
from phonenumber_field.phonenumber import PhoneNumber
from postman.models import Message
from unidecode import unidecode_expect_nonascii

from core.auth import PERM_SUPERVISOR, AuthRole
from core.templatetags.utils import random_identifier
from hosting.countries import COUNTRIES_DATA
from hosting.models import Gender, Phone, Place, Profile, Website
from maps import SRID
from maps.data import COUNTRIES_GEO

person_type_mapping = {Profile.Titles.MRS: 'F', Profile.Titles.MR: 'M'}


class Command(BaseCommand):
    requires_migrations_checks = True
    help = """
        Scrambles the personal data in the database so that only the production
        environment of Pasporta Servo contains the PII.
        Usage: ./manage.py scramble
        """

    object_types = (
        'users', 'profiles', 'places', 'phones', 'websites', 'avatars', 'messages',
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action='store_true',
            dest='dry_run',
            default=False,
            help="Test the result of the operation without actually modifying "
                 "data in the database.",
        )
        parser.add_argument(
            "-p", "--passwords",
            nargs=3,
            metavar=("PWD-REG", "PWD-SV", "PWD-ADM"),
            help="A triple of passwords to use for the regular (REG), "
                 "the supervisor (SV), and the admin (ADM) users.",
        )
        for objtype in self.object_types:
            parser.add_argument(
                f"--{objtype}",
                choices=('y', 'n'),
                dest=f'scramble_only_{objtype}',
                help="Scramble only "
                     + (f"{objtype[:-1].title()} objects" if objtype != 'avatars'
                        else "profile avatar files")
                     + " if 'y'; avoid scrambling "
                     + ("these objects" if objtype != 'messages'
                        else "any conversations or exchanged messages")
                     + " if 'n'.",
            )

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.dry_run = options['dry_run']
        self.password_templates = options['passwords']
        if not self.should_continue():
            return

        include = [
            objtype for objtype in self.object_types
            if options[f'scramble_only_{objtype}'] == 'y'
        ]
        exclude = [
            objtype for objtype in self.object_types
            if options[f'scramble_only_{objtype}'] == 'n'
        ]

        def should_handle(objtype):
            return (
                (include and objtype in include)
                or (len(include) == 0 and objtype not in exclude)
            )

        if self.verbosity >= 1:
            self.stdout.write("Loading replacement strings...", ending=" ")
            self.stdout.flush()
            time.sleep(1)
        self.faker = Faker(locale='la')
        self.faker.add_provider(ScrambleProvider)
        self._faker_cache = {}
        self._letter_cache = {}
        basic_latin_range = chain(
            range(65, 91), range(97, 123), range(192, 215), range(217, 223)
        )
        for x in basic_latin_range:
            self._letter_cache[chr(x)] = True  # Latin letter.
        for x in range(1024, 1120):
            self._letter_cache[chr(x)] = False  # Non-latin letter.

        if should_handle('avatars'):
            if self.verbosity >= 1:
                self.stdout.write("Loading replacement images...", ending=" ")
                self.stdout.flush()
                time.sleep(1)
            preload_images(self.faker.provider('PS.Providers.Scramble'), self)

        if self.verbosity >= 1:
            self.stdout.write("Done.")
            self.stdout.flush()
            time.sleep(1)

        for objtype in self.object_types:
            if should_handle(objtype):
                getattr(self, f'handle_{objtype}')()

        if hasattr(self, 'passwords'):
            self.stdout.write(
                "User passwords scrambled according to user roles:\n\t"
                f" administrator (su)    password = {self.passwords[AuthRole.ADMIN]}\n\t"
                f" supervisor            password = {self.passwords[AuthRole.SUPERVISOR]}\n\t"
                f" regular user          password = {self.passwords[AuthRole.VISITOR]}\n"
            )

    def should_continue(self):
        self.stdout.write(self.style.NOTICE(
            "NEVER execute this command on the production environment. "
            "It will cause irreversible damage to the live/production data. "
        ))
        re_prompt = re.compile(r'($|y(?:es)?$|n(?:o)?$)', re.IGNORECASE)
        answer = None
        while not answer:
            answer = re_prompt.match(input("Do you want to continue? [y/N] ").strip())
        if not answer.group(1).lower() in ["y", "yes"]:
            return False
        if self.dry_run:
            return True
        try:
            conf = os.environ.get('DJANGO_SETTINGS_MODULE', '')
            if 'prod' in conf:
                raise EnvironmentError
            # if not conf:
            #     link = os.readlink('./pasportaservo/settings/local_settings.py')
            #     if link == 'prod.py':
            #         raise EnvironmentError
            if settings.ENVIRONMENT == 'PROD':
                raise EnvironmentError
        except (FileNotFoundError, AttributeError):
            raise CommandError("Local Django settings misconfigured.")
        except EnvironmentError:
            raise CommandError(
                "Looks like you are running on the production server. Aborting.")
        return True

    def stdout_long_description(self, obj, field_name='description'):
        return " ".join(getattr(obj, field_name)[:30].split()) + "..."

    def handle_users(self):
        character_set = 'ABCDEFGHJKLMNPQRSTUWXYZabcdefghjmnpqrstvwxyz23456789=*'
        if not self.password_templates:
            self.passwords = {
                AuthRole.VISITOR:    random_hash(8,  allowed_chars=character_set),
                AuthRole.SUPERVISOR: random_hash(12, allowed_chars=character_set),
                AuthRole.ADMIN:      random_hash(16, allowed_chars=character_set),
            }
        else:
            self.passwords = dict(
                zip(
                    (AuthRole.VISITOR, AuthRole.SUPERVISOR, AuthRole.ADMIN),
                    self.password_templates
                )
            )
        self.dry_users, count_changed = {}, 0

        for user in get_user_model().objects.order_by('id'):
            if self.verbosity >= 2:
                self.stdout.write(
                    f"<User #{user.pk}: {user.username}>, {user.email}")

            user.username = random_identifier(10)
            self.scramble_email(
                user, 'u', mailbox='user', pre_scrambled_value=user.username)
            scrambled_pwd = self.passwords[
                AuthRole.ADMIN if user.is_superuser else
                (AuthRole.SUPERVISOR if user.has_perm(PERM_SUPERVISOR) else
                 AuthRole.VISITOR)
            ]
            user.set_password(scrambled_pwd)
            if not self.dry_run:
                user.save(update_fields=['username', 'email', 'password'])

            if self.verbosity >= 2:
                self.stdout.write(
                    f"\t changed to {user.username} {user.email} "
                    f"{{pwd: {scrambled_pwd} }}"
                )
            if self.dry_run:
                self.dry_users[user.pk] = user
            count_changed += 1

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                f"Scrambled {count_changed} users."
            ))

    def handle_profiles(self):
        count_changed, count_total = 0, 0
        dry_users = getattr(self, 'dry_users', {})

        def stdout_birth_date(profile):
            return profile.birth_date if profile.birth_date else 'yyyy-mm-dd'

        def stdout_death_date(profile):
            return f" ✢ {profile.death_date}" if profile.death_date else ""

        def stdout_gender(profile):
            return f" ⚧ {profile.gender}" if profile.gender else ""

        for profile in Profile.all_objects.order_by('-id'):
            if self.dry_run and profile.user_id and dry_users:
                profile.user = dry_users[profile.user_id]
            if self.verbosity >= 2:
                self.stdout.write(
                    f"{profile!r}, {profile.title}"
                    f" ({stdout_birth_date(profile)}{stdout_death_date(profile)})"
                    f" {stdout_gender(profile)} {profile.email}"
                )

            is_changed = any([
                func(profile) for func in [
                    self.scramble_personal_name,
                    self.scramble_family_name,
                    self.scramble_birth_date,
                    self.scramble_death_date,
                    self.scramble_gender,
                    partial_func(self.scramble_email, prefix='p', mailbox='spam'),
                    self.scramble_description,
                ]
            ])
            if not self.dry_run and is_changed:
                profile.save(update_fields=[
                    'first_name', 'last_name', 'birth_date', 'death_date',
                    'gender', 'email', 'description',
                ])

            if self.verbosity >= 2 and is_changed:
                self.stdout.write(
                    f"\t changed to {profile.title} {profile} "
                    f"({stdout_birth_date(profile)}{stdout_death_date(profile)}) "
                    f"{stdout_gender(profile)} {profile.email}"
                )
                if profile.description:
                    self.stdout.write(
                        f"\t \t {self.stdout_long_description(profile)}"
                    )
            if is_changed:
                count_changed += 1
            count_total += 1

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                f"Scrambled {count_changed} profiles"
                f" ({count_total-count_changed} not changed)."
            ))

    def handle_places(self):
        count_changed, count_total = 0, 0

        for place in Place.all_objects.order_by('-id'):
            if self.verbosity >= 2:
                self.stdout.write(f"{place!r}")
                if place.short_description:
                    self.stdout.write(f"[ {place.short_description} ]")

            is_changed = any([
                func(place) for func in [
                    self.scramble_postcode,
                    self.scramble_city,
                    self.scramble_address,
                    partial_func(self.scramble_city, closest=True),
                    self.scramble_location,
                    partial_func(self.scramble_description, short=True),
                    self.scramble_description,
                ]
            ])
            if not self.dry_run and is_changed:
                place.save(update_fields=[
                    'postcode', 'city', 'address', 'closest_city',
                    'latitude', 'longitude', 'location',
                    'description', 'short_description',
                ])

            if self.verbosity >= 2 and is_changed:
                closest_city = f" ⌈{place.closest_city}⌋" if place.closest_city else ""
                addr = f", {' '.join(place.address.split())}" if place.address else ""
                self.stdout.write(
                    f"\t changed to {place.postcode} {place.city}{closest_city} {addr}"
                )
                if place.short_description:
                    self.stdout.write(f"\t \t [ {place.short_description} ]")
                if place.description:
                    self.stdout.write(f"\t \t {self.stdout_long_description(place)}")
                if place.location:
                    bounds = (
                        COUNTRIES_GEO[place.country]['bbox'] if place.country
                        else "the world"
                    )
                    self.stdout.write(
                        f"\t \t @ {place.location.x:.6f},{place.location.y:.6f}"
                        f" of {bounds}"
                    )
            if is_changed:
                count_changed += 1
            count_total += 1

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                f"Scrambled {count_changed} places"
                f" ({count_total-count_changed} not changed)."
            ))

    def handle_phones(self):
        count_changed = 0

        for phone in Phone.all_objects.order_by('-id'):
            if self.verbosity >= 2:
                self.stdout.write(
                    f"{phone!r}"
                    + (f"\t[ {phone.comments} ]" if phone.comments else "")
                )

            self.scramble_phone(phone)
            self.scramble_comment(phone)
            if not self.dry_run:
                phone.save(update_fields=['number', 'comments'])

            if self.verbosity >= 2:
                self.stdout.write(
                    f"\t changed to {phone.number.as_international}"
                    + (f"  [ {phone.comments} ]" if phone.comments else "")
                )
            count_changed += 1

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                f"Scrambled {count_changed} phone numbers."
            ))

    def handle_websites(self):
        count_changed = 0

        for website in Website.all_objects.order_by('-id'):
            if self.verbosity >= 2:
                self.stdout.write(f"{website!r}")

            self.scramble_url(website)
            if not self.dry_run:
                website.save(update_fields=['url'])

            if self.verbosity >= 2:
                self.stdout.write(f"\t changed to {website.url}")
            count_changed += 1

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                f"Scrambled {count_changed} user website URLs."
            ))

    def handle_avatars(self):
        rootdir = os.path.join(settings.MEDIA_ROOT, 'avatars')
        images = [os.path.join(rootdir, f) for f in os.listdir(rootdir)
                  if os.path.isfile(os.path.join(rootdir, f))]
        count_changed = count_randomized = count_total = 0
        list_failed = []
        if self.verbosity >= 2:
            self.stdout.write(f"Changing files in {rootdir}")

        for image in images:
            _, ext = os.path.splitext(image)
            if ext.lower() in ['.jpg', '.jpeg']:
                ext = 'JPG'
            else:
                ext = ext[1:].upper()
            is_changed, failure_reason = self.scramble_image(image, ext, self.dry_run)
            if is_changed:
                count_changed += 1
            else:
                list_failed.append(
                    {'file': os.path.basename(image), 'reason': failure_reason}
                )
                profiles = Profile.all_objects.filter(
                    avatar=os.path.relpath(image, start=settings.MEDIA_ROOT))
                if profiles:
                    random_image = ContentFile(self.faker.image(), "rando.png")
                    for p in profiles:
                        # Each model has to be manually saved to trigger renaming
                        # and placement of the binary data in the correct folder.
                        p.avatar = random_image
                        if not self.dry_run:
                            p.save(update_fields=['avatar'])
                        count_randomized += 1
                    list_failed[-1]['randomized'] = tuple(
                        profiles.values_list('pk', flat=True)
                    )
            count_total += 1

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                f"Scrambled {count_changed} avatar files"
                + f" ({count_total-count_changed} not changed"
                + (f"; for those {count_randomized} profiles' avatars randomized"
                   if count_randomized else "")
                + ")."
            ))
        if self.verbosity >= 2 and list_failed:
            for failure in list_failed:
                self.stdout.write(
                    f"\tFAILED {failure['file']} : {failure['reason']}"
                    + (f" (Avatar set to random scribble;"
                       f" profile#{','.join(map(str, failure['randomized']))})"
                       if failure.get('randomized') else "")
                )

    def handle_messages(self):
        count_cnv_changed, count_msg_changed = 0, 0
        thread, thread_subject = None, ''

        for message in Message.objects.order_by('thread_id', 'id'):
            if self.verbosity >= 2:
                self.stdout.write(f"{message!r}")

            if thread is None or thread != message.thread_id:
                thread = message.thread_id
                self.scramble_comment(message, field_name='subject')
                thread_subject = message.subject
                count_cnv_changed += 1
            else:
                message.subject = "Re: " + thread_subject
            self.scramble_description(
                message, short=self.faker.random.random() > 0.60, field_name='body')
            if not self.dry_run:
                message.save(update_fields=['subject', 'body'])

            if self.verbosity >= 2:
                self.stdout.write(
                    f"\t changed to {message.subject}"
                )
                if message.body:
                    self.stdout.write(
                        f"\t \t {self.stdout_long_description(message, 'body')}"
                    )
            count_msg_changed += 1

        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                f"Scrambled {count_cnv_changed} conversations,"
                f" {count_msg_changed} messages."
            ))

    def scramble_personal_name(self, profile):
        if not profile.first_name:
            return False
        profile.first_name = self.faker.personal_name(
            person_type_mapping.get(profile.title),
            profile.first_name.strip()[0].upper()
        )
        return True

    def scramble_family_name(self, profile):
        if not profile.last_name:
            return False
        profile.last_name = self.faker.family_name(
            person_type_mapping.get(profile.title),
            profile.last_name.strip()[0].upper()
        )
        return True

    def scramble_birth_date(self, profile):
        if not profile.birth_date:
            return False
        decade = int(profile.birth_date.year / 10) * 10
        start_date = date(decade, 1, 1)
        end_date = min(date(decade+9, 12, 31), date.today())
        profile.birth_date = self.faker.date_between_dates(start_date, end_date)
        return True

    def scramble_death_date(self, profile):
        if not profile.death_date:
            return False
        decade = int(profile.death_date.year / 10) * 10
        start_date = date(decade, 1, 1)
        if profile.birth_date:
            start_date = max(start_date, profile.birth_date)
        end_date = min(date(decade+9, 12, 31), date.today())
        profile.death_date = self.faker.date_between_dates(start_date, end_date)
        return True

    def scramble_gender(self, profile):
        if not profile.gender:
            return False
        if not hasattr(self, '_genders_cache'):
            self._genders_cache = list(Gender.objects.all())
        profile.gender = self.faker.random.choice(self._genders_cache)
        return True

    def scramble_email(
            self, instance, prefix='d', mailbox='null', pre_scrambled_value=None
    ):
        if not instance.email:
            return False
        invalid = instance.email.startswith(settings.INVALID_PREFIX)
        invalid_prefix = settings.INVALID_PREFIX if invalid else ''
        scarambol = pre_scrambled_value or random_identifier(10)
        instance.email = (
            f'{invalid_prefix}{prefix}.{scarambol}@{mailbox}.pasportaservo.org'
        )
        return True

    def scramble_description(
            self, instance, short=False, field_name=None, field_limit=140
    ):
        if not field_name:
            field_name = 'description' if not short else 'short_description'
        if not getattr(instance, field_name):
            return False
        if not short:
            field_value = (
                ('\n'*2).join([
                    self.faker.paragraph(nb_sentences=4)
                    for _ in range(self.faker.random_int(1, 3))
                ])
            )
        else:
            field_value = self.faker.sentence(nb_words=8)[:field_limit]
        setattr(instance, field_name, field_value)
        return True

    def scramble_postcode(self, place):
        if not place.postcode:
            return False
        regex = (
            place.country and COUNTRIES_DATA[place.country]['postcode_regex']
            or r'\d{5}'
        )
        # The * repetition qualifier makes the generator go wild,
        # strictly limit to 1 copy.
        regex = regex.replace('*', '{1}')
        # Articially limit the length of overly permissive chunks.
        regex = re.sub(r'{0,\d\d}', '{0,2}', regex)
        # Generate a random value according to the constrained regular expression.
        # All whitespaces are condensed to single space and the value is uppercased.
        value = ""
        while value in ("", "GIR0AA", "GIR 0AA"):
            # The generator has a strong preference to this UK postal code...
            value = ' '.join(rstr.xeger(regex).upper().strip().split())
        place.postcode = value
        return True

    def scramble_city(self, place, closest=False):
        if (not closest) and not place.city:
            return False
        if (closest) and not place.closest_city:
            return False
        # Find a suitable address fake provider according to the language
        # of the place's country.
        # If none found, fall back to a random, language-neutral, string.
        lang = (
            place.country
            and COUNTRIES_DATA[place.country]['languages'][0].replace('-', '_')
            or None
        )
        if lang and (lang not in self._faker_cache):
            try:
                faker = Faker(
                    locale=lang,
                    providers=['faker.providers.address', 'faker.providers.person'])
            except AttributeError:
                # Locale not available in the Faker library.
                faker = None
            else:
                provider_lang = faker.provider('faker.providers.address').__lang__
                if not provider_lang.startswith(lang):
                    faker = None
            self._faker_cache[lang] = faker
        faker = lang and self._faker_cache[lang]
        if faker:
            new_city = faker.city()
            if new_city[0] not in self._letter_cache:
                letter_name = unicodedata.name(new_city[0], '')
                self._letter_cache[new_city[0]] = letter_name.startswith('LATIN ')
            if not self._letter_cache[new_city[0]]:
                # First letter is not a latin one, convert the city name to latin.
                new_city = f'{unidecode_expect_nonascii(new_city)} ({new_city})'
        else:
            new_city = self.faker.random_city()
        setattr(place, 'closest_city' if closest else 'city', new_city)
        return True

    def scramble_address(self, place):
        if not place.address.strip():
            return False
        place.address = self.faker.eo_address()
        return True

    def scramble_location(self, place):
        updated = False
        if any([place.latitude, place.longitude]):
            place.latitude, place.longitude = None, None
            updated = True
        if place.location:
            country = place.country or self.faker.random_element(COUNTRIES_GEO.keys())
            place.location = Point(
                [
                    self.faker.random.uniform(a, b)
                    for a, b in zip(*COUNTRIES_GEO[country]['bbox'].values())
                ],
                srid=SRID
            )
            updated = True
        return updated

    def scramble_phone(self, phone):
        if not phone.number.is_valid():
            phone.number = PhoneNumber.from_string(
                self.faker.numerify('% %## ## ##'), region=phone.country.code)
            return True
        phone.number.national_number = 0
        while not phone.number.is_valid():
            phone.number.national_number = self.faker.random_int(10000, 99999999990)
        return True

    def scramble_comment(self, instance, field_name='comments'):
        if not getattr(instance, field_name):
            return False
        field_value = self.faker.sentence(
            nb_words=self.faker.random_int(4, 7), variable_nb_words=False
        )[:-1]
        setattr(instance, field_name, field_value)
        return True

    def scramble_url(self, instance, field_name='url'):
        setattr(instance, field_name, self.faker.uri())
        return True

    def scramble_image(self, img, img_type, only_verify=False):
        try:
            content = self.faker.avatar()
        except Exception as e:
            return False, str(e)
        else:
            if not only_verify:
                with open(img, 'wb') as img_file:
                    img_file.write(content)
            return True, None


def preload_images(provider, cmd=None):
    if cmd and cmd.verbosity >= 2:
        cmd.stdout.write("\n")
    for avatar_type in provider.avatars.values():
        content_types = (
            [avatar_type['content-type']] if isinstance(avatar_type['content-type'], str)
            else list(avatar_type['content-type'])
        )
        for avatar in avatar_type['list']:
            try:
                if cmd and cmd.verbosity >= 2:
                    cmd.stdout.write(avatar['url'][:60], ending="\r")
                    cmd.stdout.flush()
                resp = urlopen(Request(avatar['url'], headers={'User-Agent': "Scrambler"}))
                if resp.status == 200 and resp.getheader('content-type') in content_types:
                    avatar['data'] = resp.read()
                    avatar['size'] = resp.getheader('content-length')
            except Exception:
                pass
            finally:
                if cmd and cmd.verbosity >= 2:
                    cmd.stdout.write(" " * len(avatar['url'][:60]), ending="\r")
                    cmd.stdout.flush()
        avatar_type['list'][:] = filter(
            lambda avatar: avatar.get('data') is not None,
            avatar_type['list']
        )
    provider.avatars._loaded = True


class ScrambleProvider(BaseProvider):
    __use_weighting__ = True
    __provider__ = 'ps.providers.scramble'

    address_formats = OrderedDict({
        '{{ eo_street_type }} {{ eo_street_name }} {{ random_int:int_under_200 }}':
            0.85,
        '{{ eo_street_type }} {{ eo_street_name }} {{ random_int:int_under_200 }}'
        + '{{ eo_house_ext }}':
            0.15,
    })
    letter_subs = {
        'Ĉ': 'C', 'Č': 'C', 'Ĝ': 'G', 'Ĥ': 'H', 'Ĵ': 'J', 'Q': 'K',
        'Ŝ': 'S', 'Š': 'S', 'Ŭ': 'V', 'W': 'V', 'X': 'K', 'Ž': 'Z',
    }

    def __init__(self, generator):
        super().__init__(generator)
        with open(os.path.join(os.path.dirname(__file__), 'scramble_values.json')) \
                as scramble_file:
            scramble_data = json.load(scramble_file)
            strings = scramble_data['strings']
            self.avatars = OrderedDict(scramble_data['avatars'])

        # Convert the JSON data into dictionary of initial letters to lists of
        # possible names, split between male and female names.
        self.personal_names = {
            person_type: {
                letter: strings['personal_names'][person_type][letter].split()
                for letter in strings['personal_names'][person_type]
            } for person_type in strings['personal_names']
        }
        # Create a combination of male and female name lists.
        self.personal_names[None] = defaultdict(list)
        for person_type in strings['personal_names']:
            for letter, names in self.personal_names[person_type].items():
                self.personal_names[None][letter].extend(names)

        # Convert the JSON data into list of possible family names.
        self.family_names = {
            letter: strings['family_names'][letter].split()
            for letter in strings['family_names']
        }
        # Convert the JSON data into a weighted list of possible prefixes,
        # with a blank prefix to be drawn two thirds of the times.
        prefixes = strings['family_prefixes'].split(',')
        probability = 0.33 / len(prefixes)
        self.family_prefixes = OrderedDict(**{prefix: probability for prefix in prefixes})
        self.family_prefixes[''] = 0.67

        # Convert the JSON data into a weighted list of possible street types.
        types = {}
        for prefix_type, percentage in {'common': 0.60, 'uncommon': 0.40}.items():
            values = strings['street_types'][prefix_type].split()
            types[prefix_type] = {
                'strings': values,
                'probability': percentage / len(values),
            }
        self.street_types = OrderedDict(**{
            prefix: prefix_type['probability']
            for prefix_type in types.values()
            for prefix in prefix_type['strings']
        })

        # Convert the JSON data into list of possible street names.
        self.street_names = (''.join(strings['street_names'])).split()

        self.generator.set_arguments('int_under_200', {'min': 1, 'max': 199})

    def _pick_random_name_from_list(self, possible_names, first_letter=None):
        if first_letter not in possible_names:
            # Check if there is an equivalent letter defined.
            first_letter = self.letter_subs.get(first_letter, first_letter)
        if first_letter not in possible_names:
            # Pick a random initial letter.
            first_letter = self.random_element(possible_names.keys())
        possible_names = possible_names[first_letter]

        return self.random_element(possible_names)

    def personal_name(self, person_type=None, first_letter=None):
        return self._pick_random_name_from_list(
            self.personal_names[
                person_type if person_type in self.personal_names else None
            ],
            first_letter
        )

    def family_name(self, person_type=None, first_letter=None):
        name = self._pick_random_name_from_list(self.family_names, first_letter)
        if name.endswith(self.family_name.consonants):
            if person_type == 'F' and self.generator.random.random() > 0.75:
                name += 'a'
            if person_type == 'M' and self.generator.random.random() > 0.90:
                name += 'e'
        if self.generator.random.random() > 0.85:
            name = (
                self.random_elements(self.family_prefixes, length=1, use_weighting=True)[0]
                + name
            )
        return name

    family_name.consonants = tuple('b d f g k l m n p r s t v w z'.split())

    def random_city(self):
        if not hasattr(self.random_city, 'character_set'):
            # Construct a weighted list of possible characters, with probability
            # to draw a vowel = 0.056, a consonant = 0.023, an extra letter = 0.003.
            character_set = {
                'vowels':     ['aeiouy', 20],
                'consonants': ['bcdfghjklmnpqrstvwxz', 8],
                'extra':      ['àáâãäåąćċčçďđèéêëėęğġģħìíîĩīıįĳķĺľłļńňñņ'
                               + 'òóôõōöőøŕřŗśšşßťŧţþùúûũūüůűųŵýŷÿźžż', 1],
            }
            full_set_len = reduce(
                operator.add,
                (len(chset[0]) * chset[1] for chset in character_set.values())
            )
            for characters in character_set.values():
                probability = characters[1] / full_set_len
                characters.append(probability)
            self.__class__.random_city.character_set = OrderedDict(**{
                letter: probability
                for letterset, appearances, probability in character_set.values()
                for letter in letterset
            })

        city_name = self.random_elements(
            self.random_city.character_set,
            length=self.random_int(3, 10), use_weighting=True)
        city_name = ''.join(city_name).capitalize()
        return city_name

    def eo_street_type(self):
        return self.random_elements(self.street_types, length=1, use_weighting=True)[0]

    def eo_street_name(self):
        return self.random_element(self.street_names)

    def eo_house_ext(self):
        return (
            self.random_element('-/# ')
            + self.random_element(self.eo_house_ext.extensions)
        )

    eo_house_ext.extensions = tuple('A B Bis C D E'.split())

    def eo_address(self):
        pattern = self.random_elements(
            self.address_formats, length=1, use_weighting=True)[0]
        return self.generator.parse(pattern)

    def avatar(self, image_type=None):
        if not hasattr(self.avatars, '_loaded'):
            raise AttributeError('Images not loaded into memory')
        if image_type and image_type.upper() not in self.avatars:
            raise LookupError('Unsupported type')
        if not image_type:
            image_type = self.random_element(self.avatars.keys())
        image_type = image_type.strip().upper()
        avatar_list = self.avatars[image_type]['list']
        if len(avatar_list) == 0:
            raise ValueError(f'No replacement provided for {image_type}')
        return self.random_element(avatar_list)['data']
