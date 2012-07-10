from urllib import urlencode
from urlparse import urlparse, parse_qs

from nose.tools import assert_equal, assert_raises

from ckanext.os.controller import Proxy, ValidationError
from ckan.tests import TestController

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
