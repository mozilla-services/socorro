<?php
require_once 'PHPUnit/Framework.php';
define('SYSPATH', '');

class Kohana
{
    public static function find_file($dir, $filename, $errorNotFound, $file_ext)
    {
	return dirname(__FILE__) . "/../application/${dir}/${filename}.${file_ext}";
    }

    public static function log($level, $msg)
    {
	echo $level . ":" . $msg;
    }
    public static function debug($thing)
    {
	echo $thing;
    }
}

require_once dirname(__FILE__).'/../application/libraries/CrashReportDump.php';

/**
 * run via phpunit CrashReportModelTest.php
 */
class  CrashReportDumpTest extends PHPUnit_Framework_TestCase
{
    /* TODO: Unit test was out of date with codebase.... revisit function in CrashReportDump and write unit tests */

    public function testCrashFilename() {
        $model = new CrashReportDump;
    }
}
?>