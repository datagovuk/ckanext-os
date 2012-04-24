//
// Name				: wmsmap.js 
// Description      : JavaScript file for the INSPIRE / UKLP search map widget
// Author			: Peter Cotroneo, Ordnance Survey
// Version			: 2.3.0.4

// ** Global variables **
var mapPanel, map, zoombar, zoompopup, boxes, rectangle;
var globalGazZoomType, globalGazCoords, globalGazTypes;
var lastSelection, lastSelectedZoomLocation, lastZoomLevel;
var boundaryLayer, defBoundaryStyle, styBoundary, styleBoundaryMap;
var selectHover, boundarypopup, boundarynamebuffer, reportoffexecuted;
var cursorXp, cursorYp, cursorposition;
var navigationControl, keyBoardDefaultControl, boundingBoxControl, drawMode;
var inputStr, outputStr, clrTxt, locationFound;
var o, da, xmlhttp, ll, ur;
var submitFlag, sectorFlag, browserFlag;
var alreadyrunflag = 0;
var useVMLRenderer;
var IEWarned = false;
var boxLayer = null,
    drawBoxControl = null;

//OpenLayers.ProxyHost = "proxy.php?url=";
window.alert = function (str) {
      Ext.MessageBox.show({
        title: 'Information',
        msg: str,
        buttons: Ext.MessageBox.OK,
        icon: Ext.MessageBox.WARNING
    });
}

if (document.addEventListener) {
	// Firefox browsers
  	document.addEventListener("DOMContentLoaded", function() {
            alreadyrunflag=1;
            inspireinit()
        }, false);
	useVMLRenderer = false;
} else if (document.all && !window.opera){
	// IE browsers
	var ver = getInternetExplorerVersion();
	if ( ver > -1 )	{
		if ( ver >= 9.0 ) {
			useVMLRenderer = false;
		} else {
			useVMLRenderer = true;	
		}
	}	
  	document.write('<script type="text/javascript" id="contentloadtag" defer="defer" src="javascript:void(0)"><\/script>');
  	var contentloadtag=document.getElementById("contentloadtag");
  	contentloadtag.onreadystatechange=function(){
    	if (this.readyState=="complete"){
      		alreadyrunflag=1;
      		inspireinit();
    	}
  	};
}

function getInternetExplorerVersion()
// Returns the version of Internet Explorer or a -1
// (indicating the use of another browser).
{
  var rv = -1; // Return value assumes failure.
  if (navigator.appName == 'Microsoft Internet Explorer') {
    var ua = navigator.userAgent;
    var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
    if (re.exec(ua) != null)
      rv = parseFloat( RegExp.$1 );
  }
  return rv;
}


// all other browsers
window.onload = function(){
  setTimeout("if (!alreadyrunflag) inspireinit()", 0);
  addSelect();
}

function addSelect() {
            // Just write the original HTML for the element to the new gazContainer div
            document.getElementById("gazContainer").innerHTML = '<select name="select" id="selectGaz" onchange="zoomGazSel(this.form.select)" onclick="zoomToLastSel()" onfocus="recordSelection(this.form.select)"></select>';
}

