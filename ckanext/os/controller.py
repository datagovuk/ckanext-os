import os
import re
import urllib2
from urllib2 import HTTPError
from urllib import quote

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render
from ckan import model
from ckan.lib.helpers import OrderedDict

# move to configuration?
SEARCH_BASE_URL_OS = '<base href="http://vmlin74/inspire/2_2_1_1/"/>'
SEARCH_BASE_URL_CKAN = '<base href="/os"/>'
PREVIEW_BASE_URL_OS = '<base href="http://localhost/inspireeval/2_2_0_7/" />'
PREVIEW_BASE_URL_CKAN = '<base href="/os"/>'
MAP_TILE_HOST = 'osinspiremappingprod.ordnancesurvey.co.uk' # Not '46.137.180.108'
GAZETTEER_HOST = 'osinspiremappingprod.ordnancesurvey.co.uk' # was 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com' # Not '46.137.180.108'
#LIBRARIES_HOST = 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com' # Not '46.137.180.108'
LIBRARIES_HOST = 'osinspiremappingprod.ordnancesurvey.co.uk' #'46.137.180.108'
LIBRARIES_OS = 'http://46.137.180.108/libraries'
TILES_URL_OS = 'http://46.137.180.108/geoserver/gwc/service/wms'
TILES_URL_CKAN = 'http://%s/geoserver/gwc/service/wms' % MAP_TILE_HOST

class ValidationError(Exception):
    pass

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
        c.libraries_base_url = 'http://%s/libraries' % LIBRARIES_HOST
        # OS had http://46.137.180.108/libraries
        return render('os/map_search.html')

    def wmsmap(self):
        return self.read_file_and_substitute_text(
            'inspire_search/scripts/wmsmap.js', {
                TILES_URL_OS: TILES_URL_CKAN,
                })        

