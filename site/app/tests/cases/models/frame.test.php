<?php 
/* SVN FILE: $Id$ */
/* Frame Test cases generated on: 2008-07-30 17:07:19 : 1217463319*/
App::import('Model', 'Frame');

class TestFrame extends Frame {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class FrameTestCase extends CakeTestCase {
	var $Frame = null;
	var $fixtures = array('app.frame');

	function start() {
		parent::start();
		$this->Frame = new TestFrame();
	}

	function testFrameInstance() {
		$this->assertTrue(is_a($this->Frame, 'Frame'));
	}

	function testFrameFind() {
		$results = $this->Frame->recursive = -1;
		$results = $this->Frame->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Frame' => array(
			'report_id'  => 1,
			'frame_num'  => 1,
			'signature'  => 'Lorem ipsum dolor sit amet'
			));
		$this->assertEqual($results, $expected);
	}
}
?>