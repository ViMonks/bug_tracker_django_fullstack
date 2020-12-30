import collections
import enum
import logging
import random
import re
import string
import time

# import boto3
import requests as _requests
import termcolor
# from botocore.client import Config

# Django
from django.db.models import Max, Min
from django.db.models.query import QuerySet, RawQuerySet
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.utils.encoding import smart_str

# 3rd Party
try:
    from termcolor import cprint as _cprint, colored  # pylint: disable=unused-import
except ImportError:
    def _cprint(msg, *_args, **_kwargs):
        print(msg)

    def colored(msg, *_args, **_kwargs):
        return msg


def cprint(msg, *args, **kwargs):
    # if settings.TESTING:
    #     return

    if settings.DEBUG:
        _cprint(msg, *args, **kwargs)
    else:
        pass
        # logger.debug


pattern = re.compile(r'[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}')


def is_uuid(s):
    matches = pattern.findall(s)
    return len(matches) == 1 and matches[0] == s


def site_url(uri='', subdomain=''):
    """
    Handles the fact that ports are annoying.
    """
    if subdomain:
        subdomain = subdomain + '.'

    protocol = settings.SITE_PROTOCOL
    host = settings.SITE_HOST
    port = settings.SITE_PORT
    if settings.SITE_PORT in [80, 443, '80', '443']:
        return f'{protocol}://{subdomain}{host}{uri}'
    return f'{protocol}://{subdomain}{host}:{port}{uri}'


def colored_resp_time(resp_time):
    """
    For stdout (either management commands or the dev server). Colors the
    supplied `resp_time` based on rules of speed.

    Args:
    @resp_time   int    The milliseconds it took for some request to come back.
    """
    resp_time = round(float(resp_time), 3)
    if resp_time < 200.0:
        color = 'green'
    elif resp_time < 500.0:
        color = 'yellow'
    else:
        color = 'red'
    return termcolor.colored(resp_time, color=color)


def parse_bool(val, or_none=False):
    """
    Takes a string, looks for negations to return False.
    """
    if isinstance(val, bool):
        return val

    if smart_str(val).lower().strip() in ['noo', 'no', 'n', 'false', 'nope', 'f', 'none', 'null',
                                          'never', 'no thanks', 'no thank you', 'nul', '0',
                                          'nil', 'nill']:
        return False

    if smart_str(val).lower().strip() in ['yes', 'yeah', 'y', 'true', 't', '1']:
        return True

    if or_none:
        return None

    return bool(val)


def _gen_chunks(r, n):
    l = []

    for x in r:
        l.append(x)
        if n and len(l) >= n:
            yield l
            l = []

    if l:
        yield l


def chunks(r, n, id_chunking=False, min_id=None, max_id=None, auto_chunking=False, id_field='id'):
    """
    Splits a list, dict or QuerySet into chunks of n.
    Returns a list of iterables of n length.


    r
        a list, dict or QuerySet

    n
        an integer

    id_chunking
        we'll find a low and high primary key id
        and chunk between them (if records have been deleted, you
        may get records that are smaller than n).

    min_id and max_id
        are manual ways to be a little faster since it doesn't need
        to do a complex filter to find the chunk endpoints

    auto_chunking
        is an automatic way to find the chunk endpoints that clears
        the filters and finds absolute chunks endpoints


    For simpler queries that just return a lot of data (IE: OFFSET is cheap):

        for users in chunks(User.objects.complex(), 1000):
            # each users is guaranteed to be 1000
            for user in users:
                print user

    For fairly complex queries where OFFSETs are quite expensive, try auto_chunking:

        for users in chunks(User.objects.complex(), 1000, auto_chunking=True):
            # each users is guaranteed to be equal to or less than 1000
            for user in users:
                print user

    """

    if isinstance(r, RawQuerySet):
        raise NotImplementedError('RawQuerySet (or .raw() usage) is not supported.')

    if isinstance(r, set):
        r = list(r)

    if isinstance(r, dict):
        if not r:
            return []

        keys, vals = zip(*r.items())
        return (
            {keys[ii]: vals[ii] for ii in range(i, i + n) if ii < len(r)}
            for i in range(0, len(r), n)
        )

    elif isinstance(r, list):
        if not r:
            return []

        return (r[i:i + n] for i in range(0, len(r), n))

    elif isinstance(r, str):
        return (u''.join(c) for c in chunks(list(r), n))

    elif isinstance(r, QuerySet):
        if id_chunking or auto_chunking:
            w = r
            if auto_chunking and not (min_id and max_id):
                w = QuerySet(r.model, using=r._db).all()
            agg = w.aggregate(Min(id_field), Max(id_field))
            mn = min_id or agg[id_field + '__min']
            mx = max_id or agg[id_field + '__max']
            if not ((mn is None) or (mx is None)):
                return (
                    r.filter(**{id_field + '__gte': i, id_field + '__lt': i + n})
                    for i in range(mn, max(mx, mn + n), n)
                )

        # don't allow result cache to skrew up slicing
        r._result_cache = None
        count = r.count()
        if not count:
            return []

        return (r[i:i + n] for i in range(0, count, n))

    elif isinstance(r, collections.Iterable):
        return _gen_chunks(r, n)

    else:
        raise Exception('r must be a dict or list')

    return []


