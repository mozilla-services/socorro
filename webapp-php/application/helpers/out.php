<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Template text encoding / escaping shortcuts helper.
 */
class out_Core
{
    /**
     * Escape a string for HTML inclusion.
     *
     * @param string content to escape
     * @return string HTML-encoded content
     */
    public static function H($s, $echo=TRUE) {
      $out = htmlentities($s, ENT_COMPAT, 'UTF-8');
        if ($echo) echo $out;
        else return $out;
    }

    /**
     * Encode a string for URL inclusion.
     *
     * @param string content to encode
     * @return string URL-encoded content
     */
    public static function U($s, $echo=TRUE) {
        $out = rawurlencode($s);
        if ($echo) echo $out;
        else return $out;
    }

    /**
     * JSON-encode a value
     *
     * @param mixed some data to be encoded
     * @return string JSON-encoded data
     */
    public static function JSON($s, $echo=TRUE) {
        $out = json_encode($s);
        if ($echo) echo $out;
        else return $out;
    }

}
