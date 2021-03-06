import re
from urllib import quote, urlencode
import socket
import logging
from urlparse import urljoin

import sqlalchemy
from pylons import config
import requests

from ckan.lib.base import request, response, c, BaseController, g, render, redirect
from ckan import model
from ckan.lib.helpers import OrderedDict, url_for
from ckanext.dgu.gemini_postprocess import get_wms_base_url

log = logging.getLogger(__name__)

# Configuration
GEOSERVER_HOST = config.get('ckanext-os.geoserver.host',
                            'osinspiremappingprod.ordnancesurvey.co.uk') # Not '46.137.180.108'
GAZETTEER_HOST = config.get('ckanext-os.gazetteer.host',
                            'osinspiremappingprod.ordnancesurvey.co.uk') # was 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com' # Not '46.137.180.108'
LIBRARIES_HOST = config.get('ckanext-os.libraries.host',
                            'osinspiremappingprod.ordnancesurvey.co.uk') # Was '46.137.180.108' and 'searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com'

# Tiles and Overview WMS are accessed directly from the OS servers.
TILES_URL_CKAN = config.get('ckanext-os.tiles.url', '//%s/geoserver/gwc/service/wms' % GEOSERVER_HOST)
WMS_URL_CKAN = config.get('ckanext-os.wms.url', '//%s/geoserver/wms' % GEOSERVER_HOST)

# WFS is used for displaying the boundaries. Requests are sent via the local
# proxy to the OS servers. The proxy is needed to overcome the 'common origin'
# javascript restriction - they are json or xml payloads whereas there is no
# such restriction for the images in the tiles/WMS.
WFS_URL_CKAN = config.get('ckanext-os.wfs.url', '/geoserver/wfs')

# API Key is provided to the javascript to make calls. If requests go via
# the proxy then that passes through the API Key with the request.
api_key = config.get('ckanext-os.geoserver.apikey', '')
if api_key:
    TILES_URL_CKAN += '?key=%s' % quote(api_key)
    WMS_URL_CKAN += '?key=%s' % quote(api_key)
    WFS_URL_CKAN += '?key=%s' % quote(api_key)

class ValidationError(Exception):
    pass

class SearchWidget(BaseController):
    def index(self):
        c.libraries_base_url = '//%s/libraries' % LIBRARIES_HOST
        c.tiles_url_ckan = TILES_URL_CKAN
        c.wms_url_ckan = WMS_URL_CKAN
        c.wfs_url_ckan = WFS_URL_CKAN
        return render('os/map_search.html')

