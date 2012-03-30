-----------------------------------
OS Widgets for DGU - CKAN Extension
===================================

This extension contains the OS Widgets for use in DGU CKAN.


Install & Configuration
=======================

To install this extension's code into your pyenv::

 pip install -e git+https://bitbucket.org/dread/ckanext-os#egg=ckanext-os

To enable it, in your CKAN config add to ckan.plugins items, as follows::

 ckan.plugins = os_search os_preview


Tests
=====

Run the tests like this::

 nosetests --ckan pyenv/src/ckanext-os/ckanext/os/tests/