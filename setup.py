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
	url='',
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
	""",
)
