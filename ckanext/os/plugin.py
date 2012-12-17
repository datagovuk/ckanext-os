import os
from logging import getLogger
import datetime

from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import (IRoutes, IConfigurer, IDomainObjectModification,
                          IResourceUrlChange, IConfigurable)
from ckan import model
import ckan.plugins.toolkit as t
import ckan.plugins as p
from ckan.lib.helpers import json
from ckan.lib.dictization.model_dictize import package_dictize
from ckan.model.types import make_uuid
import ckan.lib.celery_app as celery_app
send_task = celery_app.celery.send_task

log = getLogger(__name__)

class SearchWidget(SingletonPlugin):
    implements(IRoutes, inherit=True)
    implements(IConfigurer)

    def after_map(self, map):
        map.connect('/data/map-based-search',
                    controller='ckanext.os.controller:SearchWidget',
                    action='index')
        map.connect('/data/search_proxy',
                    controller='ckanext.os.controller:Proxy',
                    action='gazetteer_proxy')

        # Proxy for boundary information etc.
        # This is ideally duplicated in the Apache config as:
        #
        # ProxyPass /geoserver/ http://searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com/geoserver/
        # ProxyPassReverse /geoserver/ http://searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com/geoserver/
        map.connect('/geoserver/{url_suffix:.*}',
                    controller='ckanext.os.controller:Proxy',
                    action='geoserver_proxy')
        return map

    def update_config(self, config):
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        our_public_dir = os.path.join(rootdir, 'ckanext',
                                      'os', 'public')
        template_dir = os.path.join(rootdir, 'ckanext',
                                    'os', 'templates')
        # set our local template and resource overrides
        config['extra_public_paths'] = ','.join([our_public_dir,
                config.get('extra_public_paths', '')])
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])

class PreviewWidget(SingletonPlugin):
    implements(IRoutes, inherit=True)
    implements(IConfigurer)

    def after_map(self, map):
        map.connect('/data/map-preview',
                    controller='ckanext.os.controller:PreviewWidget',
                    action='index')
        map.connect('/data/preview_proxy',
                    controller='ckanext.os.controller:Proxy',
                    action='preview_proxy')
        map.connect('/data/preview_getinfo',
                    controller='ckanext.os.controller:Proxy',
                    action='preview_getinfo')
##        map.connect('/geoserver/{url_suffix:.*}',
##                    controller='ckanext.os.controller:Proxy',
##                    action='geoserver_proxy')

        # Preview list 'Shopping basket'
        map.connect('/api/2/util/preview_list/add/{id}',
                    controller='ckanext.os.controller:PreviewList',
                    action='add')
        map.connect('/api/2/util/preview_list/remove/{id}',
                    controller='ckanext.os.controller:PreviewList',
                    action='remove')
        map.connect('/api/2/util/preview_list/reset',
                    controller='ckanext.os.controller:PreviewList',
                    action='reset')
        map.connect('/api/2/util/preview_list',
                    controller='ckanext.os.controller:PreviewList',
                    action='view')
        return map

    def update_config(self, config):
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        our_public_dir = os.path.join(rootdir, 'ckanext',
                                      'os', 'public')
        template_dir = os.path.join(rootdir, 'ckanext',
                                    'os', 'templates')
        # set our local template and resource overrides
        config['extra_public_paths'] = ','.join([our_public_dir,
                config.get('extra_public_paths', '')])
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])

class SpatialIngesterPlugin(SingletonPlugin):
    """
    Registers to be notified whenever CKAN resources are created or their URLs change,
    and will create a new celery task to ingest the spatial resource.
    """
    implements(IDomainObjectModification, inherit=True)
    implements(IResourceUrlChange)
    implements(IConfigurable)

    def configure(self, config):
        self.site_url = config.get('ckan.site_url_internally') or config.get('ckan.site_url')
        self.spatial_datastore_url = config['ckanext-os.spatial-datastore.url']

    def notify(self, entity, operation=None):
        if not isinstance(entity, model.Package):
            return
        dataset = entity

        log.debug('Notified of dataset event: %s %s', dataset.name, operation)

        # Ignore operation for now
        #if operation == model.DomainObjectOperation.new:

        self._create_task(dataset)

    def _create_task(self, dataset):
        site_user = t.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True, 'defer_commit': True}, {}
        )
        context = json.dumps({
            'site_url': self.site_url,
            'site_user_apikey': site_user['apikey'],
            'spatial_datastore_url': self.spatial_datastore_url
        })
        dataset_dict = package_dictize(dataset, {'model': model})
        data = json.dumps(dataset_dict)

        task_id = make_uuid()
        archiver_task_status = {
            'entity_id': dataset.id,
            'entity_type': u'dataset',
            'task_type': u'os',
            'key': u'celery_task_id',
            'value': task_id,
            'error': u'',
            'last_updated': datetime.datetime.now().isoformat()
        }
        archiver_task_context = {
            'model': model,
            'user': site_user['name'],
            'ignore_auth': True
        }

        #get_action('task_status_update')(archiver_task_context, archiver_task_status)
        queue = 'priority'
        send_task("os.spatial_ingest", args=[context, data], task_id=task_id, queue=queue)
        log.debug('Spatial Ingest put into celery queue %s: %s site_user=%s site_url=%s',
                  queue, dataset.name, site_user['name'], self.site_url)
