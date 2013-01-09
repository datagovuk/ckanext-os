import os
import re
import urllib2
from urllib2 import HTTPError, URLError
from urllib import quote, urlencode
import logging
from lxml import etree
import urlparse

from pylons import config
from sqlalchemy import create_engine

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render, redirect
from ckan import model
from ckan.lib.helpers import OrderedDict, url_for

log = logging.getLogger(__name__)

spatial_db_connection = None
def get_spatial_db_connection():
    '''Returns a db connection (sqlalchemy engine) to the
    Spatial db (postgis).

    Not using SQLAlchemy connection pooling because in DGU
    we use pgbouncer for this. But caches connection between
    future requests of this thread.

    May raise AbortError (i.e. suitable a request).
    '''
    global spatial_db_connection
    if spatial_db_connection is None:
        spatial_datastore_url = config.get('ckanext-os.spatial-datastore.url')
        if not spatial_datastore_url:
            log.error('Spatial datastore not setup - please configure ckanext-os.spatial-datastore.url')
            abort(500, 'Spatial datastore not setup')
        spatial_db_connection = create_engine(spatial_datastore_url, echo=False)
    return spatial_db_connection

class WfsServer(BaseController):
    def index(self):
        if not request.body:
            abort(400, 'No POST data')

        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('application/xml'):
            abort(400, 'Content type should be "application/xml"')

        # call get_capabilities or get_feature
        xml_tree = etree.fromstring(request.body)
        root_tag = xml_tree.tag
        import pdb; pdb.set_trace()
        if root_tag == '{http://www.opengis.net/wfs}GetCapabilities':
            return self.get_capabilities()
        elif root_tag == '{http://www.opengis.net/wfs}GetFeature':
            return self.get_feature(xml_tree)
        else:
            abort(400, 'Request method not supported: %s' % root_tag)

    def get_capabilities(self):
        uri = urlparse.urljoin(config.get('ckan.site_url_internally') or config['ckan.site_url'], 'data/wfs')
        params = {'uri': uri}
        capabilities = CAPABILITIES_START_XML % params
        for feature_type_xml in self._get_feature_types_xml():
            capabilities += feature_type_xml
        capabilities += CAPABILITIES_END_XML
        return capabilities

    def _get_feature_types_xml(self):
        engine = get_spatial_db_connection()
        
        SQL_SELECT_FTS = "select datasetid, ST_SetSRID(ST_Extent(ST_Transform(geom,4326)), 4326) as bbox from feature group by datasetid"

        # this is for getFeatureCapabilities instead of SQL_SELECT_FTS
        #SQL_SELECT_FTS_BY_COLLECTION = "select feature.datasetid, ST_SetSRID(ST_Extent(ST_Transform(feature.geom,4326)), 4326) as bbox from feature,dataset where feature.datasetid = dataset.id and dataset.collid = %(collection_id)s group by feature.datasetid;" % collection_id

        # Run SQL on PostGIS
        result = engine.execute(SQL_SELECT_FTS)
        log.info('GetCapabilities PostGIS request returned %i features',
                 result.rowcount)
        
        for feature in result:
            yield FEATURE_XML % {'name': feature.name,
                                 'title': feature.title,
                                 'description': feature.description,
                                 'minx': feature.bbox[0],
                                 'miny': feature.bbox[1],
                                 'maxx': feature.bbox[2],
                                 'maxy': feature.bbox[3],
                                 }

    def get_feature(self, xml_tree):
        for query in xml_tree.xpath('//a/@href'):
            typeName_element = query.findChild('typeName')
            if not typeName_element:
                abort(400, 'unable to find typeName attribute of the query')
            typeName = typeName_element.name
            if ':' in typeName:
                typeName = typeName.split(':')[-1]
            typeName = typeName.strip()

            bbox_element = query.findChild('typeName')
            if bbox_element:
                pass


FEATURE_XML = '''
        <FeatureType>
            <Name>%(name)s</Name>
            <Title>%(title)s</Title>
            <Abstract>%(description)s</Abstract>
            <ows:Keywords/>
            <DefaultSRS>urn:ogc:def:crs:EPSG:27700</DefaultSRS>
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>%(minx)s %(miny)s</ows:LowerCorner>
                <ows:UpperCorner>%(maxx)s %(maxy)s</ows:UpperCorner>
            </ows:WGS84BoundingBox>
        </FeatureType>";
'''

CAPABILITIES_START_XML = '''<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<wfs:WFS_Capabilities version=\"1.1.0\"
                      xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
                      xmlns=\"http://www.opengis.net/wfs\"
                      xmlns:wfs=\"http://www.opengis.net/wfs\"
                      xmlns:ows=\"http://www.opengis.net/ows\"
                      xmlns:ogc=\"http://www.opengis.net/ogc\"
                      xmlns:xlink=\"http://www.w3.org/1999/xlink\"
                      xsi:schemaLocation=\"http://www.opengis.net/wfs wfs.xsd\"
                      updateSequence=\"26057\">
    <ows:ServiceIdentification>
        <ows:Title>OSLabs Spatial Data Simple WFS </ows:Title>
        <ows:Abstract>Simple WFS service providing read only access to parsed data sets
        </ows:Abstract>
        <ows:ServiceType>WFS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.1.0</ows:ServiceTypeVersion>
        <ows:Fees>NONE</ows:Fees>
        <ows:AccessConstraints>NONE</ows:AccessConstraints>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name=\"GetCapabilities\">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href=\"%(uri)s\" />
                    <ows:Post xlink:href=\"%(uri)s\" />
                </ows:HTTP>
            </ows:DCP>
            <ows:Parameter name=\"AcceptVersions\">
                <ows:Value>1.1.0</ows:Value>
            </ows:Parameter>
            <ows:Parameter name=\"AcceptFormats\">
               <ows:Value>text/xml</ows:Value>
           </ows:Parameter>"
        </ows:Operation>
        <ows:Operation name=\"GetFeature\">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href=\"%(uri)s\" />
                    <ows:Post xlink:href=\"%(uri)s\" />
                </ows:HTTP>
            </ows:DCP>
            <ows:Parameter name=\"outputFormat\">
                <ows:Value>json</ows:Value>
            </ows:Parameter>
        </ows:Operation>
    </ows:OperationsMetadata>
    <FeatureTypeList>
        <Operations>
            <Operation>Query</Operation>
        </Operations>
'''

CAPABILITIES_END_XML = '''
</FeatureTypeList>
    <ogc:Filter_Capabilities/>
</wfs:WFS_Capabilities>'''
