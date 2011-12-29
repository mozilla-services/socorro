<?php defined('SYSPATH') or die('No direct script access.');

require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

class Crash_Trends_Controller extends Controller {

    public function __construct() {
        parent::__construct();
        $this->crash_trends_model = new Crash_Trends_Model();
    }
    
    /**
    * Public functions map to routes on the controller
    * http://<base-url>/NewReport/index/[product, version, ?'foo'='bar', etc]
    */
    public function index() {

    }
}
?>