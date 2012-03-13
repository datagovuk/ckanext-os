from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes
from ckan.plugins import IController

class SearchWidget(SingletonPlugin):
    implements(IRoutes)

    def before_map(self, map):
        map.connect('/map-based-search',
                    controller='ckanext.os.controller:SearchWidget',
                    action='index')
        map.connect('/map-based-preview',
                    controller='ckanext.os.controller:PreviewWidget',
                    action='index')
        return map


