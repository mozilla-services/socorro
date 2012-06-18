<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

class Signature_Summary_Controller extends Controller {

    public function __construct()
    {
        parent::__construct();
        $this->summary_model = new Signature_Summary_Model();
    }

    public function index()
    {
        $d = array('signature' => '', 'range_value' => '7', 'range_unit' => 'days');
        $params = $this->getRequestParameters($d);
        $signature = $params['signature'];
        $duration = $params['duration'];
        if(!$signature) {
            Event::run('system.404');
        }

        $urlParams = array('signature' => $signature, 'range_value' => $range_value, 'range_unit' => $range_unit,);
        $this->setViewData(array(
            'signature' => $signature,
            'duration' => $duration,
            'data_url' => url::site('signature_summary/json_data') . '?' . html::query_string($urlParams),

        ));
    }

    public function json_data()
    {
        $d = array('signature' => '', 'range_value' => '7', 'range_unit' => 'days', 'version' => array(), 'date' => date('Y-m-d'));
        $params = $this->getRequestParameters($d);
        $signature = $params['signature'];
        $start = date('Y-m-d', strtotime($params['date'] .
                    " - {$params['range_value']} {$params['range_unit']}"));
        $end = date('Y-m-d', strtotime($params['date']));
        if(!empty($params['version'])) {
            $versions = $params['version'];
        } else {
            $versions = array();
        }

        $uptime = $this->summary_model->getSummary('uptime', $signature, $start, $end, $versions);
        $products = $this->summary_model->getSummary('products', $signature, $start, $end);
        $oses = $this->summary_model->getSummary('os', $signature, $start, $end, $versions);
        $processes = $this->summary_model->getSummary('process_type', $signature, $start, $end, $versions);
        $flashes = $this->summary_model->getSummary('flash_version', $signature, $start, $end, $versions);
        $architecture = $this->summary_model->getSummary('architecture', $signature, $start, $end, $versions);
        $results = array();

        foreach($architecture as $arch) {
            $obj = new stdClass();
            $obj->architecture = $arch->category;
            $obj->percentage = $arch->percentage*100;
            $obj->numberOfCrashes = $arch->report_count;
            $results['architectures'][] = $obj;
        }

        foreach($oses as $os) {
            $obj = new stdClass();
            $obj->os = $os->category;
            $obj->percentage = $os->percentage*100;
            $obj->numberOfCrashes = $os->report_count;
            $results['percentageByOs'][] = $obj;
        }

        foreach($products as $product) {
            $obj = new stdClass();
            $obj->product = $product->product_name;
            $obj->version = $product->version_string;
            $obj->percentage = $product->percentage;
            $obj->numberOfCrashes = $product->report_count;
            $results['productVersions'][] = $obj;
        }

        foreach ($uptime as $up) {
            $obj = new stdClass();
            $obj->range = $up->category;
            $obj->percentage = $up->percentage*100;
            $obj->numberOfCrashes = $up->report_count;
            $results['uptimeRange'][] = $obj;
        }

        foreach($processes as $process) {
            $obj = new stdClass();
            $obj->processType = $process->category;
            $obj->numberOfCrashes = $process->report_count;
            $obj->percentage = $process->percentage*100;
            $results['processTypes'] = $obj;
        }

        foreach($flashes as $flash) {
            $obj = new StdClass();
            $obj->flashVersion = $flash->category;
            $obj->numberOfCrashes = $flash->report_count;
            $obj->percentage = $flash->percentage*100;
            $results['flashVersions'][] = $obj;
        }


        echo json_encode($results); exit; // We can halt processing here.
    }
}
