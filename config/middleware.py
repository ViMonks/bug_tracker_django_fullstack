import logging
import time

# Django
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

# Local Apps
from .middleware_utils import colored, colored_resp_time, cprint

logger = logging.getLogger(__name__)


class ProductionLogBadResponsesMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        if response.status_code > 302 and 'favicon' not in request.path:
            logger.warning(
                '{} {} {}: {}'.format(
                    response.status_code,
                    request.method,
                    request.path,
                    response.content[:100],
                ),
            )
        return response


class LogStuff(MiddlewareMixin):

    def process_request(self, request):
        querystring = ''
        if request.META['QUERY_STRING']:
            querystring = '?%s' % request.META['QUERY_STRING']
            querystring = querystring.replace('%2C', ',')
        cprint(
            '%s %s %s%s' % (
                request.method,
                request.META.get('CONTENT_TYPE', ''),
                request.META.get('PATH_INFO', ''),
                querystring,
            ),
            color='cyan',
        )
        try:
            _is_write: bool = request.method in ['POST', 'PUT', 'PATCH', 'DELETE']
            if _is_write and bool(request.body) and 'application/json' in request.META.get('CONTENT_TYPE'):
                cprint(request.body, color='cyan')
        except Exception as e:
            print(e)  # NOQA
            # JSON errors are possible if the post data is weird, but whatever
            pass

    def process_view(self, request, view_func, view_args, view_kwargs):
        if settings.DEBUG:
            cprint("Calling view {}".format(view_func.__name__), color="green")

    def process_exception(self, request, exception):
        import traceback
        cprint(traceback.format_exc(), color='red')

    def process_response(self, request, response):
        # if 'print_queries' not in request.GET.keys():
        #     return response

        if response.status_code > 399 and response.status_code < 500:
            cprint(response.content, color='red')

        try:
            import sqlparse
        except ImportError:
            sqlparse = None

        if len(connection.queries) > 0 and settings.DEBUG:
            total_time = 0.0
            for query in connection.queries:
                total_time = total_time + float(query['time'])
                continue
                print('')
                if sqlparse:
                    print(sqlparse.format(query['sql'], reindent=True))
                    print('\033[93m' + query['time'] + '\033[0m')
                else:
                    print(query['sql'])
                print('')
            print("\033[1;32m[TOTAL DB TIME: %s seconds]\033[0m" % round(total_time, 4))
            print("  Ran %d queries" % len(connection.queries))
        return response


class LocalizeTimezone(MiddlewareMixin):

    def process_request(self, request):
        if request.user.is_authenticated:
            timezone.activate(request.user.get_timezone())
        else:
            timezone.deactivate()

    def process_response(self, request, response):
        timezone.deactivate()
        return response


class TimeRequests(MiddlewareMixin):

    def process_request(self, request):
        request._start_time = time.time()  # pylint: disable=protected-access

    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            resp_time_ms = (time.time() - request._start_time) * 1000  # pylint: disable=protected-access

            if settings.DEBUG:
                querystring = ''
                if request.META['QUERY_STRING']:
                    querystring = '?%s' % request.META['QUERY_STRING']
                    querystring = querystring.replace('%2C', ',')
                path = f'{request.path}{querystring}'
                print(
                    'Responded {} after {} ms :: {}'.format(
                        self.colored_response_code(response.status_code),
                        colored_resp_time(resp_time_ms),
                        path,
                    )
                )
        return response

    def colored_response_code(self, code):
        if code in [200, 201, 202, 204]:
            return colored(code, color='green')
        elif code in [301, 302]:
            return colored(code, color='blue')
        return colored(code, color='red')
