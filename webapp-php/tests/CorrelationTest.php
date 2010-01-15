<?php
require_once 'PHPUnit/Framework.php';
define('SYSPATH', '');
require_once dirname(__FILE__).'/../application/libraries/Correlation.php';

class Kohana
{
    public static function log($level, $msg)
    {
	echo $level . ":" . $msg;
    }
}

/**
 * run via phpunit CorrelationTest.php
 */
class  CorrelationTest extends PHPUnit_Framework_TestCase
{
    public function testCorrelationParseInterestingModules()
    {
	//$two_mb = 1024 * 1024 * 2; // 2MB

        $c = new Correlation;
	$data = $c->getGz('data/CorrolatedModules/20091216_Firefox_3.5.5-interesting-modules.txt.gz',
			  //8 * 1024 * 100); // 8K
			  1024 * 8); // 8KB

	#echo var_dump($data);
	$this->assertTrue(array_key_exists('Flash Player@0x92160', $data), 'Flash Crash Signature exists');
	$this->assertTrue(array_key_exists('Mac OS X', $data['Flash Player@0x92160']), 'Crash exists for Mac');
	$this->assertFalse(array_key_exists('Windows NT', $data['Flash Player@0x92160']), 'Crash does not exist for Windows NT');
	$this->assertEquals(62, count($data['Flash Player@0x92160']['Mac OS X']), 'We have 62 lines of correlation info');
	$this->assertEquals('82% (652/792) vs.  46% (8437/18276) AudioIPCPlugIn', 
			    $data['Flash Player@0x92160']['Mac OS X'][0], 
			    'First line is what we expect');
    }

    public function xtestCorrelationParseInterestingModulesAndVersions()
    {
        $c = new Correlation;
	$data = $c->getGz('data/CorrolatedModules/20091216_Firefox_3.5.5-interesting-modules-with-versions.txt.gz',
			  //8 * 1024 * 100); // 8K
			  1024 * 8); // 8KB

	echo var_dump($data);
	$this->assertTrue(array_key_exists('RtlEnterCriticalSection', $data), 'RtlEnterCriticalSection Crash Signature exists');
	$this->assertTrue(array_key_exists('Windows NT', $data['RtlEnterCriticalSection']), 'Crash exists for Windows NT');
	$this->assertEquals(144, count($data['RtlEnterCriticalSection']['Windows NT']), 'We have  lines of correlation info');
	$this->assertEquals('54% (840/1545) vs.  20% (21143/106275) sensapi.dll', 
			    $data['RtlEnterCriticalSection']['Windows NT'][0], 
			    'First line is what we expect');
    }

    public function testCorrelationParseInterestingAddons()
    {
	    //'data/CorrolatedModules/20091216_Firefox_3.5.5-interesting-addons-with-versions.txt.gz';
	    //'data/CorrolatedModules/20091216_Firefox_3.5.5-core-counts.txt.gz';

        $c = new Correlation;
	$data = $c->getGz('data/CorrolatedModules/20091216_Firefox_3.5.5-interesting-addons.txt.gz',
			  //8 * 1024 * 100); // 8K
			  1024 * 8); // 8KB


	$sig = 'UserCallWinProcCheckWow';
	$os = 'Windows NT';
	$this->assertTrue(array_key_exists($sig, $data), $sig . ' Crash Signature exists');
	$this->assertTrue(array_key_exists($os, $data[$sig]), 'Crash exists for ' . $os);
	$this->assertEquals(10, count($data[$sig][$os]), 'We have  lines of correlation info');
	$this->assertEquals('55% (819/1492) vs.  44% (46343/106275) {20a82645-c095-46ed-80e3-08825760534b} (Microsoft .NET Framework Assistant, http://www.windowsclient.net/)', 
			    $data[$sig][$os][0], 
			    'First line is what we expect');
    }

/*  
    //SLOW TEST: Uncomment to run this slow test. Useful for perf improvements or testing max file size flag 
    public function testCorrelationParseInterestingAddonsAndVersions()
    {
        $c = new Correlation;
	$data = $c->getGz('data/CorrolatedModules/20091216_Firefox_3.5.5-interesting-addons-with-versions.txt.gz',
			  //8 * 1024 * 100); // 8K
			  1024 * 8); // 8KB

	echo var_dump($data);
	$sig = 'UserCallWinProcCheckWow';
	$os = 'Windows NT';
	$this->assertTrue(array_key_exists($sig, $data), $sig . ' Crash Signature exists');
	$this->assertTrue(array_key_exists($os, $data[$sig]), 'Crash exists for ' . $os);
	$this->assertEquals(10, count($data[$sig][$os]), 'We have  lines of correlation info');
	$this->assertEquals('55% (819/1492) vs.  44% (46343/106275) {20a82645-c095-46ed-80e3-08825760534b} (Microsoft .NET Framework Assistant, http://www.windowsclient.net/)', 
			    $data[$sig][$os][0], 
			    'First line is what we expect');
			    }*/

    public function testCorrelationParseCoreCounts()
    {
        $c = new Correlation;
	$data = $c->getGz('data/CorrolatedModules/20091216_Firefox_3.5.5-core-counts.txt.gz',
			  1024 * 8);

	$sig = 'UserCallWinProcCheckWow';
	$os = 'Windows NT';
	$this->assertTrue(array_key_exists($sig, $data), $sig . ' Crash Signature exists');
	$this->assertTrue(array_key_exists($os, $data[$sig]), 'Crash exists for ' . $os);
	$this->assertEquals(7, count($data[$sig][$os]), 'We have  lines of correlation info');
	$this->assertEquals('0% (3/1492) vs.   1% (669/106275) x86 with 0 cores', 
			    $data[$sig][$os][0], 
			    'First line is what we expect');
    }


    public function testTxtCorrelationParseCoreCounts()
    {
        $c = new Correlation;
	$data = $c->getTxt('data/CorrolatedModules/20091216_Thunderbird_3.0b4-interesting-modules.txt',
			  1024 * 8);

	$sig = '__delayLoadHelper2';
	$os = 'Windows NT';
	$this->assertTrue(array_key_exists($sig, $data), $sig . ' Crash Signature exists');
	$this->assertTrue(array_key_exists($os, $data[$sig]), 'Crash exists for ' . $os);
	$this->assertEquals(46, count($data[$sig][$os]), 'We have  lines of correlation info');
	$this->assertEquals('100% (14/14) vs.  30% (15/50) AcGenral.dll', 
			    $data[$sig][$os][0], 
			    'First line is what we expect');
    }


    public function testParseSignature()
    {
	$c = new Correlation;
	$this->assertEquals($c->parseSignature('  TextRunWordCache::CacheHashEntry::KeyEquals(TextRunWordCache::CacheHashKey const*) const|EXC_BAD_ACCESS / KERN_PROTECTION_FAILURE (109 crashes)'),
					       'TextRunWordCache::CacheHashEntry::KeyEquals(TextRunWordCache::CacheHashKey const*) const',
					       'A single signature we grab it');

	$this->assertEquals($c->parseSignature('  objc_msgSend | HPSmartPrint@0xe1ef|EXC_BAD_ACCESS / KERN_INVALID_ADDRESS (89 crashes)'),
					       'HPSmartPrint@0xe1ef',
					       'A signature after a SkipList item');
    }
}
?>