<?php defined('SYSPATH') or die('No direct script access.');
/* **** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Socorro Crash Reporter
 *
 * The Initial Developer of the Original Code is
 * The Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2006
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK *****
 *
 */

/**
 * Handles GET queries to the Bugzilla REST API and caches
 * the result in the Kohana apps local cache.
 */
class Bugzilla_Model extends Model {

    /**
     *  Makes a rest api request against the bugzilla rest api provided in the
     *  config. If you need to make a request with compound methods, like bug
     *  history, combine the methods together before passing it to this method.
     *  If a method has no arguments, pass an empty array.
     *
     *  @param string query_string - query for the api
     *  @return array - json decoded array of the result, or an empty
     *                  array if there was any sort of problem
     */
    public function query_api($query_string) {
        $cache = Cache::instance();

        $bz_api_url = Kohana::config('bzapi.url');
        $bz_specific_cache_timeout = Kohana::config('bzapi.timeout');

        // add trailing slash, if needed
        if (substr($bz_api_url, -1) !== "/") $bz_api_url .= "/";
        if (!isset($bz_api_url)) { return array(); }

        // simple cache fallthrough
        $bug_info = $cache->get($query_string);
        if (! $bug_info) {
            $request = curl_init($bz_api_url . $query_string);
            curl_setopt($request,
                        CURLOPT_HTTPHEADER,
                        array(
                           "Accept: application/json",
                           "Content-Type: application/json"
                        ));
            curl_setopt($request, CURLOPT_RETURNTRANSFER, 1);
            curl_setopt($request, CURLOPT_FAILONERROR, true);
            $response = curl_exec($request);
            if (!$response) {
                Kohana::log('error', 'Problem connecting to Bugzilla: ' . curl_error($request));
            }
            curl_close($request);
            $bug_info = (strpos($response, "<pre>Page not found") !== 0) ? $response : "";
            $cache->set($query_string, $bug_info, NULL, $bz_specific_cache_timeout);
        }

        $decoded_bug_info = json_decode($bug_info, $assoc=True);
        $decoded_bug_info = ($decoded_bug_info === null) ? array() : $decoded_bug_info;

        array_walk_recursive(
            $decoded_bug_info,
            create_function(
                '&$value',
                '$value = htmlEntities($value, ENT_QUOTES);'
            )
        );

        return $decoded_bug_info;
    }
}
