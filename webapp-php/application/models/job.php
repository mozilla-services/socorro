<?php
/**
 *
 */
class Job_Model extends Model {

    /**
     * Fetch a single job by UUID
     *
     * @param  string UUID by which to look up job
     * @return object job data
     */
    public function getByUUID($uuid) {

        $job = $this->db->query(
            '/* soc.web job.byuuid */ SELECT * FROM jobs WHERE uuid=?', $uuid
        )->current();

        if (!$job) return FALSE;

        return $job;
    }

}
