function ParamParser(){
	
    this.urls = new Array();
    this.eastBndLon = null;
    this.westBndLon = null;
    this.northBndLat = null;
    this.southBndLat = null;
 
    pairs = location.search.split("\?")[1].split("&");
    for (i in pairs) {
    
        keyval = pairs[i].split("=");

        if (keyval[0] == "easting" || keyval[0] == "e") 
            this.eastBndLon = parseFloat(keyval[1]);
        if (keyval[0] == "westing" || keyval[0] == "w") 
            this.westBndLon = parseFloat(keyval[1]);
        if (keyval[0] == "northing" || keyval[0] == "n") 
            this.northBndLat = parseFloat(keyval[1]);
        if (keyval[0] == "southing" || keyval[0] == "s") 
            this.southBndLat = parseFloat(keyval[1]);
        if (keyval[0] == "url" || keyval[0] == "u") 
            this.urls.push(decodeURIComponent(keyval[1]));
    }
	
    this.getBBox = function(){
        return {
            "eastBndLon": this.eastBndLon,
            "westBndLon": this.westBndLon,
            "northBndLat": this.northBndLat,
            "southBndLat": this.southBndLat
        }
    }
    this.getUrls = function(){
        return this.urls
    };
}

paramParser = new ParamParser();


