/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Custon model base class.
 */
class Model extends Model_Core {

	public function __construct() {
        parent::__construct();
        $this->cache = new Cache();
	}

    /**
     * Fetch all rows resulting from a query, exhausting the iterator.
     *
     * @param  string  SQL query to attempt
     * @param  boolean Whether or not to try caching the query results
     * @param  array Parameters to be escaped and bound in the SQL using Kohana Database query method.
     * @return array   Set of rows returned
     */
	public function fetchRows($sql, $do_cache=TRUE, $binds=NULL) {

        if ($do_cache) {
            $cache_key = $this->queryHashKey($sql, $binds);
            $data = $this->cache->get($cache_key);
            if ($data) {
                return $data;
            }
        }

        // The DB abstraction works on iterators, so slurp it all down.
	if (is_null($binds)) {
	    $result = $this->db->query($sql);
	} else {
	    $result = $this->db->query($sql, $binds);
	}

        $data = array();
        foreach ($result as $row) $data[] = $row;

        if ($do_cache && $data) {
            $this->cache->set($cache_key, $data);
        }

        return $data;
    }

    /**
     *
     * @param  string SQL query
     * @param  array Parameters to be escaped and bound in the SQL using Kohana Database query method.
     * @return array
     */
    public function fetchSingleColumn($sql, $col_name, $binds=NULL) {
	if (is_null($binds)) {
	    $result = $this->db->query($sql);
	} else {
	    $result = $this->db->query($sql, $binds);
	}

        $data = array();
        foreach ($result as $row) {
            $data[] = $row->{$col_name};
        }
        return $data;
    }

    /**
     * Create the hash key that will be used to store the query in cache.
     *
     * @param string The $sql statement
     * @param  array Parameters to be escaped and bound in the SQL using Kohana Database query method.
     * @return string A query hash string
     */
    public function queryHashKey($sql, $binds=NULL) {
	    if (is_array($binds)) {
            $cache_key = 'query_hash_' . md5($sql . implode('_', $binds));
	    } else {
            $cache_key = 'query_hash_' . md5($sql);
	    }
	    return $cache_key;
    }

}
