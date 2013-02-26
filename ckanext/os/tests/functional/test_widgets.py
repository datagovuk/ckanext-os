from urllib import urlencode, quote
from urlparse import urlparse, parse_qs

from nose.tools import assert_equal, assert_raises

from ckanext.os.controllers.widgets import Proxy, ValidationError
from ckanext.os.tests import MockOsServerCase
from ckan.tests import TestController

class TestSearchProxy(TestController, MockOsServerCase):
    def test_gazetteer_proxy(self):
        q = 'London'
        url = '/data/search_proxy?t=gz&q=%s' % quote(q)
        res = self.app.get(url)
        response = res.body
        assert '<county>Greater London Authority</county>' in response, response
        assert response.startswith('''<?xml version="1.0" encoding="UTF-8"?>
  <GazetteerResultVO>
    <items>'''), response[:100]

    def test_gazetteer_proxy_unicode(self):
        q = 'Ll%C5%B7n' # Llyn but with a circumflex over the 'y', urlencoded
        url = '/data/search_proxy?t=gz&q=%s' % q
        res = self.app.get(url)
        response = res.body
        assert '<GazetteerResultVO>' in response, response

    def test_gazetteer_postcode_proxy(self):
        q = 'DL3 0UR' # BBC Complaints postcode
        url = '/data/search_proxy?t=pc&q=%s' % quote(q)
        res = self.app.get(url)
        response = res.body
        assert_equal (response, '''<?xml version="1.0" encoding="UTF-8"?>
  <CodePointItemVO>
    <easting>-1.5719322177872677</easting>
    <northing>54.55246821308707</northing>
    <point>-1.5719322177872677 54.55246821308707</point>
  </CodePointItemVO>
''')
    

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

    def test_preview_similar_urls(self):
        offset = '/data/map-preview'
        url = '%s?%s' % (
            offset,
            urlencode([
                ('url','http://server1.com/wmsserver'),
                ('url','http://server1.com/wmsserver?unique=parameter'),
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
                ('url','http://server1.com/wmsserver'),
                ('url','http://server1.com/wmsserver?unique=parameter'),
                ('a','1'),
                ('b','2')
            ])
        )
        res = self.app.get(url)

        # The response should be a redirect, with the Location header showing
        # only one of the urls, the rest of the params and the 'deduped' parameter
        assert res.status == 302

        new_url = res.header('Location')

        assert new_url

        parts = urlparse(new_url)
        params = parse_qs(parts.query)

        assert params['url'] and len(params['url']) == 2
        assert_equal(params['url'][0], 'http://server1.com/wmsserver')
        assert_equal(params['url'][1], 'http://server1.com/wmsserver?unique=parameter')
        assert 'a' in params and params['a'] == ['1']
        assert 'b' in params and params['b'] == ['2']
        assert 'deduped' in params and params['deduped'] == ['true']

        # The new url should not redirect
        res = self.app.get(new_url)
        assert res.status == 200
        assert '<html' in res.body
        assert 'Map Based Preview' in res.body
