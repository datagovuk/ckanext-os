Ext.namespace("GeoExt.tree");
GeoExt.tree.WMSCapabilitiesLoader = function (config) {
    Ext.apply(this, config);
    GeoExt.tree.WMSCapabilitiesLoader.superclass.constructor.call(this)
};
Ext.extend(GeoExt.tree.WMSCapabilitiesLoader, Ext.tree.TreeLoader, {
    url: null,
    layerOptions: null,
    layerParams: null,
    hasLayers: true,
    requestMethod: 'GET',
    getParams: function (node) {
        return {
            'service': 'WMS',
            'request': 'GetCapabilities'
        }
    },
    processResponse: function (response, node, callback, scope) {
        var capabilities = new OpenLayers.Format.WMSCapabilities().read(response.responseXML || response.responseText);
        if (!capabilities.capability) {
            this.hasLayers = false;
            scope.loading = false
        } else {
            this.processLayer(capabilities.capability, capabilities.capability.request.getmap.href, node);
            if (typeof callback == "function") {
                callback.apply(scope || node, [node])
            }
        }
    },
    createWMSLayer: function (layer, url) {
        if (layer.name) {
            return new OpenLayers.Layer.WMS(layer.title, url, OpenLayers.Util.extend({
                formats: layer.formats[0],
                layers: layer.name
            }, this.layerParams), OpenLayers.Util.extend({
                minScale: layer.minScale,
                queryable: layer.queryable,
                maxScale: layer.maxScale,
                metadata: layer
            }, this.layerOptions))
        } else {
            return null
        }
    },
    processLayer: function (layer, url, node) {
        Ext.each(layer.nestedLayers, function (el) {
            var n = this.createNode({
                text: el.title || el.name,
                nodeType: 'node',
                layer: this.createWMSLayer(el, url),
                leaf: (el.nestedLayers.length === 0),
                expanded: true
            });
            if (n) {
                node.appendChild(n)
            }
            if (el.nestedLayers) {
                this.processLayer(el, url, n)
            }
        }, this)
    }
});