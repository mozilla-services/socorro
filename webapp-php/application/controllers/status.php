<?php
/**
 * This controller displays system status.
 */
class Status_Controller extends Controller {

    /**
     * Default status dashboard nagios can hit up for data.
     */
    public function index() {

        $db = Database::instance('default');

        $jobs_stats = $db->query(
            " SELECT max(jobs.completeddatetime) AS lastProcessedDate, " . 
            "        avg(jobs.completeddatetime - jobs.starteddatetime) AS avgProcessTime, " . 
            "        avg(jobs.completeddatetime - jobs.queueddatetime) AS avgWaitTime " .
            " FROM jobs " .
            " WHERE jobs.completeddatetime IS NOT NULL"
        );

        $jobs_count = $db->query(
            ' SELECT count(jobs.id) AS jobsPending ' . 
            ' FROM jobs ' . 
            ' WHERE jobs.completeddatetime IS NULL'
        );

        $proc_count = $db->query(
            ' SELECT count(processors.id) AS numProcessors ' . 
            ' FROM processors'
        );

        $old_jobs = $db->query(
            ' SELECT jobs.queueddatetime AS oldestQueuedJob '.
            ' FROM jobs ' . 
            ' WHERE jobs.completeddatetime IS NULL ' . 
            ' ORDER BY jobs.queueddatetime LIMIT 1 '
        );

        $this->setViewData(array(
            'lastProcessedDate' => $jobs_stats->current()->lastprocesseddate,
            'jobsPending'       => $jobs_count->current()->jobspending,
            'numProcessors'     => $proc_count->current()->numprocessors,
            'oldestQueuedJob'   => $old_jobs->current() ? $old_jobs->current()->oldestqueuedjob : 'None',
            'avgProcessTime'    => $jobs_stats->current()->avgprocesstime,
            'avgWaitTime'       => $jobs_stats->current()->avgwaittime
        ));

    }

}
