import urllib2
from urllib import quote
import SimpleHTTPServer

from nose.tools import assert_equal, assert_raises

from ckanext.os.controller import GAZETTEER_HOST, MAP_TILE_HOST, Proxy, ValidationError

boundary_request = '<wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="json" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><wfs:Query typeName="inspire:UK_Admin_Boundaries_250m_4258" srsName="EPSG:4258" xmlns:inspire="http://ordnancesurvey.co.uk/spatialdb"><ogc:Filter xmlns:ogc="http://www.opengis.net/ogc"><ogc:BBOX><ogc:PropertyName>the_geom</ogc:PropertyName><gml:Envelope xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:4258"><gml:lowerCorner>-5.4529443561525 51.077000998278</gml:lowerCorner><gml:upperCorner>-0.6249563498509 53.269250249574</gml:upperCorner></gml:Envelope></ogc:BBOX></ogc:Filter></wfs:Query></wfs:GetFeature>'

class InspireHarness(SimpleHTTPServer.SimpleHTTPRequestHandler):
    pass

class TestProxyWithHarness:
    @classmethod
    def setup_class(cls):
        harness = InspireHarness()
    def test_gazetteer_proxy(self):
        q = 'London'


class TestPreviewProxy:
    def test_wms_url_correcter_normal(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=GetCapabilities&service=WMS'),
            'http://host.com?request=GetCapabilities&service=WMS')
        assert_equal(Proxy.wms_url_correcter('http://lasigpublic.nerc-lancaster.ac.uk/ArcGIS/services/Biodiversity/GMFarmEvaluation/MapServer/WMSServer?request=GetCapabilities&service=WMS'), 'http://lasigpublic.nerc-lancaster.ac.uk/ArcGIS/services/Biodiversity/GMFarmEvaluation/MapServer/WMSServer?request=GetCapabilities&service=WMS')

    def test_wms_url_correcter_duplicate_keys(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=GetCapabilities&service=WMS1&service=WMS2'),
            'http://host.com?request=GetCapabilities&service=WMS2')

    def test_wms_url_correcter_bad_structure(self):
        assert_raises(ValidationError, Proxy.wms_url_correcter, 
                      'http://host.com?request=GetCapabilities&')
        assert_raises(ValidationError, Proxy.wms_url_correcter, 
                      'http://host.com?request=GetCapabilities&')

    def test_wms_url_correcter_missing_params(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?service=WMS'),
            'http://host.com?request=GetCapabilities&service=WMS')
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=GetCapabilities'),
            'http://host.com?request=GetCapabilities&service=WMS')
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com'),
            'http://host.com?request=GetCapabilities&service=WMS')

    def test_wms_url_correcter_duff_values_unchanged(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=&service=123'),
            'http://host.com?request=&service=123')
        

class TestExternalServers:
    def test_gazetteer_proxy(self):
        q = 'London'
        url = 'http://%s/InspireGaz/gazetteer?q=%s' % \
              (GAZETTEER_HOST, quote(q))
        f = urllib2.urlopen(url)
        response = f.read()
        assert '<county>City Of London</county>' in response, response
        assert response.startswith('''<?xml version="1.0" encoding="UTF-8"?>
  <GazetteerResultVO>
    <items>'''), response[:100]

    def test_gazetteer_postcode_proxy(self):
        q = 'DL3 0UR' # BBC Complaints postcode
        url = 'http://%s/InspireGaz/postcode?q=%s' % \
              (GAZETTEER_HOST, quote(q))
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
              (GAZETTEER_HOST, quote(q))
        f = urllib2.urlopen(url)
        response = f.read()
        assert_equal('''<?xml version="1.0" encoding="UTF-8"?>
  <EmptyCodePointItemVO>
    <easting/>
    <northing/>
    <point>null null</point>
  </EmptyCodePointItemVO>
''', response)

    def test_admin_boundary(self):
        url = 'http://%s/geoserver/wfs' % \
              (MAP_TILE_HOST)
        headers = {'Content-Type': 'application/xml'}
        post_data = boundary_request
        request = urllib2.Request(url, post_data, headers)
        f = urllib2.urlopen(request)
        response = f.read()
        assert '"NAME":"Wrecsam - Wrexham"' in response, response
        assert '"bbox":[' in response
        assert response.startswith('''{"type":"FeatureCollection","features":[{"type":"Feature","id":"UK_Admin_Boundaries_250m_4258.fid'''), response[:100]

