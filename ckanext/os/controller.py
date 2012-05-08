import os
import re
import urllib2
from urllib2 import HTTPError, URLError
from urllib import quote
from urllib import urlencode
import logging

from pylons import session as pylons_session
from pylons import config

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render
from ckan import model
from ckan.lib.helpers import OrderedDict, json

log = logging.getLogger(__name__)

# Configuration
GEOSERVER_HOST = config.get('ckanext-os.geoserver.host',
                            'osinspiremappingprod.ordnancesurvey.co.uk') # Not '46.137.180.108'
GAZETTEER_HOST = config.get('ckanext-os.gazetteer.host',
                            'osinspiremappingprod.ordnancesurvey.co.uk') # was 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com' # Not '46.137.180.108'
LIBRARIES_HOST = config.get('ckanext-os.libraries.host',
                            'osinspiremappingprod.ordnancesurvey.co.uk') # Was '46.137.180.108' and 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com'
TILES_URL_CKAN = config.get('ckanext-os.tiles.url', 'http://%s/geoserver/gwc/service/wms' % GEOSERVER_HOST)
WFS_URL_CKAN = config.get('ckanext-os.wfs.url', '/geoserver/wfs')


api_key = config.get('ckanext-os.tiles.apikey', '')
if api_key:
    TILES_URL_CKAN += '?key=%s' % quote(api_key)
    WFS_URL_CKAN += '?key=%s' % quote(api_key)

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
            content = re.sub(existing, replacement, content)
        return content
    

class SearchWidget(BaseWidget):
    def index(self):
        c.libraries_base_url = 'http://%s/libraries' % LIBRARIES_HOST
        return render('os/map_search.html')

class PreviewWidget(BaseWidget):
    def index(self):
        c.libraries_base_url = 'http://%s/libraries' % LIBRARIES_HOST
        return render('os/map_preview.html')

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
        log.info('Proxied request to URL: %s', url)
        try:
            f = urllib2.urlopen(request)
        except HTTPError, e:
            response.status_int = 400
            return 'Proxied server returned %s: %s' % (e.code, e.msg)
        except URLError, e:
            err = str(e)
            if 'Connection timed out' in err:
                response.status_int = 504
                return 'Proxied server timed-out: %s' % err
            log.error('Proxy URL error. URL: %r Error: %s', url, s)
            raise e # Send an exception email to handle it better
        res = f.read()
        log.debug('Proxy reponse %s: %s', f.code, res[:100])
        return res
        
    def geoserver_proxy(self, url_suffix):
        '''Proxy for geoserver services.
        Depending on the geoserver provider, calls may require a key parameter
        - an API key only to be used by authorized clients software / users.

        /geoserver/gwc/service/wms - OS base map tiles (via GeoWebCache) (for Search & Preview)
                                     NB Tile requests appear to go direct to that server
                                        (not via this proxy)
        /geoserver/wfs - Boundaries info (for Search)
        '''
        key = request.params.get('key')
        loggable_key = (key[:2] + 'x'*(len(key)-2)) if key else None
        log.debug('Geoserver proxy for url_suffix=%r key=%r', url_suffix, loggable_key)
        if url_suffix not in ('gwc/service/wms', 'wfs'):
            response.status_int = 404
            return 'Path not proxied'
        url = 'http://%s/geoserver/%s' % \
              (GEOSERVER_HOST, url_suffix)
        if key:
            url += '?key=%s' % quote(key)
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
                if not param_str.strip():
                    continue
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

# Preview list 'Shopping basket'
class PreviewList(BaseController):
    def _get(self, id):
        preview_list = pylons_session.get('preview_list', [])
        for entry in preview_list:
            if entry['id'] == id: 
                return entry

    def _querystring(self, pkg):
        out = []
        for r in pkg.resources:
            # NB This WMS detection condition must match that in dgu/ckanext/dgu/lib/helpers.py
            if 'wms' in r.url.lower() or r.format.lower() == 'wms':
                out.append(('url',r.url))
        return urlencode(out)

    def reset(self):
        pylons_session['preview_list'] = []
        pylons_session.save()
        return self.view()
        
    def add(self, id):
        if not id:
            abort(409, 'Dataset not identified')
        preview_list = pylons_session.get('preview_list', [])
        pkg = model.Package.get(id)
        if not self._get(pkg.id):
            if not pkg:
                abort(404, 'Dataset not found')
            extent = (pkg.extras.get('bbox-north-lat'),
                      pkg.extras.get('bbox-west-long'),
                      pkg.extras.get('bbox-east-long'),
                      pkg.extras.get('bbox-south-lat'))
            preview_list.append({
                'id': pkg.id,
                'querystring': self._querystring(pkg),
                'name': pkg.name,
                'extent': extent,
                })
            pylons_session['preview_list'] = preview_list
            pylons_session.save()
        return self.view()

    def remove(self, id):
        if not id:
            abort(409, 'Dataset not identified')
        preview_list = pylons_session.get('preview_list', [])
        pkg = model.Package.get(id)
        if not pkg:
            abort(404, 'Dataset not found')
        entry = self._get(pkg.id)
        if not entry:
            abort(409, 'Dataset not in preview list')            
        preview_list.remove(entry)
        pylons_session['preview_list'] = preview_list
        pylons_session.save()
        return self.view()

    def view(self):
        preview_list = pylons_session.get('preview_list', [])
        response.headers['Content-Type'] = 'application/json;charset=utf-8'
        return json.dumps(preview_list)
