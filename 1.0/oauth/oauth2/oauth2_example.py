"""
Copyright (C) <2012> <Demian Brecht>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import requests
import json
import logging
import sys, os
from functools import wraps
from datetime import datetime, timedelta
from time import mktime

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from ConfigParser import ConfigParser
    from urlparse import urlparse, urlsplit, urlunsplit, parse_qsl
    from urllib import urlencode
    from urllib2 import Request, urlopen
    from io import BytesIO 

    # monkeypatch httpmessage
    from httplib import HTTPMessage
    def get_charset(self):
        try:
            data = filter(lambda s: 'Content-Type' in s, self.headers)[0]
            if 'charset' in data:
                cs = data[data.index(';') + 1:-2].split('=')[1].lower()
                return cs
        except IndexError:
            pass

        return 'utf-8'
    HTTPMessage.get_content_charset = get_charset 
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from configparser import ConfigParser
    from urllib.parse import (urlparse, parse_qsl, urlencode,
        urlunsplit, urlsplit)
    from io import BytesIO 
    from urllib.request import Request, urlopen

from gzip import GzipFile
from json import loads

ENCODING_UTF8 = 'utf-8'
SERVER_PORT = 8099
REDIRECT_URL = 'http://localhost:%s/login/lrs' % SERVER_PORT

# Include /xapi/ at the end
LRS_ENDPOINT = 'http://localhost:8000/xapi/'

LRS_AUTH_ENDPOINT = LRS_ENDPOINT + 'oauth2/authorize'
LRS_ACCESS_TOKEN_ENDPOINT = LRS_ENDPOINT + 'oauth2/access_token'
LRS_RESOURCE_ENDPOINT = LRS_ENDPOINT + 'statements'

# SCOPE is a space delimited string
SCOPE = 'statements/write statements/read/mine define'
CLIENT_ID = '<client id>'
CLIENT_SECRET = '<client secret>'

logging.basicConfig(format='%(message)s')
l = logging.getLogger(__name__)


class Client(object):
    """ OAuth 2.0 client object
    """

    def __init__(self, auth_endpoint=None, token_endpoint=None,
        resource_endpoint=None, client_id=None, client_secret=None,
        token_transport=None):
        """ Instantiates a `Client` to authorize and authenticate a user

        :param auth_endpoint: The authorization endpoint as issued by the
                              provider. This is where the user should be
                              redirect to provider authorization for your
                              application.
        :param token_endpoint: The endpoint against which a `code` will be
                               exchanged for an access token.
        :param resource_endpoint: The base url to use when accessing resources
                                  via `Client.request`.
        :param client_id: The client ID as issued by the provider.
        :param client_secret: The client secret as issued by the provider. This
                              must not be shared.
        """
        assert token_transport is None or hasattr(token_transport, '__call__')

        self.auth_endpoint = auth_endpoint
        self.token_endpoint = token_endpoint
        self.resource_endpoint = resource_endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_transport = token_transport or transport_query
        self.token_expires = -1
        self.refresh_token = None

    def auth_uri(self, redirect_uri=None, scope=None, scope_delim=None, 
        state=None, **kwargs):

        """  Builds the auth URI for the authorization endpoint

        :param scope: (optional) The `scope` parameter to pass for
                      authorization. The format should match that expected by
                      the provider (i.e. Facebook expects comma-delimited,
                      while Google expects space-delimited)
        :param state: (optional) The `state` parameter to pass for
                      authorization. If the provider follows the OAuth 2.0
                      spec, this will be returned to your `redirect_uri` after
                      authorization. Generally used for CSRF protection.
        :param **kwargs: Any other querystring parameters to be passed to the
                         provider.
        """
        kwargs.update({
            'client_id': self.client_id,
            'response_type': 'code',
        })

        if scope is not None:
            kwargs['scope'] = scope

        if state is not None:
            kwargs['state'] = state

        if redirect_uri is not None:
            kwargs['redirect_uri'] = redirect_uri

        return '%s?%s' % (self.auth_endpoint, urlencode(kwargs))

    def request_token(self, parser=None, redirect_uri=None, **kwargs):
        """ Request an access token from the token endpoint.
        This is largely a helper method and expects the client code to
        understand what the server expects. Anything that's passed into
        ``**kwargs`` will be sent (``urlencode``d) to the endpoint. Client
        secret and client ID are automatically included, so are not required
        as kwargs. For example::

            # if requesting access token from auth flow:
            {
                'code': rval_from_auth,
            }

            # if refreshing access token:
            {
                'refresh_token': stored_refresh_token,
                'grant_type': 'refresh_token',
            }

        :param parser: Callback to deal with returned data. Not all providers
                       use JSON.
        """

        kwargs = kwargs and kwargs or {}

        parser = parser or _default_parser
        kwargs.update({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'grant_type' in kwargs and kwargs['grant_type'] or \
                'authorization_code'
        })
        if redirect_uri is not None:
            kwargs.update({'redirect_uri': redirect_uri})

        # TODO: maybe raise an exception here if status code isn't 200?
        msg = urlopen(self.token_endpoint, urlencode(kwargs).encode(
            'utf-8'))
        data = parser(msg.read().decode(msg.info().get_content_charset() or
            'utf-8'))

        for key in data:
            setattr(self, key, data[key])

        # expires_in is RFC-compliant. if anything else is used by the
        # provider, token_expires must be set manually
        if hasattr(self, 'expires_in'):
            try:
                # python3 dosn't support long
                seconds = long(self.expires_in)
            except:
                seconds = int(self.expires_in)
            self.token_expires = mktime((datetime.utcnow() + timedelta(
                seconds=seconds)).timetuple())

    def refresh(self):
        self.request_token(refresh_token=self.refresh_token,
            grant_type='refresh_token')

    def request(self, method=None, data=None, headers=None, parser=None): 
        """ Request user data from the resource endpoint
        :param method: HTTP method. Defaults to ``GET`` unless data is not None
                       in which case it defaults to ``POST``
        :param data: Data to be POSTed to the resource endpoint
        :param parser: Parser callback to deal with the returned data. Defaults
                       to ``json.loads`.`
        """
        assert self.access_token is not None
        parser = parser or loads 

        if not method:
            method = 'GET' if not data else 'POST'

        req = self.token_transport('{0}'.format(self.resource_endpoint), self.access_token, data=data, method=method, headers=headers)

        resp = urlopen(req)
        data = resp.read()
        try:
            return parser(data.decode(resp.info().get_content_charset() or
                'utf-8'))
            # try to decode it first using either the content charset, falling
            # back to utf-8

        except UnicodeDecodeError:
            # if we've gotten a decoder error, the calling code better know how
            # to deal with it. some providers (i.e. stackexchange) like to gzip
            # their responses, so this allows the client code to handle it
            # directly.
            return parser(data)

def transport_headers(url, access_token, data=None, method=None, headers=None):
    try:
        req = Request(url, data=data, method=method)
    except TypeError:
        req = Request(url, data=data)
        req.get_method = lambda: method

    add_headers = {'Authorization': 'Bearer {0}'.format(access_token)}
    if headers is not None:
        add_headers.update(headers)

    req.headers.update(add_headers)
    return req

def transport_query(url, access_token, data=None, method=None, headers=None):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update({
        'access_token': access_token
    })
    url = urlunsplit((parts.scheme, parts.netloc, parts.path,
        urlencode(query), parts.fragment))
    try:
        req = Request(url, data=data, method=method)
    except TypeError:
        req = Request(url, data=data)
        req.get_method = lambda: method

    if headers is not None:
        req.headers.update(headers)

    return req

def _default_parser(data):
    try:
        return loads(data)
    except ValueError:
        return dict(parse_qsl(data))


class Handler(BaseHTTPRequestHandler):
    route_handlers = {
        '/': 'handle_root',
        '/login/lrs': 'handle_lrs_login',
        '/oauth2/lrs': 'handle_lrs'
    }

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in self.route_handlers:
            getattr(self, self.route_handlers[url.path])(
            dict(parse_qsl(url.query)))
        else:
            self.send_response(404)

    def success(func):
        def wrapper(self, *args, **kwargs):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.log_message(self.path)
            self.end_headers()
            return func(self, *args, **kwargs)
        return wrapper

    @success
    def handle_root(self, data):
        self.wfile.write('''
            login with: <a href='/oauth2/lrs'>LRS</a>
        '''.encode(ENCODING_UTF8))

    def dump_response(self, data):
        for k in data:
            self.wfile.write('{0}: {1}<br>'.format(k,
                data[k]).encode(ENCODING_UTF8))

    def dump_client(self, c):
        for k in c.__dict__:
            self.wfile.write('{0}: {1}<br>'.format(k,
                c.__dict__[k]).encode(ENCODING_UTF8))
        self.wfile.write('<hr/>'.encode(ENCODING_UTF8))

    def dump_data(self, data):
        self.wfile.write(data)


    def handle_lrs(self, data):
        self.send_response(302)
        c = Client(auth_endpoint=LRS_AUTH_ENDPOINT,
            client_id=CLIENT_ID)
        self.send_header('Location', c.auth_uri(
            state='somestate',
            scope=SCOPE,
            redirect_uri=REDIRECT_URL))
        self.end_headers()

    @success
    def handle_lrs_login(self, data):
        c = Client(token_endpoint=LRS_ACCESS_TOKEN_ENDPOINT,
            resource_endpoint=LRS_RESOURCE_ENDPOINT,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_transport=transport_headers)
        
        c.request_token(code=data['code'],
            redirect_uri=REDIRECT_URL)

        self.dump_client(c)        
        d = c.request(headers={'Authorization': "Bearer " + str(c.access_token), 'content-type': 'application/json', 'X-Experience-API-Version': '1.0.2'})
        self.dump_response(d)
        
        headers={'Authorization': "Bearer " + str(c.access_token), 'content-type': 'application/json', 'X-Experience-API-Version': '1.0.2'}

        post_payload = json.dumps({"actor":{"mbox":"mailto:oauth2@test.com", "name":"Tester"}, "verb":{"id":"http://adlnet.gov/xapi/verbs/attempted"},
            "object":{"id":"http://onlyatest.com"}})
        
        post_resp = requests.post(LRS_RESOURCE_ENDPOINT, data=post_payload, headers=headers, verify=False)
        self.dump_data(post_resp.content)

if __name__ == '__main__':
    l.setLevel(1)
    server_address = ('', SERVER_PORT)
    server = HTTPServer(server_address, Handler)
    l.info('Starting server on %sport %s \nPress <ctrl>+c to exit' % server_address)
    server.serve_forever()