function inspireinit() {
            setText();
            // To be used to keep track of Draw button press
            drawMode = false;
            var browserName=navigator.appName; 
            if (browserName == "Microsoft Internet Explorer") { 
              document.attachEvent("onmousemove",function(evt){
                  windowMouseMove(evt)
                                       });
            }
            // Firefox and others
            else if(document.addEventListener) {
              document.addEventListener("mousemove", function(evt) {
                  windowMouseMove(evt)
              }, false);					
            }
	        // boundaries off at the start
	        document.getElementById("boundaries").checked = false;
	        
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
    
    		//var gwcLayer;
    
    		OpenLayers.DOTS_PER_INCH = 90.71428571428572;
    
    		var options = {
			        size: new OpenLayers.Size(903,435),
			        //resolutions: resolutions,
					scales: [15000000, 10000000, 5000000, 1000000, 250000, 75000],
			        maxExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
			        restrictedExtent: new OpenLayers.Bounds(-30, 48.00, 3.50, 64.00),
			        tileSize: new OpenLayers.Size(250, 250),
			        units: 'degrees',
			        projection: "EPSG:4258"
    		};
    
    		 // Set the copyright statements
                copyrightStatements = "Contains Ordnance Survey data (c) Crown copyright and database right  [2012] <br>" + "Contains Royal Mail data (c) Royal Mail copyright and database right [2012]<br>" + "Contains bathymetry data by GEBCO (c) Copyright [2012]<br>" + "Contains data by Land & Property Services (Northern Ireland) (c) Crown copyright [2012]";
    
    		// setup tiled layer
    		tiled = new OpenLayers.Layer.WMS("Geoserver layers - Tiled", //"http://46.137.180.108:80/geoserver/wms", {
			CKANEXT_OS_TILES_URL, {
		        //LAYERS: 'sea_dtm,InspireVectorStack',
				LAYERS: 'InspireETRS89',
		        STYLES: '',
		        format: 'image/png',
		        tiled: true
		        // tilesOrigin : map.maxExtent.left + ',' + map.maxExtent.bottom
    			}, {
		        buffer: 0,
		        displayOutsideMaxExtent: true,
		        isBaseLayer: true,
		        attribution: copyrightStatements,
                transitionEffect: 'resize'
    		});
    
    		function zoomEnd(event){
                    if (zoompopup != undefined) {
                        zoompopup.hide();
                    }
                    checkBoundaries();
                }
        	
           function mouseMove(event){
	           	if (zoompopup != undefined) {
		           	var positionCursor = cursorposition.lastXy;
		       		if (positionCursor != null) {
	                        var currentX = positionCursor.x;
                   			var currentY = positionCursor.y;
	                        if (currentX >= 14 && currentX <= 36 && currentY >= 80 && currentY <= 152) {
	                    			// we want to keep the popup
                    		} else {
            					zoompopup.hide();
                    	    }
                	}
	        	}
        	}

      function windowMouseMove(evt) {
		
			if (evt.pageX) {
				cursorXp =  evt.pageX;
			} else if (evt.clientX){
				cursorXp = evt.clientX + (document.documentElement.scrollLeft ? document.documentElement.scrollLeft : document.body.scrollLeft);		
			}
		   if (evt.pageY){
				cursorYp = evt.pageY;
		   } else if (evt.clientY) {
				cursorYp = evt.clientY + (document.documentElement.scrollTop ? document.documentElement.scrollTop : document.body.scrollTop);   
			}	
		}	  
		    // Create a map with a listener that checks for zoom ends
		    map = new OpenLayers.Map("mappanel", {
		        eventListeners: {
		            "zoomend": zoomEnd, 
		            "mousemove": mouseMove
		        }
		    });

		    // Set the options on the map
		    map.setOptions(options);
    
		    // Set the WMS parameters  
		    var wmsParams = {
		        format: 'image/png'
		    };
   
		    // Set the WMS options
		    var wmsOptions = {
		        buffer: 0,
		        attribution: copyrightStatements
		    };
    
		    // Define the OS mapping layer
		    //gwcLayer = new OSInspire.Layer.WMS("INSPIRE", "http://46.137.172.224/geoserver/wms", wmsParams, wmsOptions);
    
		    // Boundaries
		    defBoundaryStyle = {
		        strokeColor: "black",
		        strokeOpacity: "0.7",
		        strokeWidth: 2,
		        fillColor: "white",
		        fillOpacity: 0.1,
		        cursor: "pointer"
		    };
    		styBoundary = OpenLayers.Util.applyDefaults(defBoundaryStyle, OpenLayers.Feature.Vector.style["default"]);
		    styleBoundaryMap = new OpenLayers.StyleMap({
		        'default': styBoundary,
		        'select': {
		            strokeColor: "black",
		            fillColor: "#FF7777"
		        }
		    });
		    
    		map.addLayers([tiled]); 
    		
		    // Remove default PanZoom bar; will use zoom slider below 
		    var ccControl = map.getControlsByClass("OpenLayers.Control.PanZoom");
		    map.removeControl(ccControl[0]);
    
		    // Add scale bar
		    map.addControl(new OpenLayers.Control.ScaleLine({
		        geodesic: true
		    }));
		    keyBoardDefaultControl = new OpenLayers.Control.KeyboardDefaults();
		    //keyboard navigation
                    map.addControl(keyBoardDefaultControl);   
                    // Navigation control to be used when admin area turned on
                    navigationControl = new OpenLayers.Control.Navigation({
                          zoomWheelEnabled: false,
                          documentDrag: true
                    });
                    map.addControl(navigationControl);
			
		    // Add mouse position. 
		    cursorposition = new OpenLayers.Control.MousePosition({
                        numdigits: 5,
                        formatOutput: formatLonlats
                    }); 
		    map.addControl(cursorposition);
		    map.setCenter(new OpenLayers.LonLat(-8.89754749, 54), 1);
    
		    // Set a flag for the Submit button
		    flag = 0;
    
		    // Create an AJAX object to be used for gazetteer and postcode searches
		    xmlhttp = new getXMLObject();
    
		    // Clear text flag
		    clrTxt = 1;

    Ext.override(Ext.dd.DragTracker, {
        onMouseMove: function (e, target) {
            if (this.active && Ext.isIE && !Ext.isIE9 && !e.browserEvent.button) {
                e.preventDefault();
                this.onMouseUp(e);
                return;
            }
            e.preventDefault();
            var xy = e.getXY(),
                s = this.startXY;
            this.lastXY = xy;
            if (!this.active) {
                if (Math.abs(s[0] - xy[0]) > this.tolerance || Math.abs(s[1] - xy[1]) > this.tolerance) {
                    this.triggerStart(e);
                } else {
                    return;
                }
            }
            this.fireEvent('mousemove', this, e);
            this.onDrag(e);
            this.fireEvent('drag', this, e);
        }
    });

    // Create a map panel with zoom slider   
    mapPanel = new GeoExt.MapPanel({
        renderTo: "mappanel",
        height: 435,
        width: 935,
        map: map,
        center: new OpenLayers.LonLat(-8.89754749, 54),
        zoom: 1,
        // Zoom slider       
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
                template: "Zoom level: {zoom}<br>Scale: 1 : {scale}",
                minWidth: 120
            }),
            // Do nothing on any keypress, Map widget is listening to it
            onKeyDown: function (e) {}
        }]
    });
}



