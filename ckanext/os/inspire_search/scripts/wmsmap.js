// Name				: wmsmap.js 
// Description      : JavaScript file for the INSPIRE / UKLP search map widget  (searchmapwms.htm)
// Author			: Peter Cotroneo, Ordnance Survey
// Version			: 2.2.1.1

// ** Global variables **
var mapPanel, map, zoombar, cursorposition, zoompopup, boxes, rectangle, ll, ur, submitFlag, boundingBoxControl;
var inputStr, sectorFlag, globalGazZoomType, globalGazCoords, lastSelection, browserFlag, clrTxt, locationFound, o, da, xmlhttp;
var boundaryLayer, defBoundaryStyle, styBoundary, styleBoundaryMap, selectHover, boundarypopup, boundarynamebuffer, reportoffexecuted;
var alreadyrunflag = 0;
var cursorXp, cursorYp, navigationControl,keyBoardDefaultControl; 
var useVMLRenderer; 
var IEWarned = false;
InspirePanZoomBar.prototype = new OpenLayers.Control.PanZoomBar();
InspirePanZoomBar.prototype.constructor = InspirePanZoomBar;
InspirePanZoomBar.superclass = OpenLayers.Control.PanZoomBar.prototype;
function InspirePanZoomBar() {
   this.forceFixedZoomLevel = true;
}
InspirePanZoomBar.prototype.zoomBarDrag = function(evt) {
	if (zoompopup != undefined) {
            zoompopup.destroy();
    };
    
	var zoomLevel = this.map.zoom;
    var zoomLevelInitial = zoomLevel;
    
    var positionCursor = cursorposition.lastXy;
    var offsetX = 10;
    var positionLonLat = map.getLonLatFromPixel(new OpenLayers.Pixel(positionCursor.x + offsetX, positionCursor.y));
   	
    if(this.mouseDragStart != null){
        // Calculating the zoom level where the slider is
        this.div.style.cursor="";
        this.map.events.un({"mouseup":this.passEventToSlider,"mousemove":this.passEventToSlider,scope:this});
		var deltaY=this.zoomStart.y-evt.xy.y;
		if(!this.forceFixedZoomLevel&&this.map.fractionalZoom){
				zoomLevel+=deltaY/this.zoomStopHeight;
				zoomLevel=Math.min(Math.max(zoomLevel,0),this.map.getNumZoomLevels()-1);
		}else{
				zoomLevel+=Math.round(deltaY/this.zoomStopHeight);
		}
        // Updating the zoompopup as the slider moves
        if (zoomLevel <= 0) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(225,5),
                       "Scale: 1 : 15000000",
                       false);
        } else if (zoomLevel == 1) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(225,5),
                       "Scale: 1 : 10000000",
                       false);
        } else if (zoomLevel == 2) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(220,5),
                       "Scale: 1 : 5000000",
                       false);
        } else if (zoomLevel == 3) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(220,5),
                       "Scale: 1 : 1000000",
                       false);
        } else if (zoomLevel == 4) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(215,5),
                       "Scale: 1 : 250000",
                       false);
       } else if (zoomLevel >= 5) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(210,5),
                       "Scale: 1 : 75000",
                       false);
       }
        
        // Code for dragging the slider
        var deltaY=this.mouseDragStart.y-evt.xy.y;
		var offsets=OpenLayers.Util.pagePosition(this.zoombarDiv);
        if((evt.clientY-offsets[1])>0&&(evt.clientY-offsets[1])<parseInt(this.zoombarDiv.style.height)-2){
			var newTop=parseInt(this.slider.style.top)-deltaY;
			this.slider.style.top=newTop+"px";this.mouseDragStart=evt.xy.clone();
		}
		OpenLayers.Event.stop(evt);
	} else {
            if (zoomLevelInitial <= 0) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(225,5),
                       "Scale: 1 : 15000000",
                       false);
         	} else if (zoomLevelInitial == 1) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(225,5),
                       "Scale: 1 : 10000000",
                       false);
            } else if (zoomLevelInitial == 2) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(220,5),
                       "Scale: 1 : 5000000",
                       false);
            } else if (zoomLevelInitial == 3) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(220,5),
                       "Scale: 1 : 1000000",
                       false);
            } else if (zoomLevelInitial == 4) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(215,5),
                       "Scale: 1 : 250000",
                       false);
            } else if (zoomLevelInitial >= 5) {
                       zoompopup = new OpenLayers.Popup("zoompopup",
                       positionLonLat,
                       new OpenLayers.Size(210,5),
                       "Scale: 1 : 75000",
                       false);
            }
      }
      zoompopup.autoSize = true;
      zoompopup.setBorder("2px solid black");
      zoompopup.setOpacity(0.7);
      map.addPopup(zoompopup);
}

