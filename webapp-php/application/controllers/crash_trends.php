<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

class Crash_Trends_Controller extends Controller {

    public function __construct() {
        parent::__construct();
        $this->crash_trends_model = new Crash_Trends_Model();
        $this->branch_model = new Branch_Model();
    }

    /**
    * Public functions map to routes on the controller
    * http://<base-url>/NewReport/index/[product, version, ?'foo'='bar', etc]
    */
    public function index() {
        $d = array('product' => 'Firefox', 'version' => '', 'start_date' => '', 'end_date' => '');
        $params = $this->getRequestParameters($d);

        $params = $this->solveForDates($params);
        $params = $this->solveForVersion($params);

        $urlParams = array('product' => $params['product'],
                           'version' => $params['version'],
                           'start_date' => $params['start_date'],
                           'end_date' => $params['end_date']);

        $this->setViewData(array(
            'report_product' => $params['product'],
            'report_products' => $this->branch_model->getProducts(),
            'version' => $params['version'],
            'start_date' => $params['start_date'],
            'end_date' => $params['end_date'],
            'data_url' => url::site('crash_trends/json_data') . '?' . html::query_string($urlParams),

        ));
    }

    public function json_data() {
        $d = array('product' => 'Firefox', 'version' => '', 'start_date' => '', 'end_date' => '');
        $params = $this->getRequestParameters($d);

        $params = $this->solveForDates($params);
        $params = $this->solveForVersion($params);

        $values = $this->crash_trends_model->getCrashTrends($params['product'],
                                                            $params['version'],
                                                            $params['start_date'],
                                                            $params['end_date']);
                                                        
        $values = $values->crashtrends;
        
        
        if(empty($values)) {
            echo json_encode(array());
            exit;
        }

        $formatted = array();
        $initial_arr = array('0' => 0, '1' => 0, '2' => 0, '3' => 0, '4' => 0, '5' => 0, '6' => 0, '7' => 0, '8' => 0);
        foreach($values as $value)
        {
            if(!isset($formatted[$value->report_date])) {
                // Initialize a particular build date's data array
                $formatted[$value->report_date] = $initial_arr;
            }

            if($value->days_out >= 8) {
                $formatted[$value->report_date]['8'] += $value->report_count;
            } else {
                $formatted[$value->report_date][$value->days_out] += $value->report_count;
            }
        }
        ksort($formatted);
        echo json_encode($formatted); exit;
    }

    /** Returns JSON **/
    public function product_versions() {
        $d = array('product' => 'Firefox');
        $params = $this->getRequestParameters($d);
        $result = $this->branch_model->getProductVersionsByProduct($params['product']);
        $return = array();

        foreach($result as $version) {
            if($version->release == 'Nightly' ||
               $version->release == 'Aurora') {
                   $return[] = $version->version;
               }
        }

        echo json_encode($return);
        exit;
    }

    protected function solveForDates(array $params) {
        $dt = new DateTime('today');
        if(empty($params['end_date'])) {
            $params['end_date'] = $dt->format('Y-m-d');
        }

        if(empty($params['start_date'])) {
            $dt->modify('- 7 days');
            $params['start_date'] = $dt->format('Y-m-d');
        }

        return $params;
    }

    protected function solveForVersion(array $params) {
        if(empty($params['version'])) {
            $p = $this->branch_model->getRecentProductVersion($params['product'], 'Nightly');
            $params['version'] = $p->version;
        }

        return $params;
    }
}
?>
