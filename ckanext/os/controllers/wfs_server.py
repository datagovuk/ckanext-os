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
from sqlalchemy.sql.expression import text

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render, redirect, json
from ckan import model
from ckan.lib.helpers import OrderedDict, url_for

log = logging.getLogger(__name__)

DEFAULT_SRS = 4326

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
        engine = create_engine(spatial_datastore_url, echo=False)
        spatial_db_connection = engine.connect()
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
        result = engine.execute(text(SQL_SELECT_FTS))
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
        name, srs, bbox = self._parse_get_feature(xml_tree)
        features = self._get_features(name, srs, bbox)
        response.headers['Content-Type'] = 'application/json;charset=utf-8'
        return self._features_as_json(features)

    def _features_as_json(self, features):
        '''Returns features in JSON format, with this structure:
        {"type": "FeatureCollection",
         "features":
          [
            {   "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [102.0, 0.5]},
                "properties": {"ID": 11,
                               "SchoolName": "Camden",
                               "SchoolType": "Primary",
                               "StreetName": "Camden Road",
                               "Town": "Carshalton",
                               "Postcode": "SM5 2NS",
                               "TelephoneNumber": "020 86477324",
                               "Easting": 527700.179,
                               "Northing": 164916.916}
            },
            ...
          ]
        }
        '''
        feature_dicts = []
        for feature in features:
            #TODO tidy
            coords = feature['coordinates']
            properties = feature['properties']
            feature_dict = {'type': 'Feature',
                            'geometry': {
                                'type': 'Point',
                                'coordinates': coords,
                                },
                            'properties': properties,
                            }
            feature_dicts.append(feature_dict)
        features_dict = {'type': 'FeatureCollection',
                         'features': feature_dicts}
        return json.dumps(features_dict)
    
    def _get_features(self, name, srs, bbox):
        engine = get_spatial_db_connection()
        params = {'dataset_id': name,
                  'srs': srs,
                  'lower_x': bbox['lower_x'],
                  'lower_y': bbox['lower_y'],
                  'upper_x': bbox['upper_x'],
                  'upper_y': bbox['upper_y'],
                  }
        if not bbox:
            query = SQL_FIND_BY_DATASETID
        elif srs == 27700:
            query = SQL_FIND_BY_DATASETID_AND_BBOX
        else:
            query = SQL_FIND_BY_DATASETID_AND_BBOX_TRANSFORM
            
        result = engine.execute(text(query), **params)
        log.info('GetFeatures PostGIS request returned %i results',
                 result.rowcount)
        return result

    def _parse_coordinate(self, envelope, corner_name):
        '''
        Given an WFS query\'s envelope (as an xml etree), returns the coordinates
        as a tuple of two floats. Any error, it calls abort (exception).
        '''
        if not corner_name in ('lowerCorner', 'upperCorner'):
            abort(500, 'Bad param for _parse_coordinate')
        corner = None
        for corner_xml in envelope.iter('{http://www.opengis.net/gml}%s' % corner_name):
            corner = corner_xml.text
        error_message_base = 'WFS Query/Filter/BBOX/Envelope/%s ' % corner_name
        if not corner:
            abort(400, error_message_base + 'element missing')
        corner = corner.strip()
        if not corner:
            abort(400, error_message_base + 'element blank')
        coordinates = corner.split(' ')
        if len(coordinates) != 2:
            abort(400, error_message_base + 'has %i coordinates but should be 2' \
                  % len(coordinates))
        try:
            coordinates = [float(coord) for coord in coordinates]
        except ValueError:
            abort(400, error_message_base + 'coordinates not floats: %s' \
                  % coordinates)
        return coordinates
            
    def _parse_get_feature(self, xml_tree):
        '''Parse GetFeature request.
        Looks for the query and yields (name, srs, bbox).
        bbox may be None. Is a dict.
        srs has a default. Is an int.
        On error, raises abort().
        '''
        for query in xml_tree.iter('{http://www.opengis.net/wfs}Query'):
            # Look at the query typeName property
            # which is: a list of feature type names that are queryable
            # e.g. 'feature:3af1eca9-5007-49d1-931f-1cd0758ac865'
            typeName = query.get('typeName') 
            if not typeName:
                abort(400, 'WFS Query element must have a typeName attribute')
            if ':' in typeName:
                typeName = typeName.split(':')[-1]
            typeName = typeName.strip()

            # defaults
            srs = DEFAULT_SRS
            bbox = None
            
            for filter_ in query.iter('{http://www.opengis.net/ogc}Filter'):
                for bbox in filter_.iter('{http://www.opengis.net/ogc}BBOX'):
                    for envelope in bbox.iter('{http://www.opengis.net/gml}Envelope'):
                        srsName = query.get('srsName', DEFAULT_SRS).strip()
                        if srsName:
                            if ':' in srsName:
                                srsName = srsName.split(':')[-1]
                            srs = int(srsName)
                        lower_x, lower_y = self._parse_coordinate(envelope, 'lowerCorner')
                        upper_x, upper_y = self._parse_coordinate(envelope, 'upperCorner')
                        # bbox must have lower corner first
                        bbox = {'lower_x': lower_x,
                                'lower_y': lower_y,
                                'upper_x': upper_x,
                                'upper_y': upper_y}
            return (typeName, srs, bbox)
        abort(400, 'No suitable WFS Query found')

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

SQL_FIND_BY_DATASETID = "select * from feature where datasetid = :dataset_id limit 200"
SQL_FIND_BY_DATASETID_AND_BBOX = "select * from feature where datasetid = :dataset_id and  geom && ST_MakeEnvelope(:lower_x, :lower_y, :upper_x, :upper_y, 27700) limit 200"
SQL_FIND_BY_DATASETID_AND_BBOX_TRANSFORM = "select  datasetid, properties, st_astext(st_transform(geom, :srs)) from feature where datasetid = :dataset_id and geom && st_transform(ST_MakeEnvelope(:lower_x, :lower_y, :upper_x, :upper_y, :srs), 27700) limit 200";