function formatLonlats(lonLat) {
	var lat = lonLat.lat;
	var long = lonLat.lon;
	var digits = parseInt(this.numdigits);
	var ns = OpenLayers.Util.getFormattedLonLat(lat);
	var ew = OpenLayers.Util.getFormattedLonLat(long,'lon');
	return ns + this.separator + ew + ' (' + (lat.toFixed(digits)) + this.separator + (long.toFixed(digits)) + ')';
}      
// Clear search box when clicked on 
function clearText(){
    if (clrTxt == 1 || document.getElementById("searchArea").value == "Place name, postcode or coordinate") {
        document.getElementById("searchArea").value = "";
    }
	keyBoardDefaultControl.deactivate();
}
function activateKeyboardDefault(){	
	keyBoardDefaultControl.activate();
}	
// Process the Search query
function processQuery(){
    // Hide and clear list box
    var thedropdown = document.getElementById('selectGaz');
    thedropdown.style.display = 'none';
    da = document.getElementById("selectGaz");
    da.options.length = 0;
    locationFound = 0;
    
    // Clear menu if already populated
    da.options.length = 0;
    sectorFlag = 0;
    
    var query = document.getElementById("searchArea");
    queryOriginal = query.value;
    queryText = query.value;
    
    // Strip any leading or trailing whitespace characters
    queryText = queryText.replace(/^\s+/, '');
    queryText = queryText.replace(/\s+$/, '');
    
    // If the query is empty, one character in length or contains the default text then inform  the user.
    if (queryText.length < 2 || queryText === 'Place name, postcode or coordinate') {
        alert('You must enter a valid place name, postcode or coordinate');
        document.getElementById("searchArea").value = "Place name, postcode or coordinate";
        return false;
    }
    
    // Check if latitude, longitude or latitude,longitude
    var commaReg = /,/
    var latRegex = /(^\+?([1-8])?\d(\.\d+)?$)|(^-90$)|(^-(([1-8])?\d(\.\d+)?$))/
    var longRegex = /(^\+?1[0-7]\d(\.\d+)?$)|(^\+?([1-9])?\d(\.\d+)?$)|(^-180$)|(^-1[1-7]\d(\.\d+)?$)|(^-[1-9]\d(\.\ d+)?$)|(^\-\d(\.\d+)?$)/
    
    if (commaReg.test(queryText)) {
        var coords = queryText.split(",");
        latStr = coords[0];
        longStr = coords[1].trim();
        
        if (longRegex.test(longStr) && latRegex.test(latStr)) {
            var longitude = parseFloat(longStr);
            var latitude = parseFloat(latStr);
            
            if (longitude < -30.00 || longitude > 3.50 || latitude < 48.00 || latitude > 64.00) {
                alert('Coordinate is outside of the searchable map bounds.');
                clrTxt = 0;
            } else {
                map.setCenter(new OpenLayers.LonLat(longitude, latitude), 4);
                clrTxt = 1;
            }
        } else {
            alert('Invalid Coordinate.');  
            clrTxt = 0;
        }
    }
    
    // Check if postcode
    else if (queryText === 'GIR 0AA' || /^[ABCDEFGHIJKLMNOPRSTUWYZ][ABCDEFGHKLMNOPQRSTUVWXY]? ?[0-9][ABCDEFGHJKSTUW]?[0-9]?[ABEHMNPRVWXY]?(?: *[0-9][ABDEFGHJLNPQRSTUWXYZ]{2})?$/i.test(queryText)) {
            // If old Girobank postcode is used, convert to Alliance & Leicester Commercial Bank  postcode
            if (queryText === 'GIR 0AA') {
                queryText = 'L30 4GB';
            }
            
            // Determine if postcode sector or full postcode
            if (queryText.length < 5) {
                sectorFlag = 1;
			}
            // Perform postcode lookup
            postcode(queryText);
    } else {
            // Perform gazetteer lookup
            gazetteer(queryText);
    }
}

function recordSelection(selObj) {
	lastSelection = selObj.selectedIndex;
}

function zoomToLastSel() {
    if (lastSelectedZoomLocation != undefined && lastZoomLevel != undefined) {
        map.setCenter(lastSelectedZoomLocation, lastZoomLevel);
    }
}