class PreviewWidget(BaseController):
    def index(self):
        # Avoid duplicate URLs for the same WMS service
        # (Only if it has not been checked before)
        if not request.params.get('deduped', False):
            urls = request.params.getall('url')
            deduped_urls = set(urls)

            if len(deduped_urls) < len(urls):
                # Redirect to the same location, but with the deduplicated
                # URLs.
                offset = url_for(controller='ckanext.os.controllers.widgets:PreviewWidget',action='index')

                query_string = urlencode([('url', u) for u in deduped_urls])

                for key,value in request.params.iteritems():
                    if key != 'url':
                        query_string += '&' + urlencode([(key, value)])
                query_string += '&deduped=true'
                new_url = offset + '?' + query_string

                redirect(new_url)

        # Render the page
        c.libraries_base_url = '//%s/libraries' % LIBRARIES_HOST
        c.tiles_url_ckan = TILES_URL_CKAN
        c.wms_url_ckan = WMS_URL_CKAN
        c.wfs_url_ckan = WFS_URL_CKAN

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
                                  (GAZETTEER_HOST, quote(q.encode('utf8'))))
        elif type_ == 'pc':
            # Postcode service
            return self._read_url('http://%s/InspireGaz/postcode?q=%s' %
                                  (GAZETTEER_HOST, quote(q.encode('utf8'))))
        else:
            response.status_int = 400
            return 'Value for t parameter not recognised'

    @staticmethod
    def obscure_apikey(txt):
        return re.sub('key=([0-9a-f]{2})[0-9a-f]+', r'key=\1xxx', txt)

    def _read_url(self, url, post_data=None, content_type=None):
        import OpenSSL.SSL
        headers = {'Content-Type': content_type} if content_type else {}
        log.debug('Proxied request to URL: %s', self.obscure_apikey(url))
        try:
            resp = requests.get(url, data=post_data, headers=headers,
                                verify=False)
            # don't verify the https certificate because we got obscure errors
            # in openssl - TypeError X509_STORE_CTX
            res = resp.text
        except requests.exceptions.ConnectionError, err:
            response.status_int = 504  # proxy failure
            return 'Proxied server had a connection error: %s' % str(err)
        except requests.exceptions.HTTPError, err:
            response.status_int = 400
            return 'Proxied server HTTP error: %s' % str(err)
        except requests.exceptions.URLRequired, err:
            response.status_int = 400
            return 'Cannot proxy an invalid URL: %s' % str(err)
        except (requests.exceptions.Timeout,
                socket.timeout), err:
            response.status_int = 504  # proxy failure
            return 'Proxied server timed-out: %s' % str(err)
        except requests.exceptions.TooManyRedirects, err:
            response.status_int = 504  # proxy failure
            return 'Proxied server sent us on too many redirects: %s' % \
                str(err)
        except requests.exceptions.RequestException, err:
            response.status_int = 504  # proxy failure
            return 'Proxied server error: %s' % str(err)
        except OpenSSL.SSL.SysCallError, err:
            # Requests doesn't catch this error - see:
            # https://github.com/appfolio/farcy/issues/83
            response.status_int = 504  # proxy failure
            return 'Proxied server SSL connection error: %s' % str(err)
        except Exception, e:
            log.error('Proxy URL error. URL: %r Error: %s', url, str(e))
            raise  # Send an exception email to handle it better
        log.debug('Proxy reponse %s: %s', resp.status_code, res[:100])
        return res

    def geoserver_proxy(self, url_suffix):
        '''Proxy for geoserver services.
        Depending on the geoserver provider, calls may require a key parameter
        - an API key only to be used by authorized clients software / users.

        /geoserver/gwc/service/wms - OS base map tiles (via GeoWebCache) (for Search & Preview)
                                     NB Tile requests appear to go direct to that server
                                        (not via this proxy)
        /geoserver/wms - Web Map Service (map images) (for Overview map)
        /geoserver/wfs - Boundaries info (for Search)
        '''
        key = request.params.get('key')
        loggable_key = (key[:2] + 'xxx') if key else None
        log.debug('Geoserver proxy for url_suffix=%r key=%r', url_suffix, loggable_key)
        if url_suffix not in ('gwc/service/wms', 'wfs','wms'):
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
        except ValueError:
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
        '''
        WMS and WFS GetCapabilities and GetFeature requests come through here
        to avoid cross-domain issue.
        '''
        # avoid status_code_redirect intercepting error responses
        request.environ['pylons.status_code_redirect'] = False

        url = request.params.get('url')

        # Check parameter
        if not (url):
            response.status_int = 400
            return 'Missing url parameter'

        # Check URL is in CKAN (otherwise we are an open proxy)
        base_url = url.split('?')[0] if '?' in url else url
        if base_url == urljoin(g.site_url, '/data/wfs'):
            # local WFS service
            return self._read_url(url, post_data=request.body,
                                  content_type='application/xml')
        else:
            # WMS
            query = model.Session.query(model.Resource) \
                         .filter(model.Resource.url.like(base_url + '%'))

            if query.count() == 0:
                response.status_int = 403
                return 'WMS URL not known: %s' % base_url

        # Correct basic errors in the WMS URL
        try:
            url = self.wms_url_correcter(url)
        except ValidationError, e:
            response.status_int = 400
            log.warning('WMS Preview proxy received invalid url: %r', url)
            return 'Invalid URL: %s' % str(e)

        content = self._read_url(url)
        if not content:
            # Varnish will change an empty response into a 500 Guru
            # meditation  (see "small blank pages" in the vcl), so return an
            # error message instead
            return 'Server returned 0 bytes'

        return content

    def preview_getinfo(self):
        '''
        This is a proxy request for the Preview map to get detail of a
        particular subset of a WMS service.

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
        base_wms_url = get_wms_base_url(wms_url)
        query = model.Session.query(model.Resource).filter(model.Resource.url.like(base_wms_url+'%'))
        if query.count() == 0:
            # Try in the 'wms_base_urls' extras too, as some WMSs use different
            # bases (specified in their GetCapabilities response)
            model_attr = getattr(model.Resource, 'extras')
            field = 'wms_base_urls'
            term = base_wms_url #.replace('/', '\\/').replace(':', '\\:')
            like = sqlalchemy.or_(
                model_attr.ilike(u'''%%"%s": "%%%s%%",%%''' % (field, term)),
                model_attr.ilike(u'''%%"%s": "%%%s%%"}''' % (field, term))
            )
            q = model.Session.query(model.Resource).filter(like)
            if q.count() == 0:
                response.status_int = 403
                return 'Base of WMS URL not known: %r' % base_wms_url

        content = self._read_url(wms_url)
        if not content:
            # Varnish will change an empty response into a 500 Guru
            # meditation  (see "small blank pages" in the vcl), so return an
            # error message instead
            return 'Server returned 0 bytes'

        return content
