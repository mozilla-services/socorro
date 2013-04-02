<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
            'query_type'   => 'contains',
            'query'        => '',
            'reason_type'  => 'contains',
            'reason'       => '',
            'date'         => '',
            'range_value'  => '1',
            'range_unit'   => 'weeks',

            'hang_type'    => 'any',
            'process_type' => 'any',
            'plugin_field' => '',
            'plugin_query_type' => '',
            'plugin_query' => '',

            'do_query'     => FALSE,

            '_force_api_impl' => ''
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

        if(isset($params['range_value'])) {
            $params['range_value'] = (int)$params['range_value'];
        }

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
        elseif ($valueInDays > $range_limit_value_in_days && !$params['admin']) {
			$error_message = 'The maximum query date range you can perform is ' . $range_limit_value_in_days . ' days. Admins may log in to increase query date range limits.';
        }
        elseif ($valueInDays > $range_limit_value_in_days && $params['admin']) {
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
        if (!$versionEmpty && $params['version'][0] == 'ALL:ALL') {
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
