<?php defined('SYSPATH') or die('No direct script access.');
/**
 *
 */
class Missing_Dump_Controller extends Controller {

    public function index() {

        echo "The dump you requested is not (yet) available.";
        exit;
    }

}
