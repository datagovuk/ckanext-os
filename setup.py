from setuptools import setup, find_packages

version = '0.1'

setup(
	name='ckanext-os',
	version=version,
	description='OS Widgets for DGU',
	long_description='',
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='OS, David Read',
	author_email='david.read@hackneyworkshop.com',
	url='http://data.gov.uk/',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.os'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[],
	entry_points=\
	"""
        [ckan.plugins]
        os_search=ckanext.os.plugin:SearchWidget
        os_preview=ckanext.os.plugin:PreviewWidget
        os_wfs_server=ckanext.os.plugin:WfsServer

        [paste.paster_command]
        mock_os_server = ckanext.os.testtools.mock_os_server:Command
        os=ckanext.os.commands:OSCommand

        [ckan.celery_task]
        tasks = ckanext.os.celery_import:task_imports
	""",
)
