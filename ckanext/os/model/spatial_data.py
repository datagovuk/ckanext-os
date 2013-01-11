import logging

from sqlalchemy import create_engine
from sqlalchemy.sql.expression import text
from pylons import config

log = logging.getLogger(__name__)

spatial_db_connection = None
def get_spatial_db_connection():
    '''Returns a db connection (sqlalchemy engine) to the
    Spatial db (postgis).

    Not using SQLAlchemy connection pooling because in DGU
    we use pgbouncer for this. But caches connection between
    future requests of this thread.

    May raise AbortError (i.e. suitable for a request).
    '''
    global spatial_db_connection
    if spatial_db_connection is None:
        spatial_datastore_url = config.get('ckanext-os.spatial-datastore.sqlalchemy.url')
        if not spatial_datastore_url:
            log.error('Spatial datastore not setup - please configure ckanext-os.spatial-datastore.url')
            abort(500, 'Spatial datastore not setup')
        engine = create_engine(spatial_datastore_url, echo=False)
        spatial_db_connection = engine.connect()
    return spatial_db_connection

def get_dataset_extents():
    '''Returns for each dataset: a datasetid and the max extent (bbox) of all its features.'''
    conn = get_spatial_db_connection()

    # Run SQL on PostGIS
    result = conn.execute(text(SQL_SELECT_FTS))
    log.info('GetCapabilities PostGIS request returned %i features',
             result.rowcount)
    return result

def get_features(name, srs, bbox):
    conn = get_spatial_db_connection()
    params = {'dataset_id': name}
    if bbox:
        params.update({
              'srs': srs,
              'lower_x': bbox['lower_x'],
              'lower_y': bbox['lower_y'],
              'upper_x': bbox['upper_x'],
              'upper_y': bbox['upper_y'],
              })
    if not bbox:
        query = SQL_FIND_BY_DATASETID
    elif srs == 27700:
        query = SQL_FIND_BY_DATASETID_AND_BBOX
    else:
        query = SQL_FIND_BY_DATASETID_AND_BBOX_TRANSFORM

    result = conn.execute(text(query), **params)
    log.info('GetFeatures PostGIS request returned %i results',
             result.rowcount)
    return result


SQL_SELECT_FTS = "select datasetid, ST_AsEWKT(ST_SetSRID(ST_Extent(ST_Transform(geom,4326)), 4326)) as bbox from feature group by datasetid"

# this is for getFeatureCapabilities instead of SQL_SELECT_FTS
#SQL_SELECT_FTS_BY_COLLECTION = "select feature.datasetid, ST_SetSRID(ST_Extent(ST_Transform(feature.geom,4326)), 4326) as bbox from feature,dataset where feature.datasetid = dataset.id and dataset.collid = %(collection_id)s group by feature.datasetid;" % collection_id

SQL_FIND_BY_DATASETID = "select datasetid, properties, ST_AsText(geom) as geom from feature where datasetid = :dataset_id limit 200"
SQL_FIND_BY_DATASETID_AND_BBOX = "select datasetid, properties, ST_AsText(geom) from feature where datasetid = :dataset_id and geom && ST_MakeEnvelope(:lower_x, :lower_y, :upper_x, :upper_y, 27700) limit 200"
SQL_FIND_BY_DATASETID_AND_BBOX_TRANSFORM = "select datasetid, properties, st_astext(st_transform(geom, :srs)) from feature where datasetid = :dataset_id and geom && st_transform(ST_MakeEnvelope(:lower_x, :lower_y, :upper_x, :upper_y, :srs), 27700) limit 200";
