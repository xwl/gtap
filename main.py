# -*- coding: utf-8 -*-
# Copyright under  the latest Apache License 2.0

import wsgiref.handlers, urlparse, base64, logging
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import urlfetch_errors
from wsgiref.util import is_hop_by_hop

gtap_vrsion = '0.3.3'

gtap_message = "<html><head><title>GAE Twitter API Proxy</title><style>body { padding: 20px 40px; font-family: Verdana, Helvetica, Sans-Serif; font-size: medium; }</style></head><body><h2>GTAP v#gtap_version# is running!</h2></p>"
gtap_message = gtap_message + "<p>This is a simple solution on Google Appengine which can proxy the HTTP request to twitter's official REST API url.</p><p>Now You can:</p><p><strong>1</strong> use <i>https://#app_url#/</i> instead of <i>https://twitter.com/</i> <br /></p><p><strong>2</strong> use <i>https://#app_url#/api/</i> instead of <i>https://api.twitter.com/</i> <br /></p><p><strong>3</strong> use <i>https://#app_url#/</i> instead of <i>https://search.twitter.com/</i> <br /></p><p><font color='red'><b>Don't forget the \"/\" at the end of your api proxy address!!!.</b></font></p></body></html>"

class MainPage(webapp.RequestHandler):
    def my_output(self, content_type, content):
        self.response.status = '200 OK'
        self.response.headers.add_header('GTAP-Version', gtap_vrsion)
        self.response.headers.add_header('Content-Type', content_type)
        self.response.out.write(content)

    def do_proxy(self, method):
        orig_url = self.request.url
        orig_body = self.request.body
        (scm, netloc, path, params, query, _) = urlparse.urlparse(orig_url)
        
        if 'Authorization' not in self.request.headers :
            headers = {}
        else:
            auth_header = self.request.headers['Authorization']
            auth_parts = auth_header.split(' ')
            user_pass_parts = base64.b64decode(auth_parts[1]).split(':')
            username = user_pass_parts[0]
            password = user_pass_parts[1]
            base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
            headers = {'Authorization': "Basic %s" % base64string}

        path_parts = path.split('/')
        
        if path_parts[1] == 'api' or path_parts[1] == 'search':
            sub_head = path_parts[1]
            path_parts = path_parts[2:]
            path_parts.insert(0,'')
            new_path = '/'.join(path_parts).replace('//','/')
            new_netloc = sub_head + '.twitter.com'
        else:
            new_path = path
            new_netloc = 'twitter.com'

        if new_path == '/' or new_path == '':
            global gtap_message
            gtap_message = gtap_message.replace('#app_url#', netloc)
            gtap_message = gtap_message.replace('#gtap_version#', gtap_vrsion)
            self.my_output( 'text/html', gtap_message )
        else:
            new_url = urlparse.urlunparse(('https', new_netloc, new_path.replace('//','/'), params, query, ''))
            logging.debug(new_url)
            logging.debug(orig_body)
            data = urlfetch.fetch(new_url, payload=orig_body, method=method, headers=headers, allow_truncated=True)
            logging.debug(data.headers)
            try :
                self.response.set_status(data.status_code)
            except Exception:
                logging.debug(data.status_code)
                self.response.set_status(503)
            
            self.response.headers.add_header('GTAP-Version', gtap_vrsion)
            for res_name, res_value in data.headers.items():
                if is_hop_by_hop(res_name) is False and res_name!='status':
                    self.response.headers.add_header(res_name, res_value)
            self.response.out.write(data.content)

    def post(self):
        self.do_proxy('post')
    
    def get(self):
        self.do_proxy('get')

def main():
    application = webapp.WSGIApplication( [(r'/.*', MainPage)], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
