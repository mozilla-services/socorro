<?php defined('SYSPATH') or die('No direct script access.');

/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Socorro Crash Reporter
 *
 * The Initial Developer of the Original Code is
 * The Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2006
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Ryan Snyder <rsnyder@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

require_once(Kohana::find_file('libraries', 'bugzilla', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'Correlation', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

/**
 * Reports based on top crashing signatures
 */
class Topcrasher_Controller extends Controller {
    
    public $service = "";
    public $host = "";
    
    public $tcbInitParams = null;

    /**
     * Constructor
     */
    public function __construct()
    {
        parent::__construct();
        $this->topcrashers_model = new Topcrashers_Model();
        $this->bug_model = new Bug_Model;
    }

    /**
     * Handle empty version values in the methods below, and redirect accordingly.
     *
     * @param   string  The product name
     * @param   string  The method name
     * @return  void
     */
    private function _handleEmptyVersion($product, $method) {
        $product_version = $this->branch_model->getRecentProductVersion($product);
        if (empty($product_version)) {
	        // If no current major versions are found, grab any available version
            $product_versions = $this->branch_model->getCurrentProductVersionsByProduct($product);
            if (isset($product_versions[0])) {
                $product_version = array_shift($product_versions);
            }
        }

        $version = $product_version->version;
        $this->chooseVersion(
            array(
                'product' => $product,
                'version' => $version,
                'release' => null
            )
        );

        url::redirect('topcrasher/'.$method.'/'.$product.'/'.$version);
    }

    /**
     * Verify that the chosen version is valid given the current product.  If
     * not, throw a 404 error.
     *
     * @return void
     */
    private function _versionExists($version) {
        if (!$this->versionExists($version)) {
            Kohana::show_404();
        }
    }

    /**
     * Generates the index page.
     */
    public function index() {
        $products = $this->featured_versions;
        $product = null;

        if(empty($products)) {
            Kohana::show_404();
        }

        foreach($products as $individual) {
            if($individual->release == 'major') {
                $product = $individual;
            }
        }

        if(empty($product)) {
            $product = array_shift($products);
        }

        return url::redirect('/topcrasher/byversion/' . $product->product . '/' . $product->version);
    }

    /**
     * Display the top crashers by product & version.
     *
     * @param   string  The name of the product
     * @param   version The version  number for this product
     * @param   int     The number of days for which to display results
     * @param   string  The crash type to query by
     * @return  void
     */
    public function byversion($product=null, $version=null, $duration=null, $crash_type=null)
    {
        if(is_null($product)) {
          Kohana::show_404();
        }
        $this->navigationChooseVersion($product, $version);
        if (empty($version)) {
            $this->_handleEmptyVersion($product, 'byversion');
        } else {
            $this->_versionExists($version);
        }

        if (empty($duration)) {
            $duration = Kohana::config('products.duration');
        }
	$duration_url_path = array(Router::$controller, Router::$method, $product, $version);
    $platform_url_path = array(Router::$controller, "byos", $product, $version);

	$durations = Kohana::config('topcrashbysig.durations');

	$config = array();
	$credentials = Kohana::config('webserviceclient.basic_auth');
	if ($credentials) {
	    $config['basic_auth'] = $credentials;
	}
	$service = new Web_Service($config);

	$host = Kohana::config('webserviceclient.socorro_hostname');

	$cache_in_minutes = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60);
	$end_date = urlencode(date('Y-m-d\TH:i:s+0000', TimeUtil::roundOffByMinutes($cache_in_minutes)));
	// $dur is number of hours
	$dur = $duration * 24;
	$limit = Kohana::config('topcrashbysig.byversion_limit', 300);
	// lifetime in seconds
	$lifetime = $cache_in_minutes * 60;

	$crash_types = Kohana::config('topcrashbysig.crash_types');
	if (empty($crash_type) || !in_array($crash_type, $crash_types)) {
		$crash_type = Kohana::config('topcrashbysig.crash_types_default');
	}

	$p = urlencode($product);
	$v = urlencode($version);
        $resp = $service->get("${host}/crashes/signatures/product/${p}/version/${v}/crash_type/${crash_type}/to_date/${end_date}/duration/${dur}/limit/${limit}", 'json', $lifetime);
	if($resp) {
	    $this->topcrashers_model->ensureProperties($resp, array(
				     'start_date' => '',
				     'end_date' => '',
				     'totalPercentage' => 0,
				     'crashes' => array(),
				     'totalNumberOfCrashes' => 0), 'top crash sig overall');
	    $signatures = array();
	    $req_props = array(
                'signature' => '',
                'count' => 0,
                'win_count' => 0,
                'mac_count' => 0,
                'linux_count' => 0,
                'currentRank' => 0,
                'previousRank' => 0,
                'changeInRank' => 0,
                'percentOfTotal' => 0,
                'previousPercentOfTotal' => 0,
                'changeInPercentOfTotal' => 0,
                'versions' => '',
                'versions_count' => '',
                'first_report' => '',
                'first_report_exact' => ''
            );

	    foreach($resp->crashes as $top_crasher) {
		$this->topcrashers_model->ensureProperties($top_crasher, $req_props, 'top crash sig trend crashes');

		if ($this->input->get('format') != "csv") {
                    //$top_crasher->{'missing_sig_param'} - optional param, used for formating url to /report/list
		    if (is_null($top_crasher->signature)) {
			$top_crasher->{'display_signature'} = Crash::$null_sig;
			$top_crasher->{'display_null_sig_help'} = TRUE;
		        $top_crasher->{'missing_sig_param'} = Crash::$null_sig_code;
		    } else if(empty($top_crasher->signature)) {
			$top_crasher->{'display_signature'} = Crash::$empty_sig;
			$top_crasher->{'display_null_sig_help'} = TRUE;
		        $top_crasher->{'missing_sig_param'} = Crash::$empty_sig_code;
		    } else {
			$top_crasher->{'display_signature'} = $top_crasher->signature;
			$top_crasher->{'display_null_sig_help'} = FALSE;
		    }

		    $top_crasher->{'display_percent'} = number_format($top_crasher->percentOfTotal * 100, 2) . "%";
		    $top_crasher->{'display_previous_percent'} = number_format($top_crasher->previousPercentOfTotal * 100, 2) . "%";
		    $top_crasher->{'display_change_percent'} = number_format($top_crasher->changeInPercentOfTotal * 100, 2) . "%";

		    array_push($signatures, $top_crasher->signature);

                    $top_crasher->{'correlation_os'} = Correlation::correlationOsName($top_crasher->win_count, $top_crasher->mac_count, $top_crasher->linux_count);
		}
		$top_crasher->trendClass = $this->topcrashers_model->addTrendClass($top_crasher->changeInRank);
            }
	    $signature_to_bugzilla = $this->bug_model->bugsForSignatures(
                                         array_unique($signatures),
                                         Kohana::config('codebases.bugTrackingUrl')
                                     );

	    if ($this->input->get('format') == "csv") {
		$this->setViewData(array('top_crashers' => $this->_csvFormatArray($resp->crashes)));
		$this->renderCSV("${product}_${version}_" . date("Y-m-d"));
	    } else {
            $this->setViewData(array(
                'resp'           => $resp,
                'duration_url'   => url::site(implode($duration_url_path, '/') . '/'),
                'last_updated'   => $resp->end_date,
                'duration'       => $duration,
                'durations'      => $durations,
                'percentTotal'   => $resp->totalPercentage,
                'product'        => $product,
                'version'        => $version,
                'platforms'      => Kohana::config('platforms.platforms'),
                'nav_selection'  => 'top_crashes',
                'sig2bugs'       => $signature_to_bugzilla,
                'start'          => $resp->start_date,
                'end_date'       => $resp->end_date,
                'crash_types'    => $crash_types,
                'crash_type'     => $crash_type,
                'crash_type_url' => url::site(implode($duration_url_path, '/') . '/' . $duration . '/'),
                'platform_url'   => url::site(implode($platform_url_path, '/') . '/'),
                'range_unit'     => 'days',
                'range_value'    => $duration,
                'top_crashers'   => $resp->crashes,
                'total_crashes'  => $resp->totalNumberOfCrashes,
                'url_nav'        => url::site('products/'.$product),
            ));
	    }
	} else {
	    header("Data access error", TRUE, 500);
	    $this->setViewData(
	        array(
           	       'nav_selection' => 'top_crashes',
                   'product'        => $product,
                   'url_nav'        => url::site('products/'.$product),
				   'version'      => $version,
				   'resp'         => $resp
			    )
            );
	     }
    }
    
    public function setupWebservice() {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $this->service = new Web_Service($config);
        $this->host = Kohana::config('webserviceclient.socorro_hostname');
    }
    
    /**
     * Raises a HTTP 500 error and populates view with response
     * @param string current selected product
     * @param string current selected version
     * @param object the response object
     * @return void
     */
    private function raise500Error($product=null, $version=null, $resp=null) {
        header("Data access error", TRUE, 500);
            $this->setViewData(
            array(
                'nav_selection' => 'top_crashes',
                'product'       => $product,
                'url_nav'       => url::site('products/'.$product),
                'version'       => $version,
                'resp'          => $resp
            )
        );
    }
    
    /**
     * Returns the correct UI string for the provided OS
     * 
     * @param string    operating system name
     * @return string   correctly formatted OS string
     */
    private function getOSDisplayName($os) 
    {
        $formattedOS = "";
        
        if(stripos($os, "win") !== false) {
            $formattedOS = Kohana::config('platforms.win_name');
        } else if(stripos($os, "mac") !== false) {
            $formattedOS = Kohana::config('platforms.mac_name');
        } else if(stripos($os, "lin") !== false) {
            $formattedOS = Kohana::config('platforms.lin_name');
        } else {
            $formattedOS = "Unsupported OS Name.";
        }
        
        return $formattedOS;
    }
    
    /**
     * @param   string  The name of the product
     * @param   version The version  number for this product
     * @param   string  The operating system
     * @param   int     The number of days for which to display results
     * @param   string  The crash type to query by
     * @return  object  Contains parameters needed by individual top crasher functions
     */
    public function initTopCrasher($product=null, $version=null, $os=null, $duration=null, $crash_type=null) 
    {
        if(is_null($product)) {
            Kohana::show_404();
        }

        $this->navigationChooseVersion($product, $version);
        if (empty($version)) {
            $this->_handleEmptyVersion($product, 'byversion');
        } else {
            $this->_versionExists($version);
        }
        
        $this->tcbInitParams->{'version'} = $version;

        /**
         * If no duration is specified, use the default from the configuration file
         */
        if (empty($duration)) {
            $duration = Kohana::config('products.duration');
        }

        $this->tcbInitParams->{'duration'} = $duration;

        $this->tcbInitParams->{'duration_url_path'} =  $this->tcbInitParams->{'platform_url_path'} = array(Router::$controller, Router::$method, $product, $version);
        $this->tcbInitParams->{'durations'} = Kohana::config('topcrashbysig.durations');

        $this->tcbInitParams->{'cache_in_minutes'} = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60);
        $this->tcbInitParams->{'end_date'} = urlencode(date('Y-m-d\TH:i:s+0000', TimeUtil::roundOffByMinutes($this->tcbInitParams->{'cache_in_minutes'})));
        // $dur is number of hours
        $this->tcbInitParams->{'dur'} = $duration * 24;
        $this->tcbInitParams->{'limit'} = Kohana::config('topcrashbysig.byversion_limit', 300);
        // lifetime in seconds
        $this->tcbInitParams->{'lifetime'} = $this->tcbInitParams->{'cache_in_minutes'} * 60;
  
        $this->tcbInitParams->{'crash_types'} = Kohana::config('topcrashbysig.crash_types');
        if (empty($crash_type) || !in_array($crash_type, $this->tcbInitParams->{'crash_types'})) {
            $crash_type = Kohana::config('topcrashbysig.crash_types_default');
        }
        
        $this->tcbInitParams->{'crash_type'} = $crash_type;

        $this->tcbInitParams->{'p'} = urlencode($product);
        $this->tcbInitParams->{'v'} = urlencode($version);
        
        $this->tcbInitParams->{'platforms'} = Kohana::config('platforms.platforms');
        $this->tcbInitParams->{'os_display_name'} = $this->getOSDisplayName($os);
        
        return $this->tcbInitParams;
    }

    /**
     * Display the top crashers by product and OS
     *
     * @param   string  The name of the product
     * @param   version The version  number for this product
     * @param   string  The operating system
     * @param   int     The number of days for which to display results
     * @param   string  The crash type to query by
     * @return  void
     */
    public function byos($product=null, $version=null, $os=null, $duration=null, $crash_type=null)
    {
        if(is_null($os)) {
            Kohana::show_404();
        }
        
        $params = $this->initTopCrasher($product, $version, $os, $duration, $crash_type);
        
        $this->setupWebservice();
        
        $resp = $this->service->get("$this->host/crashes/signatures/product/{$params->{'p'}}/version/{$params->{'v'}}/os/{$os}/crash_type/{$params->crash_type}/to_date/{$params->{'end_date'}}/duration/{$params->dur}/limit/{$params->limit}", 'json', $params->lifetime);
        
        if($resp) {
            $signatures = array();
            foreach($resp->crashes as $top_crasher) {
                
                if ($this->input->get('format') != "csv") {
                
                    if (is_null($top_crasher->signature)) {
                        $top_crasher->{'display_signature'} = Crash::$null_sig;
                        $top_crasher->{'display_null_sig_help'} = TRUE;
                        $top_crasher->{'missing_sig_param'} = Crash::$null_sig_code;
                    } else if(empty($top_crasher->signature)) {
                        $top_crasher->{'display_signature'} = Crash::$empty_sig;
                        $top_crasher->{'display_null_sig_help'} = TRUE;
                        $top_crasher->{'missing_sig_param'} = Crash::$empty_sig_code;
                    } else {
                        $top_crasher->{'display_full_signature'} = $top_crasher->signature;
                        $top_crasher->{'display_signature'} = substr($top_crasher->signature, 0, 80);
                        $top_crasher->{'display_null_sig_help'} = FALSE;
                    }
                    
                    $top_crasher->{'display_percent'} = number_format($top_crasher->percentOfTotal * 100, 2) . "%";
                    $top_crasher->{'display_previous_percent'} = number_format($top_crasher->previousPercentOfTotal * 100, 2) . "%";
                    $top_crasher->{'display_change_percent'} = number_format($top_crasher->changeInPercentOfTotal * 100, 2) . "%";
                    
                    array_push($signatures, $top_crasher->signature);
                    $top_crasher->{'correlation_os'} = Correlation::correlationOsName($top_crasher->win_count, $top_crasher->mac_count, $top_crasher->linux_count);
                    
                    $top_crasher->trendClass = $this->topcrashers_model->addTrendClass($top_crasher->changeInRank);
                }
            }
                
            $signature_to_bugzilla = $this->bug_model->bugsForSignatures(
                array_unique($signatures),
                Kohana::config('codebases.bugTrackingUrl')
            );
            
            $byverion_url_path = array(Router::$controller, "byversion", $product, $version);
            
            if ($this->input->get('format') == "csv") {
                $this->setViewData(array('top_crashers' => $this->_csvFormatArray($resp->crashes)));
                $this->renderCSV("${product}_${version}_" . date("Y-m-d"));
            } else {
                $this->setViewData(array(
                    'resp'           => $resp,
                    'product'        => $product,
                    'version'        => $params->version,
                    'os'             => $params->{'os_display_name'},
                    'platforms'      => $params->{'platforms'},
                    'top_crashers'   => $resp->crashes,
                    'crash_types'    => $params->crash_types,
                    'crash_type'     => $params->crash_type,
                    'duration'       => $params->{'duration'},
                    'durations'      => $params->{'durations'},
                    'byverion_url'   => url::site(implode($byverion_url_path, '/')),
                    'crash_type_url' => url::site(implode($params->{'duration_url_path'}, '/') . '/' . $os . '/' . $params->{'duration'} . '/'),
                    'duration_url'   => url::site(implode($params->{'duration_url_path'}, '/') . '/' . $os . '/'),
                    'platform_url'   => url::site(implode($params->{'platform_url_path'}, '/') . '/'),
                    'start_date'     => $resp->start_date,
                    'end_date'       => $resp->end_date,
                    'range_unit'     => 'days',
                    'range_value'    => $params->{'duration'},
                    'sig2bugs'       => $signature_to_bugzilla
                ));
            }
        } else {
            $this->raise500Error($product, $version, $resp);
        }
    }

    /**
     * AJAX request for grabbing crash history data to be plotted
     * @param string - the product
     * @param string - the version
     * @param string - the signature OR $null_sig TODO
	 * @param string	The start date by which to begin the plot
	 * @param string	The end date by which to end the plot
     * @return responds with JSON suitable for plotting
     */
    public function plot_signature($product, $version, $start_date, $end_date, $signature)
    {
	//Bug#532434 Kohana is escaping some characters with html entity encoding for security purposes
	$signature = html_entity_decode($signature);

	header('Content-Type: text/javascript');
	$this->auto_render = FALSE;

	$config = array();
	$credentials = Kohana::config('webserviceclient.basic_auth');
	if ($credentials) {
	    $config['basic_auth'] = $credentials;
	}
	$service = new Web_Service($config);

	$host = Kohana::config('webserviceclient.socorro_hostname');


	$cache_in_minutes = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60);

    $start_date = date('c', strtotime($start_date)); 
    $end_date = date('c', strtotime($end_date)); 
    $duration = TimeUtil::determineHourDifferential($start_date, $end_date); // Number of hours


	$start_date = urlencode($start_date);
	$end_date = urlencode($end_date);

	$limit = Kohana::config('topcrashbysig.byversion_limit', 300);
	$lifetime = $cache_in_minutes * 60; // Lifetime in seconds

	$p = urlencode($product);
	$v = urlencode($version);

	//Bug#534063
	if ($signature == Crash::$null_sig) {
	    $signature = Crash::$null_sig_api_value;
        } else if($signature == Crash::$empty_sig) {
	    $signature = Crash::$empty_sig_api_value;
        }
	$rsig = rawurlencode($signature); //NPSWF32.dll%400x136a29
	// Every 3 hours
        $resp = $service->get("${host}/topcrash/sig/trend/history/p/${p}/v/${v}/sig/${rsig}/end/${end_date}/duration/${duration}/steps/60", 'json', $lifetime);


	if($resp) {
	    $data = array('startDate' => $resp->{'start_date'},
			  'endDate'   => $resp->{'end_date'},
			  'signature' => $resp->signature,
		          'counts'    => array(),
			  'percents'  => array());
	    for ($i =0; $i < count($resp->signatureHistory); $i++) {

		$item = $resp->signatureHistory[$i];
		array_push($data['counts'], array(strtotime($item->date) * 1000, $item->count));
		array_push($data['percents'], array(strtotime($item->date) * 1000, $item->percentOfTotal * 100));
	    }
	    echo json_encode($data);
	} else {
	    echo json_encode(array('error' => 'There was an error loading the data'));
	}
    }

    /**
     * Helper method for formatting a topcrashers list of objects into data
     * suitable for CSV output
     * @param array of topCrashersBySignature object
     * @return array of strings
     * @see Topcrashers_Model
     */
    private function _csvFormatArray($topcrashers)
    {
        $csvData = array(array('Rank', 'Change In Rank', 'Percentage of All Crashes',
			       'Previous Percentage', 'Signature',
			       'Total', 'Win', 'Mac', 'Linux',
                   'Version Count', 'Versions'));
        $i = 0;
        foreach ($topcrashers as $crash) {
            $line = array();
            $sig = strtr($crash->signature, array(
                ',' => ' ',
                '\n' => ' ',
                '"' => '&quot;'
            ));
            array_push($line, $i);
            array_push($line, $crash->changeInRank);
            array_push($line, $crash->percentOfTotal);
            array_push($line, $crash->previousPercentOfTotal);
            array_push($line, $sig);
            array_push($line, $crash->count);
            array_push($line, $crash->win_count);
            array_push($line, $crash->mac_count);
            array_push($line, $crash->linux_count);
            array_push($line, $crash->versions_count);
            array_push($line, str_replace(",",";",$crash->versions));
            array_push($csvData, $line);
            $i++;
        }
      return $csvData;
    }

    /**
     * Helper method for formatting a topcrashers list of objects into data
     * suitable for CSV output
     * @param array of topCrashersBySignature object
     * @return array of strings
     * @see Topcrashers_Model
     */
    private function _csvFormatOldArray($topcrashers)
    {
        $csvData = array(array('Rank, Percentage of All Crashes, Signature, Total, Win, Linux, Mac'));
	$i = 0;
        foreach ($topcrashers as $crash) {
	    $line = array();
	    $sig = strtr($crash->signature, array(
                    ',' => ' ',
                    '\n' => ' ',
		    '"' => '&quot;'
            ));
	    array_push($line, $i);
	    array_push($line, $crash->percent);
	    array_push($line, $sig);
	    array_push($line, $crash->total);
	    array_push($line, $crash->win);
	    array_push($line, $crash->mac);
	    array_push($line, $crash->linux);
	    array_push($csvData, $line);
	    $i++;
	}
      return $csvData;
    }

    /**
     * Generates the report from a URI perspective.
     * URLs are truncated after the query string
     *
     * @param   string product name
     * @param   string version Example: 3.7a1pre
     * @return  null
     */
    public function byurl($product=null, $version=null) {
        if(is_null($product)) {
	        Kohana::show_404();
        }
        $this->navigationChooseVersion($product, $version);
        if (empty($version)) {
            $this->_handleEmptyVersion($product, 'byurl');
        } else {
            $this->_versionExists($version);
        }

        $by_url_model = new TopcrashersByUrl_Model();
        list($start_date, $end_date, $top_crashers) =
        $by_url_model->getTopCrashersByUrl($product, $version);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
            'beginning'     => $start_date,
            'ending_on'     => $end_date,
            'nav_selection' => 'top_url',
            'product'       => $product,
            'top_crashers'  => $top_crashers,
            'url_nav'       => url::site('products/'.$product),
            'version'       => $version,
        ));
    }

    /**
     * Generates the report from a domain name perspective
     *
     * @param string product name
     * @param string version Example: 3.7a1pre
     */
    public function bydomain($product=null, $version=null) {
        if(is_null($product)) {
            Kohana::show_404();
        }
        $this->navigationChooseVersion($product, $version);
        if (empty($version)) {
            $this->_handleEmptyVersion($product, 'bydomain');
        } else {
            $this->_versionExists($version);
        }

        $by_url_model = new TopcrashersByUrl_Model();
        list($start_date, $end_date, $top_crashers) =
	    $by_url_model->getTopCrashersByDomain($product, $version);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
            'beginning'     => $start_date,
            'ending_on'     => $end_date,
    	    'nav_selection' => 'top_domain',
            'product'       => $product,
            'top_crashers'  => $top_crashers,
            'url_nav'       => url::site('products/'.$product),
            'version'       => $version,
        ));
    }

    /**
     * List the top 100 (x) Alexa top site domains, ordered by site ranking, and
 	 * show the bugs that affect them.
     *
	 * @access 	public
     * @param 	string 	The product name (e.g. 'Firefox')
     * @param 	string 	The version (e.g. '3.7a1pre')
 	 * @return 	void
     */
    public function bytopsite($product=null, $version=null) {
        if(is_null($product)) {
            Kohana::show_404();
        }

        $this->navigationChooseVersion($product, $version);
         if (empty($version)) {
             $this->_handleEmptyVersion($product, 'bytopsite');
         } else {
             $this->_versionExists($version);
         }

         $by_url_model = new TopcrashersByUrl_Model();
         list($start_date, $end_date, $top_crashers) = $by_url_model->getTopCrashersByTopsiteRank($product, $version);

         cachecontrol::set(array(
             'expires' => time() + (60 * 60)
         ));

         $this->setViewData(array(
         	'beginning' 	=> $start_date,
             'ending_on' 	=> $end_date,
             'nav_selection' => 'top_topsite',
             'product'       => $product,
             'top_crashers'  => $top_crashers,
             'url_nav' => url::site('products/'.$product),
             'version'       => $version,
         ));
    }

    /**
     * AJAX GET method which returns last 2 weeks of
     * Aggregated crash signatures based on
     * signaturesforurl/{product}/{version}?url={url_encoded_url}&page={page}
     * product - Firefox
     * version - 3.0.3
     * url - http://www.youtube.com/watch
     * page - page offset, defaults to 1
     */
    public function signaturesforurl($product, $version){
      $url = urldecode( $_GET['url']);
      $page = 1;
      if( array_key_exists('page', $_GET)){
        $page = intval($_GET['page']);
      }

      header('Content-Type: text/javascript');
      $this->auto_render = false;
      $by_url_model =  new TopcrashersByUrl_Model();

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

      $signatures = $by_url_model->getSignaturesByUrl($product, $version, $url, $page);
      foreach($signatures as $signature) {
        $sig = $signature->signature;
        $signature->signature = urlencode($sig);
        $signature->label = htmlentities($sig);
      }

      echo json_encode($signatures);
    }

    /**
     * AJAX GET method which returns all urls under this domain
     * which have had crash reports in the last 2 weeks.
     * urlsfordomain/{product}/{version}?domain={url_encoded_domain}&page={page}
     * product - Firefox
     * version - 3.0.3
     * domain - www.youtube.com
     * page - page offset, defaults to 1
     */
    public function urlsfordomain($product, $version){
      $domain = urldecode( $_GET['domain']);
      $page = 1;
      if( array_key_exists('page', $_GET)){
        $page = intval($_GET['page']);
      }
      header('Content-Type: text/javascript');
      $this->auto_render = false;
      $by_url_model =  new TopcrashersByUrl_Model();

      cachecontrol::set(array(
          'expires' => time() + (60 * 60)
      ));

      echo json_encode($by_url_model->getUrlsByDomain($product, $version, $domain, $page));
    }
}
