<?php defined('SYSPATH') or die('No direct script access.');
class SearchReportHelper{
  function __construct() {
    $this->showWarning = FALSE;
  }

  function defaultParams(){
    return array('product'      => array(),
		 'branch'       => array(),
		 'version'      => array(),
		 'platform'     => array(),
		 
		 'query_search' => 'signature',
		 'query_type'   => 'contains',
		 'query'        => '',
		 'date'         => '',
		 'range_value'  => '1',
		 'range_unit'   => 'weeks',
		 
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
    
    if($productEmpty && $versionEmpty){
      $params['product'] = array('Firefox');
      $this->showWarning = TRUE;
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