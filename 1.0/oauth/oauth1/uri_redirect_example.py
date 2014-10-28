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
import oauth.oauth as oauth
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

LRS_INITIATE_ENDPOINT = LRS_ENDPOINT + 'OAuth/initiate'
LRS_AUTH_ENDPOINT = LRS_ENDPOINT + 'OAuth/authorize'
LRS_ACCESS_TOKEN_ENDPOINT = LRS_ENDPOINT + 'OAuth/token'
LRS_RESOURCE_ENDPOINT = LRS_ENDPOINT + 'statements'

# SCOPE is a space delimited string
SCOPE = 'all'
CLIENT_ID = 'e14d98d642250ee72884'
CLIENT_SECRET = '4909182f5493a34b166d7633b76e283c77955f52'

logging.basicConfig(format='%(message)s')
l = logging.getLogger(__name__)

class SimpleOAuthClient(oauth.OAuthClient):
    def __init__(self, request_token_url='', access_token_url='', authorization_url=''):
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authorization_url = authorization_url

    def fetch_request_token(self, oauth_request):
        response = requests.get(oauth_request.to_url(), headers=oauth_request.to_header(), verify=False)
        if response.status_code != 200:
            raise Exception("something didn't work right\nresponse: %s -- %s" % (response.status_code, response.content))
        return oauth.OAuthToken.from_string(response.content)

    def fetch_access_token(self, oauth_request):
        response = requests.get(oauth_request.to_url(), headers=oauth_request.to_header(), verify=False)        
        if response.status_code != 200:
            raise Exception("something didn't work right\nresponse: %s -- %s" % (response.status_code, response.content))
        return oauth.OAuthToken.from_string(response.content)

    def authorize_token(self, oauth_request):
        response = requests.get(oauth_request.to_url(), allow_redirects=True, verify=False)
        
        # bankin on a redirect
        if response.status_code != 200:
            if response.status_code > 300 and response.status_code < 400:
                newurl = response.headers['location']
                import urlparse, cgi
                parts = urlparse.urlparse(newurl)[2:]
            
                print parts[2]
                u = urlparse.parse_qs(parts[2])
                return 'http://example.com?oauth_verifier=%s' % raw_input("go to %s, verify, enter PIN here: " % u['next'])
            else:
                raise Exception("something didn't work right\nresponse: %s -- %s" % (response.status_code, response.content))
            
        return response.content

    def access_resource(self, oauth_request):
        headers = oauth_request.to_header()
        headers['X-Experience-API-Version']= '1.0'
        
        response = requests.get(oauth_request.get_normalized_http_url(), headers=headers, verify=False)
        if response.status_code == 200 or response.status_code == 204:
            return response.content
        else:
            raise Exception("response didn't come back right\nresponse:%s -- %s" % (response.status_code, response.content))

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
        '/oauth1/lrs': 'handle_lrs'
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
            login with: <a href='/oauth1/lrs'>LRS</a>
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

    def handle_lrs(self, data):
        self.send_response(302)
        
        consumer = SimpleOAuthClient(LRS_INITIATE_ENDPOINT, LRS_ACCESS_TOKEN_ENDPOINT,
            LRS_AUTH_ENDPOINT)
        client = oauth.OAuthConsumer(CLIENT_ID, CLIENT_SECRET)        
        signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
        signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()

        oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer,
            callback=CALLBACK_URL, http_url=client.request_token_url)
        oauth_request.sign_request(signature_method_plaintext, consumer, None)

        token = client.fetch_request_token(oauth_request)
        oauth_request = oauth.OAuthRequest.from_token_and_callback(token=token, http_url=client.authorization_url)
        response = client.authorize_token(oauth_request)
        



        self.send_header('Location', c.auth_uri(
            state='somestate',
            scope=SCOPE,
            redirect_uri=REDIRECT_URL))
        self.end_headers()

    @success
    def handle_lrs_login(self, data):    
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, verifier=verifier, http_url=client.access_token_url)
        oauth_request.sign_request(signature_method_plaintext, consumer, token)
        token = client.fetch_access_token(oauth_request)

        oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, http_method='GET', http_url=RESOURCE_URL)
        oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)

        resource = client.access_resource(oauth_request)
        print resource






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

        post_payload = json.dumps({"actor":{"mbox":"mailto:oauth1@test.com", "name":"Tester"}, "verb":{"id":"http://adlnet.gov/xapi/verbs/attempted"},
            "object":{"id":"http://onlyatest.com"}})
        
        post_resp = requests.post(LRS_RESOURCE_ENDPOINT, data=post_payload, headers=headers, verify=False)
        print post_resp.content

if __name__ == '__main__':
    l.setLevel(1)
    server_address = ('', SERVER_PORT)
    server = HTTPServer(server_address, Handler)
    l.info('Starting server on %sport %s \nPress <ctrl>+c to exit' % server_address)
    server.serve_forever()