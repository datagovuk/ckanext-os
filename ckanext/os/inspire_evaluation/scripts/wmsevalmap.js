// Name				: wmsevalmap.js 
// Description      : JavaScript file for the INSPIRE / UKLP evaluation map widget (evalmapwms.htm)
// Author			: Peter Cotroneo, Ordnance Survey, Andrew Bailey (C)
// Version			: 2.2.0.7

var tree, mapPanel, map, xmlHttp, leftPanel;
var urls, reachableUrls, unreachableUrls;
var intervalID, bBoxErr;
var gwcLayer;
var bBox; // array to store the parsed parameters
var mapBounds; // OpenLayers.Bounds of the parsed parameters
var mapExtent; // OpenLayers.Bounds transformed to correct projection
var boxes; // OpenLayers.Layer to store area of interest
var redBox; // OpenLayers.Marker to store area of interest
var borderColor;

/*
 * Projection definitions
 */
Proj4js.defs["EPSG:4258"] = "+proj=longlat +ellps=GRS80 +no_defs";
Proj4js.defs["EPSG:27700"] = "+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +datum=OSGB36 +units=m +no_defs";
Proj4js.defs["EPSG:29903"] = "+proj=tmerc +lat_0=53.5 +lon_0=-8 +k=1.000035 +x_0=200000 +y_0=250000 +a=6377340.189 +b=6356034.447938534 +units=m +no_defs";
Proj4js.defs["EPSG:2157"] = "+proj=tmerc +lat_0=53.5 +lon_0=-8 +k=0.99982 +x_0=600000 +y_0=750000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs";
Proj4js.defs["EPSG:4326"] = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs";

Ext.QuickTips.init();