// Zoom to Gazetteer location
function zoomGazSel(selObj){

	// Prevent selection of categories, code for backward compatibility
	// as IEs < 8 dont support disabled attribute for options
	if ((globalGazCoords[selObj.selectedIndex - 1]) == null) {
          if (selObj[lastSelection] != undefined) {
            selObj[lastSelection].selected = true;
          }
          return;
	}	
    // If admin area is selected from dropdown, enable display admin area automatically
    if (globalGazTypes[selObj.selectedIndex - 1] == "BOUNDARY" || globalGazTypes[selObj.selectedIndex - 1] == "NORTHERN IRELAND DISTRICT") {
        if (!document.getElementById('boundaries').checked) {
            document.getElementById('boundaries').checked = true;
            checkBoundaries();
        }
    }
    // Coordinates
    var coords = globalGazCoords[selObj.selectedIndex - 1].split(" ");
    // Type/F_CODE
    var zoomLevel = globalGazZoomType[selObj.selectedIndex - 1];
    
    map.setCenter(new OpenLayers.LonLat(coords[0], coords[1]), zoomLevel);
    
    // Record last zoom levels
    lastZoomLevel = zoomLevel;
    lastSelectedZoomLocation = map.getCenter();

    // Clear text field
    document.getElementById("searchArea").value = "Place name, postcode or coordinate";
	selObj.focus();
}

// Get XML object (for Gazetteer and Postcode lookups)
function getXMLObject(){

    var xmlHttp = false;
    
    try {
        // Old Microsoft Browsers    
        xmlHttp = new ActiveXObject("Msxml2.XMLHTTP")
        browserFlag = "IE6";
    } catch (e) {
        try {
            // Microsoft IE 6.0+           
            xmlHttp = new ActiveXObject("Microsoft.XMLHTTP")
            browserFlag = "IE6+"
        } catch (e2) {
            // Return false if no browser acceps the XMLHTTP object           
            xmlHttp = false;
        }
    }
    if (!xmlHttp && typeof XMLHttpRequest != 'undefined') {
        //For Mozilla, Opera Browsers
        xmlHttp = new XMLHttpRequest();
        browserFlag = "notIE";
    }
    return xmlHttp;
}


// Call Gazetteer servlet
function gazetteer(queryText){
    if (xmlhttp) {
        var url = "search_proxy?t=gz&q=" + queryText;
        xmlhttp.open("GET", url, true);
        xmlhttp.onreadystatechange = handleGazServerResponse;
        xmlhttp.send(null);
    }
}

// Handle response from Gazetteer servlet
function handleGazServerResponse(){
    // if not ready, don't do anything
    if (xmlhttp.readyState != 4) {
        return;
    }
    
    // if the request was aborted, don't do anything
    if (xmlhttp.status == 0) {
        return;
    }
    
    // if the request is not fully completed, pop up an error
    if (xmlhttp.status != 200) {
        alert('Error calling the Gazetteer service. Please try again.');
        return;
    }
    
    var gazTxt = xmlhttp.responseText;
    try {
        gazInfo(gazTxt);
    } 
    catch (e) {
        setText();
    }
    
}

