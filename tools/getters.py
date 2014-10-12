# -*- coding: utf-8 -*-
import re
import hashlib
from datetime import date

from phonenumber_field.phonenumber import PhoneNumber
from phonenumbers.phonenumberutil import NumberParseException

def get_username(name, mail):
    username = name.strip()
    if len(username) > 30:
        if len(mail) > 30:
            username = mail[0:mail.index('@')]
            if len(username) > 30:
                h = hashlib.md5()
                h.update(username)
                username = h.digest()
        else:
            username = mail
    return username


def get_title(sekso):
    if sekso == 'Ina':
        return 'Mrs'
    if sekso == 'Vira':
        return 'Mr'
    return ''


def get_birth_date(year):
    if year:
        year = year.strip(' .-')
        if len(year) == 4:
            return date(int(year), 1, 1)
        if len(year) == 2 and int(year) > 30:
            return date(int('19'+year), 1, 1)
        if '/' in year:
            day, month, y = year.split('/')
            if len(y) == 2:
                return date(int('19'+y), int(month), int(day))
            elif len(y) == 4:
                return date(int(y), int(month), int(day))
        else:
            print('  Invalid birth year:', year)
    return None


def get_postcode(string):
    postcode = '' if not string else string.strip()
    if len(postcode) > 11:
        if ' TX, ' in postcode:
            # Just for one postcode, cutting the begining where is 4 digit house number
            postcode = postcode[5:]
        matches = re.search(r'([0-9\-]{4,11})', postcode)
        if matches:
            postcode = matches.group()
        else:
            print('  Invalid postcode:', postcode)
            return ''
    elif len(postcode.strip('.-')) == 0:
        return ''
    return postcode


def get_avatar(path):
    return re.sub('files/pictures/', 'avatars/', path)


def get_truefalse(jesno):
    return True if jesno == 'Jes' else False


def get_int_or_none(string):
    if not string:
        return None
    if string.strip(' -'):
        try:
            return int(string)
        except ValueError:
            print('  Invalid integer for max host/night:', string)
    return None


def get_in_book(string):
    valid = [
        "Mi aperu en la listo de membroj kaj en la libro",
        "Mi ne volas aperi en la listo sed jes en la libro"
    ]
    invalid = [
        "Mi aperu en la listo, sed ne en la libro",
        "Mi ne volas aperi en la listo nek en la libro"
    ]
    if string in valid:
        return True
    return False


def get_phone_number(raw_number, country):
    # Dealing with exceptions
    raw_number = re.sub(r'^\+00', '+', raw_number)
    raw_number = re.sub(r'^\+42 602 ', '+420 602 ', raw_number)
    raw_number = re.sub(r'(^\+01 |^00-1-|^00 1 )', '+1 ', raw_number)  # US
    raw_number = re.sub(r'^045 ', '+45 ', raw_number)  # DK
    raw_number = re.sub(r'(^80|^380\+|^\+38-|^38-)', '+380 ', raw_number)  # UA
    raw_number = re.sub(r'(^55|^00 55|^055)', '+55 ', raw_number) if country == 'BR' else raw_number
    raw_number = re.sub(r'^0041 ', '+41 ', raw_number)  # CH
    raw_number = re.sub(r'(^0086\-|^86)', '+86 ', raw_number)  # CN
    raw_number = re.sub(r'(^\+098 |^0)', '+98 ', raw_number) if country == 'IR' else raw_number
    raw_number = re.sub(r'^\+69 ', '+49 69 ', raw_number)
    raw_number = re.sub(r'^\+80 ', '+81 ', raw_number)
    raw_number = re.sub(r'^54\+011\+', '+54 011 ', raw_number)
    raw_number = re.sub(r'( \(eksterlande$| \(enlande\)$)', '', raw_number)
    raw_number = re.sub(r' \(nur en Japanio\)$', '', raw_number)
    raw_number = re.sub(r' \(p\.3257\)$', '', raw_number)
    raw_number = re.sub(r'\(20\-23h UTC\)', '', raw_number)
    raw_number = re.sub(r'\(0\)', '', raw_number)  # Remove (0)
    raw_number = re.sub(r'(\(|\))', '', raw_number)  # Remove parenthesis
    raw_number = re.sub(r'(\-|\.)', ' ', raw_number)  # Remove '-' and '.'
    raw_number = raw_number.lower().strip('ifmnty oi zs')
    if raw_number and len(raw_number) > 3:
        _country = [country] if country else []
        try:
            phone_number = PhoneNumber.from_string(raw_number, *_country)
            return phone_number.as_e164
        except NumberParseException as e:
            print('  Invalid phone number:', country, raw_number, ' Error', e)
    return ''

def get_phone_type(string):
    if string:
        if 'Poŝtelefona' in string:
            return 'm'  # Mobile
        if 'Hejma' in string:
            return 'h'  # Home
        if 'Labora' in string:
            return 'w'  # Work
        if 'Faksilo' in string:
            return 'h'  # Home
    return ''


def get_state_province(string, country):
    if string and country not in ('FR', 'NL', 'SK'):
        if len(string) < 70:
            return string.strip()
        else:
            print('  Invalid state or province:', string)
    return ''


def get_websites(string):
    if string.strip('htps:/ '):
        raw_websites = re.split(r',| |kaj', string)
        websites = []
        for website in raw_websites:
            website = website.strip()
            if website:
                forbidden = ['@', '..', '.bili', 'script']
                invalid = any([sign in website for sign in forbidden])
                if '.' in website and not invalid:
                    if not 'http' in website:
                        website = 'http://' + website
                    websites.append(website)
                else:
                    print('  Invalid website:', website)
        return websites
    return []
