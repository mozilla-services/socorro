<?php defined('SYSPATH') or die('No direct script access.');

class OS_Name_Model extends Model {

    public function getData() {
        return $this->db->query("
            SELECT os_name, os_short_name from os_names
        ");
    }

    public function add($os_name, $os_short_name) {
        try {
            $result = $this->db->query("
                INSERT INTO os_names (os_name, os_short_name)
                VALUES (?, ?)",
                $os_name, $os_short_name);
        } catch (Exception $e) {
            Kohana::log('error',
                        'Could not add a record into the os_names table in OS_Name_Model->add method\r\n'.$e->getMessage());
        }
    }

    public function delete($os_name, $os_short_name) {
        try {
            $result = $this->db->query("
                DELETE FROM os_names
                WHERE os_name = ? AND
                      os_short_name = ?",
                $os_name, $os_short_name);
        } catch (Exception $e) {
            Kohana::log('error',
                        'Could not add a record into the os_names table in OS_Name_Model->delete method\r\n'.$e->getMessage());
        }
    }
}
