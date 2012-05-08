<?php

header('Content-type: text/xml; charset=utf-8');

function validateUrl() {

			return true;

	}


if (validateUrl()) {

  $split_array = explode('?', $_GET['url']);

  //if valid url
  if (preg_match('|^http(s)?://[a-z0-9-]+(.[a-z0-9-]+)*(:[0-9]+)?(/.*)?$|i', $split_array[0])) {

    $variables = array();

    //if questionmark found then create an array of variables from string after question mark
    if (count($split_array) > 1){
      $variables = explode('&',strtolower($split_array[1]));
    }

    //remove duplicates
    $distinct_variables = array();
    foreach ($variables as $variable){
      $key_value = explode('=',$variable);
      if (count($key_value) > 1){
        $distinct_variables[$key_value[0]] = $key_value[1];
      }
    }

    //make sure that request and service variables are set
    if(!isset($distinct_variables['request'])){
      $distinct_variables['request'] = 'getcapabilities';
    }
    if(!isset($distinct_variables['service'])){
      $distinct_variables['service'] = 'wms';
    }

    //put key and value back together
    $variables = array();
    foreach ($distinct_variables as $key => $value){
      $variables[] = $key . '=' . $value;
    }

    //create properly formatted url
    $proper_url = $split_array[0] . '?' . implode('&',$variables);
    echo file_get_contents($proper_url);
  }
}

?>