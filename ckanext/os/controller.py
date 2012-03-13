import os
import urllib2
from urllib2 import HTTPError

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render

# move to configuration
OS_URL_BASE = '<base href="http://vmlin74/inspire/2_2_1_1/"/>'
CKAN_URL_BASE = '<base href="/os"/>'
INSPIRE_IP_ADDRESS = 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com' # Not '46.137.180.108'

class BaseWidget(BaseController):
    def __init__(self):
        super(BaseWidget, self).__init__()
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        self.os_dir = os.path.join(rootdir, 'ckanext', 'os')
        

class SearchWidget(BaseWidget):
    def __init__(self):
        super(SearchWidget, self).__init__()        
        self.widget_dir = os.path.join(self.os_dir, 'inspire_search')
        
    def index(self):
        f = open(os.path.join(self.widget_dir, 'searchmapwms.htm'), 'r')
        try:
            html = f.read()
        finally:
            f.close()
        assert OS_URL_BASE in html
        html = html.replace(OS_URL_BASE, CKAN_URL_BASE)
        return html

class PreviewWidget(BaseController):
    def index(self):
        pass    

class Proxy(BaseController):
    def proxy(self):
        # avoid status_code_redirect intercepting error responses
        request.environ['pylons.status_code_redirect'] = False

        type_ = request.params.get('t')
        q = request.params.get('q')
        # Check parameters
        if not (type_ and q):
            response.status_int = 400
            return 'Missing t or q parameter'
        if type_ == 'gz':
            # Gazetteer service
            return self._read_url('http://%s/InspireGaz/gazetteer?q=%s' %
                                  (INSPIRE_IP_ADDRESS, q))
        elif type_ == 'pc':
            # Postcode service
            return self._read_url('http://%s/InspireGaz/postcode?q=%s' %
                                  (INSPIRE_IP_ADDRESS, q))
        else:
            response.status_int = 400
            return 'Value for t parameter not recognised'

    def _read_url(self, url):
        try:
            f = urllib2.urlopen(url)
        except HTTPError, e:
            response.status_int = 400
            return 'Proxied server returned %s: %s' % (e.code, e.msg)
        return f.read()
        
