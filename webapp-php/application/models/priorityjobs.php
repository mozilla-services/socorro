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
        // Check for an existing UUID, and only insert if none found.
        $rv = $this->db->query('/* soc.web priojobs.seladd */ SELECT uuid FROM priorityjobs WHERE uuid=?', $uuid);
        if (!$rv->count()) {
            $rv = $this->db->query('/* soc.web priojobs.add */ INSERT INTO priorityjobs ( uuid ) VALUES (?)', $uuid);
        }
        return true;
    }

}
