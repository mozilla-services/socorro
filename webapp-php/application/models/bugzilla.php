<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
