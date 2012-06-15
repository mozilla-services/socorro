<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Handle all request to /dumps.
 *
 * @author 	Ryan Snyder <ryan@foodgeeks.com>
 */
class Dumps_Controller extends Controller
{

	/**
	* The root of the /dumps file calls, used to validate and return json datadumps.
	*
	* http://{site_name}/dumps/{file_name}.json
	*
	* @access 	public
	* @param 	string 	The $filename being requested
	* @return 	string 	The json filedump
	*/
	public function file($filename=null)
	{
        header("Content-Type: text/plain; charset=UTF-8");

		if (!empty($filename)) {
			$filename = 'dumps/' . $filename;
			if (file_exists($filename)) {
				$handle = fopen($filename, "r");
				echo fread($handle, filesize($filename));
				fclose($handle);
				exit;
			}
		}

        // If the file was not found, return a json 404 statement.
        header("HTTP/1.0 404 Not Found");
		echo json_encode(
            array(
			    'status' => '404',
			    'error' => 'File Not Found'
		    )
        );
		exit;
	}

}