Ext.onReady(function(){

    OSInspire = {};
    
    OSInspire.Layer = {};
    
    OSInspire.Layer.WMS = OpenLayers.Class(OpenLayers.Layer.WMS, {
    
        getURL: function(bounds){
        
            bounds = this.adjustBounds(bounds);
            
            var imageSize = this.getImageSize();
            
            var newParams = {};
            
            // WMS 1.3 introduced axis order
            
            var reverseAxisOrder = this.reverseAxisOrder();
            
            newParams.BBOX = this.encodeBBOX ? bounds.toBBOX(null, reverseAxisOrder) : bounds.toArray(reverseAxisOrder);
            
            newParams.WIDTH = imageSize.w;
            
            newParams.HEIGHT = imageSize.h;
            
            newParams.LAYERS = this.layerNames[this.map.zoom];
            
            var requestString = this.getFullRequestString(newParams);
            
            return requestString;
            
        },
        
        CLASS_NAME: "OSInspire.Layer.WMS"
    
    });
    
    OpenLayers.DOTS_PER_INCH = 90.71428571428572;
    
    OpenLayers.Util.onImageLoadError = function(){
        
		// this.src provides the wms request
        var errorStr = this.src.substring(0, (this.src.indexOf("?") + 1));
        var childStr = "";
		
		var foundBadWMS = false;
        var root = tree.getRootNode();
        var children = root.childNodes;
        // for (var i = 0; i < children.length; i++) {
            // if (children[i].text == errorStr) {
                // Ext.MessageBox.alert('Error', ("The WMS source: " + children[i].text + " has failed to load & will be switched off. It is possible that the WMS supports a different projection."));
                // children[i].cascade(function(n){
                    // var ui = n.getUI();
                    // ui.toggleCheck(false);
                // });
				// foundBadWMS = true;
            // }
        // }
		
		if (!(foundBadWMS))
		{
			// src may be returning with a different sub-domain but the same parent domain/hostname
			errorStr = getHostname(this.src);
			var count = errorStr.split("."); 
			if (count.length > 2)
			{
				// www.xxx.com counts the same as yyy.xxx.com
				var parentDomain = errorStr.substring((errorStr.indexOf(".")+1), errorStr.length);
				for (var j = 0; j < children.length; j++) {
					parentDomainOfNode = getHostname(children[j].text);
					parentDomainOfNode = parentDomainOfNode.substring((parentDomainOfNode.indexOf(".")+1), parentDomainOfNode.length);
					if (parentDomain == parentDomainOfNode) {
						Ext.MessageBox.alert('Error', ("The WMS source: " + children[j].text + " has failed to load - please switch it off or try a different projection."));
						children[j].cascade(function(m){
							var ui2 = m.getUI();
							ui2.toggleCheck(false);
						});
						foundBadWMS = true;
					}
				}				
			}
		}
		
		if (!(foundBadWMS))
		{
			// an unknown error has occurred
			//Ext.MessageBox.alert('Error','An unknown error has occurred with a WMS source.');
		}
    }
 
    var options = {
        projection: "EPSG:4258",
        units: 'degrees',
        maxExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
        displayProjection: new OpenLayers.Projection("EPSG:4326"),
        scales: [15000000, 10000000, 5000000, 1000000, 250000, 75000, 50000, 25000, 10000, 5000, 2500],
		//resolutions: [0.037269176337885415,0.024846117558590276,0.012423058779295138,0.002484611755859028,0.000621152938964757,0.00018634588168942707,0.00012423058779295138,0.00006211529389647569,0.000024846117558590272,0.000012423058779295136,0.000006211529389647568,0.0000024846117558590276],
		// size: new OpenLayers.Size(903, 435),		
        restrictedExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
        tileSize: new OpenLayers.Size(250, 250)
    };
    
    copyrightStatements = "Contains Ordnance Survey data (c) Crown copyright and database right [2011].<br>" +
    "Contains Royal Mail data (c) Royal Mail copyright and database right [2011]<br>" +
    "Contains bathymetry data by GEBCO (c) Copyright [2011].<br>" +
    "Contains data by Land & Property Services (Northern Ireland) (c) Crown copyright [2011]";
    
    // setup base mapping
    tiled = new OpenLayers.Layer.WMS("OS Base Mapping", "http://46.137.180.108/geoserver/gwc/service/wms", {		
		LAYERS: 'InspireETRS89',
        styles: '',
        format: 'image/png',
        tiled: true
    }, {
        buffer: 0,
        displayOutsideMaxExtent: true,
        isBaseLayer: true,
        attribution: copyrightStatements,
        transitionEffect: 'resize'
    });
	
    var wmsParams = {
        format: 'image/png'
    };
    
    var wmsOptions = {
        buffer: 0,
        //layerNames: layerNames,
        attribution: copyrightStatements
    };
    map = new OpenLayers.Map("mappanel", options);
    
    map.events.on({ "zoomend": function(e){
		if (tiled.getVisibility()) 
		{
			tiled.redraw();
		}
    }
    });
    
    map.events.on({
        "moveend": function(e){
            // nada
        }
    });
      
    // Remove default PanZoom bar; will use zoom slider below 
    var ccControl = map.getControlsByClass("OpenLayers.Control.PanZoom");
    map.removeControl(ccControl[0]);
    
    // Add scale bar
    map.addControl(new OpenLayers.Control.ScaleLine({
        geodesic: true
    }));
    
    // keyboard control
    map.addControl(new OpenLayers.Control.KeyboardDefaults({
        autoActivate: true
    }));
    
    // Add mouse position.  
    function formatLonlats(lonLat){
        var lat = lonLat.lat;
        var lon = lonLat.lon;
        var ns = OpenLayers.Util.getFormattedLonLat(lat);
        var ew = OpenLayers.Util.getFormattedLonLat(lon, 'lon');
        return ns + ', ' + ew + ' (' + (lat.toFixed(5)) + ', ' + (lon.toFixed(5)) + ')';
    }
    map.addControl(new OpenLayers.Control.MousePosition({
        formatOutput: formatLonlats
    }));
    
    // Add keyboard navigation
    map.addControl(new OpenLayers.Control.KeyboardDefaults());
    
    // Create arrays
    reachableUrls = new Array();
    unreachableUrls = new Array();
    children = new Array();
    urls = new Array();
    // Build array of URLs
    for (i = 0; i < paramParser.getUrls().length; i++) {
        urls[i] = paramParser.getUrls()[i];
    }

    // ### Bounding box
    boxes = new OpenLayers.Layer.Boxes("Boxes");
    borderColor = "red";
    // Extract bounding box and bounds before AJAX call
    bBox = new Array(paramParser.getBBox().westBndLon, paramParser.getBBox().eastBndLon, paramParser.getBBox().northBndLat, paramParser.getBBox().southBndLat)
    
    // ### add the default layers
    //map.addLayers([untiled, tiled]); 		    
    map.addLayer(tiled);
    map.addLayer(boxes);
    
    // Bounding box logic        
    if (isNaN(paramParser.getBBox().westBndLon) || isNaN(paramParser.getBBox().eastBndLon) || isNaN(paramParser.getBBox().southBndLat) || isNaN(paramParser.getBBox().northBndLat)) 
	{
        // failed parsed box paramters - need to generate a default mapBounds & mapExtent
        Ext.MessageBox.alert('Error', 'The values providing for the bounding box are not numerical.', '');
        bBoxErr = 1;
    }
    else {
        if (paramParser.getBBox().westBndLon < -30.00 || paramParser.getBBox().eastBndLon > 3.50 || paramParser.getBBox().southBndLat < 48.00 || paramParser.getBBox().northBndLat > 64.00) 
		{
            // failed parsed box paramters - need to generate a default mapBounds & mapExtent
            Ext.MessageBox.alert('Error', 'The coordinates of the bounding box are outside of the searchable map bounds.', '');                 
            bBoxErr = 1;
        }
        else 
		{
            if (paramParser.getBBox().westBndLon > paramParser.getBBox().eastBndLon) 
			{
                // failed parsed box paramters - need to generate a default mapBounds & mapExtent
                Ext.MessageBox.alert('Error', 'The west bounding longitude cannot be greater than the east bounding longitude.', '');                           
                bBoxErr = 1;
            }
            else 
			{
                if (paramParser.getBBox().southBndLat > paramParser.getBBox().northBndLat) 
				{
                    // failed parsed box paramters - need to generate a default mapBounds & mapExtent
                    Ext.MessageBox.alert('Error', 'The south bounding latitude cannot be greater than the north bounding latitude.', '');                                     
                    bBoxErr = 1;
                }
                else 
				{
                    // acceptable parsed box parameters - need to construct bounding box
                    mapBounds = new OpenLayers.Bounds(bBox[0], bBox[3], bBox[1], bBox[2]);
                    mapExtent = mapBounds.clone();
                    redBox = new OpenLayers.Marker.Box(mapExtent, borderColor);
                    boxes.addMarker(redBox);
                    bBoxErr = 0;
                }
            }
        }
    }
   
    buildUI(urls);    
});