// Process Gazetteer response
function gazInfo(gazTxt){
    globalGazCoords = new Array();
    globalGazZoomType = new Array();
    globalGazTypes = new Array();

    var gazXml = (new DOMParser()).parseFromString(gazTxt, "text/xml");
    var gazEntries = gazXml.getElementsByTagName("GazetteerItemVO");
    
    /**
     // If one match found
     if (gazEntries.length == 1) {
     
     var point = gazXml.getElementsByTagName("point")[0];
     var coords = point.firstChild.data.split(" ");
     var type = type.firstChild.data;
     map.setCenter(new OpenLayers.LonLat(coords[0], coords[1]), 4);
     locationFound = 1;
     
     }
     **/
    // Create a list box
    lrTypeBuffer = "";
    numberHeaders = 0;
    var gazEntries_length = gazEntries.length;
    if (gazEntries_length >= 1) {
        locationFound = 1;
        o = new Option();
        o.text = "Select place name from list";
        da.options[da.options.length] = o;
        
        // Build list box
        for (var i = 0; i < gazEntries_length; i++) {
            var name = gazEntries[i].getElementsByTagName("name");
            var county = gazEntries[i].getElementsByTagName("county");
            var point = gazEntries[i].getElementsByTagName("point");
            var type = gazEntries[i].getElementsByTagName("type");
            var zoomtype = gazEntries[i].getElementsByTagName("zoomtype");
            
            // Adding a title for each group 
            lrType = type[0].firstChild.data;
            if (lrTypeBuffer == "" || lrTypeBuffer.substring(0,lrTypeBuffer.length - 1) != lrType.substring(0,lrTypeBuffer.length - 1)) {
                lrTypeBuffer = lrType;
                o = new Option();
                o.style.color = 'blue';
                o.style.fontWeight = 'bold';
                o.text = '---';
                if (lrTypeBuffer == "BOUNDARY") {
                    o.text = o.text + "Great Britain Administrative Area";
                }
                if (lrTypeBuffer == "NORTHERN IRELAND DISTRICT") {
                    o.text = o.text + "Northern Ireland District";
                }
                if (lrTypeBuffer == "CITY") {
                    o.text = o.text + "City";
                }
                if (lrTypeBuffer == "TOWN") {
                    o.text = o.text + "Town";
                }
                if (lrTypeBuffer == "ANTIQUITY") {
                    o.text = o.text + "Antiquity";
                }
                if (lrTypeBuffer == "FOREST") {
                    o.text = o.text + "Forest";
                }
                if (lrTypeBuffer == "HILL") {
                    o.text = o.text + "Hill";
                }
                if (lrTypeBuffer == "WATER") {
                    o.text = o.text + "Water";
                }
                if (lrTypeBuffer == "FARM") {
                    o.text = o.text + "Farm";
                }
                if (lrTypeBuffer == "ROMAN") {
                    o.text = o.text + "Roman";
                }
                if (lrTypeBuffer == "OTHER") {
                    o.text = o.text + "Other";
                }
                if (lrTypeBuffer == "UNKNOWN") {
                    o.text = o.text + "Unknown";
                }
                if (lrTypeBuffer == "MARITIME2" || lrTypeBuffer == "MARITIME3" || lrTypeBuffer == "MARITIME4" || lrTypeBuffer == "MARITIME5") {
                    o.text = o.text + "Marine";
                }				
                o.text = o.text + '---';
				o.disabled="disabled";
                da.options.add(o);
                numberHeaders = numberHeaders + 1;
            }
            // Adding an entity
            o = new Option();
            try {
                if (county[0].firstChild.data == "County") {
                    outputStr = name[0].firstChild.data;
                    o.text = outputStr.substr(0, 59);
                } else {
                    outputStr = name[0].firstChild.data + ", " + county[0].firstChild.data;
                    o.text = outputStr.substr(0, 59);
                }
            } catch (e) {
                // Handle the case for NI locations that are missing a county value
                outputStr = name[0].firstChild.data;
                o.text = outputStr.substr(0, 59);
            }
            
            da.options.add(o);
            
            // Populate coordinates and gazetteer type/F_CODE
            index = i + numberHeaders;
            globalGazCoords[index] = point[0].firstChild.data;
            globalGazZoomType[index] = zoomtype[0].firstChild.data;
            globalGazTypes[index] = lrType;
        }
        
        // Make list box visible
        document.getElementById('selectGaz').style.display = 'block';
        clrTxt = 1;
    }
    if (locationFound == 0) {
        alert('Location not found.');
        clrTxt = 0;
        
    }
    lastSelectedZoomLocation = null;
    lastZoomLevel = null;
}

// Call Postcode servlet
function postcode(queryText){

    if (xmlhttp) {
    
        var url = "search_proxy?t=pc&q=" + queryText;
        
        xmlhttp.open("GET", url, true);
        xmlhttp.onreadystatechange = handlePostcodeServerResponse;
        xmlhttp.send(null);
        
    }
    
}

// Handle response from Postcode servlet
function handlePostcodeServerResponse(){


    // if not ready, don't do anything
    if (xmlhttp.readyState != 4) {
        return;
    }
    
    // if the request was aborted, don't do anything
    if (xmlhttp.status == 0) {
        return;
    }
    
    // if the request is not fully completed, pop up an error
    if (xmlhttp.status != 200) {
        alert('Error calling the Postcode service. Please try  again.');
        return;
    }
    
    var gazTxt = xmlhttp.responseText;
    try {
        pcInfo(gazTxt);
    } catch (e) {
        setText();
    }
    
}

// Process Postcode response
function pcInfo(gazTxt){

    // globalGazCoords = new Array();
    
    var gazXml = (new DOMParser()).parseFromString(gazTxt, "text/xml");
    
    var root = gazXml.documentElement;
    
   var gaz = gazXml.getElementsByTagName("CodePointItemVO");

    if (gaz.length == 0) {
        alert('Location not found.');
        clrTxt = 0;
        return;
    }

    var point = gazXml.getElementsByTagName("point")[0];
    var coords = point.firstChild.data.split(" ");

    if (coords[0] != "null" && coords[1] != "null") {
    
    
        // Set zoom level depending on sector or full postcode
        if (sectorFlag == 0) {
            zoomLevel = 5;
        } else {
            zoomLevel = 4
        }
        
        map.setCenter(new OpenLayers.LonLat(coords[0], coords[1]), zoomLevel);
        
        clrTxt = 1;
        //		                   clearText();
        //                          setText();
        activateKeyboardDefault();
        
    } else {
    
        alert('Location not found.');
        clrTxt = 0;
        
        
    }
    
}