if (document.addEventListener) {
	// Firefox browsers
  	document.addEventListener("DOMContentLoaded", function() {alreadyrunflag=1; inspireinit()}, false);
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
  if (navigator.appName == 'Microsoft Internet Explorer')
  {
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
            document.getElementById("gazContainer").innerHTML = '<select name="select" id="selectGaz" onchange="zoomGazSel(this.form.select)" onfocus="recordSelection(this.form.select)"></select>';
}

function inspireinit() {
            setText();
            // To be used to keep track of Draw button press
			var browserName=navigator.appName; 
			if (browserName=="Microsoft Internet Explorer")
			{ 
				document.attachEvent("onmousemove",function(evt){windowMouseMove(evt)});
			}
			// Firefox and others
			else if(document.addEventListener){
				document.addEventListener("mousemove",function(evt){windowMouseMove(evt)},false);					
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
    
    		var gwcLayer;
    
    		OpenLayers.DOTS_PER_INCH = 90.71428571428572;
    
    		//var resolutions = [OpenLayers.Util.getResolutionFromScale(15000000, 'degrees'), OpenLayers.Util.getResolutionFromScale(10000000, 'degrees'), OpenLayers.Util.getResolutionFromScale(5000000, 'degrees'), OpenLayers.Util.getResolutionFromScale(1000000, 'degrees'), OpenLayers.Util.getResolutionFromScale(250000, 'degrees'), OpenLayers.Util.getResolutionFromScale(75000, 'degrees')];
    		
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
		    copyrightStatements = "Contains Ordnance Survey data (c) Crown copyright and database right  [2011] <br>" +
		    "Contains Royal Mail data (c) Royal Mail copyright and database right [2011]<br>" +
		    "Contains bathymetry data by GEBCO (c) Copyright [2011]<br>" +
		    "Contains data by Land & Property Services (Northern Ireland) (c) Crown copyright [2011]";
    
    		// setup tiled layer
    		tiled = new OpenLayers.Layer.WMS("Geoserver layers - Tiled", //"http://46.137.180.108:80/geoserver/wms", {
			"http://searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com/geoserver/gwc/service/wms", {
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
      function windowMouseMove(evt){
		
			if (evt.pageX) {
				cursorXp =  evt.pageX;
			}
			else if (evt.clientX){
				cursorXp = evt.clientX + (document.documentElement.scrollLeft ? document.documentElement.scrollLeft : document.body.scrollLeft);		
			}
		   if (evt.pageY){
				cursorYp = evt.pageY;
		   }
			else if (evt.clientY) {
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
		    gwcLayer = new OSInspire.Layer.WMS("INSPIRE", "http://searchAndEvalProdELB-2121314953.eu-west-1.elb.amazonaws.com/geoserver/wms", wmsParams, wmsOptions);
    
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
			navigationControl = new OpenLayers.Control.Navigation({zoomWheelEnabled:false});
			
		    // Add mouse position. 
		    cursorposition = new OpenLayers.Control.MousePosition({numdigits:5,formatOutput: formatLonlats}); 
		    map.addControl(cursorposition);
		    map.setCenter(new OpenLayers.LonLat(-3, 54),1);
    
		    // Set a flag for the Submit button
		    flag = 0;
    
		    // Create an AJAX object to be used for gazetteer and postcode searches
		    xmlhttp = new getXMLObject();
    
		    // Clear text flag
		    clrTxt = 1;

		    // Add a zoom bar
		    zoombar = new InspirePanZoomBar();
		    map.addControl(zoombar);
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
    if (clrTxt == 1) {
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
                alert('Coordinate is outside of the searchable  map bounds.');
            }
            else {
                map.setCenter(new OpenLayers.LonLat(longitude, latitude), 4);
            }
        }
        else {
            alert('Invalid Coordinate.');  
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
    }
    else {
            // Perform gazetteer lookup
            gazetteer(queryText);
    }
}
function recordSelection(selObj)
{
	lastSelection = selObj.selectedIndex;
}
// Zoom to Gazetteer location
function zoomGazSel(selObj){

	// Prevent selection of categories, code for backward compatibility
	// as IEs < 8 dont support disabled attribute for options
	if((globalGazCoords[selObj.selectedIndex - 1]) == null)
	{
	    selObj[lastSelection].selected=true;
		return;
	}	
    // Coordinates
    var coords = globalGazCoords[selObj.selectedIndex - 1].split(" ");
    // Type/F_CODE
    var zoomLevel = globalGazZoomType[selObj.selectedIndex - 1];
    
    map.setCenter(new OpenLayers.LonLat(coords[0], coords[1]), zoomLevel);
    
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
    } 
    catch (e) {
        try {
            // Microsoft IE 6.0+           
            xmlHttp = new ActiveXObject("Microsoft.XMLHTTP")
            browserFlag = "IE6+"
        } 
        catch (e2) {
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
        o = document.createElement("OPTION");
        o.text = "Select place name from list";
        da.options.add(o);
        
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
                o = document.createElement("OPTION");
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
            o = document.createElement("OPTION");
            try {
                if (county[0].firstChild.data == "County") {
                    o.text = name[0].firstChild.data;
                }
                else {
                    o.text = name[0].firstChild.data + ", " + county[0].firstChild.data;
                }
            } 
            catch (e) {
                // Handle the case for NI locations that are missing a county value
                o.text = name[0].firstChild.data;
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
    } 
    catch (e) {
        setText();
    }
    
}

// Process Postcode response
function pcInfo(gazTxt){

    // globalGazCoords = new Array();
    
    var gazXml = (new DOMParser()).parseFromString(gazTxt, "text/xml");
    
    var root = gazXml.documentElement;
    
    var coords = point.firstChild.data.split(" ");
    
    if (coords[0] != "null" && coords[1] != "null") {
    
    
        // Set zoom level depending on sector or full postcode
        if (sectorFlag == 0) {
            zoomLevel = 5;
        }
        else {
            zoomLevel = 4
        }
        
        map.setCenter(new OpenLayers.LonLat(coords[0], coords[1]), zoomLevel);
        
        clrTxt = 1;
        setText();
        
    }
    else {
    
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
    };
	
    // Create a bounding box control
    boundingBoxControl = new OpenLayers.Control();
    OpenLayers.Util.extend(boundingBoxControl, {
        draw: function(){
            this.box = new OpenLayers.Handler.Box(boundingBoxControl, {
                "done": this.notice
            }, {
                keyMask: OpenLayers.Handler.MOD_NONE
            });
            this.box.activate();
            
        },
        
        notice: function(bounds){
            // Remove previous bounding box, so we display only one at a time		
            try {
                map.removeLayer(boxes);  
            } 
            catch (e) {
            }
            
            // Set a flag for the Submit button
            submitFlag = 1;
            
            // Get longitude and latitude of the lower left and upper right of the box
            ll = map.getLonLatFromViewPortPx(new OpenLayers.Pixel(bounds.left, bounds.bottom));
            ur = map.getLonLatFromViewPortPx(new OpenLayers.Pixel(bounds.right, bounds.top));
            
            
            // Draw the bounding box
            boxes = new OpenLayers.Layer.Boxes("Boxes");
            bounds = new OpenLayers.Bounds(ll.lon, ll.lat, ur.lon, ur.lat);
            var borderColor = "red";
            rectangle = new OpenLayers.Marker.Box(bounds, borderColor);
            boxes.addMarker(rectangle);
            
            map.addLayer(boxes);
            
            // Deactivate the control
            this.box.deactivate();
            
            // Reactivate boundaries hovering
            if (selectHover != undefined) {
            	selectHover.activate();
   			};
        }
    })
    
    // Add the bounding box control to the map
    map.addControl(boundingBoxControl);
}

// Clear the bounding box
function clearBoundingBox(){

    //  Dont need to add it again, theres a default one
    //map.addControl(new OpenLayers.Control.Navigation());
    
    try {
    
        map.removeLayer(boxes);
        
    } 
    catch (e) {
    
    }
    
    // Set a flag for the Submit button
    submitFlag = 0;
    
}

// Submit the bounding box	 
function submitBox(){

	if(ll == undefined || ur == undefined){
		alert('You must draw a bounding box before submitting.');
		return;
	}	
		// Prepare coordinates per UK Gemini 2.1 spec 
        var wblon = ll.lon.toFixed(2);
        var eblon = ur.lon.toFixed(2);
        var nblat = ur.lat.toFixed(2);
        var sblat = ll.lat.toFixed(2);
        
        if (wblon < -30.00 || eblon > 3.50 || sblat < 48.00 || nblat > 64.00) {
        
            alert('Coordinates are outside of the searchable map  bounds.');
            
        }
        else {
        
            // UK Gemini2.1 variables to be passed to CKAN
            var bBox = new Array(wblon, eblon, nblat, sblat);
            
            /**
           
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
            
             **/

            // We replace any existing co-ords in the search url, then 
            // append the ones that have been selected.
            // This is just a temporary measure pending getting proper 
            // geo-search faceting working.
            var pageUrlBase = window.location.href.slice(0, window.location.href.indexOf('?'));
            var existingParams = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
            var params = [];
            // extract existing params and remove any existing bbox ones
            for(var i = 0; i < existingParams.length; i++) {
                param = existingParams[i].split('=');
                if (param[0].match(/^bb[nsew]$/) == null) {
                  params.push(param[0] + '=' + param[1]);
                }
              }
            //pageUrl = pageUrl.replace('[&?]bb[nsew]=(-)?\d*\.\d*');
            //pageUrl.replace(/[&?]bb[eswn]=-?\d*\.\d*/g, '');
            // add new bounding box to params
            params.push('bbw'+'='+bBox[0]);
            params.push('bbe'+'='+bBox[1]);
            params.push('bbs'+'='+bBox[3]);
            params.push('bbn'+'='+bBox[2]);

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
  },
});

function boundaryLoadstart() {	
	//setTimeout("document.body.style.cursor = 'wait'", 10);
	if (useVMLRenderer && (!(IEWarned)))
	{
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
		var CanvasLayerArray = new Array("", "", "UK_Admin_Boundaries_1500m_4258", "UK_Admin_Boundaries_250m_4258", "UK_Admin_Boundaries_50m_4258", "uk_boundaries_withoutlondon_5m");
		var featureType;
	  	if (map.getZoom() == 5) {
        		if (boundaryLayer == undefined ) {
					if (useVMLRenderer)
					{
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
					if (useVMLRenderer)
					{
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
					if (useVMLRenderer)
					{
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
				if (useVMLRenderer)
				{
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
		if (boundaryname.length != 0)
		{
			if (boundarynamebuffer == undefined || boundaryname != boundarynamebuffer) {
				// remove the previous popup
				if (boundarypopup != undefined) {
					boundarypopup.destroy();
				}
				
				// add a popup
				var positionCursor = cursorposition.lastXy;
				if (positionCursor != null || (cursorXp != null && cursorYp != null)) {
					var offsetX = 10;
					// Only use cursorXp, cursorYp for the firsttime when positionCursor is null
					var x = positionCursor != null ? positionCursor.x :cursorXp-50;
					var y = positionCursor != null ? positionCursor.y :cursorYp-50;				
					var positionLonLat = map.getLonLatFromPixel(new OpenLayers.Pixel(x + offsetX, y));
					// Removed (B) from the tooltip display
					var index = boundaryname.indexOf("(B)");
					if( index != -1){
						boundaryname = boundaryname.substring(0,index);
					}				
					boundarypopup = new OpenLayers.Popup("boundarypopup",
										positionLonLat,
										new OpenLayers.Size(225,5),
										"<b>" + boundaryname + "</b>",
										false);
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
  if(document.getElementById("searchArea").value == ""){
    document.getElementById("searchArea").value = "Place name, postcode or coordinate";
  }
}

// Makes the Enter key press the Search button
function tabToEnter(e){

    var keynum;
    
    if (window.event) // IE
    {
        keynum = e.keyCode;
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


//Inline HTML Tooltip script: By JavaScript Kit: http://www.javascriptkit.com
//Created: July 10th, 08'

var htmltooltip={
  tipclass: 'htmltooltip',
  fadeeffect: [true, 200],
  anchors: [],
  tooltips: [], //array to contain references to all tooltip DIVs on the page

  positiontip:function($, tipindex, e){
    var anchor=this.anchors[tipindex]
    var tooltip=this.tooltips[tipindex]
    var scrollLeft=window.pageXOffset? window.pageXOffset : this.iebody.scrollLeft
    var scrollTop=window.pageYOffset? window.pageYOffset : this.iebody.scrollTop
    var docwidth=(window.innerWidth)? window.innerWidth-15 : htmltooltip.iebody.clientWidth-15
    var docheight=(window.innerHeight)? window.innerHeight-18 : htmltooltip.iebody.clientHeight-15
    var tipx=anchor.dimensions.offsetx
    var tipy=anchor.dimensions.offsety+anchor.dimensions.h
    tipx=(tipx+tooltip.dimensions.w-scrollLeft>docwidth)? tipx-tooltip.dimensions.w : tipx //account for right edge
    tipy=(tipy+tooltip.dimensions.h-scrollTop>docheight)? tipy-tooltip.dimensions.h-anchor.dimensions.h : tipy //account for bottom edge


    var winH = $(window).height();
    var winW = $(window).width();

    //Set the popup window to center
    var MapHeight = $(tooltip).height();
    var MapWidth = $(tooltip).width();
    if (MapHeight < 100 || MapWidth < 100) {
      MapHeight = -270;
      MapWidth = 550;
    }

    $(tooltip).css({
      left: winW/2-MapWidth/2,
      top: winH/2-MapHeight/2 - 160
    })
  },

  showtip:function($, tipindex, e){
    var tooltip=this.tooltips[tipindex]
    if (this.fadeeffect[0])
      $(tooltip).hide().fadeIn(this.fadeeffect[1])
    else
      $(tooltip).show()
  },

  hidetip:function($, tipindex, e){
    var tooltip=this.tooltips[tipindex]
    if (this.fadeeffect[0])
      $(tooltip).fadeOut(this.fadeeffect[1])
    else
      $(tooltip).hide()
  },

  updateanchordimensions:function($){
    var $anchors=$('a[rel="'+htmltooltip.tipclass+'"]')
    $anchors.each(function(index){
      this.dimensions={
        w:this.offsetWidth,
        h:this.offsetHeight,
        offsetx:$(this).offset().left,
        offsety:$(this).offset().top
        }
    })
  },

  render:function(){
    jQuery(document).ready(function($){
      htmltooltip.iebody=(document.compatMode && document.compatMode!="BackCompat")? document.documentElement : document.body;


      var $anchors=$('a[rel="' + htmltooltip.tipclass +'"]');

      //var $anchors=$('*[@rel="'+htmltooltip.tipclass+'"]');
      var $tooltips=$('div[class="'+htmltooltip.tipclass+'"]');
      $anchors.each(function(index){ //find all links with "title=htmltooltip" declaration
        this.dimensions={
          w:this.offsetWidth,
          h:this.offsetHeight,
          offsetx:$(this).offset().left,
          offsety:$(this).offset().top
          } //store anchor dimensions
        this.tippos=index+' pos' //store index of corresponding tooltip
        var tooltip=$tooltips.eq(index).get(0) //ref corresponding tooltip
        if (tooltip==null) //if no corresponding tooltip found
          return //exist
        tooltip.dimensions={
          w:tooltip.offsetWidth,
          h:tooltip.offsetHeight
          }
        $(tooltip).remove().appendTo('body') //add tooltip to end of BODY for easier positioning
        htmltooltip.tooltips.push(tooltip) //store reference to each tooltip
        htmltooltip.anchors.push(this) //store reference to each anchor
        var $anchor=$(this)
        $anchor.hover(
          function(e){ //onMouseover element
            htmltooltip.positiontip($, parseInt(this.tippos), e)
            htmltooltip.showtip($, parseInt(this.tippos), e)
          },
          function(e){ //onMouseout element
            htmltooltip.hidetip($, parseInt(this.tippos), e)
          }
          )
        $(window).bind("resize", function(){
          htmltooltip.updateanchordimensions($)
          })
      })
    })
  }
}

htmltooltip.render()
