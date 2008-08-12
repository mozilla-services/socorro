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
     * @return array   Set of rows returned
     */
    public function fetchRows($sql, $do_cache=TRUE) {

        if ($do_cache) {
            // Kind of dirty, but hashing the whole query seems to work.
            $cache_key = 'query_hash_' . md5($sql);
            $data = $this->cache->get($cache_key);
            if ($data) {
                log::log($data, "DB CACHE HIT $cache_key");
                return $data;
            }
        }

        // The DB abstraction works on iterators, so slurp it all down.
        $result = $this->db->query($sql);
        $data = array();
        foreach ($result as $row) $data[] = $row;

        if ($do_cache && $data) {
            log::log($data, "DB CACHE MISS $cache_key");
            $this->cache->set($cache_key, $data);
        }

        return $data;
    }

    /**
     *
     * @param  string SQL query
     * @return array
     */
    public function fetchSingleColumn($sql, $col_name) {
        $result = $this->db->query($sql);
        $data = array();
        foreach ($result as $row) {
            $data[] = $row->{$col_name};
        }
        return $data;
    }

}
