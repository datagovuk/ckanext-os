<?php

header('Content-type: text/xml; charset=utf-8');

// This function will always return true for the OS environment
// See getinfo.php_coi for the proxy that should be used by COI, where it should be renamed getinfo.php
function validateUrl() {

			return true;

	}

if (validateUrl()) {

echo file_get_contents($_GET['url']);

}
?>