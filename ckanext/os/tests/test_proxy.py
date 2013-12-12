import urllib2
from urllib import quote
from urllib2 import HTTPError
from httplib import BadStatusLine
import SimpleHTTPServer

from nose.tools import assert_equal, assert_raises
from pylons import config

from ckan.lib.helpers import url_for
from ckanext.os.controllers.widgets import GAZETTEER_HOST, GEOSERVER_HOST
from ckanext.os.testtools.mock_os_server import MOCK_OS_SERVER_HOST_AND_PORT, MOCK_API_KEY
from ckanext.os.tests import MockOsServerCase

boundary_request = '<wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="json" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><wfs:Query typeName="inspire:UK_Admin_Boundaries_250m_4258" srsName="EPSG:4258" xmlns:inspire="http://ordnancesurvey.co.uk/spatialdb"><ogc:Filter xmlns:ogc="http://www.opengis.net/ogc"><ogc:BBOX><ogc:PropertyName>the_geom</ogc:PropertyName><gml:Envelope xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:4258"><gml:lowerCorner>-5.4529443561525 51.077000998278</gml:lowerCorner><gml:upperCorner>-0.6249563498509 53.269250249574</gml:upperCorner></gml:Envelope></ogc:BBOX></ogc:Filter></wfs:Query></wfs:GetFeature>'

class OsServerCase:
    def test_gazetteer_proxy(self):
        q = 'London'
        url = 'http://%s/InspireGaz/gazetteer?q=%s' % \
              (self.gazetteer_host, quote(q))
        f = urllib2.urlopen(url)
        response = f.read()
        assert '<county>Greater London Authority</county>' in response, response
        assert response.startswith('''<?xml version="1.0" encoding="UTF-8"?>
  <GazetteerResultVO>
    <items>'''), response[:100]

    def test_gazetteer_proxy_unicode(self):
        q = 'Ll%C5%B7n' # Llyn but with a circumflex over the 'y', urlencoded
        url = 'http://%s/InspireGaz/gazetteer?q=%s' % \
              (self.gazetteer_host, q)
        f = urllib2.urlopen(url)
        response = f.read()
        assert '<GazetteerResultVO>' in response, response

    def test_gazetteer_postcode_proxy(self):
        q = 'DL3 0UR' # BBC Complaints postcode
        url = 'http://%s/InspireGaz/postcode?q=%s' % \
              (self.gazetteer_host, quote(q))
        f = urllib2.urlopen(url)
        response = f.read()
        assert_equal (response, '''<?xml version="1.0" encoding="UTF-8"?>
  <CodePointItemVO>
    <easting>-1.5719322177872677</easting>
    <northing>54.55246821308707</northing>
    <point>-1.5719322177872677 54.55246821308707</point>
  </CodePointItemVO>
'''), response

    def test_gazetteer_postcode_proxy_null_response(self):
        q = 'SO16 0AS' # OS's postcode - gives a blank response
        url = 'http://%s/InspireGaz/postcode?q=%s' % \
              (self.gazetteer_host, quote(q))
        f = urllib2.urlopen(url)
        response = f.read()
        assert_equal('''<?xml version="1.0" encoding="UTF-8"?>
  <EmptyCodePointItemVO>
    <easting/>
    <northing/>
    <point>null null</point>
  </EmptyCodePointItemVO>
''', response)

    def test_gazetteer_postcode_proxy_bad_space(self):
        q = 'EH99 1SP'
        url = 'http://%s/InspireGaz/postcode?q=%s' % \
              (self.gazetteer_host, q) # NB: Not quoted - space remains
        exc = None
        try:
            f = urllib2.urlopen(url)
        except HTTPError, exc:
            pass
        if exc:
            # What real OS server does
            assert_equal(exc.code, 400)
        else:
            # What our test server does
            res = f.read()
            assert 'Error code 400' in res, res

    def test_admin_boundary(self):
        url = 'http://%s/geoserver/wfs?key=%s' % \
              (self.map_tile_host, quote(self.api_key))
        headers = {'Content-Type': 'application/xml'}
        post_data = boundary_request
        request = urllib2.Request(url, post_data, headers)
        f = urllib2.urlopen(request)
        response = f.read()
        assert '"NAME":"Wrecsam - Wrexham"' in response, response
        assert '"bbox":[' in response
        assert response.startswith('''{"type":"FeatureCollection","features":[{"type":"Feature","id":"UK_Admin_Boundaries_250m_4258.fid'''), response[:100]

    def test_admin_boundary_without_key(self):
        url = 'http://%s/geoserver/wfs' % \
              (self.map_tile_host)
        headers = {'Content-Type': 'application/xml'}
        post_data = boundary_request
        request = urllib2.Request(url, post_data, headers)
        assert_raises(BadStatusLine, urllib2.urlopen, request)
            
        response = f.read()
        assert '"NAME":"Wrecsam - Wrexham"' in response, response
        assert '"bbox":[' in response
        assert response.startswith('''{"type":"FeatureCollection","features":[{"type":"Feature","id":"UK_Admin_Boundaries_250m_4258.fid'''), response[:100]

class TestExternalOsServers(OsServerCase):
    gazetteer_host = GAZETTEER_HOST
    map_tile_host = GEOSERVER_HOST
    api_key = config['ckanext-os.geoserver.apikey'] # this needs setting in your development.ini - it is just for tests.

class TestMockOsServers(OsServerCase, MockOsServerCase):
    gazetteer_host = MOCK_OS_SERVER_HOST_AND_PORT
    map_tile_host = MOCK_OS_SERVER_HOST_AND_PORT
    api_key = MOCK_API_KEY
