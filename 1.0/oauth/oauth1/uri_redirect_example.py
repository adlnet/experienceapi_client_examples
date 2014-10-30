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
import logging
import oauth.oauth as oauth
import memcache

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from urlparse import urlparse, parse_qsl
    from urllib import urlencode

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

ENCODING_UTF8 = 'utf-8'
SERVER_PORT = 8099
# Redirect URL to send LRS back here
REDIRECT_URL = 'http://localhost:%s/login/lrs' % SERVER_PORT

# Include /xapi/ at the end
LRS_ENDPOINT = 'http://localhost:8000/xapi/'

LRS_INITIATE_ENDPOINT = LRS_ENDPOINT + 'OAuth/initiate'
LRS_AUTH_ENDPOINT = LRS_ENDPOINT + 'OAuth/authorize'
LRS_ACCESS_TOKEN_ENDPOINT = LRS_ENDPOINT + 'OAuth/token'
LRS_RESOURCE_ENDPOINT = LRS_ENDPOINT + 'statements'

# SCOPE is a space delimited string
SCOPE = 'all'
CLIENT_ID = '<client id>'
CLIENT_SECRET = '<client secret>'

SIGNATURE_METHOD = oauth.OAuthSignatureMethod_PLAINTEXT()


logging.basicConfig(format='%(message)s')
l = logging.getLogger(__name__)

mc = memcache.Client(['127.0.0.1:11211'], debug=0)

class Client(object):
    """ OAuth 1.0 client object
    """

    def __init__(self, request_endpoint=None, auth_endpoint=None, token_endpoint=None,
        resource_endpoint=None, client_id=None, client_secret=None, refresh_token=None,
        access_token=None, oauth_verifier=None):
        """ Instantiates a `Client` to authorize and authenticate a user """
        self.request_endpoint = request_endpoint
        self.auth_endpoint = auth_endpoint
        self.token_endpoint = token_endpoint
        self.resource_endpoint = resource_endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = None
        self.access_token = None
        self.oauth_verifier = oauth_verifier

    def request_uri(self, oauth_callback, scope=None):

        """  Builds the auth URI for the authorization endpoint  """
        
        if scope is not None:
            scope = {'scope': scope}

        consumer = oauth.OAuthConsumer(CLIENT_ID, CLIENT_SECRET)
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=oauth_callback, http_url=self.request_endpoint)
        oauth_request.sign_request(SIGNATURE_METHOD, consumer, None)

        path = oauth_request.to_url()
        if scope:
            path = path + "&%s" % urlencode(scope)
        return path

    def auth_uri(self, oauth_token, **kwargs):

        """  Builds the auth URI for the authorization endpoint  """
        
        kwargs.update({
            'oauth_token': oauth_token,
        })
        return '%s?%s' % (self.auth_endpoint, urlencode(kwargs))

    def fetch_access_token(self, token):
        consumer = oauth.OAuthConsumer(CLIENT_ID, CLIENT_SECRET)
        
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, verifier=self.oauth_verifier,
            http_url=LRS_ACCESS_TOKEN_ENDPOINT)
        oauth_request.sign_request(SIGNATURE_METHOD, consumer, token)

        response = requests.get(oauth_request.to_url(), headers=oauth_request.to_header(), verify=False)

        resp_list = response.content.split('&')
        oauth_token = resp_list[1].split('=')[1]
        oauth_token_secret = resp_list[0].split('=')[1]
        return oauth_token, oauth_token_secret

class Handler(BaseHTTPRequestHandler):
    route_handlers = {
        '/': 'handle_root',
        '/login/lrs': 'handle_lrs_login',
        '/oauth/lrs': 'handle_lrs'
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

    def dump_data(self, data):
        self.wfile.write(data)

    @success
    def handle_root(self, data):
        self.wfile.write('''
            login with: <a href='/oauth/lrs'>LRS</a>
        '''.encode(ENCODING_UTF8))

    def handle_lrs(self, data):
        self.send_response(302)
        c = Client(request_endpoint=LRS_INITIATE_ENDPOINT,
            auth_endpoint=LRS_AUTH_ENDPOINT,
            client_id=CLIENT_ID)

        response = requests.get(c.request_uri(oauth_callback=REDIRECT_URL, scope=SCOPE), verify=False)
        handler_token = oauth.OAuthToken.from_string(response.content)
        mc.set("token", handler_token)

        self.send_header('Location', c.auth_uri(
            oauth_token=handler_token.key))
        self.end_headers()

    @success
    def handle_lrs_login(self, data):
        c = Client(request_endpoint=LRS_INITIATE_ENDPOINT,
            token_endpoint=LRS_ACCESS_TOKEN_ENDPOINT,
            resource_endpoint=LRS_RESOURCE_ENDPOINT,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            oauth_verifier=data['oauth_verifier'])

        handler_token = mc.get("token")
        access_token, access_token_secret = c.fetch_access_token(token=handler_token)
        access_token = oauth.OAuthToken(access_token, access_token_secret)
        
        consumer = oauth.OAuthConsumer(CLIENT_ID, CLIENT_SECRET)
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=access_token, http_method='GET', http_url=LRS_RESOURCE_ENDPOINT)
        oauth_request.sign_request(SIGNATURE_METHOD, consumer, access_token)

        headers = oauth_request.to_header()
        headers['X-Experience-API-Version']= '1.0'
        response = requests.get(oauth_request.get_normalized_http_url(), headers=headers, verify=False)
        self.dump_data(response.content)

if __name__ == '__main__':
    l.setLevel(1)
    server_address = ('', SERVER_PORT)
    server = HTTPServer(server_address, Handler)
    l.info('Starting server on %sport %s \nPress <ctrl>+c to exit' % server_address)
    server.serve_forever()