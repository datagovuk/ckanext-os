import os
import re
import urllib2
from urllib2 import HTTPError, URLError
from urllib import quote, urlencode
import logging
from lxml import etree
import urlparse

from pylons import config

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render, redirect, json
from ckan import model
from ckan.lib.helpers import OrderedDict, url_for
from ckanext.os.model import spatial_data as spatial_model

log = logging.getLogger(__name__)

DEFAULT_SRS = 4326 #WGS84

class WfsServerError(Exception):
    pass

class WfsServer(BaseController):
    def index(self):
        if not request.body:
            abort(400, 'No POST data')

        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('application/xml'):
            abort(400, 'Content type should be "application/xml"')

        # call get_capabilities or get_feature
        try:
            xml_tree = etree.fromstring(request.body)
        except etree.XMLSyntaxError, e:
            abort(400, 'Content did not parse as XML: %s' % e)
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
        result = spatial_model.get_dataset_extents()
        
        for feature in result:
            dataset_id = feature['datasetid'] 
            bbox_ewkt = feature['bbox']
            bbox = parse_bbox_ewkt(bbox_ewkt)
            yield FEATURE_XML % {'name': dataset_id, # TODO
                                 'title': dataset_id,
                                 'description': '',
                                 'minx': bbox['sw'][0],
                                 'miny': bbox['sw'][1],
                                 'maxx': bbox['ne'][0],
                                 'maxy': bbox['ne'][1],
                                 }

    def get_feature(self, xml_tree):
        name, srs, bbox = self._parse_get_feature(xml_tree)
        features = spatial_model.get_features(name, srs, bbox)
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
            # ignore feature['datasetid']
            try:
                properties = json.loads(feature['properties'])
            except ValueError:
                log.error('Properties did not parse as JSON. Dataset: %s Properties: %r',
                          feature['datasetid'], feature['properties'])
                properties = 'Error loading properties'
            coords = parse_point_wkt(feature['geom'])
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
            log.info('WFS Query typeName: %s parsed: SRS %s BBOX %s',
                     typeName, srs, bbox.values() if bbox else None)
            return (typeName, srs, bbox)
        abort(400, 'No suitable WFS Query found')

def parse_bbox_ewkt(bbox_ewkt):
    '''
    Parse bbox in ewkt format
    e.g. 'SRID=4326;POLYGON((-0.241608190098641 51.3255056327391,-0.241608190098641 51.3899664544441,-0.135869140341743 51.3899664544441,-0.135869140341743 51.3255056327391,-0.241608190098641 51.3255056327391))'
    Returns as {'srid': 4326,
                'sw': (-0.241608190098641, 51.3255056327391),
                'ne': (-0.135869140341743, 51.3899664544441)}
    '''
    match = re.match('^SRID=(\d+);POLYGON\(\(([^ ]+) ([^ ]+),[^ ]+ [^ ]+,([^ ]+) ([^ ]+),[^ ]+ [^ ]+,[^ ]+ [^ ]+\)\)$', bbox_ewkt)
    if not match:
        raise WfsServerError('Could not parse bounding box that was stored: %r' % bbox_ewkt)
    groups = match.groups()
    return {'srid': int(groups[0]),
            'sw': (float(groups[1]), float(groups[2])),
            'ne': (float(groups[3]), float(groups[4])),
            }

def parse_point_wkt(point_wkt):
    '''
    Parse POINT in wkt format
    e.g. 'POINT(529045.924 165372.031)'
    Returns as (529045.924, 165372.031)
    '''
    match = re.match('^POINT\(([^ ]+) ([^ ]+)\)$', point_wkt)
    if not match:
        raise WfsServerError('Could not parse point: %r' % point_wkt)
    groups = match.groups()
    return (float(groups[0]), float(groups[1]))

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
        </FeatureType>
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