// Draw Search Box 
function drawBoundingBox(){
	// Deactivate boundaries hovering
	if (selectHover != undefined) {
            selectHover.deactivate();
            if (boundarypopup != undefined) {
            	boundarypopup.hide();
    		}
    }
    if (drawMode) {
        return;
    }
    drawMode = true;

    if (boxLayer === null) {
        var style = {
            strokeColor: "red",
            strokeWidth: 2,
            fillColor: "white"
        };
        var styleMapConfig = {
            "default": Ext.apply(Ext.apply({}, style), {
                fillOpacity: 0.0
            }),
            "temporary": Ext.apply(Ext.apply({}, style), {
                fillOpacity: 0.5
            })
        };
        boxLayer = new OpenLayers.Layer.Vector("Box layer", {
            styleMap: new OpenLayers.StyleMap(styleMapConfig),
            eventListeners: {
                "sketchcomplete": function (evt) {
                    boxLayer.destroyFeatures();
                }
            }
        });

        map.addLayer(boxLayer);
    }
    if (drawBoxControl === null) {
        drawBoxControl = new OpenLayers.Control.DrawFeature(boxLayer, OpenLayers.Handler.RegularPolygon, {
            handlerOptions: {
                sides: 4,
                irregular: true
            },
            eventListeners: {
                "featureadded": function (evt) {
                    drawMode = false;
                    // Set a flag for the Submit button
                    submitFlag = 1;
                    var bounds = evt.feature.geometry.getBounds();
                    // Get longitude and latitude of the lower left and upper right of the box
                    ll = new OpenLayers.Pixel(bounds.left, bounds.bottom);
                    ur = new OpenLayers.Pixel(bounds.right, bounds.top);
                    evt.object.deactivate();
                    // Reactivate boundaries hovering
                    if (selectHover != undefined) {
                        selectHover.activate();
                    }
                }
            }
        });
        map.addControl(drawBoxControl);
    }

    drawBoxControl.activate();
}
// Clear the bounding box
function clearBoundingBox() {
    drawBoxControl.deactivate();
    boxLayer.destroyFeatures();
    // Set a flag for the Submit button
    submitFlag = 0;
}

function isBoundingBoxDrawn() {
    if (ll == undefined || ur == undefined) {
        return false;
    }
    var wblon = ll.x.toFixed(2);
    var eblon = ur.x.toFixed(2);
    var nblat = ur.y.toFixed(2);
    var sblat = ll.y.toFixed(2);
    if (!isNaN(wblon) && !isNaN(eblon) && !isNaN(nblat) && !isNaN(sblat) && submitFlag == 1) {
        return true;
    }
    return false;
}

// Submit the bounding box	 
function submitBox(){
    if (!isBoundingBoxDrawn()) {
		alert('You must draw a bounding box before submitting.');
		return;
    }	
    // Prepare coordinates per UK Gemini 2.1 spec 
        var wblon = ll.x.toFixed(2);
        var eblon = ur.x.toFixed(2);
        var nblat = ur.y.toFixed(2);
        var sblat = ll.y.toFixed(2);
        
        if (wblon < -30.00 || eblon > 3.50 || sblat < 48.00 || nblat > 64.00) {
          alert('Coordinates are outside of the searchable map  bounds.');   
        } else {
        
            // UK Gemini2.1 variables to be passed to CKAN
            var bBox = new Array(wblon, eblon, nblat, sblat);
            
            /*
           
             //TEST: Display coordinates of bounding box in popup
            
             alert("   *** Submit Test ***" +
            
             "\n\nWest Bounding Longitude: " +
            
             bBox[0] +
            
             "\nEast Bounding Longitude:  " +
            
             bBox[1] +
            
             "\nNorth Bounding Latitude:  " +
            
             bBox[2] +
            
             "\nSouth Bounding Latitude:  " +
            
             bBox[3] +
            
             "\n\nProjection: " +
            
             map.getProjectionObject(), '');
            
             */

            // We replace any existing co-ords in the search url, then 
            // append the ones that have been selected.
            if (window.location.href.indexOf('?') != -1) {
              var pageUrlBase = window.location.href.slice(0, window.location.href.indexOf('?'));
              var existingParams = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
              if (existingParams.toString() == "") {
                existingParams = [];
              }
            } else {
              var pageUrlBase = window.location.href;
              var existingParams = [];
            }
            var params = [];
            // extract existing params and remove any existing bbox ones
            for(var i = 0; i < existingParams.length; i++) {
                param = existingParams[i].split('=');
                if (param[0].match(/^ext_bbox$/) == null) {
                  params.push(param[0] + '=' + param[1]);
                }
              }
            // add new bounding box to params
            // bBox is in order: w e n s
            // ext_bbox needs it in order: minx,miny,maxx,maxy = w s e n
            params.push('ext_bbox'+'='+bBox[0]+','+bBox[3]+','+bBox[1]+','+bBox[2]);

            // Assemble full pageUrl
            var pageUrl = pageUrlBase + '?';
            pageUrl = pageUrl + params.join('&')
            pageUrl = pageUrl.replace('/data/map-based-search','/data/search');
            window.location = pageUrl;
        }
}

$.extend({
  getUrlParams: function(ignore_keys_regex){
    var vars = [], param;
    var params = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < params.length; i++)
    {
      param = params[i].split('=');
      if (params[0].match(ignore_keys_regex) != null) {
        vars[hash[0]](hash[0]);
      }
    }
    return vars;
  }
});

