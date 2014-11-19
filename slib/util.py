from urllib.parse import urlparse, parse_qs


# This function has been adapted from redis.connection.ConnectionPool.from_url.
# I changed it to return a dict which is compatible with tornadoredis.Client's keyword arguments.
def parse_redis_url(url, db=None, **kwargs):
    """
    Return a connection pool configured from the given URL.

    For example::

        redis://[:password]@localhost:6379/0
        rediss://[:password]@localhost:6379/0
        unix://[:password]@/path/to/socket.sock?db=0

    Three URL schemes are supported:
        redis:// creates a normal TCP socket connection
        rediss:// creates a SSL wrapped TCP socket connection
        unix:// creates a Unix Domain Socket connection

    There are several ways to specify a database number. The parse function
    will return the first specified option:
        1. A ``db`` querystring option, e.g. redis://localhost?db=0
        2. If using the redis:// scheme, the path argument of the url, e.g.
           redis://localhost/0
        3. The ``db`` argument to this function.

    If none of these options are specified, db=0 is used.

    Any additional querystring arguments and keyword arguments will be
    passed along to the ConnectionPool class's initializer. In the case
    of conflicting arguments, querystring arguments always win.
    """
    url_string = url
    url = urlparse(url)
    qs = ''

    # in python2.6, custom URL schemes don't recognize querystring values
    # they're left as part of the url.path.
    if '?' in url.path and not url.query:
        # chop the querystring including the ? off the end of the url
        # and reparse it.
        qs = url.path.split('?', 1)[1]
        url = urlparse(url_string[:-(len(qs) + 1)])
    else:
        qs = url.query

    url_options = {}

    for name, value in parse_qs(qs).items():
        if value and len(value) > 0:
            url_options[name] = value[0]

    # We only support redis:// and unix:// schemes.
    if url.scheme == 'unix':
        url_options.update({
            'password': url.password,
            'unix_socket_path': url.path
        })

    else:
        url_options.update({
            'host': url.hostname,
            'port': int(url.port or 6379),
            'password': url.password,
        })

        # If there's a path argument, use it as the db argument if a
        # querystring value wasn't specified
        if 'selected_db' not in url_options and url.path:
            try:
                url_options['selected_db'] = int(url.path.replace('/', ''))
            except (AttributeError, ValueError):
                pass

    # last shot at the selected_db value
    url_options['selected_db'] = int(url_options.get('selected_db', db or 0))

    # update the arguments from the URL values
    kwargs.update(url_options)
    return kwargs
