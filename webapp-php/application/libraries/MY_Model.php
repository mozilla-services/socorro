<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Custon model base class.
 */
class Model extends Model_Core
{

    public function __construct()
    {
        parent::__construct();
        $this->cache = new Cache();
    }

    /**
     * Return a signature with encoded slashes and plusses, ready to be sent
     * to a middleware service.
     */
    public function encodeSignature($signature)
    {
        $signature = str_replace('/', '%2F', $signature);
        $signature = str_replace('+', '%2B', $signature);
        return $signature;
    }

    /**
     * Create the hash key that will be used to store the query in cache.
     *
     * @param string The $sql statement
     * @param  array Parameters to be escaped and bound in the SQL using Kohana Database query method.
     * @return string A query hash string
     */
    public function queryHashKey($sql, $binds=NULL)
    {
        if (is_array($binds))
        {
            $cache_key = 'query_hash_' . md5($sql . implode('_', $binds));
        }
        else
        {
            $cache_key = 'query_hash_' . md5($sql);
        }
        return $cache_key;
    }
}
