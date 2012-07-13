<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 *  Handler for redirects from missing dumps.
 */
class Missing_Dump_Controller extends Controller {

    public function index() {
        echo "The dump you requested is not (yet) available.";
        exit;
    }
}
