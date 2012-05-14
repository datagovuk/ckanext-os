-----------------------------------
OS Widgets for DGU - CKAN Extension
===================================

This extension contains the OS Widgets for use in DGU CKAN.

NB: This software is open source, but the services provided by OS servers are not free. For usage of these other than on data.gov.uk, please contact Ordnance Survey for a licence.


Install & Configuration
=======================

To install this extension's code into your pyenv::

 pip install -e git+https://bitbucket.org/dread/ckanext-os#egg=ckanext-os

To enable it, in your CKAN config add to ckan.plugins items, as follows::

 ckan.plugins = os_search os_preview

To improve performance of the geoserver calls (boundary information) add these lines to your Apache config::
 
 ProxyPass /geoserver/ http://osinspiremappingprod.ordnancesurvey.co.uk/geoserver/
 ProxyPassReverse /geoserver/ http://osinspiremappingprod.ordnancesurvey.co.uk/geoserver/

and enable Apache modules: ``mod_proxy`` and ``mod_proxy_http``::

 sudo a2enmod proxy_http

To configure the servers used in the widgets, put the following lines in your ckan configuration file and change the values from the defaults shown::

 ckanext-os.geoserver.host = osinspiremappingprod.ordnancesurvey.co.uk
 ckanext-os.gazetteer.host = osinspiremappingprod.ordnancesurvey.co.uk
 ckanext-os.libraries.host = osinspiremappingprod.ordnancesurvey.co.uk
 ckanext-os.tiles.url = http://osinspiremappingprod.ordnancesurvey.co.uk/geoserver/gwc/service/wms
 ckanext-os.wfs.url = /geoserver/wfs
 ckanext-os.geoserver.apikey = 


Preview List
============

This extension provides an API to help store a 'shopping basket'-style list of packages to preview. You can add and remove items from it and request a list.

Examples
--------

Add: a request to ``api/2/util/preview_list/add/-municipal-waste-generation-in-england-from-2000-01-to-2009-10`` adds this package to the list. The package can be specified as either an ID or name. The response is the full preview list (JSON-encoded).

Remove: a request to ``api/2/util/preview_list/remove/-municipal-waste-generation-in-england-from-2000-01-to-2009-10`` then removes it again. Again the response contains the full list.

List: You can also just request the list using ``/api/2/util/preview_list``.

In an HTML template the list can be accessed as: ``${session.get('preview_list', []}``


Tests
=====

Run the tests like this::

 nosetests --ckan pyenv/src/ckanext-os/ckanext/os/tests/

