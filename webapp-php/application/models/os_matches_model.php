<?php defined('SYSPATH') or die('No direct script access.');

class OS_Match_Model extends Model {

    public function getData() {
        $result = $this->db->query("
            SELECT os_name as os_name,
                   match_string as pattern
            FROM os_name_matches");
        return $result;
    }

    public function add($os_family, $pattern) {
        try {
            $result = $this->db->query("
                INSERT INTO os_name_matches (os_name, match_string)
                VALUES (?, ?)",
                $os_family, $pattern);
        } catch (Exception $e) {
            Kohana::log('error',
                        'Could not add a record into the os_name_matches table in OS_Match_Model->add method\r\n'.$e->getMessage());
        }
    }

    public function delete($os_family, $pattern) {
        try {
            $result = $this->db->query("
                DELETE from os_name_matches
                WHERE os_name = ? AND
                      match_string = ?",
                $os_family, $pattern);
        } catch (Exception $e) {
            Kohana::log('error',
                        'Could not add a record into the os_names table in OS_Match_Model->delete method\r\n'.$e->getMessage());
        }
    }
}
