<?php
require_once 'PHPUnit/Framework.php';
define('SYSPATH', '');
require_once dirname(__FILE__).'/../application/libraries/bugzilla.php';

  class BugzillaTest extends PHPUnit_Framework_TestCase
{
    public function testAllSorting() {
        $bugzilla = new Bugzilla();
	$bugInfos = array(
			  array('id' => '12345', 'resolution' => ''),
			  array('id' => '6789', 'resolution' => 'DUPLICATE'),
			  array('id' => '666', 'resolution' => 'FIXED'),
			  array('id' => '1101975', 'resolution' => 'INCOMPLETE'),
			  array('id' => '9876', 'resolution' => 'INVALID'),
			  array('id' => '6543', 'resolution' => 'WONTFIX'),
			  array('id' => '5432345', 'resolution' => 'WORKSFORME'));

	$bugzilla->sortByResolution($bugInfos);

	$this->assertEquals('',           $bugInfos[0]['resolution']); //still #0
        $this->assertEquals('WORKSFORME', $bugInfos[1]['resolution']); //was #6
	$this->assertEquals('WONTFIX',    $bugInfos[2]['resolution']); //was #5
	$this->assertEquals('DUPLICATE',  $bugInfos[3]['resolution']); //was #1
	$this->assertEquals('INVALID',    $bugInfos[4]['resolution']); //still #4
	$this->assertEquals('FIXED',      $bugInfos[5]['resolution']); //was #2
	$this->assertEquals('INCOMPLETE', $bugInfos[6]['resolution']); //was #3
    }

    public function testArraySort() {
      $this->assertEquals(2, array_search("", array('FOO', 'BAR', "", 'BAZ')));
      $this->assertEquals(2, array_search('', array('FOO', 'BAR', '', 'BAZ')));
    }

    public function testOpenSorting() {
        $bugzilla = new Bugzilla();
	$bugInfos = array(
			  array('id' => '481302', 'resolution' => 'FIXED'),
			  array('id' => '487271', 'resolution' => 'FIXED'),
			  array('id' => '495177', 'resolution' => ''));

	$bugzilla->sortByResolution($bugInfos);

	$this->assertEquals('',           $bugInfos[0]['resolution']); //was #2
	$this->assertEquals('495177',           $bugInfos[0]['id']); 
	$this->assertEquals('FIXED',      $bugInfos[1]['resolution']); //was #1
	$this->assertEquals('FIXED',      $bugInfos[2]['resolution']); //was #2
    }
}
?>