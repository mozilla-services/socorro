<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Custon model base class.
 */
class Model extends Model_Core {

	public function __construct() {
        parent::__construct();
	}

    /**
     * Fetch all rows resulting from a query, exhausting the iterator.
     *
     * @param  string SQL query to attempt
     * @return array  Set of rows returned
     */
    public function fetchRows($sql) {
        $result = $this->db->query($sql);
        $data = array();
        foreach ($result as $row) {
            $data[] = $row;
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
