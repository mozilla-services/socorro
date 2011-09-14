<?php defined('SYSPATH') or die('No direct script access.');
/* **** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Socorro Crash Reporter
 *
 * The Initial Developer of the Original Code is
 * The Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2006
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK *****
 *
 */


/**
 * Bug Model responsible for the bug and bug_associations tables
 */
class Bug_Model extends Model {

   /**
    * Given a list of signatures, retrieves bug information
    * associated with these signatures. Example output
    * ( 'arena_dalloc_small' => ('bug_id' => 23423323, 'status' => 'RESOLVED', 'resolution' => 'FIXED') )
    * @param array - A list of strings, each one being a crash signature
    * @return array - an associative array of bug infos keyed by signature
    */
    public function bugsForSignatures($signatures)
    {
        $sigs = array();
        foreach ($signatures as $sig) {
	    if (trim($sig) != '') {
	        array_push($sigs, $this->db->escape($sig));
	    }
        }
	if (count($sigs) == 0) {
	    return array();
	}

        return $report = $this->db->query(
"/* soc.web bugsForSigs */
SELECT ba.signature, bugs.id FROM bugs
JOIN bug_associations AS ba ON bugs.id = ba.bug_id
WHERE EXISTS(
    SELECT 1 FROM bug_associations
    WHERE bug_associations.bug_id = bugs.id AND
          signature IN (" . implode(", ", $sigs) . "))",
             TRUE)->result_array(FALSE);
    }
}
?>

