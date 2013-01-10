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
      context - dict containing 'site_user_apikey' and 'site_url'
      data - resource_dict
             e.g. {
                   "revision_id": "2bc8ed56-8900-431a-b556-2417f309f365",
                   "id": "842062b2-e146-4c5f-80e8-64d072ad758d"}
                   "content_length": "35731",
                   "hash": "",
                   "description": "",
                   "format": "",
                   "url": "http://www.justice.gov.uk/publications/companywindingupandbankruptcy.htm",
                   "openness_score_failure_count": "0",
                   "content_type": "text/html",
                   "openness_score": "1",
                   "openness_score_reason": "obtainable via web page",
                   "position": 0,
                  }
      '''
    log = spatial_ingest.get_logger()
    log.info('Starting spatial_ingest task: %r', data)
    try:
        data = json.loads(data)
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
    postgis_url = context['spatial_datastore_url'] # ckanext-os.spatial-datastore.url
    dataset_id = dataset_dict[u'id']

    params = [postgis_url, api_url, api_key, dataset_id]
    command = ['java', 'ingester.java'] + params
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
        log.error('Uncaught Spatial Ingester failure: %r, %r', e, e.args)
        #_save_status(False, 'Spatial Ingester failure', e, status, resource['id'])
        return

    # Success
    #_save_status(True, 'Archived successfully', '', status, resource['id'])
    return json.dumps({
        'resource': resource,
    })