function boundaryLoadstart() {	
	//setTimeout("document.body.style.cursor = 'wait'", 10);
  if (useVMLRenderer && (!(IEWarned))) {
    IEWarned = true;
    alert("A version of Internet Explorer older than IE9 has been detected. Administrative Areas will take some time to display in this browser, please be patient.");
  }
  document.body.style.cursor = 'wait';
  // var theCursor = 
  // document.layers ? document.cursor :
  // document.all ? document.all.cursor :
  // document.getElementById ? document.getElementById('cursor') : null;
  // theCursor='wait';
  //OpenLayers.Element.addClass(this, "olCursorWait"); 
}


function boundaryLoadend() {
	//alert(document.body.style.cursor);
	setTimeout("document.body.style.cursor = 'default'", 50);
	//document.body.style.cursor='default';
}


// Display/remove boundaries
function checkBoundaries() {
	if (boundaryLayer != null ) {
			removeBoundaries();
	}
    
    if (document.getElementById("boundaries").checked == false) {
    	if (boundarypopup != undefined) {
            	boundarypopup.hide();
    	}
  	} else {
		var VMLLayerArray = new Array("", "", "UK_Admin_Boundaries_3000m_4258", "UK_Admin_Boundaries_600m_4258", "UK_Admin_Boundaries_250m_4258", "UK_Admin_Boundaries_50m_4258");
		var CanvasLayerArray = new Array("", "", "UK_Admin_Boundaries_1500m_4258", "UK_Admin_Boundaries_250m_4258", "UK_Admin_Boundaries_50m_4258", "UK_Admin_Boundaries_5m_4258");
		var featureType;
	  	if (map.getZoom() == 5) {
                  if (boundaryLayer == undefined ) {
                    if (useVMLRenderer) {
                      featureType = VMLLayerArray[5];
                    } else {
                      featureType = CanvasLayerArray[5];
                    }
                    boundaryLayer = new OpenLayers.Layer.Vector("Boundaries", {
							projection: new OpenLayers.Projection("EPSG:4258"),
							strategies: [new OpenLayers.Strategy.BBOX()],
							protocol: new OpenLayers.Protocol.WFS({								
								version: "1.1.0",
								srsName: "EPSG:4258",
								url: "/geoserver/wfs",
								featureType: featureType, 
								featurePrefix: "inspire",
								featureNS: "http://ordnancesurvey.co.uk/spatialdb",
								outputFormat: "json",
								readFormat: new OpenLayers.Format.GeoJSON()
								}),									
								eventListeners: {
									"loadstart": boundaryLoadstart, 
									"loadend": boundaryLoadend
								},
								styleMap: styleBoundaryMap
								//,renderers: ["Canvas", "SVG", "VML"]
							});					
					map.addLayer(boundaryLayer);
					boundaryLayer.setVisibility(true);	            	
					boundaryHovering();
		   		}
		} else if (map.getZoom() == 4) {
        		if (boundaryLayer == undefined ) {
					if (useVMLRenderer) {
						featureType = VMLLayerArray[4];
					} else {
						featureType = CanvasLayerArray[4];
					}
					boundaryLayer = new OpenLayers.Layer.Vector("Boundaries", {
							projection: new OpenLayers.Projection("EPSG:4258"),
							strategies: [new OpenLayers.Strategy.BBOX()],
							protocol: new OpenLayers.Protocol.WFS({								
								version: "1.1.0",
								srsName: "EPSG:4258",
								url: "/geoserver/wfs",
								featureType: featureType, 
								featurePrefix: "inspire",
								featureNS: "http://ordnancesurvey.co.uk/spatialdb",
								outputFormat: "json",
								readFormat: new OpenLayers.Format.GeoJSON()
								}),									
								eventListeners: {
									"loadstart": boundaryLoadstart, 
									"loadend": boundaryLoadend
								},
								styleMap: styleBoundaryMap
								//,renderers: ["Canvas", "SVG", "VML"]
							});					
					map.addLayer(boundaryLayer);
					boundaryLayer.setVisibility(true);	            	
					boundaryHovering();
		   		}
		} else if (map.getZoom() == 3) {
        		if (boundaryLayer == undefined ) {
					if (useVMLRenderer) {
						featureType = VMLLayerArray[3];
					} else {
						featureType = CanvasLayerArray[3];
					}
					boundaryLayer = new OpenLayers.Layer.Vector("Boundaries", {
							projection: new OpenLayers.Projection("EPSG:4258"),
							strategies: [new OpenLayers.Strategy.BBOX()],
							protocol: new OpenLayers.Protocol.WFS({								
								version: "1.1.0",
								srsName: "EPSG:4258",
								url: "/geoserver/wfs",
								featureType: featureType, 
								featurePrefix: "inspire",
								featureNS: "http://ordnancesurvey.co.uk/spatialdb",
								outputFormat: "json",
								readFormat: new OpenLayers.Format.GeoJSON()
								}),									
								eventListeners: {
									"loadstart": boundaryLoadstart, 
									"loadend": boundaryLoadend
								},
								styleMap: styleBoundaryMap
								//,renderers: ["Canvas", "SVG", "VML"]
							});					
					map.addLayer(boundaryLayer);
					boundaryLayer.setVisibility(true);	            	
					boundaryHovering();
		   		}
		} else if (map.getZoom() == 2) {
			if (boundaryLayer == undefined ) {
				if (useVMLRenderer) {
					featureType = VMLLayerArray[2];
				} else {
					featureType = CanvasLayerArray[2];
				}
				boundaryLayer = new OpenLayers.Layer.Vector("Boundaries", {
						projection: new OpenLayers.Projection("EPSG:4258"),
						strategies: [new OpenLayers.Strategy.BBOX()],
						protocol: new OpenLayers.Protocol.WFS({								
							version: "1.1.0",
							srsName: "EPSG:4258",
							url: "/geoserver/wfs",
							featureType: featureType, 
							featurePrefix: "inspire",
							featureNS: "http://ordnancesurvey.co.uk/spatialdb",
							outputFormat: "json",
							readFormat: new OpenLayers.Format.GeoJSON()
							}),									
							eventListeners: {
								"loadstart": boundaryLoadstart, 
								"loadend": boundaryLoadend
							},
							styleMap: styleBoundaryMap
							//,renderers: ["Canvas", "SVG", "VML"]
						});					
				map.addLayer(boundaryLayer);
				boundaryLayer.setVisibility(true);	            	
				boundaryHovering();
			}
		} 
	}
        
    refreshMap();
}