class PreviewWidget(BaseWidget):
    def index(self):
        c.libraries_base_url = 'http://%s/libraries' % LIBRARIES_HOST
        # OS had http://46.137.180.108/libraries
        return render('os/map_preview.html')

    def wmsevalmap(self):
        return self.read_file_and_substitute_text(
            'inspire_search/scripts/wmsevalmap.js', {
                TILES_URL_OS: TILES_URL_CKAN,
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
                                  (GAZETTEER_HOST, quote(q)))
        elif type_ == 'pc':
            # Postcode service
            return self._read_url('http://%s/InspireGaz/postcode?q=%s' %
                                  (GAZETTEER_HOST, quote(q)))
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

    @staticmethod
    def wms_url_correcter(wms_url):
        '''Corrects basic errors in WMS URLs.
        May raise ValidationError if it really cannot be made sense of.
        '''
        # e.g. wms_url = u'http://lasigpublic.nerc-lancaster.ac.uk/ArcGIS/services/Biodiversity/GMFarmEvaluation/MapServer/WMSServer?request=GetCapabilities&service=WMS'
        # Split up params
        try:
            if '?' in wms_url:
                base_url, params_str = wms_url.split('?')
            else:
                base_url, params_str = wms_url, ''
            params_list = params_str.split('&')
            if params_list == ['']:
                params_list = []
            params = OrderedDict()
            for param_str in params_list:
                key, value = param_str.split('=')
                params[key.lower()] = value
                # duplicates get removed here automatically
        except ValueError, e:
            raise ValidationError('URL structure wrong')

        # Add in request and service params if missing
        if 'request' not in params:
            params['request'] = 'GetCapabilities'
        if 'service' not in params:
            params['service'] = 'WMS'

        # Only allow particular parameter values
        if params['request'].lower() not in ('getcapabilities', 'getfeatureinfo'):
            raise ValidationError('Invalid value for "request"')
        if params['service'].lower() != 'wms':
            raise ValidationError('Invalid value for "service"')

        # Reassemble URL
        params_list = []
        for key, value in params.items():
            params_list.append('%s=%s' % (key, value))
        wms_url = base_url + '?' + '&'.join(params_list)
        
        return wms_url
        
    def preview_proxy(self):
        # avoid status_code_redirect intercepting error responses
        request.environ['pylons.status_code_redirect'] = False

        wms_url = request.params.get('url')

        # Check parameter
        if not (wms_url):
            response.status_int = 400
            return 'Missing url parameter'

        # Check URL is in CKAN (otherwise we are an open proxy)
        query = model.Session.query(model.Resource).filter_by(url=wms_url)
        if query.count() == 0:
            response.status_int = 403
            return 'WMS URL not known'

        # Correct basic errors in the WMS URL
        try:
            wms_url = self.wms_url_correcter(wms_url)
        except ValidationError, e:
            response.status_int = 400
            return 'Invalid URL: %s' % str(e)
            
        return self._read_url(wms_url)

    def preview_getinfo(self):
        '''
        This is a proxy request for the Preview map to get detail of a particular subset of a WMS service.
        
        Example request:
        http://dev-ckan.dgu.coi.gov.uk/data/preview_getinfo?url=http%3A%2F%2Flasigpublic.nerc-lancaster.ac.uk%2FArcGIS%2Fservices%2FBiodiversity%2FGMFarmEvaluation%2FMapServer%2FWMSServer%3FLAYERS%3DWinterOilseedRape%26QUERY_LAYERS%3DWinterOilseedRape%26STYLES%3D%26SERVICE%3DWMS%26VERSION%3D1.1.1%26REQUEST%3DGetFeatureInfo%26EXCEPTIONS%3Dapplication%252Fvnd.ogc.se_xml%26BBOX%3D-1.628338%252C52.686046%252C-0.086204%252C54.8153%26FEATURE_COUNT%3D11%26HEIGHT%3D845%26WIDTH%3D612%26FORMAT%3Dimage%252Fpng%26INFO_FORMAT%3Dapplication%252Fvnd.ogc.wms_xml%26SRS%3DEPSG%253A4258%26X%3D327%26Y%3D429
        and that url parameter value unquotes to:
        http://lasigpublic.nerc-lancaster.ac.uk/ArcGIS/services/Biodiversity/GMFarmEvaluation/MapServer/WMSServer?LAYERS=WinterOilseedRape&QUERY_LAYERS=WinterOilseedRape&STYLES=&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&EXCEPTIONS=application%2Fvnd.ogc.se_xml&BBOX=-1.628338%2C52.686046%2C-0.086204%2C54.8153&FEATURE_COUNT=11&HEIGHT=845&WIDTH=612&FORMAT=image%2Fpng&INFO_FORMAT=application%2Fvnd.ogc.wms_xml&SRS=EPSG%3A4258&X=327&Y=429
        '''
        # avoid status_code_redirect intercepting error responses
        request.environ['pylons.status_code_redirect'] = False

        wms_url = request.params.get('url')

        # Check parameter
        if not (wms_url):
            response.status_int = 400
            return 'Missing url parameter'

        # Check base of URL is in CKAN (otherwise we are an open proxy)
        # (the parameters get changed by the Preview widget)
        base_wms_url = wms_url.split('?')[0]
        query = model.Session.query(model.Resource).filter(model.Resource.url.like(base_wms_url+'%'))
        if query.count() == 0:
            response.status_int = 403
            return 'Base of WMS URL not known: %r' % base_wms_url

        return self._read_url(wms_url)


'''
header('Content-type: text/xml; charset=utf-8');

function validateUrl() {

	$wmsUrl = $_GET['url'];

	$str1="?";
	$str2="request=getcapabilities";
	$str3="request=getfeatureinfo";
	$str4="service=wms";

	$chk1 = strpos(strtolower($wmsUrl),$str1);
	$chk2 = strpos(strtolower($wmsUrl),$str2);
	$chk3 = strpos(strtolower($wmsUrl),$str3);
	$chk4 = strpos(strtolower($wmsUrl),$str4);

	if (($chk1 == true && $chk2 == true && $chk4 == true) || ($chk1 == true && $chk3 == true && $chk4 == true)) {

		return true;

	}
	else {

		return false;

	}

 }

if (validateUrl()){

	echo file_get_contents($_GET['url']);

}
'''
