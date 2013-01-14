from urllib import quote, urlencode
from urlparse import urljoin
from pylons import session as pylons_session

from ckan.lib.base import request, response, c, BaseController, model, abort, h, g, render, redirect
from ckan.lib.helpers import json

# Preview list 'Shopping basket'
class PreviewList(BaseController):
    def _get(self, id):
        preview_list = pylons_session.get('preview_list', [])
        for entry in preview_list:
            if entry['id'] == id:
                return entry

    def _querystring(self, pkg):
        out = []
        for r in pkg.resources:
            # NB This WFS/WMS detection condition must match that in dgu/ckanext/dgu/lib/helpers.py
            if r.extras.get('wfs_service') == 'ckanext_os' or (r.format or '').lower() == 'wfs':
                out.append(('wfsurl', urljoin(g.site_url, '/data/wfs')))
                out.append(('resid', r.id))
                resname = pkg.title
                if r.description:
                    resname += ' - %s' % r.description
                out.append(('resname', resname))
                           
            if 'wms' in (r.url or '').lower() or (r.format  or '').lower() == 'wms':
                out.append(('url',r.url))
        return urlencode(out)

    def reset(self):
        pylons_session['preview_list'] = []
        pylons_session.save()
        return self.view()

    def add(self, id):
        if not id:
            abort(409, 'Dataset not identified')
        preview_list = pylons_session.get('preview_list', [])
        pkg = model.Package.get(id)
        if not self._get(pkg.id):
            if not pkg:
                abort(404, 'Dataset not found')
            extent = (pkg.extras.get('bbox-north-lat'),
                      pkg.extras.get('bbox-west-long'),
                      pkg.extras.get('bbox-east-long'),
                      pkg.extras.get('bbox-south-lat'))
            preview_list.append({
                'id': pkg.id,
                'querystring': self._querystring(pkg),
                'name': pkg.name,
                'extent': extent,
                })
            pylons_session['preview_list'] = preview_list
            pylons_session.save()
        return self.view()

    def remove(self, id):
        if not id:
            abort(409, 'Dataset not identified')
        preview_list = pylons_session.get('preview_list', [])
        pkg = model.Package.get(id)
        if not pkg:
            abort(404, 'Dataset not found')
        entry = self._get(pkg.id)
        if not entry:
            abort(409, 'Dataset not in preview list')
        preview_list.remove(entry)
        pylons_session['preview_list'] = preview_list
        pylons_session.save()
        return self.view()

    def view(self):
        preview_list = pylons_session.get('preview_list', [])
        response.headers['Content-Type'] = 'application/json;charset=utf-8'
        return json.dumps(preview_list)