// to remove boundaries
function removeBoundaries() {
	boundaryLayer.setVisibility(false);
	if (boundarypopup != undefined) {
          boundarypopup.hide();
    }
    boundaryLayer = undefined;
	map.removeControl(navigationControl);
}

function boundaryHovering() {
	var report = function(e){
		// Add navigation to re-enable panning
		map.addControl(navigationControl);
		
		var boundaryname = "" + e.feature.attributes.NAME;
		if (boundaryname.length != 0) {
			if (boundarynamebuffer == undefined || boundaryname != boundarynamebuffer) {
				// remove the previous popup
				if (boundarypopup != undefined) {
					boundarypopup.destroy();
				}
				
				// add a popup
				var positionCursor = cursorposition.lastXy;
				if (positionCursor != null || (cursorXp != null && cursorYp != null)) {
                                  var centroid = e.feature.geometry.getCentroid();

					// Removed (B) from the tooltip display
					var index = boundaryname.indexOf("(B)");
					if( index != -1){
						boundaryname = boundaryname.substring(0,index);
					}				
					boundarypopup = new OpenLayers.Popup("boundarypopup",
                                                                             //        e.feature.geometry.getBounds().getCenterLonLat(),                                                                        
                                                                             new OpenLayers.LonLat(centroid.x, centroid.y), new OpenLayers.Size(225, 5), "<b>" + boundaryname + "</b>", false);
					boundarypopup.autoSize = true;
					boundarypopup.panMapIfOutOfView = false;
					boundarypopup.keepInMap = false;
					boundarypopup.closeOnMove = true;
					boundarypopup.setBorder("2px solid black");
					boundarypopup.setOpacity(0.8);
					map.addPopup(boundarypopup);
					reportoffexecuted = false;
				}
				
				boundarynamebuffer = boundaryname;
			} else {
				if (reportoffexecuted) {
					if (boundarypopup != undefined) {
						boundarypopup.show();
					}
				}
			}
		}
	};
	
	var reportoff = function(e){
		// Add navigation to re-enable panning
		map.addControl(navigationControl);
		
		if (boundarypopup != undefined) {
            	boundarypopup.hide();
            	reportoffexecuted = true;
    	}
	};
	    
	// Hovering over the boundary will display the name of the boundary in the DIV
	selectHover = new OpenLayers.Control.SelectFeature(boundaryLayer, {
				hover: true,
				eventListeners: {
					featurehighlighted: report,
					featureunhighlighted: reportoff
				}
			});
	map.addControl(selectHover);
	selectHover.activate();
}

function refreshMap() {
	var currentCenter = map.getCenter();
	map.setCenter(currentCenter);
}

// Set the text in the Search text field
function setText(){
  if (document.getElementById("searchArea").value == "") {
    document.getElementById("searchArea").value = "Place name, postcode or coordinate";
  }
}

// Makes the Enter key press the Search button
function tabToEnter(e){

    var keynum;
    
    if (window.event) // IE
    {
        keynum = e.keyCode;
    } else if (e.which) // Netscape/Firefox/Opera
    {
        keynum = e.which;
    }
    else 
        if (e.which) // Netscape/Firefox/Opera
        {
            keynum = e.which;
        }
    
    if (keynum == 13) {
    
        document.getElementById("buttonID").focus();
    }
}

// Converts upper case words into words with only the first letter capitalised
function fixcase(str){

    return str.replace(/(?:^\w|[A-Z]|\b\w)/g, function(letter, index){
        return index == 0 ? letter.toUpperCase() : letter.toLowerCase();
    });
    
}

// Bootstrap tooltip
$(function() {
  $('.htmltooltip').popover({
    placement: 'right'
      })
    });
