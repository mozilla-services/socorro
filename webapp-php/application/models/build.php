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
            $apiData[] = $version;
        }

        if ($from_date)
        {
            $apiData[] = 'from_date';
            $apiData[] = $from_date;
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
