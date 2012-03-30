import os
import urllib2
from urllib2 import HTTPError

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render

# move to configuration?
SEARCH_BASE_URL_OS = '<base href="http://vmlin74/inspire/2_2_1_1/"/>'
SEARCH_BASE_URL_CKAN = '<base href="/os"/>'
PREVIEW_BASE_URL_OS = '<base href="http://localhost/inspireeval/2_2_0_7/" />'
PREVIEW_BASE_URL_CKAN = '<base href="/os"/>'
MAP_TILE_HOST = 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com' # Not '46.137.180.108'
GAZETTEER_HOST = 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com' # Not '46.137.180.108'
LIBRARIES_OS = 'http://46.137.180.108/libraries'
LIBRARIES_CKAN = '/os/libraries'
SEARCH_TILES_OS = 'http://46.137.180.108/geoserver/gwc/service/wms'
SEARCH_TILES_CKAN = 'http://%s/geoserver/gwc/service/wms' % MAP_TILE_HOST

class BaseWidget(BaseController):
    def __init__(self):
        super(BaseWidget, self).__init__()
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        self.os_dir = os.path.join(rootdir, 'ckanext', 'os')
        
    def read_file_and_substitute_text(self, filepath, substitution_map):
        '''Takes a filepath and returns its contents, having made specific
        substitutions in the text.

        @param filepath is relative to self.os_dir
        '''
        f = open(os.path.join(self.os_dir, filepath), 'r')
        try:
            content = f.read()
        finally:
            f.close()
        for existing, replacement in substitution_map.items():
            assert existing in content, '%s not found' % existing
            content = content.replace(existing, replacement)
        return content
    

class SearchWidget(BaseWidget):
    def index(self):
        return self.read_file_and_substitute_text(
            'inspire_search/searchmapwms.htm', {
                SEARCH_BASE_URL_OS: SEARCH_BASE_URL_CKAN,
                LIBRARIES_OS: LIBRARIES_CKAN,
                })

    def wmsmap(self):
        return self.read_file_and_substitute_text(
            'inspire_search/scripts/wmsmap.js', {
                SEARCH_TILES_OS: SEARCH_TILES_CKAN,
                })        

class PreviewWidget(BaseWidget):
    def index(self):
        return self.read_file_and_substitute_text(
            'inspire_preview/evalmapwms.htm', {
                PREVIEW_BASE_URL_OS: PREVIEW_BASE_URL_CKAN,
                LIBRARIES_OS: LIBRARIES_CKAN,
                })

class Proxy(BaseController):
    def gazetteer_proxy(self):
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
                                  (GAZETTEER_HOST, q))
        elif type_ == 'pc':
            # Postcode service
            return self._read_url('http://%s/InspireGaz/postcode?q=%s' %
                                  (GAZETTEER_HOST, q))
        else:
            response.status_int = 400
            return 'Value for t parameter not recognised'

    def _read_url(self, url, post_data=None, content_type=None):
        headers = {'Content-Type': content_type} if content_type else {}
        request = urllib2.Request(url, post_data, headers)
        try:
            f = urllib2.urlopen(request)
        except HTTPError, e:
            response.status_int = 400
            return 'Proxied server returned %s: %s' % (e.code, e.msg)
        return f.read()
        
    def geoserver_proxy(self, url_suffix):
        # for boundary information etc.
        url = 'http://%s/geoserver/%s' % \
              (MAP_TILE_HOST, url_suffix)
        return self._read_url(url, post_data=request.body,
                              content_type=request.headers.get('Content-Type'))
        
