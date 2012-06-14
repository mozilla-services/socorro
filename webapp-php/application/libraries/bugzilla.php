<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
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
