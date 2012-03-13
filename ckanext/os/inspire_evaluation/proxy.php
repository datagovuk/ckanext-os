<?php

header('Content-type: text/xml; charset=utf-8');

function validateUrl() {

	$wmsUrl = $_GET['url'];

	$str1="?";
	$str2="request=getcapabilities";
	$str3="request=getfeatureinfo";
	$str4="service=wms";

	$chk1 = strpos(strtolower($wmsUrl),$str1);
	$chk2 = strpos(strtolower($wmsUrl),$str2);
	$chk3 = strpos(strtolower($wmsUrl),$str3);
	$chk4 = strpos(strtolower($wmsUrl),$str4);

	if (($chk1 == true && $chk2 == true && $chk4 == true) || ($chk1 == true && $chk3 == true && $chk4 == true)) {

		return true;

	}
	else {

		return false;

	}

 }

if (validateUrl()){

	echo file_get_contents($_GET['url']);

}

?>