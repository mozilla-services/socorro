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
 * A helper for class for report queries.
 */
class SearchReportHelper{

    public function defaultParams(){
        return array('product' => array(),
            'branch'       => array(),
            'version'      => array(),
            'platform'     => array(),
            'build_id'     => '',
            
            'query_search' => 'signature',
            'query_type'   => 'exact',
            'query'        => '',
            'date'         => '',
            'range_value'  => '1',
            'range_unit'   => 'weeks',
            
            'hang_type'    => 'any',
            'process_type' => 'any',
            'plugin_field' => '',
            'plugin_query_type' => '',
            'plugin_query' => '',
            
            'do_query'     => FALSE
        );
    }

    /**
     * Normalizes the params for a search against the reports table.
     * This includes limiting the scope of the search by changing
     * the param values.
     * 
     * @param array An array of $_GET parameters
     */
    public function normalizeParams( &$params ){
        $params['query'] = urldecode($params['query']);
        $this->normalizeProduct($params);
        $this->normalizeDateUnitAndValue($params);
    }

    /**
     * Normalizes the range_value and range_unit parameters which 
     * handle date ranges for the query.
     * 
     * @bizrule Only a user considered an admin may perform a query with 
     *          a date range greater than 31 days.
     * @bizrule Admins must select a product in order to perform a query with
     *          a date range greater than 31 days.
     * @bizrule Queries may not be greater than 120 days in length; once
     *          we feel comfortable with performance this may be increased. 
     * @param array An array of $_GET parameters
     */
    public function normalizeDateUnitAndValue(&$params){
		$range_defaults = Kohana::config('application.query_range_defaults');
		$range_key = (isset($params['admin']) && $params['admin']) ? 'admin' : 'user';

		$range_default_value = $range_defaults[$range_key]['range_default_value'];
		$range_default_unit = $range_defaults[$range_key]['range_default_unit'];
		$range_limit_value_in_days = $range_defaults[$range_key]['range_limit_value_in_days'];

        $valueInDays = 0;
        if ($params['range_unit'] == 'hours') {
            $valueInDays = intval( $params['range_value'] ) / 24;
        } elseif ($params['range_unit'] == 'days') {
            $valueInDays = intval( $params['range_value'] );
        } elseif ($params['range_unit'] == 'weeks') {
            $valueInDays = intval( $params['range_value'] ) * 7;
        } elseif ($params['range_unit'] == 'months') {
            $valueInDays = intval( $params['range_value'] ) * 28; // low end of a month            
        } 

        if ($valueInDays <= 0) {
            $params['range_value'] = $range_default_value;
            $params['range_unit'] = $range_default_unit;
        }
        elseif (
            $valueInDays > $range_limit_value_in_days && 
            (!isset($params['admin']) || $params['admin'] === false)
        ) {
			$error_message = 'The maximum query date range you can perform is ' . $range_limit_value_in_days . ' days. Admins may log in to increase query date range limits.';
        } 
        elseif ($valueInDays > $range_limit_value_in_days && (isset($params['admin']) && $params['admin'] === true)) {
			$error_message = 'The maximum query date range you can perform is ' . $range_limit_value_in_days . ' days.';  
        }
		elseif (
            $valueInDays > $range_defaults['user']['range_limit_value_in_days'] && 
            $params['admin'] && 
            (!isset($params['product']) || (isset($params['product']) && empty($params['product'])))
        ) {
			$error_message = 'You must select a product in order to perform a query with a date range greater than ' . $range_defaults['user']['range_limit_value_in_days'] . ' days.';
		}

		if (isset($error_message) && !empty($error_message)) {
			$error_message .= ' Query results have been narrowed to the default range of ' . $range_default_value . ' ' . $range_default_unit . '.';
            $params['range_value'] = $range_default_value;
            $params['range_unit'] = $range_default_unit;
            client::messageSend($error_message, E_USER_WARNING);			
		}
    }

    /**
     * Normalizes the product, version and build_id values for the query.
     * 
     * @param array An array of $_GET parameters
     */
    public function normalizeProduct(&$params){
        $productEmpty = $this->empty_param($params['product']);
        $versionEmpty = $this->empty_param($params['version']);
        $buildIdEmpty = $this->empty_param($params['build_id']);

        if ($productEmpty && $versionEmpty && $buildIdEmpty) {
            $params['product'] = array();
        }
        if ($versionEmpty || (!$versionEmpty && $params['version'][0] == 'ALL:ALL')) {
            $params['version'] = array();
        }
    }
    
    /**
     * Handle empty parameters.
     * 
     * @param array An array of $_GET parameters
     */
    function empty_param($anArray){
        $arrayEmpty = FALSE;
        if(empty($anArray)){
            $arrayEmpty = TRUE;
        } else {
            if (is_null($anArray[0]) || empty($anArray[0])) {
                $arrayEmpty = TRUE;
            }
        }
        return $arrayEmpty;
    }

    /**
     * Returns a string YYYY-MM-DD for the current time.
     * Method mainly exists to decouple system time from 
     * code.
     *
     * @return string YYYY-MM-DD 
     */
    function currentDate(){
        if (isset($this->currentDateForTest)) {
            return $this->currentDateForTest;
        } else {
            return date('Y-m-d');
        }
    }

    /**
     * Sets the current date for testing purposes.
     */
    function setCurrentDateForTest($aDate){
         $this->currentDateForTest = $aDate;
    }

	/* */
}
