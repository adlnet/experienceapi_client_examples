"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Example consumer. This is not recommended for production.
Instead, you'll want to create your own subclass of OAuthClient
or find one that works with your web framework.
"""
"""
tom c changed stuff to work with the ADL LRS
"""
import time
import oauth.oauth as oauth
import requests

# settings for the local test consumer
LOCAL = True
SCHEME = 'http' if LOCAL else 'https' #'http'
SERVER = '127.0.0.1' if LOCAL else 'lrs.adlnet.gov' #'127.0.0.1'
PORT = '8000' if LOCAL else '443' #8000

# fake urls for the test server (matches ones in server.py)
REQUEST_TOKEN_URL = '%s://%s:%s%s' % (SCHEME,SERVER,PORT,'/XAPI/OAuth/initiate')
ACCESS_TOKEN_URL = '%s://%s:%s%s' % (SCHEME,SERVER,PORT,'/XAPI/OAuth/token')
AUTHORIZATION_URL = '%s://%s:%s%s' % (SCHEME,SERVER,PORT,'/XAPI/OAuth/authorize')
CALLBACK_URL = 'oob'
RESOURCE_URL = '%s://%s:%s%s' % (SCHEME,SERVER,PORT,'/XAPI/statements')

# key and secret granted by the service provider for this consumer application - same as the MockOAuthDataStore
CONSUMER_KEY = '<consumer key>'
CONSUMER_SECRET = '<consumer secret>'

# change this 
ERROR_FILE = '/home/ubuntu/Desktop/error.html'

class SimpleOAuthClient(oauth.OAuthClient):

    def __init__(self, request_token_url='', access_token_url='', authorization_url=''):
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authorization_url = authorization_url

    def fetch_request_token(self, oauth_request):
        response = requests.get(oauth_request.to_url(), headers=oauth_request.to_header(), verify=False)
        if response.status_code != 200:
            print "Fail: %s" % response.status_code
            f = open(ERROR_FILE, 'w')
            f.write(response.content)
            f.close()
            print "text written to %s" % ERROR_FILE
        return oauth.OAuthToken.from_string(response.content)

    def fetch_access_token(self, oauth_request):
        response = requests.get(oauth_request.to_url(), headers=oauth_request.to_header(), verify=False)
        
        return oauth.OAuthToken.from_string(response.content)

    def authorize_token(self, oauth_request):
        response = requests.get(oauth_request.to_url(), allow_redirects=False, verify=False)
        
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
                print "Fail: %s" % response.status_code
                f = open(ERROR_FILE, 'w')
                f.write(response.content)
                f.close()
                print "text written to %s" % ERROR_FILE
                raise Exception("something didn't work right\nresponse: %s -- %s" % (response.status_code, response.content))
            
        return response.content

    def access_resource(self, oauth_request):
        headers = oauth_request.to_header()
        headers['X-Experience-API-Version']= '0.95'
        
        response = requests.get(oauth_request.get_normalized_http_url(), headers=headers, verify=False)
        if response.status_code == 200 or response.status_code == 204:
            return response.content
        else:
            print "Fail: %s" % response.status_code
            #print r.text
            f = open(ERROR_FILE, 'w')
            f.write(response.content)
            f.close()
            print "text written to %s" % ERROR_FILE
            raise Exception("response didn't come back right\nresponse:%s -- %s" % (response.status_code, response.content))

def run_example():

    # setup
    print '** OAuth Python Library Example **'
    client = SimpleOAuthClient(REQUEST_TOKEN_URL, ACCESS_TOKEN_URL, AUTHORIZATION_URL)
    consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
    signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
    signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
    pause()

    # get request token
    print '* Obtain a request token ...'
    pause()
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=client.request_token_url)
    oauth_request.sign_request(signature_method_plaintext, consumer, None)
    print 'REQUEST (via headers)'
    pause()
    token = client.fetch_request_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    print 'callback confirmed? %s' % str(token.callback_confirmed)
    pause()

    print '* Authorize the request token ...'
    pause()
    oauth_request = oauth.OAuthRequest.from_token_and_callback(token=token, http_url=client.authorization_url)
    print 'REQUEST (via url query string)'
    pause()
    
    response = client.authorize_token(oauth_request)
    print 'GOT'
    print response
    #  get the verifier
    import urlparse, cgi
    query = urlparse.urlparse(response)[4]
    params = cgi.parse_qs(query, keep_blank_values=False)
    verifier = params['oauth_verifier'][0]
    print 'verifier: %s' % verifier
    pause()

    # get access token
    print '* Obtain an access token ...'
    pause()
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, verifier=verifier, http_url=client.access_token_url)
    oauth_request.sign_request(signature_method_plaintext, consumer, token)
    print 'REQUEST (via headers)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    token = client.fetch_access_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    # access some protected resources
    print '* Access protected resources ...'
    pause()
    
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, http_method='GET', http_url=RESOURCE_URL)
    oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)
    
    print 'REQUEST (via get)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    
    resource = client.access_resource(oauth_request)
    
    print 'GOT'
    print 'resource:\n %s' % resource
    pause()

def pause():
    print ''
    time.sleep(1)

if __name__ == '__main__':
    run_example()
    print 'Done.'
