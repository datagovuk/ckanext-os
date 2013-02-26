from sqlalchemy.sql.expression import text

from ckan.lib.base import json
from ckanext.os.model import spatial_data as spatial_model

TEST_COLLECTION_ID = 'c2f3d01b-5823-4451-a974-1c58c823fea0'
TEST_DATASET_ID = '4d836459-f02a-4c42-993f-3066ba2b61f0'

def create_test_spatial_data():
    conn = spatial_model.get_spatial_db_connection()

    collections = [
        {'id': TEST_COLLECTION_ID,
         'hash': '24B436C17A710184B1A921AEE33FB2BE',
         }
        ]
    for collection in collections:
        conn.execute(text('INSERT INTO collection ("id", "hash") VALUES (:id, :hash);'),
                     collection)

    datasets = [
        {'id': TEST_DATASET_ID,
         'collid': TEST_COLLECTION_ID,
         }
        ]
    for dataset in datasets:
        conn.execute(text('INSERT INTO dataset ("id", "collid") VALUES (:id, :collid);'),
                     dataset)

    features = [
        {'datasetid': TEST_DATASET_ID,
         'properties': '{"ID":1,"SITE":"Beddington Park","ADDRESS":"Church Road","WARD":"Beddington North","Easting":529045.924,"Northing":165372.031,"Area":4039.859,"Perimeter":464.361}',
         #'created': '2013-01-10 17:27:27.223566',
         #'modified': '2013-01-10 17:27:27.223566',
         'geom': '0101000020346C00002B8716D92B25204191ED7C3FE02F0441'},
        {'datasetid': TEST_DATASET_ID,
         'properties': '{"ID":4,"SITE":"Carshalton Park","ADDRESS":"Ruskin Road","WARD":"Carshalton Central","Easting":528009.573,"Northing":164145.634,"Area":3613.636,"Perimeter":214.241}',
         #'created': '2013-01-10 17:27:27.223566',
         #'modified': '2013-01-10 17:27:27.223566',
         'geom': '0101000020346C000089416025131D20418D976E128D090441',
         }
        ]
    for feature in features:
        conn.execute(text('INSERT INTO feature ("datasetid", "properties", "geom") VALUES (:datasetid, :properties, :geom);'),
                     feature)

def rebuild_spatial_db():
    conn = spatial_model.get_spatial_db_connection()
    res = conn.execute(text('SELECT id FROM collection WHERE id = :id'),
                       {'id': TEST_COLLECTION_ID})
    if res.rowcount:
        conn.execute(text('DELETE FROM collection WHERE id = :id'),
                       {'id': TEST_COLLECTION_ID})


