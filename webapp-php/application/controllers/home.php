<?php defined('SYSPATH') or die('No direct script access.');

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Handle the homepage and specific pages within the / root uri.
 */
class Home_Controller extends Controller
{

   /**
     * SocorroUI homepage is temporarily serving as a redirect to the
     * default product dashboard.
     */
    public function dashboard()
    {
        if (isset($this->chosen_version)) {
            $url = 'products/'.$this->chosen_version['product'];
        } else {
            $url = 'products/' . Kohana::config('products.default_product');
        }
        url::redirect($url);
    }

    /* */
}