def queryset_chunks(queryset, chunk_size, id_field='id'):
    return chunks(queryset, chunk_size, auto_chunking=True, id_field=id_field)


def chunkify(r, n, id_chunking=False, min_id=None, max_id=None, auto_chunking=False):
    """
    Same API as chunks() but yields each item one at a time:

        for user in chunkify(User.objects.all(), 500, id_chunking=True):
            print user

    """
    for li in chunks(r, n, id_chunking=id_chunking, min_id=min_id, max_id=max_id, auto_chunking=auto_chunking):
        if isinstance(li, QuerySet):
            li = li.iterator()  # this breaks prefetch???
        for item in li:
            yield item


# s3 = boto3.resource(
#     's3',
#     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#     config=Config(signature_version=settings.AWS_S3_SIGNATURE_VERSION),
# )
# default_bucket = s3.Bucket(settings.AWS_STORAGE_BUCKET_NAME)


def url_to_s3(url, key=None, bucket=None, is_public=False, **kwargs):
    key = key or url.rsplit('/')[-1]
    resp = _requests.get(url)
    resp.raise_for_status()
    file_obj = ContentFile(resp.content)
    return data_to_s3(
        file_obj,
        key,
        bucket,
        is_public,
        ContentType=resp.headers.get('content-type', 'image/png'),
        **kwargs
    )


def data_to_s3(data, key, bucket=None, is_public=False, **kwargs):

    bucket = bucket or default_bucket

    s3_kwargs = {
        'Key': key,
        'Body': data,
    }
    if is_public:
        s3_kwargs['ACL'] = 'public-read'

    s3_kwargs.update(kwargs)
    return bucket.put_object(**s3_kwargs)


def get_complete_s3_url(obj):
    """
    @obj    s3.Object   What is returned from `url_to_s3`
    """
    return "https://s3.{region}.amazonaws.com/{bucket}/{key}".format(
        region=settings.AWS_S3_REGION_NAME,
        bucket=obj.bucket_name,
        key=obj.key,
    )


def choicify_enum(opts: enum.Enum, display_transform=None) -> tuple:
    if display_transform is None:
        display_transform = lambda x: x  # NOQA
    return tuple((option.value, display_transform(option.name),) for option in list(opts))


def friendly_choicify_enum(opts: enum.Enum) -> tuple:
    """Converts an enum into a Django ChoicesField-friendly tuple

    Turns something like this:

        class MyEnum(enum.IntFlag):
            Yes = enum.auto()
            No = enum.auto()

    Into this:

        (('Yes', 1,), ('No', 2,),)
    """
    def transform(val: str) -> str:
        val = val.replace('_', ' ')
        return f'{val[0].upper()}{val[1:]}'  # `title()` smashes Pascal-casing
    return choicify_enum(opts, transform)


letters = f'{string.ascii_letters}{string.digits}'

def genstring(length=10) -> str:
    rndm = ''
    for _ in range(length):
        rndm += random.choice(letters)
    return rndm
