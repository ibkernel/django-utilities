import datetime
import re
from decimal import Decimal
from functools import wraps

import sqlparse
from django.db import connections, reset_queries

from configurations import DjangoConfig

__all__ = [
    'print_latest_n_sqls', 'print_last_n_sql', 'debug_print_queries'
]


def debug_print_queries(func):
    """
    print all the sql executed in the decorated function,
    """

    @wraps(func)
    def inner_func(*args, **kwargs):
        res = func(*args, **kwargs)

        if DjangoConfig.DEBUG:
            print(f'function: {func.__name__}\n----------------\n')
            for name in connections:
                query_log_size = len(connections[name].queries)
                if query_log_size > 0:
                    print_latest_n_sqls(connections[name], last_n=query_log_size)

            print(f'\n----------------\n')

            reset_queries()
        return res

    return inner_func


def print_latest_n_sqls(connection, last_n=1, pretty_print=True):
    """
    print latest n sql under provided db connection from farthest to nearest
    """
    assert last_n >= 1

    for i in range(last_n, 0, -1):
        print_last_n_sql(connection, i, pretty_print)
        print(end='\n\n')


def print_last_n_sql(connection, last_n=1, pretty_print=True):
    """
    print the last N sql under provided db connection
    """
    assert last_n >= 1

    if connection.display_name == 'MySQL':
        _print_last_n_sql_for_mysql(connection, last_n, pretty_print)
    elif connection.display_name == 'SQL Server':
        _print_last_n_sql_for_sql_server(connection, last_n, pretty_print)
    else:
        raise NotImplementedError(f'vendor {connection.display_name} not implemented')


def _print_last_n_sql_for_mysql(connection, last_n=1, pretty_print=True):
    query_data = connection.queries[-last_n]['sql']
    if pretty_print:
        print(sqlparse.format(query_data, reindent=True, keyword_case="upper"), end='\n')
    else:
        print(query_data)


def _print_last_n_sql_for_sql_server(connection, last_n=1, pretty_print=True):
    query_data = connection.queries[-last_n]['sql']

    # get query between first quotes
    quoted = re.compile("'[^']*'")
    query_string = quoted.findall(query_data)[0].strip("'").replace('%s', '{}')

    # get params string after param_prefix
    param_prefix = ' - PARAMS = '
    params_string = query_data[query_data.find(param_prefix) + len(param_prefix):]

    # turn params into python object

    params = eval(params_string)

    sql_with_params = _build_sql_with_params(query_string, params)

    if pretty_print:
        print(sqlparse.format(sql_with_params, reindent=True, keyword_case="upper"), end='\n')
    else:
        print(sql_with_params)


def _build_sql_with_params(query_string, params):
    sanitized_params = []

    for p in params:
        if isinstance(p, (datetime.date, datetime.datetime)):
            s_p = "'" + str(p) + "'"
        elif isinstance(p, Decimal):
            s_p = str(p)
        else:
            s_p = str(p)
        sanitized_params.append(s_p)
    return query_string.format(*sanitized_params)


if __name__ == '__main__':

    # some query under YOUR_DB_NAME_HERE db
    # ...

    # print the latest two query
    print_latest_n_sqls(connection=connections['YOUR_DB_NAME_HERE'], last_n=2)

    # print the last query only
    print_last_n_sql(connection=connections['YOUR_DB_NAME_HERE'], last_n=1)


    @debug_print_queries
    def foo():
        # some orm queries
        pass

    # print all executed sql in foo()
    foo()
