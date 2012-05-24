<?php defined('SYSPATH') or die('No direct script access.');

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * This controller displays system status.
 */
class Status_Controller extends Controller {

    /**
     * Class constructor.
     *
     * @return void
     */
    public function __construct()
    {
        parent::__construct();
    }

    /**
     * Default status dashboard nagios can hit up for data.
     */
    public function index() {
        $server_status_model = new Server_Status_Model();
        $serverStats = $server_status_model->getStats();
        cachecontrol::set(array(
            'last-modified' => time(),
            'expires' => time() + (120) // 120 seconds
        ));

        $product = $this->chosen_version['product'];

        $this->setViewData(array(
            'server_stats'            => $serverStats['data'],
            'plotData'                => $serverStats['plotData'],
            'url_base'                => url::site('products/'.$product),
            'url_nav'                 => url::site('products/'.$product)
        ));
    }
}
