<?php defined('SYSPATH') or die('No direct script access.');
//require_once dirname(__FILE__).'/../libraries/MY_CrashReportDump.php';

/**
 * Bugzilla Model responsible for the bug and bug_associations tables
 */
class Bug_Model extends Model {

   /**
    * Given a list of signatures, retrieves bug information
    * assoicated with these signatures. Example output
    * ( 'arena_dalloc_small' => ('bug_id' => 23423323, 'status' => 'RESOLVED', 'resolution' => 'FIXED') )
    * @param array - A list of strings, each one being a crash signature
    * @return array - an associative array of bug infos keyed by signature
    */
    public function bugsForSignatures($signatures)
    {
      Kohana::log('info', "proocessing " . Kohana::debug($signatures));
        return $report = $this->db->query(
"/* soc.web bugsForSigs */
SELECT ba.signature, bugs.id, bugs.status, bugs.resolution, bugs.short_desc FROM bugs
JOIN bug_associations AS ba ON bugs.id = ba.bug_id
WHERE EXISTS( 
    SELECT 1 FROM bug_associations
    WHERE bug_associations.bug_id = bugs.id AND 
          signature IN ('" . implode("', '", $signatures) . "'))", 
             TRUE)->result_array(FALSE);
    }
}
?>