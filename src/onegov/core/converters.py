""" Contains custom converters used by onegov.town. """

import isodate
import morepath

from datetime import date, datetime
from onegov.core.framework import Framework
from onegov.core.utils import is_uuid
from onegov.core.custom import custom_json as json
from time import mktime, strptime
from uuid import UUID


def extended_date_decode(s):
    """ Decodes a date string HTML5 (RFC3339) compliant."""
    if not s:
        return None

    try:
        return date.fromtimestamp(mktime(strptime(s, '%Y-%m-%d')))
    except OverflowError:
        raise ValueError()


def extended_date_encode(d):
    """ Encodes a date HTML5 (RFC3339) compliant. """
    if not d:
        return ''

    return d.strftime('%Y-%m-%d')


extended_date_converter = morepath.Converter(
    decode=extended_date_decode, encode=extended_date_encode
)


def json_decode(s):
    """ Decodes a json string to a dict. """
    if not s:
        return None

    return json.loads(s)


def json_encode(d):
    """ Encodes a dictionary to json. """
    if not d:
        return '{}'

    return json.dumps(d)


json_converter = morepath.Converter(
    decode=json_decode, encode=json_encode
)


def uuid_decode(s):
    """ Turns a uuid string into a UUID instance. """

    return is_uuid(s) and UUID(s) or None


def uuid_encode(uuid):
    """ Turns a UUID instance into a uuid string. """
    if not uuid:
        return ''

    if isinstance(uuid, str):
        return uuid

    return uuid.hex


uuid_converter = morepath.Converter(
    decode=uuid_decode, encode=uuid_encode
)


@Framework.converter(type=UUID)
def get_default_uuid_converter():
    return uuid_converter


def bool_decode(s):
    """ Decodes a boolean. """
    return False if s == '0' or s == '' else True


def bool_encode(d):
    """ Encodes a boolean. """
    return d and '1' or '0'


bool_converter = morepath.Converter(
    decode=bool_decode, encode=bool_encode
)


@Framework.converter(type=bool)
def get_default_bool_converter():
    return bool_converter


def datetime_decode(s):
    """ Decodes a datetime. """
    return None if not s else isodate.parse_datetime(s)


def datetime_encode(d):
    """ Encodes a datetime. """
    return isodate.datetime_isoformat(d) if d else ''


datetime_converter = morepath.Converter(
    decode=datetime_decode, encode=datetime_encode
)


@Framework.converter(type=datetime)
def get_default_datetime_converter():
    return datetime_converter


def integer_range_encode(t):
    return t and f'{t[0]}-{t[1]}' or ''


def integer_range_decode(s):
    return s and tuple(int(p) for p in s.split('-', 1))


integer_range_converter = morepath.Converter(
    decode=integer_range_decode, encode=integer_range_encode
)
