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

  function __construct() {
    $this->showWarning = FALSE;
  }

  function defaultParams(){
    return array('product'      => array(),
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
   */
  function normalizeParams( &$params ){
    $this->showWarning = FALSE;
    $params['query'] = urldecode($params['query']);
    $this->normalizeDateUnitAndValue($params);
    $this->normalizeProduct($params);
  }

  function normalizeDateUnitAndValue(&$params){
    $valueInDays = 0;
    $limitValue = 0;
    $limitUnit = $params['range_unit'];
    if($params['range_unit'] == 'hours'){
      $valueInDays = intval( $params['range_value'] ) / 24;
      $limitValue = 14 * 24;
    }elseif($params['range_unit'] == 'days'){
      $valueInDays = intval( $params['range_value'] );
      $limitValue = 14;
    }elseif( $params['range_unit'] == 'weeks'){
      $valueInDays = intval( $params['range_value'] ) * 7;
      $limitValue = 2;
    }elseif($params['range_unit'] == 'months'){
                                                      //low end of a month
      $valueInDays = intval( $params['range_value'] ) * 28;
      $limitValue = 2;
      $limitUnit = 'weeks';
    }else{
      $params['range_value'] = 2;
      $params['range_unit'] = 'weeks';
    }

    if( $valueInDays > 31 ){
      $params['range_value'] = $limitValue;
      $params['range_unit'] = $limitUnit;
      $this->showWarning = TRUE;
    }
  }

  function normalizeProduct(&$params){
    $productEmpty = $this->empty_param($params['product']);
    $versionEmpty = $this->empty_param($params['version']);
    $buildIdEmpty = $this->empty_param($params['build_id']);
    
    if($productEmpty && $versionEmpty && $buildIdEmpty){
      $params['product'] = array();
      $this->showWarning = TRUE;
    }
    if (! $versionEmpty  && $params['version'][0] == 'ALL:ALL') {
      $params['version'] = array();
    }
  }

  function empty_param($anArray){
    $arrayEmpty = FALSE;
    if(empty($anArray)){
      $arrayEmpty = TRUE;
    } else {
      if( is_null($anArray[0] ) ||
	  empty($anArray[0] )){
	$arrayEmpty = TRUE;
      }
    }
    return $arrayEmpty;
  }

  /**
   * Returns a string YYYY-MM-DD for the current time.
   * Method mainly exists to decouple system time from 
   * code.
   */
  function currentDate(){
    if( isset($this->currentDateForTest) ){
      return $this->currentDateForTest;
    }else{
      return date('Y-m-d');
    }

  }
  function setCurrentDateForTest($aDate){
    $this->currentDateForTest = $aDate;
  }
  function shouldShowWarning(){
    return $this->showWarning;
  }
}
?>