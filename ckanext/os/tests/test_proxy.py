import os
import urllib2
from urllib import quote,urlencode
from urlparse import urlparse, parse_qs
from urllib2 import HTTPError
import SimpleHTTPServer

from ckan.lib.helpers import url_for

from nose.tools import assert_equal, assert_raises

from ckanext.os.controller import GAZETTEER_HOST, GEOSERVER_HOST, Proxy, ValidationError
from ckanext.os.testtools.mock_os_server import MOCK_OS_SERVER_HOST_AND_PORT
from ckan.tests import BaseCase
from ckan.tests import TestController

boundary_request = '<wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="json" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><wfs:Query typeName="inspire:UK_Admin_Boundaries_250m_4258" srsName="EPSG:4258" xmlns:inspire="http://ordnancesurvey.co.uk/spatialdb"><ogc:Filter xmlns:ogc="http://www.opengis.net/ogc"><ogc:BBOX><ogc:PropertyName>the_geom</ogc:PropertyName><gml:Envelope xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:4258"><gml:lowerCorner>-5.4529443561525 51.077000998278</gml:lowerCorner><gml:upperCorner>-0.6249563498509 53.269250249574</gml:upperCorner></gml:Envelope></ogc:BBOX></ogc:Filter></wfs:Query></wfs:GetFeature>'

class MockOsServerCase(BaseCase):
    @classmethod
    def setup_class(self):
        self.pid = self._start_server()
        self._wait_for_url()

    @classmethod
    def teardown_class(self):
        self._stop_server(self.pid)

    @staticmethod
    def _start_server():
        import subprocess
        process = subprocess.Popen(['paster', '--plugin=ckanext-os', 'mock_os_server', 'run'])
        return process

    @staticmethod
    def _wait_for_url(url='http://%s/' % MOCK_OS_SERVER_HOST_AND_PORT, timeout=15):
        for i in range(int(timeout)*100):
            import urllib2
            import time
            try:
                response = urllib2.urlopen(url)
            except urllib2.URLError:
                time.sleep(0.1)
            else:
                break

    @staticmethod
    def _stop_server(process):
        pid = process.pid
        pid = int(pid)
        if os.system("kill -9 %d" % pid):
            raise Exception, "Can't kill foreign Mock OS Server (pid: %d)." % pid

class TestPreviewProxy:
    def test_wms_url_correcter_normal(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=GetCapabilities&service=WMS'),
            'http://host.com?request=GetCapabilities&service=WMS')
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=getcapabilities&service=wms'),
            'http://host.com?request=getcapabilities&service=wms')
        assert_equal(Proxy.wms_url_correcter('http://lasigpublic.nerc-lancaster.ac.uk/ArcGIS/services/Biodiversity/GMFarmEvaluation/MapServer/WMSServer?request=GetCapabilities&service=WMS'), 'http://lasigpublic.nerc-lancaster.ac.uk/ArcGIS/services/Biodiversity/GMFarmEvaluation/MapServer/WMSServer?request=GetCapabilities&service=WMS')

    def test_wms_url_correcter_duplicate_keys(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=GetCapabilities&request=GetFeatureInfo'),
            'http://host.com?request=GetFeatureInfo&service=WMS')

    def test_wms_url_correcter_trailing_ampersand(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=GetCapabilities&'),
            'http://host.com?request=GetCapabilities&service=WMS')

    def test_wms_url_correcter_bad_structure(self):
        assert_raises(ValidationError, Proxy.wms_url_correcter,
                      'http://host.com?request=')
        assert_raises(ValidationError, Proxy.wms_url_correcter,
                      'http://host.com?request=?')

    def test_wms_url_correcter_missing_params(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?service=WMS'),
            'http://host.com?service=WMS&request=GetCapabilities')
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?request=GetCapabilities'),
            'http://host.com?request=GetCapabilities&service=WMS')
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com'),
            'http://host.com?request=GetCapabilities&service=WMS')

    def test_wms_url_correcter_duff_values_unchanged(self):
        assert_equal(Proxy.wms_url_correcter(
            'http://host.com?colour=blue&rainbow='),
            'http://host.com?colour=blue&rainbow=&request=GetCapabilities&service=WMS')

    def test_wms_url_correcter_disallowed_values(self):
        assert_raises(ValidationError, Proxy.wms_url_correcter,
                      'http://host.com?request=DoBadThing')
        assert_raises(ValidationError, Proxy.wms_url_correcter,
                      'http://host.com?service=NotWMS')

class TestPreviewController(TestController):

    def test_preview_unique_urls(self):

        offset = '/data/map-preview'

        url = '%s?%s' % (
            offset,
            urlencode([
                ('url','http://server1.com/wmsserver'),
                ('url','http://server2.com/wmsserver?'),
                ('a','1'),
                ('b','2')
            ])
        )

        res = self.app.get(url)

        # No redirect should occur, just render the map preview template
        assert res.status == 200
        assert '<html' in res.body
        assert 'Map Based Preview' in res.body

    def test_preview_duplicate_urls(self):

        offset = '/data/map-preview'

        url = '%s?%s' % (
            offset,
            urlencode([
                ('url','http://server1.com/wmsserver'),
                ('url','http://server1.com/wmsserver?request=GetCapabilities'),
                ('url','http://server1.com/wmsserver?'),
                ('a','1'),
                ('b','2')
            ])
        )

        res = self.app.get(url)

        # The response should be a redirect, with the Location header showing
        # only one of the urls, the rest of the params and the 'checked' parameter
        assert res.status == 302

        new_url = res.header('Location')

        assert new_url

        parts = urlparse(new_url)
        params = parse_qs(parts.query)

        assert params['url'] and len(params['url']) == 1
        assert 'a' in params and params['a'] == ['1']
        assert 'b' in params and params['b'] == ['2']
        assert 'checked' in params and params['checked'] == ['true']

        # The new url should not redirect
        res = self.app.get(new_url)
        assert res.status == 200
        assert '<html' in res.body
        assert 'Map Based Preview' in res.body



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
        url = 'http://%s/geoserver/wfs' % \
              (self.map_tile_host)
        headers = {'Content-Type': 'application/xml'}
        post_data = boundary_request
        request = urllib2.Request(url, post_data, headers)
        f = urllib2.urlopen(request)
        response = f.read()
        assert '"NAME":"Wrecsam - Wrexham"' in response, response
        assert '"bbox":[' in response
        assert response.startswith('''{"type":"FeatureCollection","features":[{"type":"Feature","id":"UK_Admin_Boundaries_250m_4258.fid'''), response[:100]

class TestExternalOsServers(OsServerCase):
    gazetteer_host = GAZETTEER_HOST
    map_tile_host = GEOSERVER_HOST

class TestMockOsServers(OsServerCase, MockOsServerCase):
    gazetteer_host = MOCK_OS_SERVER_HOST_AND_PORT
    map_tile_host = MOCK_OS_SERVER_HOST_AND_PORT
