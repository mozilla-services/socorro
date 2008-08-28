<?php
/**
 * Management of data in the priorityjobs table.
 */
class Priorityjobs_Model extends Model {

    /**
     * Add a new priority job by UUID
     *
     * @param  string The UUID of the report in question
     * @return mixed  Result of the DB insert
     */
    public function add($uuid) {
        try {
            $rv = @$this->db->query('INSERT INTO priorityjobs ( uuid ) VALUES (?)', $uuid); 
        } catch (Kohana_Database_Exception $e) {
            // HACK: Trap and ignore a potential duplicate key error here, but 
            // raise any other errors.
            if (strpos( (string) $e, 'duplicate key' ) === FALSE ) throw $e;
        }
        return true;
    }

}
