<?php
require_once 'PHPUnit/Framework.php';
define('SYSPATH', '');
require_once dirname(__FILE__).'/../application/libraries/CrashReportDump.php';
/**
 * run via phpunit CrashReportModelTest.php
 */
class  CrashReportDumpTest extends PHPUnit_Framework_TestCase
{
    public function testCrashFilename() {
        $model = new CrashReportDump;
        $actual = $model->crashFilename('/data', 'cdaafc66-411d-11dd-b495-001321b13766');
	$this->assertEquals('/data/cd/aa/cdaafc66-411d-11dd-b495-001321b13766.jsonz', $actual);
    }

    public function testBadUUID() {
        $model = new CrashReportDump;
        $failed = FALSE;
        try {
	    $model->crashFilename('/data', '');
	    $failed = TRUE;
	} catch (Exception $e) {
  	    //no-op
	}
	if ($failed) {
	    $this->fail('We should throw on a bad UUID');
	}
    }
}
?>