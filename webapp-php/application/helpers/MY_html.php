/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php defined('SYSPATH') or die('No direct script access.');
/**
 * HTML markup helpers.
 *
 */
class html extends html_Core {

    /**
     * Build a query string from a simple associative array.
     *
     * Implemented here because http_build_query() doesn't do the right thing
     * with multiple parameters and Kohana's html::query_string() is
     * deprecated.
     *
     * @param  array  Associative array to be converted into a query string.
     * @return string Constructed query string
     */
    public static function query_string($data) {
        $parts = array();

        foreach ($data as $name => $val) {
            if (!is_array($val)) {
                $val = array($val);
            }
            foreach ($val as $subval) {
		if(!empty($subval)) {
                    $parts[] = rawurlencode($name) . '=' . rawurlencode($subval);
		}
            }
        }

        return join('&', $parts);
    }

}
