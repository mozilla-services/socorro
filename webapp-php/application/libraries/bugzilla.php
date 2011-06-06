<?php defined('SYSPATH') or die('No direct script access.');
/* ***** BEGIN LICENSE BLOCK *****
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
 *   Austin King <aking@mozilla.com> (Original Author)
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
 * ***** END LICENSE BLOCK ***** */
/**
 * Responsible for knowlege about how Bugzilla information relates to 
 * the Crash Reporting system.
 */
class Bugzilla{
    public $resolutionOrder = array('', 'WORKSFORME', 'WONTFIX', 'DUPLICATE', 'INVALID', 'FIXED', 'INCOMPLETE');

    /**
     * An array of all of the statuses that define an open bug,
     * hashed to provide a quick lookup.
     */
    public $open_statuses = array(
                                'UNCONFIRMED' => true,
                                'NEW' => true,
                                'ASSIGNED' => true,
                                'REOPENED' => true,
                                ' ' => true // default status
                            );

   /**
    * Given a list of arrays which contain Bug Infos
    * this method will sort into display order based
    * on the resolution field. This method changes the
    * array in-place.
    */
    public function sortByResolution(&$bugInfos)
    {
      usort($bugInfos, array($this, '_sortByResolution'));
    }

    public function _sortByResolution($thisBug, $thatBug)
    {
      $thisPos = (is_array($thisBug['resolution'])) ? false : array_search(trim($thisBug['resolution']), $this->resolutionOrder);
      $thatPos = (is_array($thatBug['resolution'])) ? false : array_search(trim($thatBug['resolution']), $this->resolutionOrder);
        if ($thisPos !== FALSE && $thatPos !== FALSE) {
	    return $thisPos > $thatPos;
	} elseif ($thisPos === FALSE and $thatPos == FALSE) {
	    return 0;
        } elseif ($thisPos === FALSE) {
	    return -1;
	} else {
  	    return 1;
	}
    }

    /**
     * Creates a signature to bugilla bug associative array suitable for display.
     * Supplemental fields are filled in from a Bugzilla API call.
     * Sorts the bugs by resolution.
     * @param array rows - array populated in the form Bug_Model returns
     * @return array - array with keys that are crash signatures and the value is a list of 
     *    bug infos
     */
    public function signature2bugzilla($rows, $bugzillaUrl)
    {
        $defaultBug = array(
                          'signature' => "",
                          'id' => "",
                          'status' => " ",
                          'resolution' => "",
                          'summary' => "",
                          'open' => true,
                          'url' => "#"
                      ); 
        
        $bug_hash = array(); // bug objects indexed by id
        foreach ($rows as $row) {
            $bug_hash[$row['id']] = array_merge($defaultBug, $row); 
        }
        
        $signature_to_bugzilla = array();        
        foreach ($bug_hash as $row) {
            if ( ! array_key_exists($row['signature'], $signature_to_bugzilla)) {
	        $signature_to_bugzilla[$row['signature']] = array();
	    }  
            
            $row['open'] = (array_key_exists($row['status'], $this->open_statuses)) ? true : false;
	    $row['url'] = $bugzillaUrl . $row['id'];
	    $row['summary'] = $row['summary'];
        
	    array_push($signature_to_bugzilla[$row['signature']], $row);
	}
	
        foreach ($signature_to_bugzilla as $k => $v) {
	    $this->sortByResolution($signature_to_bugzilla[$k]);	        
	}
        
        return $signature_to_bugzilla;
    }
}
?>
