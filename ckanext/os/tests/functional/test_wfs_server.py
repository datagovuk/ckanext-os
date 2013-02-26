from nose.tools import assert_equal, assert_raises

from ckan.tests import TestController
from ckanext.os.tests.create_test_data import create_test_spatial_data, rebuild_spatial_db, TEST_DATASET_ID
from ckanext.os.controllers.wfs_server import parse_bbox_ewkt, parse_point_wkt

class TestWfsServer(TestController):
    offset = '/data/wfs'
    simple_get_cap_xml = '''<?xml version="1.0"?>
<wfs:GetCapabilities
              service="WFS"
              version="1.0.0"

              xmlns:wfs="http://www.opengis.net/wfs"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/WFS-basic.xsd"
/>
'''
    simple_get_feature_xml = '''
<wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="JSON" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <wfs:Query typeName="feature:%(dataset_id)s" srsName="EPSG:4258">
  </wfs:Query>
</wfs:GetFeature>''' % {'dataset_id': TEST_DATASET_ID}
    get_feature_xml_with_bbox = '''
<wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="JSON" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <wfs:Query typeName="feature:%(dataset_id)s" srsName="EPSG:4326">
    <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
      <ogc:BBOX>
        <gml:Envelope xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:4258">
          <gml:lowerCorner>-64.087504189526 45.416727752366</gml:lowerCorner>
          <gml:upperCorner>37.587504189526 66.583272247634</gml:upperCorner>
        </gml:Envelope>
      </ogc:BBOX>
    </ogc:Filter>  
  </wfs:Query>
</wfs:GetFeature>''' % {'dataset_id': TEST_DATASET_ID}
    get_feature_xml_with_bbox_and_srs = '''
<wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="JSON" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <wfs:Query typeName="feature:%(dataset_id)s" srsName="EPSG:4258">
    <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
      <ogc:BBOX>
        <gml:Envelope xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:4258">
          <gml:lowerCorner>-64.087504189526 45.416727752366</gml:lowerCorner>
          <gml:upperCorner>37.587504189526 66.583272247634</gml:upperCorner>
        </gml:Envelope>
      </ogc:BBOX>
    </ogc:Filter>  
  </wfs:Query>
</wfs:GetFeature>''' % {'dataset_id': TEST_DATASET_ID}
    headers = {'Content-Type': 'application/xml; charset=utf-8'}

    @classmethod
    def setup_class(cls):
        rebuild_spatial_db()
        create_test_spatial_data()

    @classmethod
    def teardown_class(cls):
        #rebuild_spatial_db()
        pass

    def test_get(self):
        # do not support GET requests
        res = self.app.get(self.offset, headers=self.headers, status=400)

    def test_empty_post(self):
        # POST must have some data
        res = self.app.post(self.offset, '', headers=self.headers, status=400)

    def test_wrong_content_type(self):
        # Content-Type should start with 'application/xml'
        wrong_headers = {'Content-Type': 'wrong-one'}
        res = self.app.post(self.offset, self.simple_get_cap_xml,
                            headers=wrong_headers, status=400)

    def test_missing_content_type(self):
        headers = {} 
        res = self.app.post(self.offset, self.simple_get_cap_xml,
                            headers=self.headers)
        # it copes
        assert res.body.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<wfs:WFS_Capabilities version="1.1.0"')

    def test_simple_get_cap(self):
        res = self.app.post(self.offset, self.simple_get_cap_xml, headers=self.headers)
        assert res.status == 200
        assert res.body.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<wfs:WFS_Capabilities version="1.1.0"')

        expected_serice_identification = '''    <ows:ServiceIdentification>
        <ows:Title>'''
        assert expected_serice_identification in res.body
        
        expected_feature_type = '''        <FeatureType>
            <Name>4d836459-f02a-4c42-993f-3066ba2b61f0</Name>
            <Title>4d836459-f02a-4c42-993f-3066ba2b61f0</Title>
            <Abstract></Abstract>
            <ows:Keywords/>
            <DefaultSRS>urn:ogc:def:crs:EPSG:27700</DefaultSRS>
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>-0.162741110481 51.3619627218</ows:LowerCorner>
                <ows:UpperCorner>-0.147419200149 51.3727500391</ows:UpperCorner>
            </ows:WGS84BoundingBox>
        </FeatureType>'''
        assert expected_feature_type in res.body

    def test_get_features_simple(self):
        res = self.app.post(self.offset, self.simple_get_feature_xml,
                            headers=self.headers)
        assert res.status == 200
        assert res.body.startswith('{"type": "FeatureCollection", "features": '),\
               res.body
        assert '"features": [{"geometry": {"type": "Point", "coordinates": [529045.924, 165372.031]}, "type": "Feature", "properties": {"Perimeter": 464.361, "Area": 4039.859, "SITE": "Beddington Park", "Easting": 529045.924, "ADDRESS": "Church Road", "WARD": "Beddington North", "ID": 1, "Northing": 165372.031}},' in res.body
        # yes feature coordinates in OS format (as that was put in by Spatial
        # Ingester).

    def test_get_features_with_bbox(self):
        params = {'dataset_id': TEST_DATASET_ID}
        res = self.app.post(self.offset, self.get_feature_xml_with_bbox, headers=self.headers)
        # BBOX has SRS of 4326 (WGS84) so it doesn't need transformation
        assert res.status == 200
        assert res.body.startswith('{"type": "FeatureCollection", "features": '),\
               res.body

    def test_get_features_with_bbox_and_srs(self):
        params = {'dataset_id': TEST_DATASET_ID}
        res = self.app.post(self.offset, self.get_feature_xml_with_bbox_and_srs, headers=self.headers)
        assert res.status == 200
        assert res.body.startswith('{"type": "FeatureCollection", "features": '),\
               res.body

    def test_parse_bbox_ewkt(self):
        bbox_ewkt = 'SRID=4326;POLYGON((-0.241608190098641 51.3255056327391,-0.241608190098641 51.3899664544441,-0.135869140341743 51.3899664544441,-0.135869140341743 51.3255056327391,-0.241608190098641 51.3255056327391))'
        res = parse_bbox_ewkt(bbox_ewkt)
        assert_equal(res, {'srid': 4326, #WGS84
                           'sw': (-0.241608190098641, 51.3255056327391),
                           'ne': (-0.135869140341743, 51.3899664544441)})

    def test_parse_point_wkt(self):
        point_wkt = 'POINT(529045.924 165372.031)'
        res = parse_point_wkt(point_wkt)
        assert_equal(res, (529045.924, 165372.031))
