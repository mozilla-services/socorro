<?php defined('SYSPATH') OR die('No direct access allowed.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Provides access to the cached Bugzilla API model.
 * Intended as a means to make cached ajax calls.
 */
class Buginfo_Controller extends Controller {

    /**
     * Disables rendering because this is a non-visual controller
     */
    public function __construct() {
        parent::__construct();
        $this->auto_render = FALSE;
    }

    /**
     * Any call to this controller proxies to whatever bugzilla rest
     * api has been configured. Empty results are returned when there
     * is a bad url, or a bad configuration.
     */
    public function __call($method, $arguments) {
        $bzapi = new Bugzilla_Model;
        $options = array(
                       'id' => "",
                       'include_fields' => ""
                   );
        $result = $bzapi->query_api($method .  Router::$query_string);
        echo json_encode($result);
        exit;
    }
}
