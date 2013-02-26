import json
import requests
import urlparse
import logging
import sys
import logging

from pylons import config
from sqlalchemy import func, distinct

import ckan.plugins as p
from ckan.lib.cli import CkanCommand

REQUESTS_HEADER = {'content-type': 'application/json'}

class CkanApiError(Exception):
    pass

class OSCommand(p.toolkit.CkanCommand):
    """
    Spatial Data commands

    Usage::

        paster os [options] update [dataset/group name/id]
           - Spatial Ingest all resources in a given dataset or group,
           or on all datasets if no dataset given

        paster os view [dataset name/id]
           - See spatial data information

        paster os clean
           - Remove all spatial data

    You can run the commands like this from the ckanext-os directory
    and they will expect a development.ini file to be present. It is often
    preferable to specify the plugin and config explicitly though::

        paster --plugin=ckanext-os os update --config=<path to CKAN config file>
    """
    
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0

    def __init__(self, name):
        super(OSCommand, self).__init__(name)
        self.parser.add_option('-q', '--queue',
                               action='store',
                               dest='queue',
                               help='Send to a particular queue')

    def command(self):
        """
        Parse command line arguments and call appropriate method.
        """
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print QACommand.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        # Now we can import ckan and create logger, knowing that loggers
        # won't get disabled
        self.log = logging.getLogger('ckanext.qa')

        from ckan.logic import get_action
        from ckan import model

        site_user = p.toolkit.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {}
        )
        context = json.dumps({
            'site_url': config.get('ckan.site_url_internally') or config['ckan.site_url'],
            'site_user_apikey': site_user.get('apikey'),
            'spatial_datastore_jdbc_url': config['ckanext-os.spatial-datastore.jdbc.url'],
            'spatial_ingester_filepath': config['ckanext-os.spatial-ingester.filepath'],
        })

        if cmd == 'update':
            self.update(site_user, context)
        elif cmd == 'view':
            if len(self.args) == 2:
                self.view(self.args[1])
            else:
                self.view()                
        elif cmd == 'clean':
            self.clean()
        else:
            self.log.error('Command "%s" not recognized' % (cmd,))

    def update(self, user, context):
        from ckan.model.types import make_uuid
        from ckan.logic import get_action
        from ckan import model
        # import tasks after load config so CKAN_CONFIG evironment variable
        # can be set
        import tasks

        for package_dict in self._package_list():
            self.log.info('Spatial Ingest for dataset being added to Celery queue "%s": %s (%d resources)' % \
                        (self.options.queue, package_dict.get('name'),
                         len(package_dict.get('resources', []))))

            data = json.dumps(package_dict)
            task_id = make_uuid()
            tasks.spatial_ingest.apply_async(args=[context, data],
                                             task_id=task_id,
                                             queue=self.options.queue)


    def _package_list(self):
        """
        Generate the package dicts as declared in self.args.

        Make API calls for the packages declared in self.args, and generate
        the package dicts.

        If no packages are declared in self.args, then retrieve all the
        packages from the catalogue.
        """
        api_url = urlparse.urljoin(config.get('ckan.site_url_internally') or config['ckan.site_url'], 'api/action')
        if len(self.args) > 1:
            for id in self.args[1:]:
                # try arg as a group name
                url = api_url + '/member_list'
                self.log.info('Trying as a group "%s" at URL: %r', id, url)
                data = {'id': id,
                        'object_type': 'package',
                        'capacity': 'public'}
                response = requests.post(url, data=json.dumps(data), headers=REQUESTS_HEADER)
                if response.status_code == 200:
                    package_tuples = json.loads(response.text).get('result')
                    package_names = [pt[0] for pt in package_tuples]
                    if not self.options.queue:
                        self.options.queue = 'bulk'
                else:
                    # must be a package id
                    package_names = [id]
                    if not self.options.queue:
                        self.options.queue = 'priority'
                for package_name in sorted(package_names):
                    data = json.dumps({'id': unicode(package_name)})
                    url = api_url + '/package_show'
                    response = requests.post(url, data, headers=REQUESTS_HEADER)
                    if response.status_code == 403:
                        self.log.warning('Package "%s" is in the group but '
                                         'returned %i error, so skipping.' % \
                                         (package_name, response.status_code))
                        continue
                    if not response.ok:
                        err = ('Failed to get package %s from url %r: %s %s' %
                               (package_name, url, response.status_code, response.error))
                        self.log.error(err)
                        raise CkanApiError(err)
                    yield json.loads(response.content).get('result')
        else:
            if not self.options.queue:
                self.options.queue = 'bulk'
            page, limit = 1, 100
            while True:
                url = api_url + '/current_package_list_with_resources'
                response = requests.post(url,
                                         json.dumps({'page': page,
                                                     'limit': limit,
                                                     'order_by': 'name'}),
                                         headers=REQUESTS_HEADER)
                if not response.ok:
                    err = ('Failed to get package list with resources from url %r: %s %s' %
                           (url, response.status_code, response.error))
                    self.log.error(err)
                    raise CkanApiError(err)
                chunk = json.loads(response.content).get('result')
                if not chunk:
                    break
                for package in chunk:
                    yield package
                page += 1
                    
    def view(self, package_ref=None):
        from ckan import model
        
        q = model.Session.query(model.TaskStatus).filter_by(task_type='qa')
        print 'QA records - %i TaskStatus rows' % q.count()
        print '      across %i Resources' % q.distinct('entity_id').count()

        if package_ref:
            pkg = model.Package.get(package_ref)
            print 'Package %s %s' % (pkg.name, pkg.id)
            for res in pkg.resources:
                print 'Resource %s' % res.id
                for row in q.filter_by(entity_id=res.id):
                    print '* %s = %r error=%r' % (row.key, row.value, row.error) 

    def clean(self):
        from ckan import model

        print 'Before:'
        self.view()

        q = model.Session.query(model.TaskStatus).filter_by(task_type='qa')
        q.delete()
        model.Session.commit()

        print 'After:'
        self.view()        
