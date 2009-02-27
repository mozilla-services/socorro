<?php

require_once 'PHPUnit/Framework.php';

define('SYSPATH', '');
require_once dirname(__FILE__).'/../system/core/Kohana.php';
require_once dirname(__FILE__).'/../application/libraries/MY_WidgetDataHelper.php';

/* Data holder simulates Mtbf_Model results */
class O {
    public function __construct($product, $release)
    {
        $this->product = $product;
        $this->release = $release;
    }
}
class T {
  public function __construct($product, $version, $enabled)
    {
        $this->product = $product;
        $this->version = $version;
        $this->enabled = $enabled;
    }
}
class SearchReportHelperTest extends PHPUnit_Framework_TestCase
{
    public function testConvertProductToReleaseMap() {
        $widget = new WidgetDataHelper;
	//Mtbf_Model->listReports style data
	$test = array(new O("Firefox", "major"), new O("Firefox", "development"), new O("Thunderbird", "milestone"));

	$expected = array("Firefox" => array("major", "development"),
			  "Thunderbird" => array("milestone"));
	$actual = $widget->convertProductToReleaseMap($test);

	$this->assertEquals($expected, $actual);
    }

    public function testFeaturedOrValid()
    {
        $widget = new WidgetDataHelper;
	$prodToReleaseMap = array("Firefox"     => array("major", "development"),
			          "Thunderbird" => array("milestone"));

        $featured = array(
                      array('product' => 'Firefox',     'release' => 'development'),
		      array('product' => 'Thunderbird', 'release' => 'milestone'));

	$this->assertEquals('development', $widget->featuredReleaseOrValid("Firefox", $prodToReleaseMap, $featured));
	$this->assertEquals('milestone', $widget->featuredReleaseOrValid("Thunderbird", $prodToReleaseMap, $featured));
	
    }

    public function testFeaturedOrValid_badConfig()
    {
        $widget = new WidgetDataHelper;
	$prodToReleaseMap = array("Firefox"     => array("major", "development"),
			          "Thunderbird" => array("milestone"));

        //given a bad config, log a warning and gimmie the first release
	$badFeatured = array(array('product' => 'Firefox', 'release' => 'huh'));
        $this->assertEquals('major', $widget->featuredReleaseOrValid("Firefox", $prodToReleaseMap, $badFeatured));
    }

    public function testConvertProductToVersionMap() {
        $widget = new WidgetDataHelper;
	//Mtbf_Model->listReports style data
	$test = array(new T("Firefox", "3.0.6", TRUE), new T("Firefox", "3.1b3pre", FALSE), new T("Thunderbird", "3.0b1", TRUE));

	$expected = array("Firefox" => array("3.0.6"),
			  "Thunderbird" => array("3.0b1"));
	$actual = $widget->convertProductToVersionMap($test);

	$this->assertEquals($expected, $actual);
    }

    public function testTCFeaturedOrValid()
    {
        $widget = new WidgetDataHelper;
	$prodToVersionMap = array("Firefox"     => array("3.0.6", "3.1b3pre"),
			          "Thunderbird" => array("3.0b1"));

        $featured = array(
                      array('product' => 'Firefox',     'version' => '3.0.6'),
		      array('product' => 'Thunderbird', 'version' => '3.0b1'));

	$this->assertEquals('3.0.6', $widget->featuredVersionOrValid("Firefox", $prodToVersionMap, $featured));
	$this->assertEquals('3.0b1', $widget->featuredVersionOrValid("Thunderbird", $prodToVersionMap, $featured));
	
    }

}
?>