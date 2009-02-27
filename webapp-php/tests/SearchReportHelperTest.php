<?php
require_once 'PHPUnit/Framework.php';
define('SYSPATH', '');
require_once dirname(__FILE__).'/../application/libraries/MY_SearchReportHelper.php';

  class SearchReportHelperTest extends PHPUnit_Framework_TestCase
{
    public function testDefaultParams() {
        $helper = new SearchReportHelper();
	$default = $helper->defaultParams();

        $this->assertEquals('signature', $default['query_search']);
    }
 
    public function testNormalization() {
      $helper = new SearchReportHelper();
 
      $badSearch = array('product' => array(),
			 'branch' => array(),
			 'version' => array(),
			 'platform' => array(),
			 'query_search' => 'signature',
			 'query_type' => 'contains',
			 'query' => '',
			 'date' => '',
			 'range_value' => '12',
			 'range_unit' => 'weeks',
			 'do_query' => 1,
			 );
      $helper->normalizeParams( $badSearch );
      $this->assertEquals( 2, $badSearch['range_value'], "We limit the # of weeks");
      $this->assertEquals( 'weeks', $badSearch['range_unit'], "Unit unchanged from weeks");
      $this->assertEquals( array('Firefox'), $badSearch['product'], "A product of version must be selected");
    }

    /* Internal API */

    public function testDateUnitAndValue(){
      $helper = new SearchReportHelper();
 
      $badSearch = $helper->defaultParams(); /*array('range_value' => '12',
		    'range_unit' => 'weeks');*/
      $badSearch['range_value'] = 3;
      $badSearch['range_unit'] = 'months';
      $helper->normalizeDateUnitAndValue( $badSearch );
      $this->assertEquals( 'weeks', $badSearch['range_unit'], "Unit changed from months to weeks");
      $this->assertEquals( 2, $badSearch['range_value'], "We limit the # of weeks");

      $badSearch['range_value'] = 40;
      $badSearch['range_unit'] = 'days';
      $helper->normalizeDateUnitAndValue( $badSearch );
      $this->assertEquals( 'days', $badSearch['range_unit'], "Unit unchanged from days");
      $this->assertEquals( 14, $badSearch['range_value'], "We limit to 31 days");

      $badSearch['range_value'] = 2;
      $badSearch['range_unit'] = 'hours';
      $helper->normalizeDateUnitAndValue( $badSearch );
      $this->assertEquals( 'hours', $badSearch['range_unit'], "Unit unchanged from hours");
      $this->assertEquals( 2, $badSearch['range_value'], "No change");


      $badSearch['range_value'] = 33 * 24;
      $badSearch['range_unit'] = 'hours';
      $helper->normalizeDateUnitAndValue( $badSearch );
      $this->assertEquals( 'hours', $badSearch['range_unit'], "Unit unchanged from hours");
      $this->assertEquals( 336, $badSearch['range_value'], "Reduced to 14 days (in hours)");
    }

    public function testDateBug466233(){
      $helper = new SearchReportHelper();
      $helper->setCurrentDateForTest('2008-10-31');

      $badSearch = $helper->defaultParams(); 
      $badSearch['date'] = '2008-08-25';
      $badSearch['range_value'] = '2';
      $badSearch['range_unit'] = 'weeks';

      $helper->normalizeParams( $badSearch );
      $this->assertEquals('2008-08-25', $badSearch['date'], 
			  "Even though over a month ago, this date is fine. The date field specifieis the beginning of date range");
    }

    public function testMinimalProductInfoNoChange(){
      $helper = new SearchReportHelper();

      $badSearch = $helper->defaultParams(); 
      $badSearch['version'] = array('Firefox:3.0.4');

      $helper->normalizeProduct( $badSearch );
      $this->assertEquals(array(), $badSearch['product'], "product no normalization");
      $this->assertEquals(array('Firefox:3.0.4'), $badSearch['version'], "or version no normalization");
    }

    public function testNoProductInfo(){
      $helper = new SearchReportHelper();

      $badSearch = $helper->defaultParams(); 
      $badSearch['product'] = array('');
      $badSearch['version'] = array('');

      $helper->normalizeProduct( $badSearch );
      $this->assertEquals(array('Firefox'), $badSearch['product'], "product no normalization");
    }


    /* Testing the Testing */

    public function testCurrentDateOverride(){
      $helper = new SearchReportHelper();
      $this->assertEquals(date('Y-m-d'), $helper->currentDate(), "Normally the system should use current time");

      $helper->setCurrentDateForTest('1975-01-10');
      $this->assertEquals('1975-01-10', $helper->currentDate(), "For tests we can fake the time");
    }
}
?>