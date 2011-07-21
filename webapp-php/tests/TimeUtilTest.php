<?php
require_once 'PHPUnit/Framework.php';
defined('SYSPATH') or define('SYSPATH', '');
require_once dirname(__FILE__).'/../application/libraries/timeutil.php';

/**
 * run via phpunit TimeUtil.php
 */
class  TimeUtilTest extends PHPUnit_Framework_TestCase
{
    public function testCrashFilename() 
    {
        // 2009-11-30T20:38:51T+0000
        $b_time = 1259642331;
        $actual = date('o-m-d\TH:i:s\T+0000', TimeUtil::roundOffByMinutes(12, $b_time));
        $this->assertEquals('2009-11-30T20:36:00T+0000', $actual, "We round down to 36 minutes");

        // 2009-11-30T20:32:40T+0000
        $a_time = 1259641960; 
        $actual = date('o-m-d\TH:i:s\T+0000', TimeUtil::roundOffByMinutes(12, $a_time));
        $this->assertEquals('2009-11-30T20:36:00T+0000', $actual, "We round up to 36 minutes");
        
        // 2009-11-30T21:00:00T+0000
        $c_time = 1259643600;
        $actual = TimeUtil::roundOffByMinutes(12, $c_time);
        $this->assertEquals($c_time, $actual, "Exactly a 12 minute increment.. no changes 2009-11-30T21:00:41T+0000");

        // 2009-11-30T20:59:59T+0000
        $d_time = 1259643599;
        echo date('o-m-d\TH:i:s\T+0000', $c_time) . "\n";
        $actual = TimeUtil::roundOffByMinutes(12, $c_time);
        $this->assertEquals($d_time + 1, $actual, "Exactly 1 second under the 12 minute increment.. Should round up to 2009-11-30T21:00:41T+0000");
    }

    public function testTime_ago_in_words()
    {
        $this->assertEquals('59 seconds', TimeUtil::time_ago_in_words(59))
        $this->assertEquals('20.0 minutes', TimeUtil::time_ago_in_words(1200));
        $this->assertEquals('9.5 hours', TimeUtil::time_ago_in_words('34235'));
        $this->assertEquals('1.4 days', TimeUtil::time_ago_in_words(123456));
        $this->assertEquals('4.1 weeks', TimeUtil::time_ago_in_words(2507358));
    }
}
?>
