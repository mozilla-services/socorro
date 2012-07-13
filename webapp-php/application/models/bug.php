<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Bug Model responsible for the bug and bug_associations tables
 */
class Bug_Model extends Model
{
    /**
     * The Web Service class.
     */
    protected $service = null;

    public function __construct()
    {
        parent::__construct();

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }

        $this->service = new Web_Service($config);
    }

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
     * A template array for representing a bug.
     */
    public $defaultBug = array(
                             'signature' => "",
                             'id' => "",
                             'status' => " ",
                             'resolution' => "",
                             'summary' => "",
                             'open' => true,
                             'url' => "#"
                         );

    /**
     * Comparator function for sorting arrays of bugs by resolution
     */
    public function _sortByResolution($thisBug, $thatBug)
    {
        $thisPos = (is_array($thisBug['resolution'])) ? -1 : array_search(trim($thisBug['resolution']), $this->resolutionOrder);
        $thatPos = (is_array($thatBug['resolution'])) ? -1 : array_search(trim($thatBug['resolution']), $this->resolutionOrder);
        return $thisPos - $thatPos;
    }

   /**
    * Given a list of signatures, retrieves bug information associated with
    * these signatures and creates a signature to bugzilla bug associative
    * array suitable for display.
    *
    * @param array - A list of strings, each one being a crash signature
    * @param string - a URL to prepend for generating links to the bugtracker
    * @return array - an associative array of bug infos keyed by signature
    */
    public function bugsForSignatures($signatures, $bugzillaUrl)
    {
        $sigs = array();
        foreach ($signatures as $sig) {
            if (trim($sig) != '') {
                array_push($sigs, $sig);
            }
        }

        if (count($sigs) == 0) {
            return array();
        }

        $uri = Kohana::config('webserviceclient.socorro_hostname') . '/bugs/';
        $data = array('signatures' => implode('+', $sigs));
        $res = $this->service->post($uri, $data);
        if (!$res || !isset($res->total) || $res->total <= 0) {
            return array();
        }
        $rows = $res->hits;

        $signature_to_bugzilla = array();
        foreach ($rows as $row) {
            $row = (array) $row;
            if (!array_key_exists($row['signature'], $signature_to_bugzilla)) {
                $signature_to_bugzilla[$row['signature']] = array();
            }

            $row = array_merge($this->defaultBug, $row);
            $row['open'] = (array_key_exists($row['status'], $this->open_statuses)) ? true : false;
            $row['url'] = $bugzillaUrl . $row['id'];
            $row['summary'] = $row['summary'];

            array_push($signature_to_bugzilla[$row['signature']], $row);
        }

        foreach ($signature_to_bugzilla as $k => $v) {
            usort($signature_to_bugzilla[$k], array($this, '_sortByResolution'));
        }

        return $signature_to_bugzilla;
    }
}