// Place bounding box layer on top
function moveLayerToTop(layer){
    var topPosition = mapPanel.map.getNumLayers() - 1;
    mapPanel.map.setLayerIndex(layer, topPosition);
}

function switchOnAllLayers(){
    for (var i = 1, len = map.layers.length; i < (len - 1); i++) {
        map.layers[i].setVisibility(true);
    }
}

// Get XML object 
function getXMLObject(){

    var xmlHttp = false;
    
    try {
    
        // Old Microsoft Browsers
        xmlHttp = new ActiveXObject("Msxml2.XMLHTTP")
        
    } 
    catch (e) {
    
        try {
        
            // Microsoft IE 6.0+
            xmlHttp = new ActiveXObject("Microsoft.XMLHTTP")
            
        } 
        catch (e2) {
        
            // Return false if no browser acceps the XMLHTTP object
            xmlHttp = false
            
        }
    }
    if (!xmlHttp && typeof XMLHttpRequest != 'undefined') {
    
        //For Mozilla, Opera Browsers
        xmlHttp = new XMLHttpRequest();
        
    }
    
    return xmlHttp;
}

// Build the UI
function buildUI(urls){

    // Test URLs
    //urls = new Array('http://domain:8080/path?query_string#fragment_id','http://12.12.23.34:8080/foo', 'http://foobar:8080/foo', 'http:/foobar', 'http//foobar.com', 'http://ogc.bgs.ac.uk/cgi-bin/BGS_1GE_Geology/wms?', 'http://ogc.bgs.ac.uk/cgi-bin/BGS_1GE_Geology/wms', 'http://ogc.bgs.ac.uk/cgi-bin/BGS_1GE_Geology/wms?request=getCapabilities&service=wms', 'http://ogc.bgs.ac.uk/cgi-bin/BGS_1GE_Geology/wms?service=wms&request=getCapabilities&');
	
    // Check the syntax of the WMS URL.  If it's invalid, remove it from the layer tree.
    // Note:  Valid URLs have the syntax:  scheme://domain:port/path?query_string#fragment_id
    
    var validUrls = new Array();
    var invalidUrls = new Array();
    var validCounter = 0;
    var invalidCounter = 0;
    
    for (var i = 0; i < urls.length; i++) {
        if (isUrl(urls[i])) {
			// Add URL to validUrls array
            validUrls[validCounter] = urls[i];
            validCounter++;
        }
        else {
			// Add URL to invalidUrls array
            if (urls[i].length > 0)
			{
				invalidUrls[invalidCounter] = urls[i];
				invalidCounter++;
			}
        }
    }
    if (invalidUrls.length > 0) {
    
        var errorStr = "The following WMS URLs have incorrect syntax and will not be displayed in the layer tree: <br><br>";
        
        for (var i = 0; i < invalidUrls.length; i++) {
            errorStr = errorStr + invalidUrls[i] + "<br>";
        }
        Ext.MessageBox.alert('WMS Error', errorStr, '');   
    }
  
    // Build layer tree from valid WMS URLs 
    for (var i = 0; i < validUrls.length; i++) {
    
        // Logic to handle the inclusion or lack of parameters in the WMS URL
        
        var wmsSuffix;
        
        // If WMS URL terminates with a ?
        if (validUrls[i].charAt(validUrls[i].length - 1) == "?") {
            wmsSuffix = "request=getCapabilities&service=wms";
            
        }
        // If WMS URL does not contain a ?
        else 
            if (validUrls[i].indexOf("?") == -1) {
                wmsSuffix = "?request=getCapabilities&service=wms";
                
            }
            // Don't append anything
            else {
                wmsSuffix = "";
            }
        
        // Replace ? and & characters with their HTML encoded counterparts
        var urlWmsSuffix = validUrls[i] + wmsSuffix;
        urlWmsSuffix = urlWmsSuffix.replace("?", "%3F");
        urlWmsSuffix = urlWmsSuffix.replace("&", "%26");
        
        // Child definition
        child = {
            text: validUrls[i],
            qtip: validUrls[i],
            
            loader: new GeoExt.tree.WMSCapabilitiesLoader({
                url: 'proxy.php?url=' + urlWmsSuffix, // Must use proxy
                layerOptions: {
                    buffer: 0,
                    singleTile: false,
                    ratio: 1,
                    opacity: 0.75
                },
                layerParams: {
                    transparent: 'true'
                },
                createNode: function(attr){
                    attr.qtip = attr.text;
                    attr.checked = attr.leaf ? false : undefined;
                    return GeoExt.tree.WMSCapabilitiesLoader.prototype.createNode.apply(this, [attr]);
                }
            }),
            expanded: true
        };
        
        children[i] = child;
        
    }
    
	var browser = navigator.userAgent;
	if ((browser.toLowerCase().indexOf('safari') > 0) || (/MSIE (\d+\.\d+);/.test(navigator.userAgent)))
	{
		// set max. length of qtip on child nodes
		for(var i=0; i<children.length; i++) {
			var qtipString = children[i].qtip;
			var tidyString = "";
			var mostSuitablePosForForwardSlash = 0;
			if (qtipString.length > 30)
			{
				while (qtipString.length > 30)
				{
					// take first chunk off and add to tidyString
					if (tidyString.length > 0)
					{
						tidyString += "<br>";
					} 
				
					mostSuitablePosForForwardSlash = 0;
					for (j = 0; j < qtipString.length; j++)
					{
						if (qtipString.charAt(j) == "/")
						{
							if (Math.pow(30-j,2) < Math.pow(30-mostSuitablePosForForwardSlash,2))
							{
								mostSuitablePosForForwardSlash = j;
							}
						}					
					}
					if (mostSuitablePosForForwardSlash != 0)
					{
						tidyString += qtipString.substring(0, mostSuitablePosForForwardSlash);
						qtipString = qtipString.substring(mostSuitablePosForForwardSlash, qtipString.length);										
						//alert("using a slash at " + mostSuitablePosForForwardSlash + "<br>" + tidyString + "<br>" + qtipString);
					} else {
						tidyString += qtipString;
						qtipString = "";
						//alert("no more cutting to do. " + "<br>" + tidyString + "<br>" + qtipString)
					}
				}
				if (qtipString.length > 0)
				{
					tidyString += "<br>" + qtipString;
				}
			}
			else
			{
				tidyString = qtipString;
			}
			children[i].qtip = tidyString;
		}
	}
	else
	{
		// do nothing, other browsers handle long url tooltips just fine
	}


	
    // Define the root for the layer tree
    root = new Ext.tree.AsyncTreeNode({
        id: 'root',
        children: children
    });
    
    // Define the layer tree
    tree = new Ext.tree.TreePanel({
    
        id: 'tree',
        header: false,
        border: false,
        title: 'WMS Layers',
        root: root,
        rootVisible: false,
        region: 'west',
        animate: true,
        lines: true,
        
        listeners: {
        
            // Add layers to the map when checked and remove when unchecked
            'checkchange': function(node, checked){
                if (checked === true) {
                
                    mapPanel.map.addLayer(node.attributes.layer);
                    moveLayerToTop(boxes);
                }
                else {
                
                    mapPanel.map.removeLayer(node.attributes.layer);
                    moveLayerToTop(boxes);
                }
            }
        }
    });
    
    // Define the map panel
    mapPanel = new GeoExt.MapPanel({
        map: map,
        region: 'center',
        // items: []
        items: [{
            xtype: "gx_zoomslider",
            vertical: true,
            // Length of slider
            height: 150,
            // x,y position of slider
            x: 10,
            y: 20,
            // Tooltips
            plugins: new GeoExt.ZoomSliderTip({
                template: "Zoom level: {zoom}<br>Scale: 1 : {scale}"
            })
        }]
    });
    
    // Create checkbox for toggling backdrop map on/off
    var checkboxes = new Ext.form.CheckboxGroup({
    
        items: [{
            boxLabel: 'Backdrop Map',
            
            checked: true,
            
            handler: function checkvalue(){
                var obj = Ext.select('input[type=checkbox]').elements;
                var i = 0;
                
                // Toggle backdrop map on/off
                if (obj[i].checked) {
                    tiled.setVisibility(true);
                    tiled.redraw();
                }
                else {
                    tiled.setVisibility(false);
                }
            }
        }]
    });
    
    // Create a panel for the checkbox  
    var chkbxPanel = new Ext.Panel({
    
        header: false,
        bodyStyle: "padding:5px",
        title: 'UK Map',
        border: false,
        region: 'west',
        width: 250,
        
        items: [checkboxes]
    
    });
    
    // projection data for combobox
    var projectionData = new Ext.data.SimpleStore({
        id: 0,
        fields: [{
            name: 'projectionName'
        }, {
            name: 'epsg'
        }],
        data: [
			['ETRS89', '4258'],
			['WGS84', '4326'],
			['British National Grid', '27700'],			
			['Irish Grid', '29903'],
			['Irish Transverse Mercator', '2157']			
		]
    });
    
    // define projections
    var proj4258 = new OpenLayers.Projection("EPSG:4258");
    var proj4326 = new OpenLayers.Projection("EPSG:4326");
    var proj27700 = new OpenLayers.Projection("EPSG:27700");
    var proj2157 = new OpenLayers.Projection("EPSG:2157");
    var proj29903 = new OpenLayers.Projection("EPSG:29903");
    
    // build options for map
    var options4258 = {
        // proper bounds for ETRS89
        maxExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
        restrictedExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
        projection: "EPSG:4258",
        units: "degrees"
    };
    var options4326 = {
        // bounds for WGS84
        maxExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
        restrictedExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
        projection: "EPSG:4326",
        units: "degrees"
    };
    var options27700 = {
        // proper bounds for BNG
		maxExtent: new OpenLayers.Bounds(-1676863.69127, -211235.79185, 810311.58692, 1870908.806),
		restrictedExtent: new OpenLayers.Bounds(-1676863.69127, -211235.79185, 810311.58692, 1870908.806),
        projection: "EPSG:27700",
        units: "m"
    };
    var options2157 = {
        // proper bounds for ITM        
        maxExtent: new OpenLayers.Bounds(-1036355.59295, 138271.94508, 1457405.79374, 2105385.88137),
        restrictedExtent: new OpenLayers.Bounds(-1036355.59295, 138271.94508, 1457405.79374, 2105385.88137),
        projection: "EPSG:2157",
        units: "m"
    };
    var options29903 = {
        // proper bounds for IG
		maxExtent: new OpenLayers.Bounds(-1436672.42532, -361887.06768, 1057647.39762, 1605667.48446),
        restrictedExtent: new OpenLayers.Bounds(-1436672.42532, -361887.06768, 1057647.39762, 1605667.48446),		
        projection: "EPSG:29903",
        units: "m"       
    };
    
    // form components
    var formPanel = new Ext.form.FormPanel({
        //labelWidth: 70,
        bodyStyle: "padding:5px",
        border: false,
        items: [{
            xtype: "combo",
            id: 'projectionCombo',
            fieldLabel: "Projection",
            emptyText: 'Projection',
            store: projectionData,
            displayField: 'projectionName',
            valueField: 'epsg',
            hiddenName: 'theEPSG',
            selectOnFocus: true,
            mode: 'local',
            typeAhead: true,
            editable: false,
            triggerAction: "all",
            value: '4258',
            listeners: {
                select: function(combo, record, index){
                
                    var epsg = "EPSG:" + combo.getValue();
                    
                    switch (epsg) {
                        case "EPSG:4258":
                            
                            // ETRS89
                            var centre = mapPanel.map.getCenter();
                            var zoom = mapPanel.map.getZoom();
                            var srcProj = new OpenLayers.Projection(mapPanel.map.projection);
                            // transform centre
                            centre.transform(srcProj, proj4258);
                            mapPanel.map.baseLayer.mergeNewParams({
								LAYERS: 'InspireETRS89'
                            });
                            // reset map
                            mapPanel.map.setOptions(options4258);
                            // reset layers
                            for (var i = 0, len = mapPanel.map.layers.length; i < len; i++) {
                                mapPanel.map.layers[i].addOptions(options4258);
                                if (mapPanel.map.layers[i].name == "Boxes") {
                                    if (redBox != null) {
                                        mapExtent = mapBounds.clone();
                                        mapExtent.transform(proj4326, proj4258);
                                        mapPanel.map.layers[i].removeMarker(redBox);
                                        redBox = new OpenLayers.Marker.Box(mapExtent, borderColor);
                                        mapPanel.map.layers[i].addMarker(redBox);
                                        mapPanel.map.layers[i].redraw();
                                    }
                                }
                            }
                            // centre map
                            mapPanel.map.setCenter(centre, zoom, true, true);
                            break;
                            
                        case "EPSG:4326":
                            
                            // WGS84
                            var centre = mapPanel.map.getCenter();
                            var zoom = mapPanel.map.getZoom();
                            var srcProj = new OpenLayers.Projection(mapPanel.map.projection);
                            // transform centre
                            centre.transform(srcProj, proj4326);
                            mapPanel.map.baseLayer.mergeNewParams({
								LAYERS: 'InspireWGS84'
                            });
                            // reset map
                            mapPanel.map.setOptions(options4326);
                            // reset layers
                            for (var i = 0, len = mapPanel.map.layers.length; i < len; i++) {
                                mapPanel.map.layers[i].addOptions(options4326);
                                if (mapPanel.map.layers[i].name == "Boxes") {
                                    if (redBox != null) {
                                        mapExtent = mapBounds.clone();
                                        mapPanel.map.layers[i].removeMarker(redBox);
                                        redBox = new OpenLayers.Marker.Box(mapExtent, borderColor);
                                        mapPanel.map.layers[i].addMarker(redBox);
                                        mapPanel.map.layers[i].redraw();
                                    }
                                }
                            }
                            // centre map
                            mapPanel.map.setCenter(centre, zoom, true, true);
                            break;
                            
                        case "EPSG:27700":
                            
                            // British National Grid
                            var centre = mapPanel.map.getCenter();
                            var zoom = mapPanel.map.getZoom();
                            var srcProj = new OpenLayers.Projection(mapPanel.map.projection);
                            // transform centre
                            centre.transform(srcProj, proj27700);
                            mapPanel.map.baseLayer.mergeNewParams({
                                LAYERS: 'InspireBNG'
                            });													
                            // reset map							
                            mapPanel.map.setOptions(options27700);
                            // reset layers
                            for (var i = 0, len = mapPanel.map.layers.length; i < len; i++) {
                                mapPanel.map.layers[i].addOptions(options27700);
                                if (mapPanel.map.layers[i].name == "Boxes") {
                                    if (redBox != null) {
                                        mapExtent = mapBounds.clone();
                                        mapExtent.transform(proj4326, proj27700);
                                        mapPanel.map.layers[i].removeMarker(redBox);
                                        redBox = new OpenLayers.Marker.Box(mapExtent, borderColor);
                                        mapPanel.map.layers[i].addMarker(redBox);
                                        mapPanel.map.layers[i].redraw();
                                    }
                                }
                            }
                            // centre map
                            mapPanel.map.setCenter(centre, zoom, true, true);
                            break;
                            
                        case "EPSG:2157":
                            
                            // Irish Transverse Mercator
                            var centre = mapPanel.map.getCenter();
                            var zoom = mapPanel.map.getZoom();
                            var srcProj = new OpenLayers.Projection(mapPanel.map.projection);
                            // transform centre
                            centre.transform(srcProj, proj2157);
                            mapPanel.map.baseLayer.mergeNewParams({
								LAYERS: 'InspireITM'
                            });
                            // reset map
                            mapPanel.map.setOptions(options2157);
                            // reset layers
                            for (var i = 0, len = mapPanel.map.layers.length; i < len; i++) {
                                mapPanel.map.layers[i].addOptions(options2157);
                                if (mapPanel.map.layers[i].name == "Boxes") {
                                    if (redBox != null) {
                                        mapExtent = mapBounds.clone();
                                        mapExtent.transform(proj4326, proj2157);
                                        mapPanel.map.layers[i].removeMarker(redBox);
                                        redBox = new OpenLayers.Marker.Box(mapExtent, borderColor);
                                        mapPanel.map.layers[i].addMarker(redBox);
                                        mapPanel.map.layers[i].redraw();
                                    }
                                }
                            }
                            // centre map
                            mapPanel.map.setCenter(centre, zoom, true, true);
                            break;
                            
                        case "EPSG:29903":
                            
                            // Irish Grid
                            var centre = mapPanel.map.getCenter();
                            var zoom = mapPanel.map.getZoom();
                            var srcProj = new OpenLayers.Projection(mapPanel.map.projection);
                            // transform centre
                            centre.transform(srcProj, proj29903);
                            mapPanel.map.baseLayer.mergeNewParams({
								LAYERS: 'InspireIG'
                            });
                            // reset map
                            mapPanel.map.setOptions(options29903);
                            // reset layers
                            for (var i = 0, len = mapPanel.map.layers.length; i < len; i++) {
                                mapPanel.map.layers[i].addOptions(options29903);
                                if (mapPanel.map.layers[i].name == "Boxes") {
                                    if (redBox != null) {
                                        mapExtent = mapBounds.clone();
                                        mapExtent.transform(proj4326, proj29903);
                                        mapPanel.map.layers[i].removeMarker(redBox);
                                        redBox = new OpenLayers.Marker.Box(mapExtent, borderColor);
                                        mapPanel.map.layers[i].addMarker(redBox);
                                        mapPanel.map.layers[i].redraw();
                                    }
                                }
                            }
                            // centre map
                            mapPanel.map.setCenter(centre, zoom, true, true);
                            break;
                            
                        default:
                            
                            // ETRS89
                            var centre = mapPanel.map.getCenter();
                            var zoom = mapPanel.map.getZoom();
                            var srcProj = new OpenLayers.Projection(mapPanel.map.projection);
                            // transform centre
                            centre.transform(srcProj, proj4258);
                            mapPanel.map.baseLayer.mergeNewParams({
								LAYERS: 'InspireETRS89'
                            });
                            // reset map
                            mapPanel.map.setOptions(options4258);
                            // reset layers
                            for (var i = 0, len = mapPanel.map.layers.length; i < len; i++) {
                                mapPanel.map.layers[i].addOptions(options4258);
                                if (mapPanel.map.layers[i].name == "Boxes") {
                                    if (redBox != null) {
                                        mapExtent = mapBounds.clone();
                                        mapExtent.transform(proj4326, proj4258);
                                        mapPanel.map.layers[i].removeMarker(redBox);
                                        redBox = new OpenLayers.Marker.Box(mapExtent, borderColor);
                                        mapPanel.map.layers[i].addMarker(redBox);
                                        mapPanel.map.layers[i].redraw();
                                    }
                                }
                            }
                            // centre map
                            mapPanel.map.setCenter(centre, zoom, true, true);
                    }
                } // end of function for selecting combo
            } // end of listeners
        }] // end of items
    }); // end of formpanel def
    // Create a panel for both checkbox and tree
    leftPanel = new Ext.Panel({
        //id: 'leftPanel',
        title: 'Map Layers',
        border: false,
        region: 'west',
        width: 295,
        minWidth: 295,
        autoScroll: true,
        collapsible: true,
        split: true,
        collapseMode: "mini",
        
        items: [formPanel, chkbxPanel, tree]
    });
    
    // Information text
    var main = new Ext.Panel({
        border: false,
        renderTo: 'info',
        
        html: "<a href=\"http://data.gov.uk/faq\" target=\"_blank\" title=\"Open Help Window\">Need help getting started?</a><br><br>" +
        "Please note:<br><br>" +
		"<b>-</b> Where a rotating circle remains in the WMS Layers window, this indicates that the service is waiting for a response from that publisher's WMS. This is due to their server not being available or to network problems.<br>" +        
        "<b>-</b> Backdrop mapping can be turned off and on using the check box at the top of the Map Layers panel.<br>" +
        "<b>-</b> Backdrop mapping is available in 9 scales: from 1:15 million to 1:10,000. Additional scales without backdrop mapping are provided to enable viewing of large scale data.<br>" +
        "<b>-</b> On selecting a layer, you may need to zoom in or out to see the data as the Publisher's WMS may restrict the scales at which it can be viewed.<br>" +
        "<b>-</b> You may need to pan to view the data if it is outside current window view.<br>" +
        "<b>-</b> Not all map layers support all projections. If a layer does not display then it may be possible for it to display by choosing a different projection.<br>" +
        "<b>-</b> All the backdrop mapping displayed in this window is derived from small scale data and is intended to aid evaluation of selected data sets only. It should not be used to assess their positional accuracy.<br>" +
		"<b>-</b> Users of Internet Explorer & Opera will find the map pan tool doesn't work in the copyright section. This is a known issue with the mapping framework. A fix will be provided in a future release."
    });
    
    // Define a viewport.  Tree will be on the left, map on the right, information on the bottom
    new Ext.Viewport({
        layout: "fit",
        hideBorders: true,
        border: false,
        items: {
            layout: "border",
            deferredRender: false,
            items: [mapPanel, leftPanel, {
                contentEl: "info",
                region: "south",
                bodyStyle: {
                    "padding": "5px"
                },
                
                collapsible: true,
                collapseMode: "mini",
                autoScroll: true,
                height: 160,
                title: "Information"
            }]
        }
    });
    
    // If no bounding box issues, zoom to the mapBounds
    if (bBoxErr == 0) {
        map.zoomToExtent(mapBounds);
    }
    else {
        mapBounds = new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00);
        //mapBounds = new OpenLayers.Bounds(-13.02, 49.79, 3.26, 60.95); // Centred upon British Isles
        mapExtent = mapBounds.clone();
        map.zoomToExtent(mapBounds);
    }
    
}

