 os
import re
import urllib2
from urllib2 import HTTPError, URLError
from urllib import quote, urlencode
import logging
from lxml import etree

from pylons import config

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render, redirect
from ckan import model
from ckan.lib.helpers import OrderedDict, url_for

class WfsServer(BaseController):
    def index(self):
        if not request.post:
            abort(400, 'No POST data')

        xml_tree = etree.fromstring(request.post)

        # call get_capabilities or get_feature

    def get_capabilities(self):
        params = {'uri': uri}
        capabilities = CAPABILITIES_START_XML % params
        for feature_type_xml in self.get_feature_types_xml():
            capabilities += feature_type_xml
        capabilities += CAPABILITIES_END_XML
        return capabilities

    def get_feature_types_xml(self):
        # TODO make connection earlier?
        'ckanext-os.spatial-datastore.url'
        SQL_SELECT_FTS = "select datasetid, ST_SetSRID(ST_Extent(ST_Transform(geom,4326)), 4326) as bbox from feature group by datasetid"
        SQL_SELECT_FTS_BY_COLLECTION = "select feature.datasetid, ST_SetSRID(ST_Extent(ST_Transform(feature.geom,4326)), 4326) as bbox from feature,dataset where feature.datasetid = dataset.id and dataset.collid = %(collection_id)s group by feature.datasetid;" % collection_id
        # TODO run SQL on PostGIS

        for feature in result:
            yield FEATURE_XML % {'name': feature.name,
                                 'title': feature.title,
                                 'description': feature.description,
                                 'minx': feature.bbox[0],
                                 'miny': feature.bbox[1],
                                 'maxx': feature.bbox[2],
                                 'maxy': feature.bbox[3],
                                 }

    def get_feature(self):
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
                    <ows:Get xlink:href=\"%1$s\" />
                    <ows:Post xlink:href=\"%1$s\" />
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
