import os
import urlparse
import subprocess

from ckan.lib.celery_app import celery
from ckan.lib.helpers import json

class OSError(Exception):
    pass

@celery.task(name="os.spatial_ingest")
def spatial_ingest(context, data):
    '''
    This is run when a resource is created, to notify the Spatial Ingester so that it
    can ingest the spatial data in CKAN.

    Params:
      context - dict containing 'site_user_apikey', 'site_url' &
                'spatial_ingester_filepath'
      data - dataset_dict
      '''
    log = spatial_ingest.get_logger()
    log.info('Starting spatial_ingest task')
    try:
        data = json.loads(data)
        log.info('Dataset: %s (%i resources)', data.get('name'),
                 len(data.get('resources', [])))
        context = json.loads(context)
        result = _spatial_ingest(context, data) 
        return result
    except Exception, e:
        if os.environ.get('DEBUG'):
            raise
        # Any problem at all is recorded in task_status and then reraised
        log.error('Error occurred during archiving resource: %s\nResource: %r',
                  e, data)
        ## update_task_status(context, {
        ##     'entity_id': data['id'],
        ##     'entity_type': u'resource',
        ##     'task_type': 'os',
        ##     'key': u'celery_task_id',
        ##     'value': unicode(update.request.id),
        ##     'error': '%s: %s' % (e.__class__.__name__,  unicode(e)),
        ##     'stack': traceback.format_exc(),
        ##     'last_updated': datetime.datetime.now().isoformat()
        ## }, log)
        raise

def _spatial_ingest(context, dataset_dict):
    """
    Run the Spatial Ingester for the given resource.
    
    Params:
      dataset_dict - dataset dict

    Should only raise on a fundamental error:
      OSError
    """
    log = spatial_ingest.get_logger()

    api_url = urlparse.urljoin(context['site_url'], 'api')
    api_key = context['site_user_apikey']
    postgis_url = context['spatial_datastore_jdbc_url'] # ckanext-os.spatial-datastore.jdbc.url
    dataset_id = dataset_dict[u'id']

    params = [postgis_url, api_url, api_key, dataset_id]
    command = [context['spatial_ingester_filepath']] + params
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError, e:
        log.error('Spatial Ingester returned non-zero: %r, %r', e, ' '.join(command))
        if os.environ.get('DEBUG'):
            raise
        #_save_status(False, 'Spatial Ingester failure', e, status, resource['id'])
        return
    except Exception, e:
        if os.environ.get('DEBUG'):
            raise
        log.error('Uncaught Spatial Ingester failure: %r, %r', e, ' '.join(command))
        #_save_status(False, 'Spatial Ingester failure', e, status, resource['id'])
        return

    # Success
    log.info('Spatial Ingester succeeded')
    #_save_status(True, 'Archived successfully', '', status, resource['id'])
    return json.dumps({
        'dataset': dataset_dict['name'],
    })
