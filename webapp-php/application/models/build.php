<?php defined('SYSPATH') or die('No direct script access.');

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));


/**
 * Model class for Nightly Builds.
 *
 * @package     SocorroUI
 * @subpackage  Models
 * @author      Ryan Snyder <rsnyder@mozilla.com>
 */
class Build_Model extends Model {

    /**
     * The Web Service class.
     */
    protected $service = null;

    /**
     * Class Constructor
     */
    public function __construct()
    {
        parent::__construct();

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }

        $this->service = new Web_Service($config);
    }

    /**
     * Get all of the nightly builds for a product for a specific time period.
     *
     * @access  public
     * @param   string  The product name
     * @param   int     The number of days to pull builds from; default 7 days
     * @return  array   An array of build objects
     */
    public function getBuildsByProduct ($product, $days=7)
    {
        $start_date = date('Y-m-d', (time() - ($days * 86400)));

        $uri = $this->buildURI($product, null, $start_date);
        $builds = $this->service->get($uri);

        if (!empty($builds))
        {
            return $builds;
        }
        return false;
    }

    /**
     * Get all of the nightly builds for a product / version for a specific time period.
     *
     * @access  public
     * @param   string  The product name
     * @param   string  The version name
     * @param   int     The number of days to pull builds from; default 7 days
     * @return  array   An array of build objects
     */
    public function getBuildsByProductAndVersion ($product, $version, $days = 7)
    {
        $start_date = date('Y-m-d', (time() - ($days * 86400)));

        $uri = $this->buildURI($product, $version, $start_date);
        $builds = $this->service->get($uri);

        if (!empty($builds))
        {
            return $builds;
        }
        return false;
    }

    /**
     * Build the URI to call to retrieve data about nightly builds.
     *
     * @access  private
     * @param   string  The product name
     * @param   string  The version name if any
     * @param   string  Retrieve builds from this date to now
     * @return  string  A URL to call
     */
    private function buildURI($product, $version = null, $from_date = null)
    {
        $separator = '/';
        $apiData = array(
            Kohana::config('webserviceclient.socorro_hostname'),
            'products/builds',
            'product',
            $product
        );

        if ($version)
        {
            $apiData[] = 'version';
            $apiData[] = rawurlencode($version);
        }

        if ($from_date)
        {
            $apiData[] = 'from_date';
            $apiData[] = rawurlencode($from_date);
        }

        $apiData[] = '';    // Trick to have the closing '/'

        return implode($separator, $apiData);
    }

    /**
     * Prepare the dates that will be used for build display.
     *
     * @param   string  The end date
     * @param   int     The number of dates to query
     * @return  array
     */
    public function prepareDates($date_end, $duration) {
        $dates = array();
        $date_diff = TimeUtil::determineDayDifferential($date_end, date('Y-m-d', mktime(0, 0, 0, date("m"), date("d"), date("Y"))));
        $timestamp = time();
        for($i = 0; $i <= $duration; $i++) {
            $date = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-($i+$date_diff), date("Y")));
            if (strtotime($date) <= $timestamp) {
                $dates[] = $date;
            }
        }
        return $dates;
    }

    /* */
}
