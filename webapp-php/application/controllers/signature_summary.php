<?php defined('SYSPATH') or die('No direct script access.');
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
        $d = array('signature' => '', 'range_value' => '7', 'range_unit' => 'days',);
        $params = $this->getRequestParameters($d);
        $signature = $params['signature'];
        $range_value = (int)$params['range_value'];
        $range_unit = $params['range_unit'];
        $end = date('Y-m-d');
        $start = date('Y-m-d', strtotime("Today - $range_value $range_unit"));

        $uptime = $this->summary_model->getUptimeCounts($signature, $start, $end);
        $products = $this->summary_model->getProductCounts($signature, $start, $end);
        $oses = $this->summary_model->getOSCounts($signature, $start, $end);

        $results = array();
        
        foreach($oses as $os) {
            $obj = new stdClass();
            $obj->os = $os->os_version_string;
            $obj->percentage = $os->report_percent;
            $obj->numberOfCrashes = $os->report_count;
            $results['percentageByOs'][] = $obj;
        }

        foreach($products as $product) {
            $obj = new stdClass();
            $obj->product = $product->product_name;
            $obj->version = $product->version_string;
            $obj->percentage = $product->report_percent;
            $obj->numberOfCrashes = $product->report_count;
            $results['productVersions'][] = $obj;
        }

        foreach ($uptime as $up) {
            $obj = new stdClass();
            $obj->range = $up->uptime_string;
            $obj->percentage = $up->report_percent;
            $obj->numberOfCrashes = $up->report_count;
            $results['uptimeRange'][] = $obj;
        }

        echo json_encode($results); exit; // We can halt processing here.
    }
}
