import os

from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes
from ckan.plugins import IConfigurer

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
        map.connect('/geoserver/{url_suffix:.*}',
                    controller='ckanext.os.controller:Proxy',
                    action='geoserver_proxy')

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
                                      'os', 'inspire_evaluation')
        template_dir = os.path.join(rootdir, 'ckanext',
                                    'os', 'inspire_evaluation')
        # set our local template and resource overrides
        #config['extra_public_paths'] = ','.join([our_public_dir,
        #        config.get('extra_public_paths', '')])
        #config['extra_template_paths'] = ','.join([template_dir,
        #        config.get('extra_template_paths', '')])

