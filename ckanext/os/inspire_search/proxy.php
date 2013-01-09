<?php
// Set the IP Address below to that of the Inspire WMS server
$INSPIRE_IP_ADDRESS = 'searchandevalitereleased-1321625557.eu-west-1.elb.amazonaws.com';
$type = $_GET['t'];
if ($type == 'gz') {
    // Gazetteer service
    echo file_get_contents('http://' . $INSPIRE_IP_ADDRESS . '/InspireGaz/gazetteer?q=' . urlencode($_GET['q']));
} else if ($type == 'pc') {
    // Postcode service
    echo file_get_contents('http://' . $INSPIRE_IP_ADDRESS . '/InspireGaz/postcode?q=' . urlencode($_GET['q']));
} else {}
?>
