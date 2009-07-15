<?php
require_once 'PHPUnit/Framework.php';

define('SYSPATH', '');
require_once dirname(__FILE__).'/../system/core/Kohana.php';
require_once dirname(__FILE__).'/../application/libraries/release.php';

class ReleaseTest extends PHPUnit_Framework_TestCase
{
    public function testConvertProductToReleaseMap() 
    {
        $release = new Release;
        $this->assertEquals($release->typeOfRelease('3.5'), Release::MAJOR);

        $this->assertEquals($release->typeOfRelease('3.5b99'), Release::MILESTONE);

        $this->assertEquals($release->typeOfRelease('3.5a'), Release::MILESTONE);

        $this->assertEquals($release->typeOfRelease('3.6pre'), Release::DEVELOPMENT);
    }
}
?>