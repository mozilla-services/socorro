<?php
/**
 * This controller displays various static info about the Socorro system
 */
class About_Controller extends Controller {

   /**
    * In about:crashes a link to this page is created for throttled
    * crash reports.
    */
    public function throttling() {
        cachecontrol::set(array(
  	  'expires' => time() + (60 * 30) // 30 minutes
        ));
    }
}