// Display error message if there is one or more unreachable WMS URLs
function displayUnreachableMsg(unreachableUrls){

    var errorStr;
    
    if (unreachableUrls.length > 0) {
    
        if (unreachableUrls.length == 1) {
            errorStr = "The following Web Map Service URL could not be reached:<br><br>";
        }
        else {
            errorStr = "The following " + unreachableUrls.length + " Web Map Services could not be reached:<br><br>";
        }
        
        for (var i = 0; i < unreachableUrls.length; i++) {
            errorStr = errorStr + unreachableUrls[i] + "<br>";
        }
        
        if (reachableUrls.length == 0) {
            errorStr = errorStr + "<br>There are no Web Map Services to overlay.  Please try again."
        }
        
        Ext.MessageBox.alert('WMS Error', errorStr, '');
    }
    
}

//function to check/uncheck all the child node.
function toggleCheck(node, isCheck){
    if (node) {
        var args = [isCheck];
        node.cascade(function(){
            c = args[0];
            this.ui.toggleCheck(c);
            this.attributes.checked = c;
        }, null, args);
    }
}

// Check if a URL has correct syntax
function isUrl(s){
    var regexp = /(http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/
    return regexp.test(s);
}

function getHostname(str) {
	var re = new RegExp('^(?:f|ht)tp(?:s)?\://([^/]+)', 'im');
	return str.match(re)[1].toString();
}